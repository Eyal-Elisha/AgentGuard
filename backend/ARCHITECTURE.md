# AgentGuard backend — how it fits together

A map from *what happens* to *where it lives*. For how to install and run
things, see the repository `README.md`.

## The shape of the system

AgentGuard is an HTTPS-intercepting proxy sitting between a browser-based AI
agent and the web, plus a local backend that decides whether each request is
safe.

```
  agent's browser
        |
        v
  mitmweb + backend/proxy/          intercepts, filters, enforces
        |
        |  POST /api/proxy/decision   (proxy blocks on this call)
        v
  Flask app, backend/routes/        validates, evaluates, records
        |
        v
  SQLite, backend/storage/          sessions, events, per-rule analyses
        ^
        |  read
  React dashboard, frontend/
```

Processes, started separately — one backend, and one proxy per protected
agent:

| Process | Started by | Entry point |
|---|---|---|
| Backend API | `python -m backend.app` | `backend/app.py` → `create_app()` in `backend/__init__.py` |
| Proxy | `python proxy_launcher.py --agent NAME` | mitmweb loading `backend/proxy/traffic_interception.py` |

The dashboard can also start and stop each proxy, through
`backend/routes/proxy_control.py`, which drives the same launcher. See
[Running several agents at once](#running-several-agents-at-once).

## The path of one request

### 1. In the proxy — `backend/proxy/`

`traffic_interception.py` is the mitmproxy addon script. It forwards each hook
to `addon.py`, which is where the whole request path is visible in one place.

**Connection level.** `connection_block.py` can kill a connection at
`tcp_start`, before any HTTP exists, when the host is on the custom blacklist.

**Triage — `filter_requests.py:should_forward`.** Analysing everything is
unaffordable and would bury the operator in noise, so most flows never reach
the backend. In order:

1. A custom-blacklist hit is forwarded only if it is high-signal enough to be
   worth an audit record — a top-level navigation or a meaningful action.
   Everything else the addon blocks locally without calling the backend.
2. Traffic to AgentGuard's own dashboard and API on loopback is skipped.
3. Browser prefetch and prerender (`Sec-Purpose`) is skipped.
4. Non-browser user agents are skipped.
5. Methods outside `ALLOWED_PROXY_METHODS` are skipped.
6. `filters/relevance/` drops static sub-resources, background services and
   telemetry.
7. Top-level navigations always pass.
8. Anything left must survive the EasyPrivacy noise lists in `filters/noise/`.

Step 8 is narrower than it looks. Steps 6 and 7 between them settle every GET —
either it is a sub-resource and dropped, or it is a navigation and passed — so
`is_noise` is only ever reached on a POST. Tracking GETs are dropped by
`filters/relevance/telemetry.py`, not by the EasyPrivacy lists.

**Prompt augmentation — `prompting/`.** For JSON request bodies, a fallback
instruction is appended to the agent's prompt fields telling it to find a
trusted alternative site rather than retrying a blocked one. This mutates the
agent's own outbound request, not the page it is reading.

**Bypass redemption — `warn_bypass/`.** A valid one-shot
`?_agentguard_bypass=` token yields a 302 to the clean URL and registers a
short-lived continue profile, so clicking "Continue anyway" does not land the
browser in a warning loop. The backend is still consulted on every request;
only the interstitial is suppressed.

**The decision — `decision_client.py`.** POSTs the request to
`/api/proxy/decision` and maps the reply, or a timeout, onto a
`BackendDecision` (`enforcement/decision.py`).

**Enforcement — `enforcement/`.** Allow passes through. Block returns the HTML
interstitial for GET navigations and a plain 403 otherwise. Warn serves the
interstitial with a "Continue anyway" link, or rewrites the response body at
response time. If the backend could not be reached, the proxy fails **closed**
by default (503) — see `AGENTGUARD_BACKEND_FAILURE_MODE`. A cached
passive-mode flag keeps a passive session from suddenly hard-blocking
everything when the backend goes away.

### 2. In the backend — `backend/routes/proxy.py`

`POST /api/proxy/decision` is restricted to loopback and RFC1918 clients by
`routes/guards.py`. It validates the envelope (`validation/proxy_requests.py`),
parses the optional fields (`validation/proxy_decision.py`), attributes the
request to a session, evaluates it, and records the result.

### 3. The rule engine — `backend/analysis/`

`proxy/rule_engine.py:evaluate_http_payload` is the orchestrator:

1. `feature_extraction/` parses the HTML once into an `ExtractedFeatures`
   snapshot — every rule reads from it rather than re-parsing.
2. `stages/stage_a/session_loader.py` loads prior events for the session.
3. Rule enablement is read from the `rules` table.
4. **Stage A** (`stages/stage_a/evaluator.py`) runs the cheap rules.
5. **Stage B** (`stages/stage_b/`) runs the semantic classifiers, if either
   Stage A asked for it or the meta-classifier is in play.
6. `analysis/scoring/` turns the rule results into a score and a decision.

**Stage A, in order.** The twelve deterministic rules
(`stage_a/deterministic_rules.py`) run first. A triggered *hard-block* rule
short-circuits: the remaining rules are recorded with NULL scores and the risk
score is forced to 1.0. Only two rules still hard-block — `domain_blacklist`
and `custom_blacklist`. `unencrypted_connection` and `typosquatting` used to,
and were demoted because each blocked more benign pages than phishing ones.

Otherwise the deterministic score is aggregated and the four contextual rules
(`stage_a/contextual_rules.py`) run if that score is in
`[AMBIGUOUS_LOW, HIGH_RISK_THRESHOLD)`. Contextual rules return `None` when
their preconditions are not met, which excludes them from aggregation rather
than diluting it.

> **The contextual rules currently never run.** That band is
> `[0.15, 0.12)` — empty — because the recalibration lowered
> `HIGH_RISK_THRESHOLD` to 0.12 without moving `AMBIGUOUS_LOW`. Nothing
> crashes; the four rules are simply always skipped, and are recorded with
> NULL scores like any other rule that did not run. Left as calibrated rather
> than quietly retuned, since picking a new band is a calibration decision.

**Stage B.** Two semantic rules, `phishing_language` and `prompt_injection`,
TF-IDF plus logistic regression, both retrained on webpage HTML — the shipped
models were originally fit on email and SMS corpora and were near-random on
pages. Text is drawn from the title, visible text and form tokens, and PII and
secrets are redacted (`stage_b/sanitization.py`) **before** anything reaches
the classifier or the log. `scikit-learn` is required to unpickle the models;
without it each rule falls back to a keyword heuristic
(`stage_b/heuristics.py`), so the pipeline still works on a bare install.

**Aggregation — `analysis/scoring/`.** Two strategies answer the same
question, and which one runs depends on whether a trained artifact loaded.

*`weighted_average.py`* is the default and the one to understand first. Risk is
a weighted **average** over the rules that actually ran, not a weighted sum.
That is the single most consequential detail in the engine — averaging
compresses scores toward zero, which is why `BLOCK` is 0.12 and `WARN` 0.04
rather than anything near the middle of `[0, 1]`, and why adding an
always-executed rule pushes every score down by enlarging the denominator.

*`meta_classifier.py`* is a model trained on the rule scores themselves, so it
can read combinations the fixed weights cannot. `scripts/fit_meta_classifier.py`
rebuilds the artifact and has a `--verify-against` mode that refits and asserts
it reproduces the deployed one. It runs whenever
`analysis/data/meta_classifier.pkl` loads, and then it — not the average —
decides, against its own thresholds (`META_WARN_THRESHOLD` 0.50,
`META_HIGH_RISK_THRESHOLD` 0.80). Its raw output is rescaled onto those round
numbers by a monotonic transform, so the rescaling changes no decision. When
the artifact is absent, `score()` returns `None` and the average takes over.

Note the consequence: **which thresholds apply depends on whether that pickle
loaded.** A bare install decides at 0.04/0.12 on the weighted average; a full
install decides at 0.50/0.80 on the model.

*`floors.py`* runs last and can only make a decision stricter. Both strategies
reduce every rule to one number, so a rule can influence the outcome only in
proportion to how much the scorer weighs it. That is right by default and wrong
for one case: a rule detecting a threat class the scorer was never trained to
predict. The meta-classifier learns from phishing labels, so it discounts
prompt injection, and a page carrying a live payload scored 0.28 while the
injection rule itself read 0.94. `DECISION_FLOORS` in `tuning.py` names the
rules allowed to force a minimum decision on their own; `apply_decision_floors`
raises the decision without touching the risk score, because the score reports
what the model believes and the decision is what we do about it.

All the calibrated numbers live in `analysis/rules/tuning.py`.

### Parsing

Every analysed request is parsed twice, once to extract features and once to
strip script and style before Stage B vectorises the text, so the parser is a
measurable share of the latency the agent waits on. `feature_extraction/
html_parser.py` selects it once and both call sites import the constant, so they
cannot drift apart. `lxml` is used when installed and `html.parser` otherwise.

The two are close but not identical: over 1,000 captured pages the same rules
fired on every page, the risk score differed on two, and one of those crossed a
decision band. Measured interleaved in one process, `lxml` cuts median analysis
from 43.6 ms to 40.8 ms and the 95th percentile from 365.8 ms to 308.6 ms.

### 4. Recording — `backend/proxy/audit/`

One event row, one `rules_analysis` row per rule — including the rules that
never ran, which keep a NULL score so a stored event stays replayable. A line
also goes to the encrypted append-only journal.

## Running several agents at once

AgentGuard protects any agent that honours system proxy settings, and several
at the same time, each behind its own proxy instance. Everything below
`proxy/launcher/` is keyed by agent: the registry, the two allocated ports,
the environment label and the log file — a shared log written by two
instances interleaves into something unreadable. `start`, `stop` and `status`
each take an agent and address the matching entry, and the stop path resolves
its port fallback against the port allocated to the agent being stopped, so
stopping one agent leaves the others running.

The agent's identity reaches the proxy as `AGENTGUARD_PROXY_AGENT_NAME` at
spawn time, so every decision the instance reports is attributed without the
request having to say so. Sessions are already unique per `(agent, environment)`.

Ports are allocated deterministically rather than dynamically, because nothing
hands the endpoint to the agent — the operator types it into the agent's own
network settings by hand. `proxy/ports.py` derives both from the agent's
position in `AGENT_CATALOGUE` (`proxy/audit/agents.py`), which is why appending
to that tuple is safe and reordering it moves endpoints already configured.
Only a catalogue member has an allocation, so only a catalogue member can be
started; any other name can still be *recorded* against a decision.

| Instance | Interception port | Administrative port |
|---|---|---|
| `AllTraffic`, the default | 8080, unchanged | 8180 |
| `BrowserOS` | 8081 | 8181 |
| `MicrosoftEdge` | 8082 | 8182 |
| The *n*th agent in catalogue order | `PROXY_PORT` + *n* | `PROXY_WEB_PORT` + *n* |

`AllTraffic` is first because it is the default and the general case: it is
not tied to a named agent but intercepts whatever is pointed at it, which is
what the system proxy does. Keeping it on 8080 means the endpoint
already configured on a machine keeps working. Note that this differs from
Table 3.5 in the project book, which has `BrowserOS` on 8080 and no catch-all
entry.

The two ranges come from separate bases because mitmweb serves its own
administrative interface on the port immediately above its interception port:
allocated from one base, the second agent's interception port would land on the
first agent's administrative port. `ports.py` falls back to the defaults if the
configured bases are close enough to recreate that collision.

All instances share one certificate authority — mitmproxy's default confdir —
so the operator installs a single certificate. Two limitations remain: every
instance calls the one backend, so agents share its analysis capacity and
passive mode is system-wide rather than per agent; and per-agent resource
attribution is not reported.

## Where things live

| Package | Holds |
|---|---|
| `analysis/rules/` | `models` (types), `tuning` (every calibrated number), `catalog` (the 18 rules) |
| `analysis/scoring/` | `weighted_average` and `meta_classifier` — the two ways to go from rule results to a decision — and `floors`, which can only make one stricter |
| `analysis/stages/stage_a/` | deterministic and contextual rules, their data and helpers |
| `analysis/stages/stage_b/` | semantic classifiers, text sanitization, heuristic fallback |
| `feature_extraction/` | HTML → `ExtractedFeatures`; `html_parser` picks the BeautifulSoup backend once for both call sites |
| `proxy/` | the mitmproxy addon and everything it calls |
| `proxy/filters/` | one yes/no question per module, composed by `filter_requests.py` |
| `proxy/enforcement/` | `decision` (the verdict), `reasons` (the text), `responses` (the HTTP) |
| `proxy/interstitials/` | the Warn and Block pages, their shared evidence rendering and theme |
| `proxy/warn_bypass/` | `tokens` (one-shot links) and `continue_profile` (what redeeming one allows) |
| `proxy/audit/` | `journal`, `agents` (the ordered catalogue), `sessions`, `decisions` |
| `proxy/ports.py` | Which two ports each agent's instance owns |
| `proxy/launcher/` | `command` (argv and log), `termination` (stopping a tree), `registry` (what is running) |
| `routes/` | HTTP API; `guards.py` holds the local-client guard |
| `validation/` | one module per request family; nothing else validates input |
| `storage/` | SQLite; `schema.py` owns the DDL, one store module per table |
| `settings/` | every setting, from one `backend/.env`: `env`, `network`, `runtime`, `credentials` |
| `auth.py`, `log_encryption.py`, `audit_logging.py` | Argon2 + JWT, Fernet at rest, the audit logger |

## Data model

Five tables, created in `storage/schema.py`:

- **users** — Argon2 hash, admin flag.
- **sessions** — one run of the proxy for one agent in one environment. At most
  one open per `(agent_name, environment)`; starting a new one closes what it
  supersedes.
- **events** — one per decision, with the URL, method, headers, guard action
  and risk score.
- **rules** — the catalogue, seeded from `analysis/rules/catalog.py` at startup.
  Seeding does not update rows that already exist, so a weight changed in code
  will not overwrite one already in the database.
- **rules_analysis** — one row per rule per event, `rule_score` NULL when the
  rule did not run.

URLs, headers, risk scores and rule details are encrypted at rest with Fernet
(`log_encryption.py`), keyed by `AGENTGUARD_LOG_ENCRYPTION_KEY`. WAL is on so
dashboard reads coexist with proxy writes.

## Things worth knowing before you change something

- **`REQUIRE_AUTH` defaults to off** when unset. Convenient in development,
  and worth saying out loud rather than discovering.
- **`sensitive_fields` is disabled in code**, via `CODE_DISABLED_RULES` in
  `analysis/rules/tuning.py`. It fired on more benign than phishing pages. The
  database toggle cannot re-enable it.
- **The thresholds are low on purpose.** See aggregation above before
  "fixing" them.
- **The contextual rules never execute.** See the gate above.
- **A page can warn with no rule triggered.** Stage B probabilities below their
  `trigger_threshold` are not "triggered", but they still enter the weighted
  average, and `WARN` is 0.04. The interstitial then has no evidence to show.
  `data/smoke.jsonl`'s benign row does exactly this.
- **`rule_engine.py` lives in `proxy/` but is backend code.** It is the
  evaluation orchestrator called from `routes/proxy.py`; the proxy process
  imports it only for `get_custom_blacklist`.
- **Stage B decides for itself whether a rule triggered**, using each rule's
  `trigger_threshold` — 0.85 for `prompt_injection`, because the public
  injection corpora outnumber benign instructions roughly 25:1 and the model
  is correspondingly over-confident.
- **No LLM is called anywhere.** The planned LLM-adjudication stage was never
  built.

## Tests

```bash
python -m pytest -q
```

`tests/backend/` mirrors the package layout. Tests marked `integration` make
real network requests and are deselected by default (see `pytest.ini`).

Note that the proxy tests need `mitmproxy`, so run them from the virtualenv
that has `requirements.txt` installed, not a bare system Python.
