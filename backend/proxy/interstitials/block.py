"""The Block interstitial — shown when AgentGuard hard-blocks a navigation.

The Warn page's terminal counterpart: same layout, red accent, no way through.
Generic on purpose — any block source renders it by passing a short `reason`
and, where there is one, the evaluation whose triggered rules get listed.
"""

from __future__ import annotations

import html
from string import Template
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit

from .evidence import format_score, js_string, risk_score_of, rules_list_html, triggered_rules
from .theme import stylesheet

_PALETTE = """
    --accent: #e1574c;
    --accent-soft: rgba(225, 87, 76, 0.15);
    --accent-line: rgba(225, 87, 76, 0.5);
    --rule-fg: #ffb4ad;
    --rule-chip: rgba(255, 180, 173, 0.15);
"""

_EXTRA_CSS = """
  .panel.danger { border-color: rgba(225, 87, 76, 0.45);
    background: linear-gradient(180deg, rgba(225, 87, 76, 0.08), var(--panel) 70%); }
  .rules-list li { border-left: 3px solid var(--accent); }
  .reason-text { font-size: 15px; color: #f1d8d5; margin: 4px 0 0; line-height: 1.5; }
  .alts-list { margin: 0; padding-left: 18px; color: #d9deea; line-height: 1.5; }
  .alts-list li { margin: 6px 0; }
"""

_NO_RULES_HTML = (
    '<p class="no-rules">'
    "AgentGuard blocked this page based on its overall risk profile."
    "</p>"
)


def _https_upgrade(url: str) -> Optional[str]:
    """The same URL over https, or None when it is not a plain-http URL."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() != "http":
        return None
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, parts.fragment))


def _safe_alternatives(original_url: str) -> List[str]:
    """Up to three next steps to offer instead of retrying the blocked URL.

    The wording stays generic on purpose: suggesting a specific replacement
    domain would be a recommendation AgentGuard cannot stand behind.
    """
    try:
        host = (urlsplit(original_url).hostname or "").lower().strip()
    except ValueError:
        host = ""

    suggestions: List[str] = []
    https_url = _https_upgrade(original_url)
    if https_url is not None:
        suggestions.append(f"Use an encrypted connection instead: {https_url}")

    if host:
        suggestions.append(
            f"Look up a different trusted website that offers the same service as {host}."
        )
        suggestions.append(
            "Search for a reputable alternative provider instead of retrying this domain."
        )
        suggestions.append("Choose a known-safe website that can accomplish the same task.")
    else:
        suggestions.append("Search for a different trusted website for your task.")
        suggestions.append("Look up trusted alternatives that accomplish the same goal.")
        suggestions.append("Choose a known-safe provider that can accomplish the same task.")
    return suggestions[:3]


def _why_blocked_html(evaluation: Optional[Dict[str, Any]], reason: str) -> str:
    """Triggered rules when the evaluation has them, else the caller's reason."""
    triggered = triggered_rules(evaluation)
    if triggered:
        return rules_list_html(triggered)
    if reason.strip():
        return f'<p class="reason-text">{html.escape(reason.strip())}</p>'
    return _NO_RULES_HTML


def build_block_html(
    *,
    original_url: str,
    reason: str,
    evaluation: Optional[Dict[str, Any]] = None,
    safe_back_url: str,
) -> bytes:
    alternatives = "".join(
        f"<li>{html.escape(item)}</li>" for item in _safe_alternatives(original_url)
    )
    return _TEMPLATE.substitute(
        style=stylesheet(palette=_PALETTE, extra_css=_EXTRA_CSS),
        safe_url=html.escape(original_url),
        score_text=format_score(risk_score_of(evaluation)),
        rules_block=_why_blocked_html(evaluation, reason),
        alternatives_block=f'<ul class="alts-list">{alternatives}</ul>',
        js_safe_back_url=js_string(safe_back_url),
    ).encode("utf-8")


_TEMPLATE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="x-ua-compatible" content="ie=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>AgentGuard — Page blocked</title>
<style>$style</style>
</head>
<body>
  <main class="wrap">
    <span class="badge">AgentGuard · Blocked</span>
    <h1>This page has been blocked.</h1>
    <p class="lead">AgentGuard refused to load the destination below.</p>

    <section class="panel danger">
      <div class="score">
        <span class="score-value">$score_text</span>
        <span class="score-label">overall risk (0 is safest, 1 is highest)</span>
      </div>
    </section>

    <section class="panel">
      <div class="section-label">Why this was blocked</div>
      $rules_block
    </section>

    <section class="panel">
      <div class="section-label">Destination</div>
      <div class="url">$safe_url</div>
    </section>

    <section class="panel">
      <div class="section-label">Safe alternatives</div>
      $alternatives_block
    </section>

    <div class="actions">
      <button class="btn-primary" type="button" onclick="goBack()">Go back to safety</button>
    </div>

    <p class="footer">
      AgentGuard blocks a page when it crosses a hard rule. Unlike a warning,
      there is no "continue anyway" option — adjust your rules or remove the
      destination from your custom blacklist if you believe this is wrong.
    </p>
  </main>
  <script>
    function goBack() {
      window.location.replace($js_safe_back_url);
    }
  </script>
</body>
</html>""")
