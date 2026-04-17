"""
Test: Authentication security hardening (tasks 0.1, 0.2).

Covers:
- Argon2 password verification (new format).
- SHA-256 legacy password verify + rehash trigger.
- JWT jti claim presence.
- JWT secret fail-fast in cloud mode.
- Revocation cache logic.
"""
from __future__ import annotations

import hashlib
import time

import pytest

# ---------------------------------------------------------------------------
# Task 0.1: Password hashing helpers
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def setup_method(self):
        # Import after class setup so we can re-import cleanly
        from src.api.auth_login import _needs_rehash, _ph, _verify_password
        self._verify = _verify_password
        self._needs_rehash = _needs_rehash
        self._ph = _ph

    def test_argon2_hash_verifies(self):
        """Fresh argon2 hash verifies correctly."""
        h = self._ph.hash("secret123")
        assert self._verify(h, "secret123")

    def test_argon2_wrong_password_fails(self):
        """Wrong password returns False, not exception."""
        h = self._ph.hash("correct")
        assert not self._verify(h, "wrong")

    def test_sha256_legacy_verifies(self):
        """Legacy SHA-256 hash still verifies correctly."""
        sha_hash = hashlib.sha256(b"demo").hexdigest()
        assert self._verify(sha_hash, "demo")

    def test_sha256_wrong_password_fails(self):
        """SHA-256 hash with wrong password returns False."""
        sha_hash = hashlib.sha256(b"correct").hexdigest()
        assert not self._verify(sha_hash, "wrong")

    def test_argon2_does_not_need_rehash(self):
        """Argon2 hashes should not trigger rehash."""
        h = self._ph.hash("pw")
        assert not self._needs_rehash(h)

    def test_sha256_needs_rehash(self):
        """Legacy SHA-256 hashes should trigger rehash."""
        sha_hash = hashlib.sha256(b"pw").hexdigest()
        assert self._needs_rehash(sha_hash)


# ---------------------------------------------------------------------------
# Task 0.2: JWT jti claim
# ---------------------------------------------------------------------------

class TestJWTClaims:
    def test_token_contains_jti(self):
        """create_access_token must embed a non-empty jti claim."""
        from src.auth import create_access_token, decode_token

        token = create_access_token(
            user_id="u1",
            username="testuser",
            role="officer",
            clearance_level=1,
            departments=["dept-test"],
        )
        claims = decode_token(token)
        assert claims.jti, "jti claim must be present and non-empty"

    def test_each_token_has_unique_jti(self):
        """Two successive tokens must have different jti values."""
        from src.auth import create_access_token, decode_token

        t1 = create_access_token("u1", "u", "officer", 1, [])
        t2 = create_access_token("u1", "u", "officer", 1, [])
        c1 = decode_token(t1)
        c2 = decode_token(t2)
        assert c1.jti != c2.jti


# ---------------------------------------------------------------------------
# Task 0.2: JWT secret strength validator
# ---------------------------------------------------------------------------

class TestJWTSecretValidator:
    def test_cloud_mode_default_secret_raises(self, monkeypatch):
        """In cloud mode, default JWT secret must raise RuntimeError at import."""
        import sys

        # Patch env vars so pydantic-settings picks up cloud mode + default secret
        monkeypatch.setenv("GOVFLOW_ENV", "cloud")
        monkeypatch.setenv("JWT_SECRET", "dev-secret-change-in-production-2026")

        # Remove cached module so Settings re-evaluates
        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]

        with pytest.raises(RuntimeError, match="INSECURE"):
            import src.config  # noqa: F401

        # Restore
        monkeypatch.delenv("GOVFLOW_ENV", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]

    def test_cloud_mode_short_secret_raises(self, monkeypatch):
        """In cloud mode, a secret shorter than 32 chars must raise RuntimeError."""
        import sys

        monkeypatch.setenv("GOVFLOW_ENV", "cloud")
        monkeypatch.setenv("JWT_SECRET", "tooshort")

        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]

        with pytest.raises(RuntimeError, match="INSECURE"):
            import src.config  # noqa: F401

        monkeypatch.delenv("GOVFLOW_ENV", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]

    def test_local_mode_weak_secret_does_not_raise(self, monkeypatch):
        """In local mode, weak secret logs a warning but does NOT raise."""
        import sys

        monkeypatch.setenv("GOVFLOW_ENV", "local")
        monkeypatch.setenv("JWT_SECRET", "dev-secret-change-in-production-2026")

        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]

        # Should not raise
        import src.config  # noqa: F401

        monkeypatch.delenv("GOVFLOW_ENV", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        for mod in list(sys.modules):
            if mod.startswith("src.config"):
                del sys.modules[mod]


# ---------------------------------------------------------------------------
# Task 0.2: Revocation cache logic (no DB required — unit test the cache)
# ---------------------------------------------------------------------------

class TestRevocationCache:
    def setup_method(self):
        from src.auth import _REVOCATION_CACHE_TTL, _cache_get, _cache_set, _revocation_cache
        self._cache = _revocation_cache
        self._get = _cache_get
        self._set = _cache_set
        self._ttl = _REVOCATION_CACHE_TTL
        # Clear before each test
        _revocation_cache.clear()

    def test_cache_miss_returns_none(self):
        assert self._get("nonexistent-jti") is None

    def test_cache_hit_returns_value(self):
        self._set("jti-001", True)
        assert self._get("jti-001") is True

    def test_cache_not_revoked(self):
        self._set("jti-002", False)
        assert self._get("jti-002") is False

    def test_cache_expiry(self, monkeypatch):
        """Entry should be evicted after TTL."""
        self._set("jti-003", True)
        # Monkey-patch monotonic to simulate TTL expiry
        original_time = time.monotonic
        monkeypatch.setattr(
            time, "monotonic", lambda: original_time() + self._ttl + 1
        )
        result = self._get("jti-003")
        assert result is None, "Stale cache entry should return None"

    def test_explicit_pop_invalidates(self):
        """Calling _revocation_cache.pop(jti) invalidates the entry."""
        self._set("jti-004", True)
        self._cache.pop("jti-004", None)
        assert self._get("jti-004") is None
