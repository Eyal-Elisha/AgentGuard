from mitmproxy import http
import re

from backend.proxy.filters.action_filter import is_action_request
from backend.proxy.filters.noise_filter import is_noise


def is_browser_user_agent(user_agent: str) -> bool:
    if not user_agent:
        return False

    if "electron/" in user_agent.lower():
        return False

    browser_patterns = ["chrome/", "firefox/", "safari/", "edg/"]
    return any(re.search(pat, user_agent, re.IGNORECASE) for pat in browser_patterns)


# MAIN ENTRY POINT
def should_forward(flow: http.HTTPFlow) -> bool:
    ua = flow.request.headers.get("user-agent", "")

    # 1. Only browser traffic
    if not is_browser_user_agent(ua):
        return False

    # 2. Remove noise (delegated)
    if is_noise(flow):
        return False

    # 3. Only meaningful actions (delegated)
    if not is_action_request(flow):
        return False

    return True