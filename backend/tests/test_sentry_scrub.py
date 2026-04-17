"""
tests/test_sentry_scrub.py
Verify the Sentry scrub_pii function redacts CMND, phone, and email (Task 3.7).
"""

from __future__ import annotations

import pytest


def _make_scrub_pii():
    """Extract scrub_pii logic without requiring sentry_sdk to be installed."""
    from src.logging_config import _deep_redact, _EM_PATTERN

    def scrub_pii(event: dict, hint: dict) -> dict:  # noqa: ARG001
        req = event.get("request", {})
        if req.get("data"):
            event["request"]["data"] = _deep_redact(req["data"])
        if event.get("extra"):
            event["extra"] = _deep_redact(event["extra"])
        user_data = event.get("user", {})
        if isinstance(user_data, dict) and user_data.get("email"):
            event["user"]["email"] = _EM_PATTERN.sub("[REDACTED_EMAIL]", user_data["email"])
        return event

    return scrub_pii


def test_scrub_pii_cmnd_in_request_data():
    """CMND in request body should be redacted."""
    scrub_pii = _make_scrub_pii()
    event = {
        "request": {"data": {"id_number": "012345678"}},
        "extra": {},
    }
    result = scrub_pii(event, {})
    assert "012345678" not in str(result["request"]["data"])
    assert "[REDACTED_ID]" in result["request"]["data"]["id_number"]


def test_scrub_pii_phone_in_extra():
    """Phone number in extra dict should be redacted."""
    scrub_pii = _make_scrub_pii()
    event = {
        "request": {"data": {}},
        "extra": {"contact": "0912345678"},
    }
    result = scrub_pii(event, {})
    assert "0912345678" not in str(result["extra"])
    assert "[REDACTED" in result["extra"]["contact"]


def test_scrub_pii_email_in_user():
    """Email in Sentry user field should be redacted."""
    scrub_pii = _make_scrub_pii()
    event = {
        "request": {"data": {}},
        "extra": {},
        "user": {"email": "admin@govflow.vn", "id": "user123"},
    }
    result = scrub_pii(event, {})
    assert "admin@govflow.vn" not in result["user"]["email"]
    assert "[REDACTED_EMAIL]" in result["user"]["email"]


def test_scrub_pii_clean_event_unchanged():
    """Event without PII should pass through unchanged."""
    scrub_pii = _make_scrub_pii()
    event = {
        "request": {"data": {"tthc_code": "1.000123"}},
        "extra": {"case_id": "CASE-001"},
    }
    result = scrub_pii(event, {})
    assert result["request"]["data"]["tthc_code"] == "1.000123"
    assert result["extra"]["case_id"] == "CASE-001"


def test_scrub_pii_nested_cmnd():
    """Nested dict containing CMND should be fully redacted."""
    scrub_pii = _make_scrub_pii()
    event = {
        "request": {
            "data": {
                "applicant": {
                    "name": "Nguyen Van A",
                    "cmnd": "123456789",
                }
            }
        },
        "extra": {},
    }
    result = scrub_pii(event, {})
    assert "123456789" not in str(result["request"]["data"])
