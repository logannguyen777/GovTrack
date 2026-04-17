#!/usr/bin/env python3
"""
backend/scripts/test_documents_extract.py
Test POST /api/documents/extract endpoint.

Uses data/samples/cccd_sample.jpg if it exists; otherwise skips file upload
and tests with a dummy URL (SSRF guard rejection path).

Run standalone:
    python backend/scripts/test_documents_extract.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

BASE_URL = "http://localhost:8100"
SAMPLE_PATH = Path(__file__).parent.parent.parent / "data" / "samples" / "cccd_sample.jpg"


def test_ssrf_guard() -> bool:
    """Verify that a non-OSS URL is rejected (SSRF guard)."""
    import urllib.parse
    from urllib.error import HTTPError

    payload = urllib.parse.urlencode(
        {"file_url": "http://internal.corporate.lan/secret", "tthc_code": "1.001757"}
    )

    req = urllib.request.Request(
        f"{BASE_URL}/api/documents/extract",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10):
            print("  [FAIL] SSRF guard: expected 400, got 200")
            return False
    except HTTPError as e:
        if e.code == 400:
            print("  [PASS] SSRF guard: correctly rejected non-OSS URL (400)")
            return True
        else:
            print(f"  [FAIL] SSRF guard: expected 400, got {e.code}")
            return False
    except Exception as e:
        print(f"  [FAIL] SSRF guard test error: {e}")
        return False


def test_file_upload() -> bool:
    """Test file upload path if sample file exists."""
    if not SAMPLE_PATH.exists():
        print(f"  [SKIP] File upload test: sample not found at {SAMPLE_PATH}")
        return True

    import email.mime.multipart
    import email.mime.base
    import email.encoders

    # Manual multipart/form-data encoding
    boundary = "----GovFlowTestBoundary"
    body_parts = []

    # File field
    with open(SAMPLE_PATH, "rb") as f:
        file_data = f.read()

    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="cccd_sample.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n".encode("utf-8")
        + file_data
        + b"\r\n"
    )

    # tthc_code field
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="tthc_code"\r\n\r\n'
        f"1.001757\r\n".encode("utf-8")
    )

    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(body_parts)

    req = urllib.request.Request(
        f"{BASE_URL}/api/documents/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())

        if "extraction_id" not in data:
            print(f"  [FAIL] File upload: missing extraction_id. Got: {list(data.keys())}")
            return False

        if "entities" not in data:
            print(f"  [FAIL] File upload: missing entities. Got: {list(data.keys())}")
            return False

        extraction_id = data["extraction_id"]
        print(f"  [PASS] File upload: extraction_id={extraction_id[:12]}...")
        print(f"         doc_type={data.get('document_type')}, entities={len(data['entities'])}")

        # Test prefill cache retrieval
        return test_prefill(extraction_id)

    except Exception as e:
        print(f"  [FAIL] File upload error: {e}")
        return False


def test_prefill(extraction_id: str) -> bool:
    """Test GET /api/assistant/prefill/{extraction_id}."""
    req = urllib.request.Request(
        f"{BASE_URL}/api/assistant/prefill/{extraction_id}",
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        if data.get("extraction_id") == extraction_id:
            print(f"  [PASS] Prefill cache: hit for {extraction_id[:12]}...")
            return True
        else:
            print(f"  [FAIL] Prefill cache: ID mismatch")
            return False
    except Exception as e:
        print(f"  [FAIL] Prefill retrieval error: {e}")
        return False


def main():
    print(f"Testing document extract API at {BASE_URL}\n")
    print("=" * 60)

    results = []

    print("Running SSRF guard test...")
    results.append(test_ssrf_guard())

    print("\nRunning file upload test...")
    results.append(test_file_upload())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
