import assert from "node:assert/strict";
import { test } from "node:test";

import { detectAgentGuardBlock } from "../integrations/browseros-fallback/agentguard_response_detector.mjs";
import { BlockedRequestTracker } from "../integrations/browseros-fallback/blocked_request_tracker.mjs";
import { SafeAlternativeSearch } from "../integrations/browseros-fallback/safe_alternative_search.mjs";
import { AgentGuardFallbackHandler } from "../integrations/browseros-fallback/fallback_handler.mjs";

function blockResponse(reason = "Unsafe destination") {
  return {
    status: 403,
    headers: { "X-AgentGuard-Decision": "block" },
    bodyText: `AgentGuard blocked the request before it reached the external destination.\n\nReason: ${reason}`,
  };
}

test("detects AgentGuard block responses distinctly from normal 403s", () => {
  assert.equal(detectAgentGuardBlock(blockResponse("Custom blacklist")).blocked, true);
  assert.equal(detectAgentGuardBlock({ status: 403, headers: {}, bodyText: "Forbidden" }).blocked, false);
  assert.equal(detectAgentGuardBlock({ status: 500, headers: { "X-AgentGuard-Decision": "block" } }).blocked, false);
});

test("tracks blocked destinations by hostname with TTL", () => {
  let now = 1000;
  const tracker = new BlockedRequestTracker({ ttlMs: 100, now: () => now });
  tracker.markBlocked("https://suspicious-example.com/login", { reason: "bad" });

  assert.equal(tracker.isBlocked("https://suspicious-example.com/other"), true);
  now = 1200;
  assert.equal(tracker.isBlocked("https://suspicious-example.com/other"), false);
});

test("builds safe alternative search candidates without embedding blocked host", () => {
  const search = new SafeAlternativeSearch();
  const candidates = search.buildSearchCandidates({
    task: "find ExampleCo docs",
    blockedUrl: "https://suspicious-example.com",
  });

  assert.ok(candidates.length >= 4);
  assert.ok(candidates.some((candidate) => candidate.kind === "official-domain"));
  assert.ok(candidates.every((candidate) => !candidate.query.includes("suspicious-example.com")));
});

test("fallback handler avoids retrying blocked URL and chooses a safe alternative", async () => {
  const attempts = [];
  const logs = [];
  const handler = new AgentGuardFallbackHandler({
    logger: {
      info: (event, payload) => logs.push({ level: "info", event, payload }),
      warn: (event, payload) => logs.push({ level: "warn", event, payload }),
    },
  });

  const result = await handler.handleNavigationResponse({
    url: "https://suspicious-example.com",
    task: "find ExampleCo docs",
    response: blockResponse("Domain is blacklisted"),
    search: async () => [
      "https://suspicious-example.com/retry",
      "https://docs.example.com",
    ],
    openUrl: async (url) => {
      attempts.push(url);
      return { status: 200, headers: {}, bodyText: "ok" };
    },
  });

  assert.equal(result.handled, true);
  assert.equal(result.blocked, true);
  assert.equal(result.chosenAlternative.url, "https://docs.example.com");
  assert.deepEqual(attempts, ["https://docs.example.com"]);
  assert.equal(handler.tracker.isBlocked("https://suspicious-example.com/again"), true);
  assert.ok(logs.some((log) => log.event.includes("agentguard_block_detected")));
});

test("fallback handler marks blocked fallback candidates and keeps searching", async () => {
  const handler = new AgentGuardFallbackHandler({
    logger: { info: () => {}, warn: () => {} },
  });

  const result = await handler.handleNavigationResponse({
    url: "https://suspicious-example.com",
    task: "find ExampleCo docs",
    response: blockResponse("Blocked original"),
    nearbyResults: ["https://docs.microsoft.com/exampleco/unsafe-mirror", "https://support.google.com/example"],
    openUrl: async (url) => {
      if (url.includes("unsafe-mirror")) return blockResponse("Unsafe mirror");
      return { status: 200, headers: {}, bodyText: "trusted" };
    },
  });

  assert.equal(result.chosenAlternative.url, "https://support.google.com/example");
  assert.equal(handler.tracker.isBlocked("https://docs.microsoft.com/exampleco/unsafe-mirror"), true);
});
