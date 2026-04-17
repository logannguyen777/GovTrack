"""
backend/src/agents/pii_filters.py
Shared PII detection and redaction module used by ConsultAgent and SummarizerAgent.

Patterns cover Vietnamese CMND/CCCD identity numbers, mobile phone numbers,
and e-mail addresses.  All patterns are widened to handle digits separated by
spaces or hyphens (common in scanned documents).

Usage:
    from backend.src.agents.pii_filters import redact, has_pii, PIILeakDetected
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("govflow.pii_filters")

# ── Pattern definitions ────────────────────────────────────────────────────

# CMND (9 digits) and CCCD (12 digits), optionally prefixed with leading 0
_BARE_ID_PATTERN = re.compile(r"\b0?\d{8,11}\b")

# Vietnamese mobile phones: 03x, 05x, 07x, 09x with optional hyphen/space separators.
# Handles groupings: 0xxx-xxx-xxx (10 digits with 4+3+3 grouping)
# and 0x-xxxx-xxxx or 0xxx-xxxx-xxx etc.
# Core requirement: starts with 0[3579], followed by 8 more digits with optional separators.
_PHONE_PATTERN = re.compile(
    r"0[3579]\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
)

# E-mail addresses (RFC-simplified)
_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)

# Labeled CCCD/CMND (context-aware, kept for backward compat with consult/summarizer)
_LABELED_ID_PATTERN = re.compile(
    r"(?:CCCD|CMND|CMT|[Ss]o\s+[Dd]inh\s+[Dd]anh|[Ss]o\s+[Cc]an\s+[Cc]uoc)"
    r"\s*:?\s*\d{9,12}"
)

# Labeled phone (handles both SDT and SĐT with Vietnamese diacritics)
_LABELED_PHONE_PATTERN = re.compile(
    r"(?:S[ĐD]T|[Ss]o\s+[Dd]ien\s+[Tt]hoai|[Ss]ố\s+điện\s+thoại|[Dd]ien\s+thoai|DT)\s*:?\s*"
    r"0[3579]\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{3,4}",
    re.UNICODE,
)

# Address detail
_ADDRESS_DETAIL_PATTERN = re.compile(
    r"(?:[Ss]o\s+nha|[Dd]uong|[Pp]huong|[Qq]uan|[Hh]uyen)\s+[\w\s,]{5,50}"
)

# Ordered: most-specific first so labeled patterns consume before bare ones
ALL_PII_PATTERNS: list[re.Pattern[str]] = [
    _LABELED_ID_PATTERN,
    _LABELED_PHONE_PATTERN,
    _ADDRESS_DETAIL_PATTERN,
    _EMAIL_PATTERN,
    _PHONE_PATTERN,
    _BARE_ID_PATTERN,
]

_PLACEHOLDER = "[REDACTED_PII]"


# ── Public API ─────────────────────────────────────────────────────────────


class PIILeakDetected(RuntimeError):
    """Raised when PII is still present in generated output after redaction."""


def redact(text: str) -> str:
    """
    Replace all detected PII occurrences with ``[REDACTED_PII]``.

    Applies patterns in specificity order (labeled → bare) so that
    the more-specific labeled forms are consumed first.
    """
    if not text:
        return text
    for pattern in ALL_PII_PATTERNS:
        text = pattern.sub(_PLACEHOLDER, text)
    return text


def has_pii(text: str) -> bool:
    """Return True if *text* still contains any PII pattern after redaction."""
    for pattern in ALL_PII_PATTERNS:
        if pattern.search(text):
            return True
    return False


def enforce_no_pii(text: str, context: str = "") -> str:
    """
    Run ``redact()``, then verify the result is clean.

    Args:
        text:    The text to check and clean.
        context: Caller description for logging (e.g. agent name + mode).

    Returns:
        Redacted text if clean.

    Raises:
        PIILeakDetected: If PII is still present after a full redaction pass.
    """
    cleaned = redact(text)
    if has_pii(cleaned):
        logger.warning(
            f"[PII] Leak detected in output from {context!r} — rejecting response"
        )
        raise PIILeakDetected(
            f"PII still present in output after redaction pass ({context})"
        )
    return cleaned
