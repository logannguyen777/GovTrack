"""
tests/test_oss_sts.py
Verify STS credential caching in oss_service (Task 3.10).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.oss_service import (
    _sts_cache,
    _sts_cache_valid,
    _STS_CACHE_TTL_S,
    get_sts_credentials,
)


def _clear_sts_cache():
    """Reset the in-module STS cache between tests."""
    _sts_cache.clear()


# ---------------------------------------------------------------------------
# Cache validity
# ---------------------------------------------------------------------------


def test_cache_invalid_when_empty():
    _clear_sts_cache()
    assert _sts_cache_valid() is False


def test_cache_valid_when_fresh():
    _clear_sts_cache()
    _sts_cache.update(
        {
            "AccessKeyId": "test-ak",
            "AccessKeySecret": "test-sk",
            "SecurityToken": "test-st",
            "_expiry": time.monotonic() + 1000,
        }
    )
    assert _sts_cache_valid() is True


def test_cache_invalid_when_expired():
    _clear_sts_cache()
    _sts_cache.update(
        {
            "AccessKeyId": "old-ak",
            "AccessKeySecret": "old-sk",
            "SecurityToken": "old-st",
            "_expiry": time.monotonic() - 1,  # already expired
        }
    )
    assert _sts_cache_valid() is False


# ---------------------------------------------------------------------------
# get_sts_credentials — local mode returns static creds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_local_mode_returns_static_creds():
    """In local dev mode, get_sts_credentials returns configured static creds."""
    _clear_sts_cache()
    from src.config import settings

    # settings.govflow_env is "local" in test environment
    assert settings.govflow_env != "cloud"

    creds = await get_sts_credentials()
    assert "AccessKeyId" in creds
    assert "AccessKeySecret" in creds
    # Local mode returns the configured access key
    assert creds["AccessKeyId"] == settings.oss_access_key_id


# ---------------------------------------------------------------------------
# get_sts_credentials — cloud mode calls _refresh_sts_credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cloud_mode_uses_cache_on_second_call():
    """Second call should return cached creds without hitting STS again."""
    _clear_sts_cache()

    _sts_cache.update(
        {
            "AccessKeyId": "cached-ak",
            "AccessKeySecret": "cached-sk",
            "SecurityToken": "cached-st",
            "_expiry": time.monotonic() + 3000,
        }
    )

    with patch("src.services.oss_service.settings") as mock_settings:
        mock_settings.govflow_env = "cloud"
        mock_settings.oss_sts_role_arn = "acs:ram::123456:role/TestRole"
        mock_settings.oss_access_key_id = "static-ak"
        mock_settings.oss_access_key_secret = "static-sk"

        creds = await get_sts_credentials()

    assert creds["AccessKeyId"] == "cached-ak"
    assert creds["SecurityToken"] == "cached-st"


@pytest.mark.asyncio
async def test_cloud_mode_refreshes_when_expired():
    """When cache is expired, get_sts_credentials calls _refresh_sts_credentials."""
    _clear_sts_cache()
    # Set expired cache
    _sts_cache.update(
        {
            "AccessKeyId": "old-ak",
            "AccessKeySecret": "old-sk",
            "SecurityToken": "old-st",
            "_expiry": time.monotonic() - 1,
        }
    )

    mock_creds = {
        "AccessKeyId": "new-ak",
        "AccessKeySecret": "new-sk",
        "SecurityToken": "new-st",
    }

    with patch("src.services.oss_service.settings") as mock_settings:
        mock_settings.govflow_env = "cloud"
        mock_settings.oss_sts_role_arn = "acs:ram::123456:role/TestRole"
        mock_settings.oss_access_key_id = "static-ak"
        mock_settings.oss_access_key_secret = "static-sk"

        with patch(
            "src.services.oss_service._refresh_sts_credentials",
            new_callable=AsyncMock,
            return_value=mock_creds,
        ) as mock_refresh:
            creds = await get_sts_credentials()

        mock_refresh.assert_called_once()

    assert creds["AccessKeyId"] == "new-ak"


# ---------------------------------------------------------------------------
# SSE-KMS headers
# ---------------------------------------------------------------------------


def test_sse_kms_headers_when_key_set():
    from src.services.oss_service import sse_kms_headers
    from unittest.mock import patch

    with patch("src.services.oss_service.settings") as mock_settings:
        mock_settings.oss_kms_key_id = "test-kms-key-id"
        headers = sse_kms_headers()

    assert headers.get("x-oss-server-side-encryption") == "KMS"
    assert headers.get("x-oss-server-side-encryption-key-id") == "test-kms-key-id"


def test_sse_kms_headers_empty_when_no_key():
    from src.services.oss_service import sse_kms_headers
    from unittest.mock import patch

    with patch("src.services.oss_service.settings") as mock_settings:
        mock_settings.oss_kms_key_id = None
        headers = sse_kms_headers()

    assert headers == {}
