from mitmproxy import http

from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.filters.action_filter import is_enforced_request_method
from backend.proxy.filters.browser_filter import is_browser_user_agent
from backend.proxy.filters.noise_filter import is_noise
from backend.proxy.rule_engine import get_custom_blacklist


def should_forward(flow: http.HTTPFlow) -> bool:
    """Forward browser document/action traffic unless it is known noise."""

    if not is_browser_user_agent(flow.request.headers.get("user-agent", "")):
        return False

    if not is_enforced_request_method(flow):
        return False

    # EasyPrivacy "noise" skips enforcement; custom blacklist must always win.
    if custom_blacklist_matches(flow.request.host, flow.request.pretty_url, get_custom_blacklist()):
        return True

    if is_noise(flow):
        return False

    return True