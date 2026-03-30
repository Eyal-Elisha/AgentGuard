from .browser_filter import is_browser_user_agent
from .noise_filter import is_noise
from .action_filter import is_action_request
from .static_filter import is_likely_static_subresource
from .sec_fetch_filter import sec_fetch_is_subresource
from .content_type_filter import is_html_response, is_binary_media_response

# Also import submodules so `backend.proxy.filters.response_logging` style imports
# can be resolved by the static analyzer and convenience imports.
from . import (
    content_type_filter,
    response_logging,
    response_eligibility,
    response_filter,
    navigation_signals,
    sec_fetch_filter,
    static_filter,
)

__all__ = [
    "is_browser_user_agent",
    "is_noise",
    "is_action_request",
    "is_likely_static_subresource",
    "sec_fetch_is_subresource",
    "is_html_response",
    "is_binary_media_response",
]
