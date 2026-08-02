"""Render the Block interstitial page shown when AgentGuard hard-blocks a
navigation.

This mirrors `warn_interstitial.py` but with a red, "this page has been
blocked" styling and no "Continue anyway" path — a block is terminal.
The page is intentionally generic: pass in a short `reason` string
(e.g. "URL matches the custom local blacklist") and, optionally, the
backend evaluation so triggered rules can be listed.

Use cases:
  * Custom blacklist hits (proxy-side block).
  * Backend deterministic / contextual / semantic block decisions.
  * Any future hard-block source — just pass a reason.
"""

from __future__ import annotations

import html
import json
from urllib.parse import urlsplit, urlunsplit
from typing import Any, Dict, List, Optional


def _rule_kind_label(rule_type: str) -> str:
    t = (rule_type or "").lower().strip()
    if t == "deterministic":
        return "Deterministic"
    if t == "contextual":
        return "Contextual"
    if t == "semantic":
        return "Semantic"
    return t.title() or "Rule"


def _coerce_rule_results(evaluation: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(evaluation, dict):
        return []
    rules = evaluation.get("rule_results")
    if not isinstance(rules, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in rules:
        if isinstance(item, dict) and item.get("triggered"):
            out.append(item)
    return out


def _format_rule_row(rule: Dict[str, Any]) -> str:
    rule_id = html.escape(str(rule.get("rule_id", "")))
    kind = html.escape(_rule_kind_label(str(rule.get("rule_type", ""))))
    explanation = html.escape(str(rule.get("explanation", "")))
    score = rule.get("score")
    score_text = f"{float(score):.2f}" if isinstance(score, (int, float)) else "—"
    return (
        "<li>"
        f"<div class=\"rule-row\">"
        f"<span class=\"rule-id\">{rule_id}</span>"
        f"<span class=\"rule-type\">{kind}</span>"
        f"<span class=\"rule-score\">how strong: {score_text}</span>"
        "</div>"
        f"<div class=\"rule-explanation\">{explanation}</div>"
        "</li>"
    )


def _https_upgrade(url: str) -> str | None:
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme.lower() != "http":
        return None
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, parts.fragment))


def _safe_alternatives(original_url: str) -> List[str]:
    out: List[str] = []
    try:
        host = (urlsplit(original_url).hostname or "").lower().strip()
    except ValueError:
        host = ""

    https_url = _https_upgrade(original_url)
    if https_url is not None:
        out.append(f"Use an encrypted connection instead: {https_url}")

    if host:
        out.append(f"Look up a different trusted website that offers the same service as {host}.")
        out.append("Search for a reputable alternative provider instead of retrying this domain.")
        out.append("Choose a known-safe website that can accomplish the same task.")
    else:
        out.append("Search for a different trusted website for your task.")
        out.append("Look up trusted alternatives that accomplish the same goal.")
        out.append("Choose a known-safe provider that can accomplish the same task.")
    return out[:3]


def build_block_html(
    *,
    original_url: str,
    reason: str,
    evaluation: Optional[Dict[str, Any]] = None,
    safe_back_url: str,
) -> bytes:
    """Render the block interstitial.

    `reason` is shown verbatim (escaped) under "Why this was blocked" when
    no triggered rules are available in `evaluation`. When the evaluation
    carries triggered rule rows, those are shown instead — `reason` still
    appears as a one-line headline summary.
    """
    safe_url = html.escape(original_url)
    safe_reason = html.escape(reason.strip()) if reason else ""

    risk_score: Optional[float] = None
    if isinstance(evaluation, dict):
        candidate = evaluation.get("risk_score")
        if isinstance(candidate, (int, float)):
            risk_score = float(candidate)
    score_text = f"{float(risk_score):.2f}" if isinstance(risk_score, (int, float)) else "—"

    js_safe_back_url = (
        json.dumps(safe_back_url).replace("</", "<\\/").replace("<!", "<\\!")
    )

    triggered = _coerce_rule_results(evaluation)
    alternatives = _safe_alternatives(original_url)
    alternatives_block = "<ul class=\"alts-list\">" + "".join(
        f"<li>{html.escape(item)}</li>" for item in alternatives
    ) + "</ul>"
    if triggered:
        rules_block = (
            "<ul class=\"rules-list\">"
            + "".join(_format_rule_row(r) for r in triggered)
            + "</ul>"
        )
    elif safe_reason:
        rules_block = f"<p class=\"reason-text\">{safe_reason}</p>"
    else:
        rules_block = (
            "<p class=\"no-rules\">"
            "AgentGuard blocked this page based on its overall risk profile."
            "</p>"
        )

    return _TEMPLATE.format(
        safe_url=safe_url,
        score_text=score_text,
        rules_block=rules_block,
        alternatives_block=alternatives_block,
        js_safe_back_url=js_safe_back_url,
    ).encode("utf-8")


