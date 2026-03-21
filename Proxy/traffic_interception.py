from mitmproxy import http
import json
import datetime
import re


# This is a part I did in order to redunce noise of other apps, and analysis that happen in the background while browsing,
# I think we have to make a separate ticket for this (the part I did in the scope ~~~~ ... ~~~~~)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

BROWSER_HEADERS = [
    "sec-fetch-site",
    "sec-fetch-mode",
    "sec-fetch-dest",
    "user-agent"
]

def is_browser_user_agent(user_agent: str) -> bool:

    if not user_agent:
        return False

    if "electron/" in user_agent.lower():
        return False

    browser_patterns = ["chrome/", "firefox/", "safari/", "edg/"]
    return any(re.search(pat, user_agent, re.IGNORECASE) for pat in browser_patterns)

def is_noise(flow: http.HTTPFlow) -> bool:
    host = flow.request.host.lower()
    url = flow.request.pretty_url.lower()

    if any(domain in host for domain in NOISE_DOMAINS):
        return True

    if "upgrade" in flow.request.headers.get("connection", "").lower():
        return True

    return False

def is_browser_traffic(flow: http.HTTPFlow) -> bool:
    ua = flow.request.headers.get("user-agent", "")
    if not is_browser_user_agent(ua):
        return False

    if is_noise(flow):
        return False

    method = flow.request.method.upper()
    has_body = bool(flow.request.content)

    if method in ["POST", "PUT", "PATCH"]:
        return True

    if method == "GET" and has_body:
        return True

    return False

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def safe_get_text(message):
    if not message or not message.content:
        return ""

    try:
        text = message.get_text()
        return text
    except Exception:
        return f"<{len(message.content)} bytes of binary/encoded data>"

def pretty_print(title, data):
    print(f"\n===== {title} =====")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"===== End of {title} =====\n")

def request(flow: http.HTTPFlow):
    if not is_browser_traffic(flow):
        return

    data = {
        "timestamp": str(datetime.datetime.now()),
        "type": "REQUEST",
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": flow.request.host,
        "headers": dict(flow.request.headers),
        "body": safe_get_text(flow.request)
    }

    pretty_print(f"{flow.request.method} {flow.request.host}", data)

def response(flow: http.HTTPFlow):
    if not is_browser_traffic(flow):
        return

    if not flow.response:
        return

    data = {
        "timestamp": str(datetime.datetime.now()),
        "type": "RESPONSE",
        "status_code": flow.response.status_code,
        "url": flow.request.pretty_url,
        "headers": dict(flow.response.headers),
        "body": safe_get_text(flow.response)
    }

    pretty_print(f"{flow.response.status_code} {flow.request.host}", data)