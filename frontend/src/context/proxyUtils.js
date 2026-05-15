function getApiBase() {
  const raw = import.meta.env.VITE_API_BASE_URL;
  return raw ? String(raw).trim().replace(/\/$/, '') : null;
}

export async function callProxyControl(active) {
  const base = getApiBase();
  if (!base) throw new Error('VITE_API_BASE_URL is not configured');
  const res = await fetch(`${base}/api/proxy/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active }),
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* ignore */ }
  if (!res.ok) throw new Error(data.error || res.statusText || 'Proxy control failed');
  return data;
}

export async function fetchProxyStatus() {
  const base = getApiBase();
  if (!base) return null;
  try {
    const res = await fetch(`${base}/api/proxy/status`);
    return res.ok ? res.json() : null;
  } catch (_) { return null; }
}
