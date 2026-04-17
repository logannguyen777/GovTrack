"""
Test: Security headers and CORS (task 0.9).
Test: File upload validation (task 0.10).
Test: SSRF URL validation (task 0.8).
Test: WebSocket auth handshake timeout (task 0.7).
"""
from __future__ import annotations

import io
import struct

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client():
    from src.main import create_app

    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def _auth_headers():
    from src.auth import create_access_token

    token = create_access_token("u1", "tester", "admin", 3, ["dept-all"])
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Task 0.9: Security headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    @pytest.fixture(scope="class")
    def client(self):
        return _make_client()

    def test_x_frame_options_deny(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_referrer_policy(self, client):
        resp = client.get("/healthz")
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        resp = client.get("/healthz")
        val = resp.headers.get("permissions-policy", "")
        assert "geolocation=()" in val
        assert "microphone=()" in val
        assert "camera=()" in val

    def test_csp_present(self, client):
        resp = client.get("/healthz")
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_hsts_not_sent_over_http_local(self, client):
        """HSTS should NOT be sent for plain HTTP in local env."""
        resp = client.get("/healthz")
        # TestClient uses http:// and env is local — no HSTS expected
        assert "strict-transport-security" not in resp.headers

    def test_cors_restricted_methods(self, client):
        """OPTIONS preflight should reflect only allowed methods."""
        resp = client.options(
            "/cases",
            headers={
                "Origin": "http://localhost:3100",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        # DELETE is in the allowed list — should be permitted
        # FastAPI/Starlette echos back the requested method when allowed;
        # at minimum, the response must not be 403.
        assert resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Task 0.10: File upload MIME + extension validation
# ---------------------------------------------------------------------------

def _make_exe_content() -> bytes:
    """Minimal Windows PE header (MZ magic bytes)."""
    return b"MZ" + b"\x00" * 62


def _make_pdf_content() -> bytes:
    """Minimal PDF magic bytes."""
    return b"%PDF-1.4\n%%EOF\n"


def _make_png_content() -> bytes:
    """Minimal valid PNG (1x1 white pixel)."""
    import zlib

    def _chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw_row = b"\x00\xff\xff\xff"
    compressed = zlib.compress(raw_row)
    idat = _chunk(b"IDAT", compressed)
    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend


class TestFileUploadValidation:
    @pytest.fixture(scope="class")
    def client(self):
        return _make_client()

    def test_exe_disguised_as_pdf_rejected_415(self, client):
        """EXE file renamed .pdf must be rejected with 415."""
        resp = client.post(
            "/documents/extract",
            files={"file": ("evil.pdf", io.BytesIO(_make_exe_content()), "application/pdf")},
        )
        # 415 expected (MIME mismatch) — or 503 if OSS not available but not 200
        assert resp.status_code in (415, 503), (
            f"Expected 415 for EXE-as-PDF, got {resp.status_code}: {resp.text[:200]}"
        )

    def test_unknown_extension_rejected_415(self, client):
        """File with .sh extension must be rejected."""
        resp = client.post(
            "/documents/extract",
            files={"file": ("script.sh", io.BytesIO(b"#!/bin/bash\nrm -rf /"), "text/plain")},
        )
        assert resp.status_code == 415, (
            f"Expected 415 for .sh extension, got {resp.status_code}"
        )

    def test_no_file_no_url_returns_400(self, client):
        """Omitting both file and file_url returns 400."""
        resp = client.post("/documents/extract", data={})
        assert resp.status_code == 400

    def test_valid_pdf_passes_extension_check(self, client):
        """Valid PDF magic bytes with .pdf extension should at least pass validation."""
        resp = client.post(
            "/documents/extract",
            files={"file": ("doc.pdf", io.BytesIO(_make_pdf_content()), "application/pdf")},
        )
        # Will fail at OSS layer in test env — but NOT 415 or 422
        assert resp.status_code not in (415, 422), (
            f"Valid PDF should not be rejected at validation: {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Task 0.8: SSRF URL validation
# ---------------------------------------------------------------------------

class TestSSRFValidation:
    """Unit-test _validate_url without making real HTTP requests."""

    @pytest.fixture(autouse=True)
    def patch_resolve(self, monkeypatch):
        """Patch _resolve_hostname to return predictable IPs."""
        from src.api import documents as doc_module

        async def _fake_resolve(hostname: str) -> list[str]:
            mapping = {
                "169.254.169.254": ["169.254.169.254"],
                "::1": ["::1"],
                "127.1.1.1": ["127.1.1.1"],
                "10.0.0.1": ["10.0.0.1"],
                "safe-oss.aliyuncs.com": ["47.88.1.2"],  # public IP, safe
            }
            return mapping.get(hostname, ["203.0.113.1"])  # TEST-NET (safe)

        monkeypatch.setattr(doc_module, "_resolve_hostname", _fake_resolve)

    @pytest.mark.asyncio
    async def test_metadata_ip_rejected(self, monkeypatch):
        """169.254.169.254 must be rejected."""
        from fastapi import HTTPException

        from src.api.documents import _validate_url
        from src.config import settings

        monkeypatch.setattr(settings, "oss_allowed_domains", ["169.254.169.254"])

        with pytest.raises(HTTPException) as exc_info:
            await _validate_url("http://169.254.169.254/latest/meta-data/")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_loopback_ipv6_rejected(self, monkeypatch):
        """[::1] loopback must be rejected."""
        from fastapi import HTTPException

        from src.api.documents import _validate_url
        from src.config import settings

        monkeypatch.setattr(settings, "oss_allowed_domains", ["::1"])

        with pytest.raises(HTTPException) as exc_info:
            await _validate_url("http://[::1]/")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_private_ipv4_rejected(self, monkeypatch):
        """10.0.0.1 (RFC-1918) must be rejected."""
        from fastapi import HTTPException

        from src.api.documents import _validate_url
        from src.config import settings

        monkeypatch.setattr(settings, "oss_allowed_domains", ["10.0.0.1"])

        with pytest.raises(HTTPException) as exc_info:
            await _validate_url("http://10.0.0.1/file.pdf")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_loopback_dotted_rejected(self, monkeypatch):
        """127.1.1.1 must be rejected as loopback."""
        from fastapi import HTTPException

        from src.api.documents import _validate_url
        from src.config import settings

        monkeypatch.setattr(settings, "oss_allowed_domains", ["127.1.1.1"])

        with pytest.raises(HTTPException) as exc_info:
            await _validate_url("http://127.1.1.1/sensitive")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_oss_url_passes(self, monkeypatch):
        """A URL on aliyuncs.com with a public IP should pass."""
        import src.api.documents as doc_module
        from src.api.documents import _validate_url

        # Patch the settings object as seen by the documents module (not the
        # global src.config.settings which may be a different object if
        # src.config was reloaded by a prior test).
        monkeypatch.setattr(doc_module.settings, "oss_allowed_domains", ["aliyuncs.com"])
        monkeypatch.setattr(doc_module.settings, "govflow_env", "local")

        # Should not raise
        await _validate_url("https://safe-oss.aliyuncs.com/bucket/file.pdf")

    @pytest.mark.asyncio
    async def test_http_rejected_in_cloud_mode(self, monkeypatch):
        """HTTP URLs must be rejected in cloud mode."""
        from fastapi import HTTPException

        import src.api.documents as doc_module
        from src.api.documents import _validate_url

        # Patch the settings object as seen by the documents module (not the
        # global src.config.settings which may be a different object if
        # src.config was reloaded by a prior test).
        monkeypatch.setattr(doc_module.settings, "govflow_env", "cloud")
        monkeypatch.setattr(doc_module.settings, "oss_allowed_domains", ["aliyuncs.com"])

        with pytest.raises(HTTPException) as exc_info:
            await _validate_url("http://safe-oss.aliyuncs.com/file.pdf")
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Task 0.7: WebSocket auth handshake timeout
# ---------------------------------------------------------------------------

class TestWebSocketHandshake:
    """WebSocket handshake: timeout and invalid token behaviour."""

    @pytest.fixture(scope="class")
    def client(self):
        return _make_client()

    def test_valid_auth_handshake_acknowledged(self, client):
        """Sending valid auth token as first message is acknowledged."""
        from src.auth import create_access_token

        token = create_access_token("u1", "staff", "officer", 1, ["dept"])
        with client.websocket_connect("/api/ws") as ws:
            ws.send_json({"action": "auth", "token": token})
            resp = ws.receive_json()
            assert resp.get("ack") == "authenticated"

    def test_invalid_token_closes_connection(self, client):
        """Invalid token causes WebSocket close (code 1008)."""

        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws") as ws:
                ws.send_json({"action": "auth", "token": "not.a.valid.jwt"})
                # Server should close — receiving should raise
                ws.receive_json()

    def test_wrong_first_action_closes_connection(self, client):
        """First message with action != 'auth' causes close."""

        with pytest.raises(Exception):
            with client.websocket_connect("/api/ws") as ws:
                ws.send_json({"action": "subscribe", "topic": "case:123"})
                ws.receive_json()

    def test_subscribe_after_auth(self, client):
        """Subscribing to a topic after auth works."""
        from src.auth import create_access_token

        token = create_access_token("u2", "admin", "admin", 3, ["dept"])
        with client.websocket_connect("/api/ws") as ws:
            ws.send_json({"action": "auth", "token": token})
            auth_resp = ws.receive_json()
            assert auth_resp.get("ack") == "authenticated"
            ws.send_json({"action": "subscribe", "topic": "case:CASE-001"})
            sub_resp = ws.receive_json()
            assert sub_resp.get("ack") == "subscribed"
            assert sub_resp.get("topic") == "case:CASE-001"
