from mitmproxy import http
import re

from backend.proxy.filters.browser_filter import is_browser_user_agent
from backend.proxy.filters.action_filter import is_action_request
from backend.proxy.filters.noise_filter import is_noise

def should_forward(flow: http.HTTPFlow) -> bool:
    ua = flow.request.headers.get("user-agent", "")

    if not is_browser_user_agent(ua):
        return False

    if is_noise(flow):
        return False

    if not is_action_request(flow):
        return False

    return True