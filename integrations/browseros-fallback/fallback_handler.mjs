import { detectAgentGuardBlock, isAgentGuardBlockResponse } from "./agentguard_response_detector.mjs";
import { BlockedRequestTracker } from "./blocked_request_tracker.mjs";
import { SafeAlternativeSearch } from "./safe_alternative_search.mjs";

function noopLogger() {
  return undefined;
}

export class AgentGuardFallbackHandler {
  constructor({
    tracker = new BlockedRequestTracker(),
    alternativeSearch = new SafeAlternativeSearch(),
    logger = console,
  } = {}) {
    this.tracker = tracker;
    this.alternativeSearch = alternativeSearch;
    this.logger = logger ?? { debug: noopLogger, info: noopLogger, warn: noopLogger };
  }

  async handleNavigationResponse({
    url,
    task,
    response,
    openUrl,
    search,
    nearbyResults = [],
  }) {
    const detection = detectAgentGuardBlock(response);
    if (!detection.blocked) {
      return { handled: false, blocked: false };
    }

    const blockedEntry = this.tracker.markBlocked(url, { reason: detection.reason });
    this.log("warn", "agentguard_block_detected", {
      url,
      reason: detection.reason,
      statusCode: detection.statusCode,
    });

    const rankedNearbyResults = this.alternativeSearch.rankResultUrls(nearbyResults, this.tracker);
    for (const candidate of rankedNearbyResults) {
      const result = await this.tryOpenAlternative({
        candidate: { ...candidate, kind: "nearby-results" },
        openUrl,
      });
      if (result) return { handled: true, blocked: true, blockedEntry, ...result };
    }

    const searchCandidates = this.alternativeSearch.buildSearchCandidates({
      task,
      blockedUrl: url,
      reason: detection.reason,
    });

    for (const candidate of searchCandidates) {
      if (this.tracker.isBlocked(candidate.url)) continue;

      if (typeof search === "function") {
        this.log("info", "agentguard_fallback_search", {
          blockedUrl: url,
          query: candidate.query,
          kind: candidate.kind,
        });
        const resultUrls = await search(candidate.query, candidate);
        const ranked = this.alternativeSearch.rankResultUrls(resultUrls ?? [], this.tracker);
        for (const rankedCandidate of ranked) {
          const result = await this.tryOpenAlternative({
            candidate: { ...rankedCandidate, kind: candidate.kind, query: candidate.query },
            openUrl,
          });
          if (result) return { handled: true, blocked: true, blockedEntry, ...result };
        }
      }

      const result = await this.tryOpenAlternative({ candidate, openUrl });
      if (result) return { handled: true, blocked: true, blockedEntry, ...result };
    }

    return {
      handled: true,
      blocked: true,
      blockedEntry,
      chosenAlternative: null,
      exhausted: true,
    };
  }

  async tryOpenAlternative({ candidate, openUrl }) {
    if (typeof openUrl !== "function") return null;
    if (this.tracker.isBlocked(candidate.url)) return null;

    this.log("info", "agentguard_fallback_attempt", {
      url: candidate.url,
      kind: candidate.kind,
      query: candidate.query,
    });

    try {
      const response = await openUrl(candidate.url, candidate);
      if (isAgentGuardBlockResponse(response)) {
        const detection = detectAgentGuardBlock(response);
        this.tracker.markBlocked(candidate.url, { reason: detection.reason });
        this.log("warn", "agentguard_fallback_candidate_blocked", {
          url: candidate.url,
          reason: detection.reason,
        });
        return null;
      }

      this.log("info", "agentguard_fallback_chosen", {
        url: candidate.url,
        kind: candidate.kind,
      });
      return { chosenAlternative: candidate, response };
    } catch (error) {
      this.log("warn", "agentguard_fallback_attempt_failed", {
        url: candidate.url,
        message: error?.message ?? String(error),
      });
      return null;
    }
  }

  log(level, event, payload) {
    const fn = this.logger?.[level] ?? this.logger?.log ?? noopLogger;
    fn.call(this.logger, `[BrowserOS][AgentGuardFallback] ${event}`, payload);
  }
}