_TEMPLATE: str = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="x-ua-compatible" content="ie=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>AgentGuard — Page blocked</title>
<style>
  :root {{
    --bg: #1b1d24;
    --panel: #262934;
    --panel-2: #2f3340;
    --text: #f4f5f7;
    --muted: #aab0bd;
    --danger: #e1574c;
    --danger-strong: #b8392f;
    --danger-soft: rgba(225, 87, 76, 0.15);
    --safe: #45b08c;
    --safe-strong: #2f8f6e;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                 Ubuntu, Cantarell, "Helvetica Neue", sans-serif; }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 24px 64px; }}
  .badge {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
    background: var(--danger-soft); color: var(--danger);
    border: 1px solid rgba(225, 87, 76, 0.5); border-radius: 999px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }}
  h1 {{ font-size: 28px; line-height: 1.25; margin: 16px 0 8px; }}
  .lead {{ color: var(--muted); margin: 0 0 28px; }}
  .panel {{ background: var(--panel); border: 1px solid #353a48; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 18px; }}
  .panel.danger {{ border-color: rgba(225, 87, 76, 0.45);
    background: linear-gradient(180deg, rgba(225, 87, 76, 0.08), var(--panel) 70%); }}
  .url {{ word-break: break-all; font-family: ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace; font-size: 14px; color: #d3d8e3; }}
  .score {{ display: flex; align-items: baseline; gap: 12px; }}
  .score-value {{ font-size: 32px; font-weight: 700; color: var(--danger); }}
  .score-label {{ color: var(--muted); font-size: 13px; }}
  .rules-list {{ list-style: none; margin: 8px 0 0; padding: 0; }}
  .rules-list li {{ padding: 12px 14px; background: var(--panel-2); border-radius: 8px;
    margin-bottom: 8px; border-left: 3px solid var(--danger); }}
  .rule-row {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    font-size: 13px; }}
  .rule-id {{ font-weight: 600; color: #ffb4ad; }}
  .rule-type {{ font-size: 11px; padding: 2px 8px; border-radius: 999px;
    background: rgba(255, 180, 173, 0.15); color: #ffb4ad;
    text-transform: uppercase; letter-spacing: 0.05em; }}
  .rule-score {{ margin-left: auto; color: var(--muted); font-size: 12px; }}
  .rule-explanation {{ font-size: 14px; color: #e6e8ed; margin-top: 6px; }}
  .reason-text {{ font-size: 15px; color: #f1d8d5; margin: 4px 0 0; line-height: 1.5; }}
  .no-rules {{ color: var(--muted); margin: 0; }}
  .alts-list {{ margin: 0; padding-left: 18px; color: #d9deea; line-height: 1.5; }}
  .alts-list li {{ margin: 6px 0; }}
  .section-label {{ color: var(--muted); font-size: 13px; text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 8px; }}
  .actions {{ display: flex; gap: 12px; margin-top: 12px; }}
  button, a.btn {{ font: inherit; cursor: pointer; padding: 12px 18px; border-radius: 10px;
    border: 1px solid transparent; font-weight: 600; transition: filter 120ms ease;
    display: inline-flex; align-items: center; justify-content: center; }}
  button:hover, a.btn:hover {{ filter: brightness(1.08); }}
  .btn-primary {{ background: var(--safe); color: #0e1a16;
    border-color: var(--safe-strong); flex: 1; }}
  a {{ color: inherit; text-decoration: none; }}
  .footer {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
</style>
</head>
<body>
  <main class="wrap">
    <span class="badge">AgentGuard · Blocked</span>
    <h1>This page has been blocked.</h1>
    <p class="lead">AgentGuard refused to load the destination below.</p>

    <section class="panel danger">
      <div class="score">
        <span class="score-value">{score_text}</span>
        <span class="score-label">overall risk (0 is safest, 1 is highest)</span>
      </div>
    </section>

    <section class="panel">
      <div class="section-label">Why this was blocked</div>
      {rules_block}
    </section>

    <section class="panel">
      <div class="section-label">Destination</div>
      <div class="url">{safe_url}</div>
    </section>

    <section class="panel">
      <div class="section-label">Safe alternatives</div>
      {alternatives_block}
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
    function goBack() {{
      window.location.replace({js_safe_back_url});
    }}
  </script>
</body>
</html>"""
