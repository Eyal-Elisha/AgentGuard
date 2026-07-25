const RULE_TYPE_SECTIONS = [
  { type: 'deterministic', label: 'Deterministic' },
  { type: 'contextual', label: 'Contextual' },
  { type: 'semantic', label: 'Semantic' },
];

const KNOWN_TYPES = new Set(RULE_TYPE_SECTIONS.map((s) => s.type));

function normalizeRuleType(ruleType) {
  return String(ruleType ?? '').toLowerCase().trim();
}

/** @returns {{ type: string, label: string, rows: object[] }[]} */
export function groupRuleAnalysisSections(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return [];

  const buckets = Object.fromEntries(RULE_TYPE_SECTIONS.map((s) => [s.type, []]));
  const other = [];

  for (const row of rows) {
    const key = normalizeRuleType(row.rule_type);
    if (KNOWN_TYPES.has(key)) buckets[key].push(row);
    else other.push(row);
  }

  const sections = RULE_TYPE_SECTIONS
    .filter((s) => buckets[s.type].length > 0)
    .map((s) => ({ type: s.type, label: s.label, rows: buckets[s.type] }));

  if (other.length > 0) {
    sections.push({
      type: 'other',
      label: 'Other',
      rows: other,
    });
  }

  return sections;
}
