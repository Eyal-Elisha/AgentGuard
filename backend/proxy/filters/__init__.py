"""The predicates behind `should_forward`, one question per module.
`filter_requests.py` composes them in the order the addon applies them.
"""

from .browser_filter import is_browser_user_agent
from .noise_filter import is_noise
from .action_filter import is_enforced_request_method
from .static_filter import is_likely_static_subresource
from .sec_fetch_filter import sec_fetch_is_subresource
from .content_type_filter import is_binary_media_response

__all__ = [
    "is_browser_user_agent",
    "is_noise",
    "is_enforced_request_method",
    "is_likely_static_subresource",
    "sec_fetch_is_subresource",
    "is_binary_media_response",
]
