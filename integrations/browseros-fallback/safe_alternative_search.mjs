import { destinationKey } from "./blocked_request_tracker.mjs";

const TRUSTED_DOMAINS = [
  "wikipedia.org",
  "docs.microsoft.com",
  "developer.mozilla.org",
  "support.google.com",
  "github.com",
  "stackoverflow.com",
];

function wordsFromHost(url) {
  const host = destinationKey(url);
  return host
    .replace(/^www\./, "")
    .split(".")[0]
    .replace(/[-_]+/g, " ")
    .trim();
}

function encodeQuery(query) {
  return encodeURIComponent(query.replace(/\s+/g, " ").trim());
}

export class SafeAlternativeSearch {
  constructor({ searchEngineBaseUrl = "https://www.google.com/search?q=" } = {}) {
    this.searchEngineBaseUrl = searchEngineBaseUrl;
  }

  buildAlternativeQueries({ task, blockedUrl, reason } = {}) {
    const subject = task?.trim() || wordsFromHost(blockedUrl) || "requested information";
    const blockedHost = destinationKey(blockedUrl);
    const reasonText = reason ? ` security issue: ${reason}` : "";

    return [
      {
        kind: "official-domain",
        query: `${subject} official website`,
        rationale: "Prefer an official domain over the blocked destination.",
      },
      {
        kind: "trusted-source",
        query: `${subject} trusted source documentation`,
        rationale: "Look for reputable documentation or established sources.",
      },
      {
        kind: "search-reformulation",
        query: `${subject} alternative source${reasonText}`,
        rationale: "Reformulate the search without retrying the unsafe URL.",
      },
      {
        kind: "nearby-results",
        query: `${subject} reviews reputable source`,
        rationale: "Use nearby reputable results when the exact site is unsafe.",
      },
      {
        kind: "safe-mirror-check",
        query: `${subject} mirror official`,
        rationale: "Consider mirrors only when they are official or clearly trusted.",
      },
    ].filter((item) => !blockedHost || !item.query.toLowerCase().includes(blockedHost));
  }

  buildSearchCandidates(input) {
    return this.buildAlternativeQueries(input).map((item) => ({
      ...item,
      url: `${this.searchEngineBaseUrl}${encodeQuery(item.query)}`,
    }));
  }

  rankResultUrls(urls, tracker) {
    return urls
      .filter((url) => !tracker?.isBlocked(url))
      .map((url) => ({
        url,
        score: this.scoreUrl(url),
      }))
      .sort((a, b) => b.score - a.score);
  }

  scoreUrl(url) {
    let score = 0;
    try {
      const parsed = new URL(url);
      if (parsed.protocol === "https:") score += 2;
      const host = parsed.hostname.replace(/^www\./, "");
      if (TRUSTED_DOMAINS.some((domain) => host === domain || host.endsWith(`.${domain}`))) {
        score += 4;
      }
      if (host.includes("official") || host.includes("support") || host.includes("docs")) {
        score += 1;
      }
      if (host.includes("mirror") || host.includes("download")) {
        score -= 1;
      }
    } catch (_) {
      score -= 10;
    }
    return score;
  }
}
