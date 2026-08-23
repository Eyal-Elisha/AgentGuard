# Offline tooling

Everything here runs outside the request path — nothing in `backend/` imports
any of it. This is where the numbers in `analysis/rules/tuning.py` came from,
and where you go to re-derive them.

| Script | Does |
|---|---|
| `load_phreshphish.py` | PhreshPhish parquet → `data/*.jsonl` |
| `split_by_domain.py` | split a JSONL into dev/test disjoint by registered domain |
| `eval_offline.py` | score a JSONL through the real rule engine → `runs/*.jsonl` |
| `eval_metrics.py` | precision/recall/AP/per-rule lift from a scored run |
| `calibrate_thresholds.py` | pick WARN and BLOCK from a scored dev split |
| `build_semantic_trainset.py` | PhreshPhish → the two CSVs Stage B trains on |
| `train_semantic_models.py` | fit and write the Stage B classifier pickles |
| `build_rule_features.py` | per-page rule-score vectors, for the meta-classifier |
| `train_meta_classifier.py` | meta-classifier vs weighted-average bake-off (reports only) |
| `fit_meta_classifier.py` | fit and **write** the deployed meta-classifier artifact |
| `try_domain.py` | what the URL-only rules say about one domain |
| `create_admin.py` | create or promote an admin user in the local DB |
| `launch_agent.py` | start a browser agent behind its own proxy port |

`create_admin.py` and `launch_agent.py` are the odd ones out — operational
helpers, not part of the eval pipeline.

## Launching an agent behind its proxy

A machine has one system proxy setting and `AllTraffic` already uses it, so a
named agent takes its endpoint on the command line instead. Turning one on from
the Guard screen already does this; the script is for doing it without the
dashboard, or for several agents at once. It starts each agent's proxy, opens
each browser through it, and stops the proxies it started once the browsers
close:

```bash
python scripts/launch_agent.py --agent BrowserOS MicrosoftEdge
```

A proxy already running, from the Guard screen or another terminal, is used as
it is and left running. `--keep-proxy` leaves one this script started running
too.

The port comes from `ports_for_agent`, the same allocation the backend and the
Guard screen report, so it cannot drift from the catalogue. Each launch gets a
profile directory of its own, because Chromium hands a new launch to an instance
that is already running and silently ignores the proxy flag;
`--use-main-profile` opts out, and then the browser has to be fully quit first.
`--browser-path` covers an install the script does not know about, and
`--dry-run` prints the command without running anything.

## What gets built

```
                    ┌──────────────────── evaluation ────────────────────┐
PhreshPhish   ──▶ data/*.jsonl ──▶ runs/*_scored.jsonl ──▶ metrics report
  (parquet)         │                        (eval_offline)  (eval_metrics)
                    │
                    ├──▶ semantic_train/*.csv ──▶ stage_b/data/*.pkl   (text classifiers)
                    │       (build_semantic_trainset)   (train_semantic_models)
                    │
                    └──▶ runs/*_feats.jsonl ──▶ meta_classifier.pkl    (stacking layer)
                            (build_rule_features)   (fit_meta_classifier)
```

Three trained artifacts come out of this, and all three are reproducible:

| Artifact | Built by | From |
|---|---|---|
| `stage_b/data/phishing.pkl` | `train_semantic_models.py` | PhreshPhish train split, domain-holdout applied |
| `stage_b/data/prompt_injection.pkl` | `train_semantic_models.py` | prompt-injection corpora + Dolly + PhreshPhish benign text |
| `analysis/data/meta_classifier.pkl` | `fit_meta_classifier.py` | rule features over the dev split |

`scikit-learn` is in `requirements.txt` (the runtime needs it to unpickle
these), but `datasets` and `pandas` are not — install them before training.
Stage B falls back to keyword heuristics when the artifacts are missing, so the
backend still runs without them.

## Determinism

Every step is seeded and order-independent:

- Dataset splitting hashes the **registered domain** (SHA-256, `split_by_domain.py`),
  so a given domain always lands on the same side regardless of input order.
- Both text classifiers use `train_test_split(..., random_state=42, stratify=...)`.
- The meta-classifier uses `GradientBoostingClassifier(random_state=42)` with a
  fixed benign weight and an alphabetically sorted feature order.

`fit_meta_classifier.py --verify-against` asserts a refit reproduces the shipped
artifact bit-for-bit; it currently passes at `max |Δp| = 7e-14`, i.e. floating
point noise.

---

## Step 1 — Get the data

```bash
python scripts/load_phreshphish.py --parquet-glob "data/phreshphish/data/test-*.parquet" --output data/phreshphish_test_30k.jsonl --limit 30000
```

Or stream from Hugging Face instead of downloading the parquet shards (slower):

```bash
python scripts/load_phreshphish.py --hf-split test --limit 30000 --output data/phreshphish_test_30k.jsonl
```

## Step 2 — Split by registered domain

Random splitting leaks: several rules read the domain, so a rule that memorises
`secure-login-24.tk` would look like a rule that learned something general.
Split by eTLD+1 instead, so no domain appears on both sides.

```bash
python scripts/split_by_domain.py --input data/phreshphish_test_30k.jsonl --dev data/dev.jsonl --test data/test.jsonl
```

The script asserts zero domain overlap and prints the label balance of each
side. Expected: dev 15,068 rows (7,700 phishing / 7,368 benign), test 14,932
rows (6,094 / 8,838).

