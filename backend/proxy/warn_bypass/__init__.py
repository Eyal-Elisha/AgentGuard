"""Letting the user past a Warn without a redirect loop, entirely server-side
since cookies are unreliable under MITM. `tokens` mints and consumes them,
`continue_profile` holds what redeeming one allows.
"""

from .continue_profile import (
    DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS,
    EXACT_ALLOW_TTL_SECONDS,
    clear_continue_anyway_for_host,
    open_subresource_window,
    register_continue_anyway,
    should_suppress_warn_interstitial,
    subresource_window_active,
)
from .tokens import (
    DEFAULT_TOKEN_TTL_SECONDS,
    WarnBypassStore,
    consume_bypass_token,
    mint_bypass_token,
)
from .urls import BYPASS_QUERY_PARAM, normalize_url, strip_query_param

__all__ = [
    "BYPASS_QUERY_PARAM",
    "DEFAULT_SUBRESOURCE_SUPPRESS_SECONDS",
    "DEFAULT_TOKEN_TTL_SECONDS",
    "EXACT_ALLOW_TTL_SECONDS",
    "WarnBypassStore",
    "clear_continue_anyway_for_host",
    "consume_bypass_token",
    "mint_bypass_token",
    "normalize_url",
    "open_subresource_window",
    "register_continue_anyway",
    "should_suppress_warn_interstitial",
    "strip_query_param",
    "subresource_window_active",
]
