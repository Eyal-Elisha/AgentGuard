"""Letting the user past a Warn without putting them in a redirect loop.

Cookies are unreliable in an HTTPS-via-MITM setup, so none are used. The flow
is entirely server-side, in two halves:

  tokens            the interstitial's "Continue anyway" link points at
                    `originalUrl?_agentguard_bypass=<token>`. The proxy
                    validates and consumes the token, then 302s to the clean
                    URL so it never lingers in the address bar.

  continue_profile  redeeming a token allows the one document load that
                    follows, plus a short window for the page's subresources,
                    to skip the interstitial.

The backend is consulted on every request throughout — events are recorded and
contextual rules still see the session history. Only the warning UI is
suppressed, and only for those narrow cases.
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
