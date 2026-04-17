"""
backend/src/services/oss_service.py
OSS operations with STS temporary credentials, SSE-KMS, and configurable TTLs.

Architecture:
- Cloud (govflow_env == "cloud"): uses oss2 + Alibaba Cloud STS AssumeRole.
  STS credentials are cached in-memory with a 3000s TTL (refresh before 3600s expiry).
- Local / dev: falls through to boto3/MinIO presigned URLs (no STS).

SSE-KMS encryption headers are applied on all PUT operations when
settings.oss_kms_key_id is set.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ..config import settings

logger = logging.getLogger("govflow.oss_service")

# ---------------------------------------------------------------------------
# STS credential cache
# ---------------------------------------------------------------------------

_sts_cache: dict[str, Any] = {}
_STS_CACHE_TTL_S: int = 3000  # refresh 600s before 3600s expiry


def _sts_cache_valid() -> bool:
    expiry: float | None = _sts_cache.get("_expiry")
    if expiry is None:
        return False
    return time.monotonic() < expiry


async def get_sts_credentials() -> dict[str, str]:
    """Return STS temporary credentials for OSS access.

    Returns a dict with keys: AccessKeyId, AccessKeySecret, SecurityToken.
    Credentials are cached for _STS_CACHE_TTL_S seconds.

    Falls back to static settings (access_key / secret_key) in local mode.
    """
    if settings.govflow_env != "cloud" or not settings.oss_sts_role_arn:
        # Local dev: return static credentials
        return {
            "AccessKeyId": settings.oss_access_key_id,
            "AccessKeySecret": settings.oss_access_key_secret,
            "SecurityToken": "",
        }

    if _sts_cache_valid():
        return {
            "AccessKeyId": _sts_cache["AccessKeyId"],
            "AccessKeySecret": _sts_cache["AccessKeySecret"],
            "SecurityToken": _sts_cache["SecurityToken"],
        }

    return await _refresh_sts_credentials()


async def _refresh_sts_credentials() -> dict[str, str]:
    """Call Alibaba Cloud STS AssumeRole and cache the result."""
    import asyncio

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _call_sts_sync)

    creds = result["Credentials"]
    _sts_cache.update(
        {
            "AccessKeyId": creds["AccessKeyId"],
            "AccessKeySecret": creds["AccessKeySecret"],
            "SecurityToken": creds["SecurityToken"],
            "_expiry": time.monotonic() + _STS_CACHE_TTL_S,
        }
    )

    logger.info(
        "STS credentials refreshed, expiry in %ds", _STS_CACHE_TTL_S
    )
    return {
        "AccessKeyId": creds["AccessKeyId"],
        "AccessKeySecret": creds["AccessKeySecret"],
        "SecurityToken": creds["SecurityToken"],
    }


def _call_sts_sync() -> dict[str, Any]:
    """Synchronous STS AssumeRole call (runs in thread executor)."""
    try:
        import base64
        import datetime
        import hashlib
        import hmac

        # Alibaba Cloud STS via alibabacloud-sts20150401 SDK or alibabacloud-credentials
        # Since the SDK may not be installed, we use a direct HTTP call via requests.
        import json
        import urllib.parse
        import urllib.request
        import uuid as _uuid

        import oss2  # noqa: F401 — ensure oss2 is available

        access_key_id = settings.oss_access_key_id
        access_key_secret = settings.oss_access_key_secret
        role_arn = settings.oss_sts_role_arn
        session_name = "GovFlowOSS"
        duration_seconds = 3600

        # STS endpoint
        endpoint = "https://sts.aliyuncs.com"

        # Build canonical request for HMAC-SHA1 signing (Alibaba Cloud v1 API)
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        nonce = str(_uuid.uuid4())

        params: dict[str, str] = {
            "Action": "AssumeRole",
            "Version": "2015-04-01",
            "Format": "JSON",
            "AccessKeyId": access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": nonce,
            "SignatureVersion": "1.0",
            "Timestamp": timestamp,
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": str(duration_seconds),
        }

        # Canonicalized query string
        sorted_params = sorted(params.items())
        encoded = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
            for k, v in sorted_params
        )
        _root = urllib.parse.quote("/", safe="")
        _encoded_q = urllib.parse.quote(encoded, safe="")
        str_to_sign = f"GET&{_root}&{_encoded_q}"

        signature = base64.b64encode(
            hmac.new(
                f"{access_key_secret}&".encode(),
                str_to_sign.encode(),
                hashlib.sha1,
            ).digest()
        ).decode()

        params["Signature"] = signature
        query_string = urllib.parse.urlencode(params)
        url = f"{endpoint}/?{query_string}"

        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            body = resp.read().decode()

        return json.loads(body)

    except Exception as exc:
        logger.error("STS AssumeRole failed: %s", exc)
        raise RuntimeError(f"STS credential refresh failed: {exc}") from exc


# ---------------------------------------------------------------------------
# SSE-KMS headers
# ---------------------------------------------------------------------------


def sse_kms_headers() -> dict[str, str]:
    """Return SSE-KMS headers for OSS PUT operations."""
    if not settings.oss_kms_key_id:
        return {}
    return {
        "x-oss-server-side-encryption": "KMS",
        "x-oss-server-side-encryption-key-id": settings.oss_kms_key_id,
    }


# ---------------------------------------------------------------------------
# Presigned URL helpers
# ---------------------------------------------------------------------------


async def presigned_get_url(oss_key: str) -> str:
    """Generate a presigned GET URL with settings.oss_presign_get_ttl_s TTL."""
    ttl = settings.oss_presign_get_ttl_s

    if settings.govflow_env == "cloud":
        creds = await get_sts_credentials()
        return _oss2_presigned_get(oss_key, ttl, creds)

    # Local MinIO path
    return _boto3_presigned_get(oss_key, ttl)


async def presigned_put_url(oss_key: str) -> str:
    """Generate a presigned PUT URL with settings.oss_presign_put_ttl_s TTL."""
    ttl = settings.oss_presign_put_ttl_s

    if settings.govflow_env == "cloud":
        creds = await get_sts_credentials()
        return _oss2_presigned_put(oss_key, ttl, creds)

    return _boto3_presigned_put(oss_key, ttl)


def _oss2_presigned_get(oss_key: str, ttl: int, creds: dict[str, str]) -> str:
    import oss2

    auth = oss2.StsAuth(
        creds["AccessKeyId"],
        creds["AccessKeySecret"],
        creds["SecurityToken"],
    ) if creds.get("SecurityToken") else oss2.Auth(
        creds["AccessKeyId"],
        creds["AccessKeySecret"],
    )
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)
    return bucket.sign_url("GET", oss_key, ttl)


def _oss2_presigned_put(oss_key: str, ttl: int, creds: dict[str, str]) -> str:
    import oss2

    auth = oss2.StsAuth(
        creds["AccessKeyId"],
        creds["AccessKeySecret"],
        creds["SecurityToken"],
    ) if creds.get("SecurityToken") else oss2.Auth(
        creds["AccessKeyId"],
        creds["AccessKeySecret"],
    )
    bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)
    headers = sse_kms_headers()
    return bucket.sign_url("PUT", oss_key, ttl, headers=headers or None)


def _boto3_presigned_get(oss_key: str, ttl: int) -> str:
    import boto3
    from botocore.config import Config as BotoConfig

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.oss_endpoint,
        aws_access_key_id=settings.oss_access_key_id,
        aws_secret_access_key=settings.oss_access_key_secret,
        region_name=settings.oss_region,
        config=BotoConfig(signature_version="s3v4"),
    )
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.oss_bucket, "Key": oss_key},
        ExpiresIn=ttl,
    )


def _boto3_presigned_put(oss_key: str, ttl: int) -> str:
    import boto3
    from botocore.config import Config as BotoConfig

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.oss_endpoint,
        aws_access_key_id=settings.oss_access_key_id,
        aws_secret_access_key=settings.oss_access_key_secret,
        region_name=settings.oss_region,
        config=BotoConfig(signature_version="s3v4"),
    )
    return s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.oss_bucket, "Key": oss_key},
        ExpiresIn=ttl,
    )
