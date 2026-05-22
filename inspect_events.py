"""One-off diagnostic: dump recent events + rule analyses around a target id."""

from __future__ import annotations

import sqlite3
import sys

START = int(sys.argv[1]) if len(sys.argv) > 1 else 1555
END = int(sys.argv[2]) if len(sys.argv) > 2 else 1565

conn = sqlite3.connect("backend/agentguard.db")
conn.row_factory = sqlite3.Row

print(f"--- EVENTS {START}..{END} ---")
for r in conn.execute(
    "SELECT event_id, session_id, timestamp, guard_action, risk_score, http_method, url "
    "FROM events WHERE event_id BETWEEN ? AND ? ORDER BY event_id",
    (START, END),
):
    print(dict(r))

print(f"\n--- RULE ANALYSIS for events {START}..{END} (only triggered or contextual) ---")
for r in conn.execute(
    "SELECT a.event_id, a.rule_code, r.rule_type, a.rule_score, a.details "
    "FROM rules_analysis a JOIN rules r ON r.rule_code = a.rule_code "
    "WHERE a.event_id BETWEEN ? AND ? "
    "AND (a.rule_score > 0 OR r.rule_type = 'contextual') "
    "ORDER BY a.event_id, r.rule_type DESC, a.rule_code",
    (START, END),
):
    print(dict(r))
