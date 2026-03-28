from mitmproxy import http
import requests

EASYPRIVACY_URL = "https://easylist.to/easylist/easyprivacy.txt"

EASYPRIVACY_DOMAINS = set()

def load_easyprivacy_domains():
    global EASYPRIVACY_DOMAINS

    try:
        print("[AgentGuard] Loading EasyPrivacy list...")
        response = requests.get(EASYPRIVACY_URL, timeout=10)

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


load_easyprivacy_domains()

def is_in_blocklist(host: str) -> bool:
    return any(domain in host for domain in EASYPRIVACY_DOMAINS)


def is_upgrade_request(flow: http.HTTPFlow) -> bool:
    connection = flow.request.headers.get("connection", "").lower()
    upgrade = flow.request.headers.get("upgrade", "").lower()

    return "upgrade" in connection or upgrade == "websocket"

def is_noise(flow: http.HTTPFlow) -> bool:
    host = flow.request.host.lower()

    if is_in_blocklist(host):
        return True

    if is_upgrade_request(flow):
        return True

    return False