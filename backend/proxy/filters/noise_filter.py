from mitmproxy import http

NOISE_DOMAINS = [
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.net",
    "analytics.tiktok.com",
    "bing.com",
    "bat.bing.com",
    "domainreliability",
    "go-mpulse.net",
    "akstat.io",
    "nr-data.net",
    "newrelic.com",
    "datadoghq.com",
    "hotjar.com",
    "segment.io",
    "mixpanel.com",
    "cdn-cgi",
    "cloudflare",
    "gstatic.com",
]


def is_noise(flow: http.HTTPFlow) -> bool:
    host = flow.request.host.lower()

    # Known tracking / analytics / CDN noise
    if any(domain in host for domain in NOISE_DOMAINS):
        return True

    # WebSocket / upgrade noise
    if "upgrade" in flow.request.headers.get("connection", "").lower():
        return True

    return False