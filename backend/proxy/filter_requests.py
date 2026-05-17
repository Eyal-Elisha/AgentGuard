from mitmproxy import http

from backend.custom_blacklist import custom_blacklist_matches
from backend.proxy.filters.action_filter import is_enforced_request_method
from backend.proxy.filters.browser_filter import is_browser_user_agent
from backend.proxy.filters.noise_filter import is_noise
from backend.proxy.rule_engine import get_custom_blacklist
from backend.settings import get_api_port, get_frontend_port


def _is_loopback_host(host: str) -> bool:
    h = (host or "").lower().strip()
    if len(h) >= 2 and h[0] == "[" and h[-1] == "]":
        h = h[1:-1]
    return h in ("127.0.0.1", "localhost", "::1")


def _is_local_agentguard_service(flow: http.HTTPFlow) -> bool:
    """Do not MITM-enforce traffic to our own dashboard or decision API (loopback)."""
    if not _is_loopback_host(flow.request.host):
        return False
    try:
        port = int(getattr(flow.request, "port", None))
    except (TypeError, ValueError):
        return False
    return port in (get_api_port(), get_frontend_port())


def should_forward(flow: http.HTTPFlow) -> bool:
    """Forward browser document/action traffic unless it is known noise."""

    if _is_local_agentguard_service(flow):
        return False

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