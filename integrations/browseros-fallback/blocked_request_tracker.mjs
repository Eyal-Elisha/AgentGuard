const DEFAULT_TTL_MS = 30 * 60 * 1000;
const DEFAULT_MAX_ENTRIES = 250;

export function destinationKey(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname.toLowerCase();
  } catch (_) {
    return String(url ?? "").trim().toLowerCase();
  }
}

export class BlockedRequestTracker {
  constructor({ ttlMs = DEFAULT_TTL_MS, maxEntries = DEFAULT_MAX_ENTRIES, now = () => Date.now() } = {}) {
    this.ttlMs = ttlMs;
    this.maxEntries = maxEntries;
    this.now = now;
    this.entries = new Map();
  }

  markBlocked(url, details = {}) {
    this.purgeExpired();
    const key = destinationKey(url);
    if (!key) return null;

    const entry = {
      key,
      url,
      reason: details.reason ?? null,
      blockedAt: this.now(),
      attempts: (this.entries.get(key)?.attempts ?? 0) + 1,
    };
    this.entries.set(key, entry);
    this.trim();
    return entry;
  }

  isBlocked(url) {
    this.purgeExpired();
    const key = destinationKey(url);
    return key ? this.entries.has(key) : false;
  }

  getBlockedDestination(url) {
    this.purgeExpired();
    return this.entries.get(destinationKey(url)) ?? null;
  }

  getBlockedRecords() {
    this.purgeExpired();
    return Array.from(this.entries.values());
  }

  purgeExpired() {
    const cutoff = this.now() - this.ttlMs;
    for (const [key, entry] of this.entries.entries()) {
      if (entry.blockedAt < cutoff) this.entries.delete(key);
    }
  }

  trim() {
    while (this.entries.size > this.maxEntries) {
      const oldestKey = this.entries.keys().next().value;
      this.entries.delete(oldestKey);
    }
  }
}
