import { useEffect, useMemo, useState } from 'react';
import { getApiBaseUrl, apiFetchHeaders } from '../api/client.js';
import { readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';

export function normalizeRule(raw) {
  return {
    rule_code: raw.rule_code != null ? String(raw.rule_code) : '',
    description: raw.description ?? null,
    rule_type: raw.rule_type != null ? String(raw.rule_type) : '',
    compute_class: raw.compute_class != null ? String(raw.compute_class) : '',
    weight: typeof raw.weight === 'number' ? raw.weight : Number(raw.weight),
    is_hard_block: Boolean(raw.is_hard_block),
    is_enabled: Boolean(raw.is_enabled),
  };
}

export function useRules() {
  const [rules, setRules] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadRules() {
      const baseUrl = getApiBaseUrl();
      if (!baseUrl) {
        if (!cancelled) { setError('API base URL not configured.'); setIsLoading(false); }
        return;
      }
      try {
        const response = await fetch(`${baseUrl}/rules`, { headers: apiFetchHeaders() });
        if (!response.ok) {
          const message = await readErrorMessage(response, 'rules');
          if (!cancelled) { setRules([]); setError(message); }
          return;
        }
        const data = await response.json();
        if (!Array.isArray(data)) {
          if (!cancelled) { setRules([]); setError('Received an unexpected response.'); }
          return;
        }
        if (!cancelled) { setRules(data.map(normalizeRule)); setError(null); }
      } catch { if (!cancelled) { setRules([]); setError('Unable to reach the server.'); }
      } finally { if (!cancelled) setIsLoading(false); }
    }
    loadRules();
    return () => { cancelled = true; };
  }, []);

  return { rules, setRules, isLoading, error, setError };
}
