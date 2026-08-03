"""Styling shared by the two interstitials. `SHARED_CSS` holds the layout and each
page supplies its own accent colour as CSS custom properties.
"""

from __future__ import annotations

SHARED_CSS = """
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen,
                 Ubuntu, Cantarell, "Helvetica Neue", sans-serif; }
  .wrap { max-width: 720px; margin: 0 auto; padding: 48px 24px 64px; }
  .badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
    background: var(--accent-soft); color: var(--accent);
    border: 1px solid var(--accent-line); border-radius: 999px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
  h1 { font-size: 28px; line-height: 1.25; margin: 16px 0 8px; }
  .lead { color: var(--muted); margin: 0 0 28px; }
  .panel { background: var(--panel); border: 1px solid #353a48; border-radius: 12px;
    padding: 18px 20px; margin-bottom: 18px; }
  .section-label { color: var(--muted); font-size: 13px; text-transform: uppercase;
    letter-spacing: 0.06em; margin-bottom: 8px; }
  .url { word-break: break-all; font-family: ui-monospace, SFMono-Regular, Menlo,
    Consolas, monospace; font-size: 14px; color: #d3d8e3; }
  .score { display: flex; align-items: baseline; gap: 12px; }
  .score-value { font-size: 32px; font-weight: 700; color: var(--accent); }
  .score-label { color: var(--muted); font-size: 13px; }
  .rules-list { list-style: none; margin: 8px 0 0; padding: 0; }
  .rules-list li { padding: 12px 14px; background: var(--panel-2); border-radius: 8px;
    margin-bottom: 8px; }
  .rule-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
    font-size: 13px; }
  .rule-id { font-weight: 600; color: var(--rule-fg); }
  .rule-type { font-size: 11px; padding: 2px 8px; border-radius: 999px;
    background: var(--rule-chip); color: var(--rule-fg);
    text-transform: uppercase; letter-spacing: 0.05em; }
  .rule-score { margin-left: auto; color: var(--muted); font-size: 12px; }
  .rule-explanation { font-size: 14px; color: #e6e8ed; margin-top: 6px; }
  .no-rules { color: var(--muted); margin: 0; }
  .actions { display: flex; gap: 12px; margin-top: 12px; }
  button, a.btn { font: inherit; cursor: pointer; padding: 12px 18px; border-radius: 10px;
    border: 1px solid transparent; font-weight: 600; transition: filter 120ms ease;
    display: inline-flex; align-items: center; justify-content: center; }
  button:hover, a.btn:hover { filter: brightness(1.08); }
  .btn-primary { background: var(--safe); color: #0e1a16;
    border-color: var(--safe-strong); flex: 1; }
  a { color: inherit; text-decoration: none; }
  .footer { color: var(--muted); font-size: 12px; margin-top: 16px; }
"""

# Surface colours are identical on both pages; only the accent differs.
BASE_PALETTE = """
    --bg: #1b1d24;
    --panel: #262934;
    --panel-2: #2f3340;
    --text: #f4f5f7;
    --muted: #aab0bd;
    --safe: #45b08c;
    --safe-strong: #2f8f6e;
"""


def stylesheet(*, palette: str, extra_css: str = "") -> str:
    """Assemble the page's `<style>` contents from its palette and extras."""
    return f":root {{{BASE_PALETTE}{palette}  }}\n{SHARED_CSS}{extra_css}"
