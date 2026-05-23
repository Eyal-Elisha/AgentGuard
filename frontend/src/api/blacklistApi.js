import { fetchWithBase, readErrorMessage } from '../components/SessionsDashboard/sessionUtils.js';

export async function fetchBlacklistApi() {
  const response = await fetchWithBase('/blacklist');
  if (!response.ok) {
    const message = await readErrorMessage(
      response,
      'Unauthorized. Only admins can access the custom blacklist.',
    );
    throw new Error(message);
  }
  return response.json();
}

export async function updateBlacklistApi(newEntries) {
  const response = await fetchWithBase('/blacklist', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entries: newEntries }),
  });
  if (!response.ok) {
    const message = await readErrorMessage(
      response,
      'Unauthorized. Only admins can modify the custom blacklist.',
    );
    throw new Error(message);
  }
  return response.json();
}
