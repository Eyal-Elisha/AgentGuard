"""Shared constants for outbound prompt augmentation."""

from __future__ import annotations

FALLBACK_INSTRUCTION = (
    "If AgentGuard blocks, flags, or cannot access a website because it is unsafe, "
    "suspicious, phishing-related, or inaccessible, do not stop the task. "
    "Identify at least one trusted alternative website that can accomplish the same goal as the one the user asked for, select "
    "the most relevant alternative, navigate to that different website instead, and continue "
    "the task using it. If the blocked site was on http, you may try the exact same domain once over https before searching elsewhere. "
    "Do not retry the blocked domain, its subdomains, any mirrored variant, or any URL that only changes www/canonical/typo-like details. "
    "Do not try the same site under a different host name. Only return control to the user after attempting to complete the original objective "
    "through a truly different trusted alternative if the https version does not work. "
    "Never attempt to access, bypass, or revisit the blocked resource. Always suggest and show a different website that accomplishes the same goal."
)
