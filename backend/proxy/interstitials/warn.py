"""The Warn interstitial — shown when a navigation is flagged but not blocked.

The page lists the rules that triggered and offers two ways out:

  * "Go back to safety" navigates to the AgentGuard dashboard.
  * "Continue anyway" is a plain link to `originalUrl?_agentguard_bypass=<token>`.
    The proxy validates and consumes the token, registers a short-lived
    continue profile for that navigation (see `warn_bypass.py`), and
    302-redirects to the clean URL so the token never lingers in the address bar.

The bypass is entirely server-side — no cookies, no client state — which is
what makes it survive the HTTPS-via-MITM setup the proxy runs in.
"""

from __future__ import annotations

import html
from string import Template
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.proxy.warn_bypass import BYPASS_QUERY_PARAM

from .evidence import format_score, js_string, rules_list_html, triggered_rules
from .theme import stylesheet

_PALETTE = """
    --accent: #f5a524;
    --accent-soft: rgba(245, 165, 36, 0.15);
    --accent-line: rgba(245, 165, 36, 0.45);
    --rule-fg: #ffd483;
    --rule-chip: rgba(255, 212, 131, 0.15);
"""

_EXTRA_CSS = """
  .btn-secondary { background: transparent; color: var(--text);
    border-color: #4a5060; }
  .footer code { background: var(--panel-2); padding: 2px 6px; border-radius: 4px; }
"""

_NO_RULES_HTML = (
    '<p class="no-rules">'
    "AgentGuard flagged this page based on its overall risk profile."
    "</p>"
)


def append_bypass_param(url: str, token: str) -> str:
    """Return `url` with the bypass token in its query string.

    Any bypass param already present is replaced, so a stale token in the
    original URL cannot survive into the "Continue anyway" link.
    """
    parts = urlsplit(url)
    pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key != BYPASS_QUERY_PARAM
    ]
    pairs.append((BYPASS_QUERY_PARAM, token))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(pairs, doseq=True), parts.fragment)
    )


def build_warn_html(
    *,
    original_url: str,
    bypass_token: str,
    risk_score: Optional[float],
    evaluation: Optional[Dict[str, Any]],
    safe_back_url: str,
) -> bytes:
    triggered = triggered_rules(evaluation)
    return _TEMPLATE.substitute(
        style=stylesheet(palette=_PALETTE, extra_css=_EXTRA_CSS),
        safe_url=html.escape(original_url),
        continue_url=html.escape(append_bypass_param(original_url, bypass_token)),
        score_text=format_score(risk_score),
        rules_block=rules_list_html(triggered) if triggered else _NO_RULES_HTML,
        js_safe_back_url=js_string(safe_back_url),
    ).encode("utf-8")


_TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="x-ua-compatible" content="ie=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>AgentGuard — Suspicious page</title>
<style>$style</style>
</head>
<body>
  <main class="wrap">
    <span class="badge">AgentGuard · Warn</span>
    <h1>This page looks suspicious.</h1>
    <p class="lead">AgentGuard flagged the destination below. Continue only if you trust this site.</p>

    <section class="panel">
      <div class="score">
        <span class="score-value">$score_text</span>
        <span class="score-label">overall risk (0 is safest, 1 is highest)</span>
      </div>
    </section>

    <section class="panel">
      <div class="section-label">Why we flagged it</div>
      $rules_block
    </section>

    <section class="panel">
      <div class="section-label">Destination</div>
      <div class="url">$safe_url</div>
    </section>

    <div class="actions">
      <button class="btn-primary" type="button" onclick="goBack()">Go back to safety</button>
      <a class="btn btn-secondary" href="$continue_url" rel="nofollow noreferrer">Continue anyway</a>
    </div>

    <p class="footer">
      Clicking <strong>Continue anyway</strong> lets this one page load without
      getting stuck in a warning loop. AgentGuard still analyzes and logs your
      browsing; the next risky page or action on this site can warn again.
    </p>
  </main>
  <script>
    function goBack() {
      window.location.replace($js_safe_back_url);
    }
  </script>
</body>
</html>""")
