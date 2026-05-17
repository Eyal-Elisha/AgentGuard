"""Render the Warn interstitial page shown when a request is flagged as Warn.

The page lists the rules that triggered, shows the risk score, and offers two
buttons:
  * "Go back"        — runs `history.back()` (or closes the tab if no history)
  * "Continue anyway" — links to the original URL with `?_agentguard_bypass=<token>`
                        appended; the proxy recognises the token and lets that
                        single request through.
"""

from __future__ import annotations

import html
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from backend.proxy.warn_bypass import BYPASS_QUERY_PARAM


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
    rule_type = html.escape(str(rule.get("rule_type", "")))
    explanation = html.escape(str(rule.get("explanation", "")))
    score = rule.get("score")
    score_text = f"{float(score):.2f}" if isinstance(score, (int, float)) else "—"
    return (
        "<li>"
        f"<div class=\"rule-row\">"
        f"<span class=\"rule-id\">{rule_id}</span>"
        f"<span class=\"rule-type\">{rule_type}</span>"
        f"<span class=\"rule-score\">score {score_text}</span>"
        "</div>"
        f"<div class=\"rule-explanation\">{explanation}</div>"
        "</li>"
    )


def append_bypass_param(url: str, token: str) -> str:
    """Return `url` with `_agentguard_bypass=<token>` added to the query string."""
    parts = urlsplit(url)
    pairs: List[Tuple[str, str]] = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k != BYPASS_QUERY_PARAM
    ]
    pairs.append((BYPASS_QUERY_PARAM, token))
    new_query = urlencode(pairs, doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def build_warn_html(
    *,
    original_url: str,
    bypass_token: str,
    risk_score: Optional[float],
    evaluation: Optional[Dict[str, Any]],
) -> bytes:
    safe_url = html.escape(original_url)
    continue_url = html.escape(append_bypass_param(original_url, bypass_token))
    score_text = f"{float(risk_score):.2f}" if isinstance(risk_score, (int, float)) else "—"

    triggered = _coerce_rule_results(evaluation)
    if triggered:
        rules_block = "<ul class=\"rules-list\">" + "".join(_format_rule_row(r) for r in triggered) + "</ul>"
    else:
        rules_block = (
            "<p class=\"no-rules\">"
            "AgentGuard flagged this page based on its overall risk profile."
            "</p>"
        )

    return _TEMPLATE.format(
        safe_url=safe_url,
        continue_url=continue_url,
        score_text=score_text,
        rules_block=rules_block,
    ).encode("utf-8")


_TEMPLATE: str = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="x-ua-compatible" content="ie=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>AgentGuard — Suspicious page</title>
<style>
  :root {{
    --bg: #1b1d24;
    --panel: #262934;
    --panel-2: #2f3340;
    --text: #f4f5f7;
    --muted: #aab0bd;
    --accent: #f5a524;
    --accent-strong: #e36414;
    --safe: #45b08c;
    --safe-strong: #2f8f6e;
    --danger: #e1574c;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                 Ubuntu, Cantarell, "Helvetica Neue", sans-serif; }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 24px 64px; }}
  .badge {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
    background: rgba(245, 165, 36, 0.15); color: var(--accent);
    border: 1px solid rgba(245, 165, 36, 0.45); border-radius: 999px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }}
  h1 {{ font-size: 28px; line-height: 1.25; margin: 16px 0 8px; }}
  .lead {{ color: var(--muted); margin: 0 0 28px; }}
  .panel {{ background: var(--panel); border: 1px solid #353a48; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 18px; }}
  .url {{ word-break: break-all; font-family: ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace; font-size: 14px; color: #d3d8e3; }}
  .score {{ display: flex; align-items: baseline; gap: 12px; }}
  .score-value {{ font-size: 32px; font-weight: 700; color: var(--accent); }}
  .score-label {{ color: var(--muted); font-size: 13px; }}
  .rules-list {{ list-style: none; margin: 8px 0 0; padding: 0; }}
  .rules-list li {{ padding: 12px 14px; background: var(--panel-2); border-radius: 8px;
    margin-bottom: 8px; }}
  .rule-row {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    font-size: 13px; }}
  .rule-id {{ font-weight: 600; color: #ffd483; }}
  .rule-type {{ font-size: 11px; padding: 2px 8px; border-radius: 999px;
    background: rgba(255, 212, 131, 0.15); color: #ffd483;
    text-transform: uppercase; letter-spacing: 0.05em; }}
  .rule-score {{ margin-left: auto; color: var(--muted); font-size: 12px; }}
  .rule-explanation {{ font-size: 14px; color: #e6e8ed; margin-top: 6px; }}
  .no-rules {{ color: var(--muted); margin: 0; }}
  .actions {{ display: flex; gap: 12px; margin-top: 12px; }}
  button {{ font: inherit; cursor: pointer; padding: 12px 18px; border-radius: 10px;
    border: 1px solid transparent; font-weight: 600; transition: filter 120ms ease; }}
  button:hover {{ filter: brightness(1.08); }}
  .btn-primary {{ background: var(--safe); color: #0e1a16;
    border-color: var(--safe-strong); flex: 1; }}
  .btn-secondary {{ background: transparent; color: var(--text);
    border-color: #4a5060; }}
  .btn-danger {{ background: var(--danger); color: #fff; border-color: #b9352c; }}
  a {{ color: inherit; text-decoration: none; }}
  .footer {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
  .footer code {{ background: var(--panel-2); padding: 2px 6px; border-radius: 4px; }}
</style>
</head>
<body>
  <main class="wrap">
    <span class="badge">AgentGuard · Warn</span>
    <h1>This page looks suspicious.</h1>
    <p class="lead">AgentGuard flagged the destination below. Continue only if you trust this site.</p>

    <section class="panel">
      <div class="score">
        <span class="score-value">{score_text}</span>
        <span class="score-label">risk score (0 – 1)</span>
      </div>
    </section>

    <section class="panel">
      <div class="rules-list-label" style="color: var(--muted); font-size: 13px;
           text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
        Why we flagged it
      </div>
      {rules_block}
    </section>

    <section class="panel">
      <div style="color: var(--muted); font-size: 13px; text-transform: uppercase;
           letter-spacing: 0.06em; margin-bottom: 6px;">Destination</div>
      <div class="url">{safe_url}</div>
    </section>

    <div class="actions">
      <button class="btn-primary" type="button" onclick="goBack()">Go back to safety</button>
      <a class="btn-secondary"
         style="display: inline-flex; align-items: center;"
         href="{continue_url}">Continue anyway</a>
    </div>

    <p class="footer">
      Each Warn requires a fresh confirmation. Clicking <strong>Continue anyway</strong>
      only allows this exact request.
    </p>
  </main>
  <script>
    function goBack() {{
      if (window.history.length > 1) {{ window.history.back(); }}
      else {{ window.close(); }}
    }}
  </script>
</body>
</html>"""
