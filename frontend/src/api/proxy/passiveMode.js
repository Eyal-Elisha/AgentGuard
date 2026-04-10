import { getApiBaseUrl } from '../client.js';

export async function fetchPassiveMode() {
  const base = getApiBaseUrl();
  if (base == null) throw new Error('API base URL is not configured');
  const res = await fetch(`${base}/api/proxy/passive-mode`);
  if (!res.ok) throw new Error('Failed to fetch passive mode');
  const data = await res.json();
  return typeof data.passive_mode === 'boolean' ? data.passive_mode : false;
}

export async function patchPassiveMode(enabled) {
  const base = getApiBaseUrl();
  if (base == null) throw new Error('API base URL is not configured');
  const res = await fetch(`${base}/api/proxy/passive-mode`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passive_mode: enabled }),
  });
  if (!res.ok) throw new Error('Failed to update passive mode');
  const data = await res.json();
  return typeof data.passive_mode === 'boolean' ? data.passive_mode : enabled;
}
