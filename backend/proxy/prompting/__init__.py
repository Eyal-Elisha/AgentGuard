"""Appends an instruction to outbound LLM prompts telling the agent to look for a
trusted alternative when a site is blocked. Rewrites the agent's own request
body, not the page it is reading.
"""

from .augment import augment_request_body
from .constants import FALLBACK_INSTRUCTION

__all__ = ["augment_request_body", "FALLBACK_INSTRUCTION"]

