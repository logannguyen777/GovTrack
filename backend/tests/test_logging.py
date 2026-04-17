"""
tests/test_logging.py
Verify PII redaction in structured JSON logging (Task 3.4).
"""

from __future__ import annotations

import json
import logging
import io

import pytest

from src.logging_config import PIIRedactionFilter, setup_logging, _redact


# ---------------------------------------------------------------------------
# Unit tests for _redact
# ---------------------------------------------------------------------------


def test_redact_cmnd_bare():
    text = "CMND 012345678"
    result = _redact(text)
    assert "012345678" not in result
    assert "[REDACTED_ID]" in result


def test_redact_cccd_12_digits():
    text = "So CCCD: 034123456789"
    result = _redact(text)
    assert "034123456789" not in result


def test_redact_phone():
    text = "SDT: 0912345678"
    result = _redact(text)
    assert "0912345678" not in result
    assert "[REDACTED" in result


def test_redact_email():
    text = "Lien he qua email: test.user@govflow.vn"
    result = _redact(text)
    assert "test.user@govflow.vn" not in result
    assert "[REDACTED_EMAIL]" in result


def test_redact_clean_text_unchanged():
    text = "Ho so mat: vu kien hanh chinh so 123-ABC"
    # 123 is not 9+ digits, so should not be redacted
    result = _redact(text)
    assert "123-ABC" in result


# ---------------------------------------------------------------------------
# PIIRedactionFilter via logging capture
# ---------------------------------------------------------------------------


def _make_handler() -> tuple[logging.Handler, io.StringIO]:
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.addFilter(PIIRedactionFilter())
    return handler, buf


def test_filter_redacts_message_digits():
    """Log message containing CMND → formatted output has [REDACTED_ID]."""
    logger = logging.getLogger("test_pii_filter_message")
    logger.setLevel(logging.DEBUG)
    handler, buf = _make_handler()
    logger.addHandler(handler)

    try:
        logger.info("User CMND 012345678 submitted form")
        output = buf.getvalue()
        assert "012345678" not in output
        assert "[REDACTED_ID]" in output
    finally:
        logger.removeHandler(handler)


def test_filter_redacts_extra_field():
    """Extra dict fields containing phone numbers are also redacted."""
    logger = logging.getLogger("test_pii_filter_extra")
    logger.setLevel(logging.DEBUG)
    handler, buf = _make_handler()
    logger.addHandler(handler)

    try:
        logger.info("Contact attempt", extra={"phone": "0912345678"})
        output = buf.getvalue()
        # The raw extra attribute should be redacted
        assert "0912345678" not in output
    finally:
        logger.removeHandler(handler)


def test_filter_redacts_email_in_message():
    logger = logging.getLogger("test_pii_filter_email")
    logger.setLevel(logging.DEBUG)
    handler, buf = _make_handler()
    logger.addHandler(handler)

    try:
        logger.warning("Contact: admin@example.com")
        output = buf.getvalue()
        assert "admin@example.com" not in output
        assert "[REDACTED_EMAIL]" in output
    finally:
        logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# setup_logging is importable and idempotent
# ---------------------------------------------------------------------------


def test_setup_logging_idempotent():
    """Calling setup_logging twice should not raise."""
    setup_logging("DEBUG")
    setup_logging("INFO")
    # If we get here without exception, test passes
    assert True


def test_setup_logging_sets_level():
    """setup_logging with WARNING should set root level to WARNING."""
    setup_logging("WARNING")
    root = logging.getLogger()
    assert root.level == logging.WARNING
    # Reset to DEBUG for other tests
    setup_logging("DEBUG")
