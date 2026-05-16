/**
 * Shared API configuration for dashboard fetch calls.
 */

export function getApiBaseUrl() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (base == null || String(base).trim() === '') return null;
  return String(base).replace(/\/$/, '');
}

import { getToken } from './authToken.js';

export function apiFetchHeaders() {
  const token = getToken();
  return token 
    ? { Accept: 'application/json', Authorization: `Bearer ${token}` }
    : { Accept: 'application/json' };
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
