import { getApiBaseUrl, apiFetchHeaders } from './client.js';

export async function fetchBlacklistApi() {
  const base = getApiBaseUrl();
  if (!base) throw new Error('API base URL is not configured');

  const response = await fetch(`${base}/api/blacklist`, {
    headers: apiFetchHeaders()
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized. Only Admins can access the custom blacklist.');
    }
    throw new Error('Failed to fetch blacklist');
  }

  return await response.json();
}

export async function updateBlacklistApi(newEntries) {
  const base = getApiBaseUrl();
  if (!base) throw new Error('API base URL is not configured');

  const headers = apiFetchHeaders();
  headers['Content-Type'] = 'application/json';

  const response = await fetch(`${base}/api/blacklist`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ entries: newEntries })
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized. Only Admins can modify the custom blacklist.');
    }
    throw new Error('Failed to update blacklist');
  }

  return await response.json();
}
