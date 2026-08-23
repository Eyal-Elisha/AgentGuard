import { getApiBaseUrl, setRuleHardBlock } from '../client.js';

async function parseApiError(response, fallbackContext) {
  let body = null;
  try {
    body = await response.json();
  } catch (parseError) {
    body = null;
    void parseError;
  }

  if (body && typeof body.error === 'string' && body.error.trim() !== '') {
    return body.error;
  }

  if (response.status === 403) {
    return 'Only an admin can change whether a rule may hard block';
  }

  if (response.status === 404) {
    return 'Rule not found';
  }

  if (response.status >= 500) {
    return 'Server error while updating rule state';
  }

  return `Failed to fetch ${fallbackContext}`;
}

export async function requestRuleHardBlockUpdate(ruleCode, nextHardBlock) {
  const baseUrl = getApiBaseUrl();
  if (baseUrl == null) {
    throw new Error(
      'API base URL is not configured. Set VITE_API_BASE_URL in your .env file.',
    );
  }

  const response = await setRuleHardBlock(baseUrl, ruleCode, nextHardBlock);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'rule update'));
  }

  return response.json();
}
