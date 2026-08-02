import { getToken } from '../api/authToken.js';

function getApiBase() {
  const raw = import.meta.env.VITE_API_BASE_URL;
  return raw ? String(raw).trim().replace(/\/$/, '') : null;
}

export async function callProxyControl(active, agentName) {
  const base = getApiBase();
  if (!base) throw new Error('VITE_API_BASE_URL is not configured');
  
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${base}/api/proxy/control`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ active, agent_name: agentName }),
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* ignore */ }
  if (!res.ok) throw new Error(data.error || res.statusText || 'Proxy control failed');
  return data;
}

export async function fetchProxyStatus() {
  const base = getApiBase();
  if (!base) return null;
  
  const token = getToken();
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(`${base}/api/proxy/status`, { headers });
    return res.ok ? res.json() : null;
  } catch (_) { return null; }
}
