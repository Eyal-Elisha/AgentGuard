/**
 * Shared API configuration for dashboard fetch calls.
 */

export function getApiBaseUrl() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (base == null || String(base).trim() === '') return null;
  return String(base).replace(/\/$/, '');
}

export function apiFetchHeaders() {
  return { Accept: 'application/json' };
}

export async function setRuleEnabled(baseUrl, ruleCode, isEnabled) {
  const response = await fetch(
    `${baseUrl}/rules/${encodeURIComponent(ruleCode)}/enabled`,
    {
      method: 'PATCH',
      headers: {
        ...apiFetchHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ is_enabled: isEnabled }),
    },
  );
  return response;
}
