"""Pulls the text Stage B classifies from the title, visible text, form tokens and
stripped HTML. Secrets and PII are redacted here, before anything reaches the
classifier or the log.
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup

from backend.feature_extraction.feature_extractor import ExtractedFeatures


_REDACTED = " <REDACTED> "


_SANITIZERS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Emails
    (re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"), _REDACTED),
    # 13–19 digit runs (credit-card-ish), optionally space/dash separated
    (re.compile(r"\b(?:\d[ \-]?){13,19}\b"), _REDACTED),
    # Long opaque tokens (JWT-ish or API keys: 24+ url-safe chars)
    (re.compile(r"\b[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), _REDACTED),  # JWT
    (re.compile(r"\b(?:sk|pk|ghp|xox[abpors])_[A-Za-z0-9_\-]{16,}\b"), _REDACTED),
    # Bearer tokens in plain text (run before the generic key=value catcher so
    # it doesn't stop at the "Bearer" word and leave the actual token behind).
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_\-\.=]+"), "Bearer <REDACTED>"),
    # key=value pairs that look secret-bearing
    (re.compile(r"(?i)(password|passwd|pwd|secret|api[_\-]?key|token|authorization)\s*[:=]\s*\S+"), r"\1=<REDACTED>"),
    # Generic long digit runs (≥9 — phone, account numbers)
    (re.compile(r"\b\d{9,}\b"), _REDACTED),
)


def _strip_noise(html: str) -> str:
    """Reparse the body to drop script/style blocks before vectorization."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def _form_tokens(features: ExtractedFeatures) -> str:
    if not features.dom:
        return ""
    parts: list[str] = []
    for form in features.dom.forms:
        if form.action:
            parts.append(f"form-action:{form.action}")
        for inp in form.inputs:
            kind = inp.get("type") or "text"
            name = inp.get("name") or ""
            ident = inp.get("id") or ""
            tok = " ".join(t for t in (f"input:{kind}", name, ident) if t)
            parts.append(tok)
    return " ".join(parts)


def extract_semantic_text(features: ExtractedFeatures) -> str:
    """Build the cleaned, joined text used as input to semantic classifiers."""
    chunks: list[str] = []
    if features.dom:
        if features.dom.page_title:
            chunks.append(features.dom.page_title)
        if features.dom.all_text_content:
            chunks.append(features.dom.all_text_content)
    if features.raw_body:
        chunks.append(_strip_noise(features.raw_body))
    chunks.append(_form_tokens(features))
    text = " ".join(c for c in chunks if c)
    return sanitize(text)


def sanitize(text: Optional[str]) -> str:
    """Redact obvious PII / secrets before classification."""
    if not text:
        return ""
    cleaned = text
    for pattern, replacement in _SANITIZERS:
        cleaned = pattern.sub(replacement, cleaned)
    # Collapse runs of whitespace introduced by redactions.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
