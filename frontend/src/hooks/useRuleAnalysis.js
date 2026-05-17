import { useEffect, useState } from 'react';
import { fetchWithBase } from '../components/SessionsDashboard/sessionUtils.js';

export function useRuleAnalysis(selectedEventId) {
  const [ruleAnalysis, setRuleAnalysis] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function loadRules() {
      if (!selectedEventId) { setRuleAnalysis([]); return; }
      try {
        const res = await fetchWithBase(`/events/${selectedEventId}/rules-analysis`);
        if (res.ok && !cancelled) {
          const data = await res.json();
          setRuleAnalysis(Array.isArray(data) ? data : []);
        }
      } catch { if (!cancelled) setRuleAnalysis([]); }
    }
    loadRules();
    return () => { cancelled = true; };
  }, [selectedEventId]);

  return ruleAnalysis;
}
