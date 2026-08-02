"""Outbound prompt augmentation.

When the agent's browser POSTs a prompt to an LLM API, the proxy appends an
instruction telling the agent to look for a trusted alternative site if a
destination is blocked, so a block becomes a redirection rather than a dead
end. This rewrites the agent's own request body, not the page it is reading.
"""

from .augment import augment_request_body
from .constants import FALLBACK_INSTRUCTION

__all__ = ["augment_request_body", "FALLBACK_INSTRUCTION"]

