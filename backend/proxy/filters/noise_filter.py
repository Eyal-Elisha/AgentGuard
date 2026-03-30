from mitmproxy import http
from urllib.parse import urlparse
import re
import threading

EASYPRIVACY_URL = "https://easylist.to/easylist/easyprivacy.txt"

EASYPRIVACY_DOMAINS = set()

NOISE_HOST_TOKENS = {
    "analytics",
    "beacon",
    "beacons",
    "signaler",
    "telemetry",
    "metrics",
    "sentry",
    "amplitude",
    "mixpanel",
    "hotjar",
    "segment",
    "collect",
    "gtag",
    "cdn",
    "update",
    "appcast",
    "extensions",
    "browseros",
    "safebrowsing",
    "gcp",
    "gvt",
    "clients",
}

PATH_NOISE_KEYWORDS = (
    "domainreliability",
    "domainreliability/upload",
    "multi-watch",
    "multi_watch",
    "update-manifest",
    "extensions.json",
    "appcast",
    "check-update",
    "update",
    "/nel/",
    "/domainreliability/",
    "/beacon",
    "/beacons",
)


def load_easyprivacy_domains():

    global EASYPRIVACY_DOMAINS

    try:
        print("[AgentGuard] Loading EasyPrivacy list...")
        import requests as _requests

        session = _requests.Session()
        session.trust_env = False
        session.proxies = {}

        response = session.get(EASYPRIVACY_URL, timeout=10)

        domains = set()

        for line in response.text.splitlines():
            line = line.strip()

            if line.startswith("||") and "^" in line:
                domain = line.split("^")[0].replace("||", "")
                domains.add(domain)

        EASYPRIVACY_DOMAINS = domains
        print(f"[AgentGuard] Loaded {len(domains)} noise domains")

    except Exception as e:
        print(f"[AgentGuard] Failed to load EasyPrivacy: {e}")
        EASYPRIVACY_DOMAINS = set()


_thread = threading.Thread(target=load_easyprivacy_domains, daemon=True)
_thread.start()


def _host_matches_easyprivacy(host: str) -> bool:

    host = host.lower()
    for domain in EASYPRIVACY_DOMAINS:
        d = domain.lower()
        if not d:
            continue

        if host == d or host.endswith('.' + d):
            return True

        if d in host:
            return True
    return False


def _tokenize_host(host: str):

    if not host:
        return []
    return re.split(r'[.\-_]+', host.lower())


def _host_has_noise_token(host: str) -> bool:

    if not host:
        return False

    tokens = _tokenize_host(host)

    for t in tokens:
        if t in NOISE_HOST_TOKENS:
            return True

    if re.search(r'clients\d+', host):
        return True
    if re.search(r'gvt\d+', host):
        return True

    return False


def is_in_blocklist(host: str) -> bool:

    if not host:
        return False
    host = host.lower()

    if _host_has_noise_token(host):
        return True

    if _host_matches_easyprivacy(host):
        return True

    return False


def is_upgrade_request(flow: http.HTTPFlow) -> bool:
    connection = flow.request.headers.get("connection", "").lower()
    upgrade = flow.request.headers.get("upgrade", "").lower()

    return "upgrade" in connection or upgrade == "websocket"


def is_noise(flow: http.HTTPFlow) -> bool:

    try:
        host = (flow.request.host or "").lower()
    except Exception:
        host = ""

    if is_in_blocklist(host):
        return True

    if is_upgrade_request(flow):
        return True

    try:
        path = urlparse(flow.request.pretty_url or "").path.lower()
    except Exception:
        path = ""

    for kw in PATH_NOISE_KEYWORDS:
        if kw in path:
            return True

    report_header = flow.request.headers.get("report-to") or flow.request.headers.get("nel")
    if report_header:
        return True

    return False
