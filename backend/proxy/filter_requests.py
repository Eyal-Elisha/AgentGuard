from mitmproxy import http

from backend.proxy.filters.action_filter import is_enforced_request_method
from backend.proxy.filters.browser_filter import is_browser_user_agent
from backend.proxy.filters.noise_filter import is_noise
from backend.proxy.policy_engine import flow_matches_custom_blacklist


def should_forward(flow: http.HTTPFlow) -> bool:
    """Forward browser document/action traffic unless it is known noise."""
    ua = flow.request.headers.get("user-agent", "")

    if not is_browser_user_agent(ua):
        return False

    if not is_enforced_request_method(flow):
        return False

    # EasyPrivacy "noise" skips enforcement; custom blacklist must always win.
    if flow_matches_custom_blacklist(flow):
        return True

    if is_noise(flow):
        return False

    return True