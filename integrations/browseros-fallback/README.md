# BrowserOS AgentGuard Fallback Adapter

This is a portable integration layer for BrowserOS navigation code. It does not change AgentGuard enforcement.

AgentGuard already returns a synthetic browser-facing response for blocked proxy requests:

- `HTTP 403`
- `X-AgentGuard-Decision: block`
- text body containing the block explanation when available

BrowserOS should treat that response as a security decision, not as an ordinary network failure.

## Where To Wire It In

This repository does not contain BrowserOS navigation/runtime source. The best insertion point in BrowserOS is the place that currently handles navigation responses or failed `page.goto`/browser-load attempts.

Wire `AgentGuardFallbackHandler.handleNavigationResponse(...)` immediately after a navigation receives a response and before the normal fatal error path runs.

Typical flow:

```js
const response = await browser.navigate(url);
const fallback = await fallbackHandler.handleNavigationResponse({
  url,
  task: userTask,
  response,
  openUrl: (candidateUrl) => browser.navigate(candidateUrl),
  search: (query) => browser.search(query),
});

if (fallback.handled && fallback.chosenAlternative) {
  return continueTaskFromCurrentPage();
}

if (fallback.handled) {
  return reportSafeFailureToUser();
}
```

## Modules

- `agentguard_response_detector.mjs` detects `403 + X-AgentGuard-Decision: block`.
- `blocked_request_tracker.mjs` keeps temporary per-task/session memory of unsafe destinations.
- `safe_alternative_search.mjs` builds official/trusted/reformulated search candidates and ranks nearby results.
- `fallback_handler.mjs` orchestrates block detection, logging, retry protection, and fallback attempts.

## Logging

The handler logs:

- blocked URL
- block reason
- fallback searches
- fallback attempts
- selected alternative
- candidates that were also blocked

Pass BrowserOS's logger in the constructor:

```js
const fallbackHandler = new AgentGuardFallbackHandler({ logger });
```
