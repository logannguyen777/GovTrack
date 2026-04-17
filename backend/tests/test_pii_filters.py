"""
tests/test_pii_filters.py
Golden tests for the shared PII filter module.

Patterns under test:
  - CMND (9 digits) / CCCD (12 digits) bare IDs
  - Vietnamese mobile phone numbers with hyphen/space separators
  - Email addresses
  - Labeled ID and phone patterns
  - Post-redaction hard check (PIILeakDetected)
"""

from __future__ import annotations

import pytest

from src.agents.pii_filters import (
    PIILeakDetected,
    enforce_no_pii,
    has_pii,
    redact,
)

_PH = "[REDACTED_PII]"


# ---------------------------------------------------------------------------
# Golden test from spec
# ---------------------------------------------------------------------------


def test_golden_all_three_types_redacted():
    """
    Spec golden test: 'CMND 012345678, SĐT 0357-123-456, email x@y.vn'
    → all 3 redacted to [REDACTED_PII].
    """
    text = "CMND 012345678, SĐT 0357-123-456, email x@y.vn"
    result = redact(text)
    assert _PH in result
    # None of the original PII should remain
    assert "012345678" not in result
    assert "0357-123-456" not in result
    assert "x@y.vn" not in result


# ---------------------------------------------------------------------------
# CMND / CCCD bare ID patterns
# ---------------------------------------------------------------------------


def test_cmnd_9_digits():
    assert _PH in redact("So CMND: 012345678")


def test_cccd_12_digits():
    assert _PH in redact("CCCD: 012345678901")


def test_bare_9_digit_id():
    """9-digit bare ID (CMND) should be redacted."""
    result = redact("Ho so cua nguoi co so 012345678 da nop.")
    assert "012345678" not in result


def test_bare_12_digit_id():
    """12-digit bare ID (CCCD) should be redacted."""
    result = redact("So the can cuoc: 034202012345")
    assert "034202012345" not in result


# ---------------------------------------------------------------------------
# Phone number patterns
# ---------------------------------------------------------------------------


def test_phone_no_separator():
    """Standard phone without separator."""
    result = redact("SDT: 0357123456")
    assert "0357123456" not in result


def test_phone_with_hyphen():
    """Phone with hyphens (as in golden test)."""
    result = redact("0357-123-456")
    assert "0357-123-456" not in result


def test_phone_with_spaces():
    """Phone with spaces."""
    result = redact("SDT 0357 123 456")
    assert "0357 123 456" not in result
    assert _PH in result


def test_phone_09_prefix():
    result = redact("Lien he 0912345678")
    assert "0912345678" not in result


def test_phone_03_prefix():
    result = redact("Lien he 0345678901")
    assert "0345678901" not in result


# ---------------------------------------------------------------------------
# Email patterns
# ---------------------------------------------------------------------------


def test_email_simple():
    result = redact("Email: user@example.com")
    assert "user@example.com" not in result
    assert _PH in result


def test_email_with_dots():
    result = redact("Gui den nguyen.van.a@gov.vn")
    assert "nguyen.van.a@gov.vn" not in result


def test_email_uppercase():
    result = redact("ADMIN@COMPANY.VN")
    assert "ADMIN@COMPANY.VN" not in result


# ---------------------------------------------------------------------------
# has_pii
# ---------------------------------------------------------------------------


def test_has_pii_true():
    assert has_pii("CCCD: 012345678901") is True


def test_has_pii_false_after_redact():
    clean = redact("Lien he 0357123456")
    assert has_pii(clean) is False


def test_has_pii_email():
    assert has_pii("user@mail.com") is True


# ---------------------------------------------------------------------------
# enforce_no_pii
# ---------------------------------------------------------------------------


def test_enforce_no_pii_clean_text():
    """Clean text passes through unchanged."""
    text = "Ho so da duoc xu ly."
    result = enforce_no_pii(text, context="test")
    assert result == text


def test_enforce_no_pii_redacts_and_passes():
    """Text with PII gets redacted and passes the check."""
    text = "CCCD: 012345678901"
    result = enforce_no_pii(text, context="test")
    assert "012345678901" not in result


def test_enforce_no_pii_raises_on_persistent_leak(monkeypatch):
    """
    If redact() fails to clean the text (edge case / bypass), enforce_no_pii
    raises PIILeakDetected.  Simulate by monkeypatching redact to return the
    input unchanged.
    """
    import src.agents.pii_filters as pii_module

    original_redact = pii_module.redact

    def _noop_redact(text: str) -> str:
        return text  # Pretend redaction did nothing

    monkeypatch.setattr(pii_module, "redact", _noop_redact)

    with pytest.raises(PIILeakDetected):
        pii_module.enforce_no_pii("CCCD 034202012345", context="test")

    # Restore
    monkeypatch.setattr(pii_module, "redact", original_redact)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_string():
    assert redact("") == ""


def test_none_like_empty():
    # enforce_no_pii("") should return "" without raising
    result = enforce_no_pii("", context="test")
    assert result == ""


def test_non_pii_numbers_not_redacted():
    """Short numbers (< 9 digits) must NOT be redacted."""
    text = "Co 5 nguoi, tong 12345 dong."
    result = redact(text)
    # 5 and 12345 are too short to trigger the 8-11 digit pattern
    assert "12345" in result
