"""The predicates behind `should_forward` — one question per module.

Each answers a single yes/no about a flow. `filter_requests.py` is what
composes them into the order the addon actually applies.
"""

from .browser_filter import is_browser_user_agent
from .noise_filter import is_noise
from .action_filter import is_action_request
from .static_filter import is_likely_static_subresource
from .sec_fetch_filter import sec_fetch_is_subresource
from .content_type_filter import is_binary_media_response

__all__ = [
    "is_browser_user_agent",
    "is_noise",
    "is_action_request",
    "is_likely_static_subresource",
    "sec_fetch_is_subresource",
    "is_binary_media_response",
]