Build the larger held-out set the same way from a disjoint slice of the test
split; this is `data/fresh.jsonl` (49,998 rows, 24,192 / 25,806), and it is the
set every headline number is reported on.

## Step 3 — Retrain the page-text classifier

Train on page text, not email text. The original classifiers were fitted on
email/SMS corpora and were near-random on webpages.
`build_semantic_trainset.py` runs PhreshPhish rows through the same
`FeatureExtractor` → `extract_semantic_text` path the classifier sees at
inference, and `--holdout-jsonl` drops every training page whose registered
domain appears in the evaluation sets.

```bash
python scripts/build_semantic_trainset.py --parquet-glob "data/phreshphish/data/train-*.parquet" --out-dir data/semantic_train --holdout-jsonl data/test.jsonl --workers 8
```

Expected: 208,750 rows kept (100,340 phishing / 108,410 benign) after dropping
279,572 of 498,255 training rows for domain overlap.

```bash
python scripts/train_semantic_models.py --rule phishing_language --benign-csv data/semantic_train/benign.csv --malicious-csv data/semantic_train/malicious.csv
```

TF-IDF (unigrams + bigrams, `min_df=2`, 50k features, sublinear term frequency)
into logistic regression (liblinear, `class_weight="balanced"`), fitted on an
80/20 stratified split with seed 42.

## Step 4 — Retrain the prompt-injection classifier

Its original negative class was instruction text only, so it treated ordinary
web pages as attacks. Pass real webpage text as additional benign examples:

```bash
AGENTGUARD_PI_WEB_BENIGN_CSV=data/semantic_train/benign.csv python scripts/train_semantic_models.py --rule prompt_injection
```

On PowerShell set the variable first:
`$env:AGENTGUARD_PI_WEB_BENIGN_CSV = "data/semantic_train/benign.csv"`.

## Step 5 — Build rule features and fit the meta-classifier

Score each dev page through the real rule engine and record what every rule
concluded. The meta-classifier never sees a page — only this vector of rule
scores. That is what makes it a stacking layer rather than another detector.

```bash
python scripts/build_rule_features.py --input data/dev.jsonl --output runs/dev_feats.jsonl --workers 8
python scripts/build_rule_features.py --input data/fresh.jsonl --output runs/fresh_feats.jsonl --workers 8
```

```bash
python scripts/fit_meta_classifier.py --train runs/dev_feats.jsonl --eval runs/fresh_feats.jsonl --output backend/analysis/data/meta_classifier.pkl
```

Benign rows are weighted x9 so the model reports probabilities as if phishing
were ~10% of traffic rather than the ~51% of the dev split. This is a
calibration choice, not a detection one: it changes what the number means, not
which pages outrank which, so ROC AUC is unaffected.

To check a refit against the shipped artifact without overwriting it:

```bash
python scripts/fit_meta_classifier.py --train runs/dev_feats.jsonl --dry-run --verify-against backend/analysis/data/meta_classifier.pkl
```

`train_meta_classifier.py` is the older bake-off script: it compares candidate
models and prints results, but writes no artifact. Use it to evaluate a change,
`fit_meta_classifier.py` to ship one.

## Step 6 — Evaluate

```bash
python scripts/eval_offline.py --input data/fresh.jsonl --output runs/fresh_scored.jsonl --workers 8 --progress-every 500
python scripts/eval_metrics.py --input runs/fresh_scored.jsonl --json runs/fresh.metrics.json
```

Reports average precision, ROC AUC, precision and FPR at recall 0.9, confusion
matrices at the production thresholds, and per-rule lift.

Expected on the held-out set: **ROC AUC 0.950, average precision 0.948**.

### Smoke test

```bash
python scripts/eval_offline.py --input data/smoke.jsonl --output runs/smoke.jsonl
python scripts/eval_metrics.py --input runs/smoke.jsonl
```

---

## Two deliberate differences from the live proxy

Both matter when reading any number this pipeline produces.

1. **Reputation lookups are off.** `domain_blacklist` queries PhishTank and
   URLhaus, which can take up to 3 s per uncached domain and, on a corpus of
   historical captures, would return *today's* feed contents rather than what
   was known when each page was live. Pass `--blacklist-network` to enable it.
   Because it is off by default, this pipeline makes no claim about how much
   reputation lookup contributes — it is not measured, not measured as zero.

2. **HTML parser.** The harness uses `lxml`; the proxy uses `html.parser`.
   Measured over 1,000 pages: the same rules fire on every page, the risk score
   differs on two, and one of those crosses a decision band. Small but not zero.
   Pass `--parser html.parser` to mirror production exactly.

## Reading the numbers honestly

1. **Don't quote accuracy.** At a realistic 1% phishing rate a detector that
   flags nothing scores 99%. Use average precision, recall, and precision
   converted to a realistic base rate.
2. **Convert precision to the deployment base rate.** These corpora are ~50%
   phishing; real traffic is ~1% or less. Precision on the corpus (0.99) is not
   deployment precision (0.74 at the Block threshold). The conversion is
   `precision = πR / (πR + (1−π)F)` for base rate π, recall R, false-positive
   rate F.
3. **Thresholds don't transfer.** The Block threshold giving 0.10% false
   positives on PhreshPhish gives 0.61% on an independent corpus. Re-tune per
   deployment.
4. **Six of the seventeen rules are unmeasured here.** The four session-aware
   rules need a session, which this harness never builds; the two blacklist
   rules are disabled per above. No conclusion rests on any of them.
