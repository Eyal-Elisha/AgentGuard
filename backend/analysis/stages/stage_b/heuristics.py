"""Keyword-based fallback scorers for Stage B semantic rules.

These are used when no trained sklearn artifact is present for a rule's
`model_id`. They produce a probability-like score in [0, 1] derived from a
small bag of high-precision phrases, so the pipeline yields useful signal
out-of-the-box before the operator runs
scripts/train_semantic_models.py.

Each entry is a list of (regex, weight) tuples. Total weight is squashed into
[0, 1] via a logistic-like saturation so the output remains comparable to the
real classifier's `predict_proba` output.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

# Compiled at import time — case-insensitive whole-phrase matches.
_PHISHING_TERMS: List[Tuple[re.Pattern[str], float]] = [
    (re.compile(r"\bverify\s+(?:your\s+)?account\b", re.I), 1.2),
    (re.compile(r"\bconfirm\s+(?:your\s+)?identity\b", re.I), 1.2),
    (re.compile(r"\bunusual\s+(?:sign[- ]?in|activity|login)\b", re.I), 1.1),
    (re.compile(r"\baccount\s+(?:suspended|locked|disabled)\b", re.I), 1.4),
    (re.compile(r"\bclick\s+(?:the\s+)?(?:link|button)\s+below\b", re.I), 0.9),
    (re.compile(r"\bre[- ]?enter\s+your\s+password\b", re.I), 1.3),
    (re.compile(r"\b(?:update|reset)\s+your\s+password\b", re.I), 1.0),
    (re.compile(r"\bwithin\s+\d+\s+(?:hours?|minutes?)\b", re.I), 0.7),
    (re.compile(r"\bsecurity\s+alert\b", re.I), 0.8),
    (re.compile(r"\bsuspicious\s+(?:activity|sign[- ]?in)\b", re.I), 1.0),
    (re.compile(r"\bdouble[- ]?check\s+your\s+(?:account|details)\b", re.I), 0.8),
    (re.compile(r"\b(?:one[- ]?time|2[- ]?factor)\s+(?:code|password|pin)\b", re.I), 0.8),
    (re.compile(r"\b(?:wire|payment|invoice)\s+(?:transfer|details)\b", re.I), 0.7),
    (re.compile(r"\bmfa\s+code\b", re.I), 0.8),
    (re.compile(r"input:password", re.I), 0.6),
]

_PROMPT_INJECTION_TERMS: List[Tuple[re.Pattern[str], float]] = [
    (re.compile(r"\bignore\s+(?:all\s+|the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts?|messages?)\b", re.I), 1.6),
    (re.compile(r"\bdisregard\s+(?:all\s+|the\s+|your\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts?)\b", re.I), 1.6),
    (re.compile(r"\b(?:act|behave|respond)\s+as\s+(?:if\s+you\s+are\s+)?(?:system|developer|admin|root|jailbroken)\b", re.I), 1.4),
    (re.compile(r"\byou\s+are\s+now\s+(?:a\s+|an\s+)?(?:dan|jailbroken|unrestricted)\b", re.I), 1.5),
    (re.compile(r"\breveal\s+(?:your\s+|the\s+)?(?:system|hidden|secret)\s+prompt\b", re.I), 1.6),
    (re.compile(r"\b(?:bypass|override|ignore)\s+(?:the\s+)?(?:safety|policy|guardrails?|restrictions?)\b", re.I), 1.5),
    (re.compile(r"\bdo\s+anything\s+now\b", re.I), 1.2),
    (re.compile(r"\b(?:print|output|show|reveal)\s+(?:your\s+|the\s+)?(?:initial|system)\s+instructions\b", re.I), 1.5),
    (re.compile(r"\bnew\s+instructions?\s*:", re.I), 1.0),
    (re.compile(r"\bend\s+of\s+(?:system\s+)?prompt\b", re.I), 1.1),
    (re.compile(r"\bpretend\s+(?:you\s+are|to\s+be)\b", re.I), 0.6),
    (re.compile(r"###\s*(?:instructions?|system)", re.I), 0.8),
    (re.compile(r"\b<\|im_start\|>|<\|im_end\|>", re.I), 1.0),
]


def _score(text: str, terms: List[Tuple[re.Pattern[str], float]]) -> float:
    if not text:
        return 0.0
    total = 0.0
    for pattern, weight in terms:
        if pattern.search(text):
            total += weight
    if total <= 0.0:
        return 0.0
    # Logistic squash so 1 strong hit ~0.55, 2 hits ~0.75, ≥4 saturates ~0.95.
    return 1.0 / (1.0 + math.exp(-(total - 1.0)))


def heuristic_score(model_id: str, text: str) -> float:
    if model_id == "phishing":
        return _score(text, _PHISHING_TERMS)
    if model_id == "prompt_injection":
        return _score(text, _PROMPT_INJECTION_TERMS)
    return 0.0


HEURISTIC_MODEL_IDS: Dict[str, str] = {
    "phishing": "phishing-keyword-bag-v1",
    "prompt_injection": "prompt-injection-keyword-bag-v1",
}
