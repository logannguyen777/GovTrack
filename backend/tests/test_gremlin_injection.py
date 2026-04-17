"""
Test: Gremlin injection prevention (task 0.3 + 0.6).

Covers:
- Pydantic Query validation rejects non-integer / out-of-range page_size values.
- SDK Guard rejects queries containing injection markers.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Pydantic query validation (task 0.3)
# ---------------------------------------------------------------------------

class TestListCasesQueryValidation:
    """Verify that FastAPI/Pydantic rejects bad page_size / skip values."""

    @pytest.fixture(scope="class")
    def client(self):
        """Sync TestClient (no real DB needed — 422 is raised before any DB call)."""
        from src.main import create_app

        app = create_app()
        # Override lifespan to skip DB init for unit tests
        app.router.lifespan_context = None
        return TestClient(app, raise_server_exceptions=False)

    def _auth_headers(self):
        from src.auth import create_access_token

        token = create_access_token(
            user_id="test-001",
            username="test",
            role="officer",
            clearance_level=1,
            departments=["dept-test"],
        )
        return {"Authorization": f"Bearer {token}"}

    def test_injection_in_page_size_string_rejected(self, client):
        """page_size must be an integer — string with injection chars → 422."""
        resp = client.get(
            "/cases",
            params={"page_size": "1); g.addV('Backdoor');//"},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 422, (
            f"Expected 422 for injection page_size, got {resp.status_code}"
        )

    def test_page_size_above_max_rejected(self, client):
        """page_size > 1000 → 422."""
        resp = client.get(
            "/cases",
            params={"page_size": 9999},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 422

    def test_page_size_zero_rejected(self, client):
        """page_size=0 → 422 (ge=1)."""
        resp = client.get(
            "/cases",
            params={"page_size": 0},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 422

    def test_negative_page_rejected(self, client):
        """page=0 → 422 (ge=1)."""
        resp = client.get(
            "/cases",
            params={"page": 0},
            headers=self._auth_headers(),
        )
        assert resp.status_code == 422

    def test_valid_params_pass_validation(self, client):
        """page=2&page_size=10 should pass validation (may fail at DB layer)."""
        resp = client.get(
            "/cases",
            params={"page": 2, "page_size": 10},
            headers=self._auth_headers(),
        )
        # 200 or a DB-layer error (503/500) — but NOT 422
        assert resp.status_code != 422


# ---------------------------------------------------------------------------
# SDK Guard injection checks (task 0.6)
# ---------------------------------------------------------------------------

from src.graph.sdk_guard import SDKGuard, SDKGuardViolation  # noqa: E402
from src.models.schemas import AgentProfile, ClearanceLevel  # noqa: E402


def _make_profile(**kwargs) -> AgentProfile:
    defaults = dict(
        agent_id="test_agent",
        agent_name="Test",
        clearance=ClearanceLevel.UNCLASSIFIED,
        read_node_labels=["Case"],
        write_node_labels=["Task"],
        read_edge_types=["HAS_DOCUMENT"],
        write_edge_types=["PRODUCED"],
        forbidden_properties=["national_id"],
        max_traversal_depth=5,
    )
    defaults.update(kwargs)
    return AgentProfile(**defaults)


class TestSDKGuardInjectionHardening:
    """Verify the new injection-guard logic added in task 0.6."""

    @pytest.fixture(autouse=True)
    def guard(self):
        self.guard = SDKGuard(_make_profile())

    def test_line_comment_rejected(self):
        """Groovy line comment '//' must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_COMMENT"):
            self.guard.validate("hasLabel('Case') // .drop()")

    def test_escaped_quote_with_comment_rejected(self):
        """Escaped quote + comment pattern must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_COMMENT"):
            self.guard.validate(r"g.V().has('Case','id','x\') // .drop()")

    def test_block_comment_rejected(self):
        """Groovy block comment '/*' must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_COMMENT"):
            self.guard.validate("g.V().hasLabel('Case')/* .drop() */")

    def test_multi_statement_semicolon_rejected(self):
        """Semicolon (multi-statement) must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_MULTI_STATEMENT"):
            self.guard.validate("g.V().has('x','y',1);g.V().drop()")

    def test_newline_in_query_rejected(self):
        """Embedded newline must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_NEWLINE"):
            self.guard.validate("g.V()\n.drop()")

    def test_carriage_return_rejected(self):
        """Embedded carriage-return must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_NEWLINE"):
            self.guard.validate("g.V().hasLabel('Case')\r.valueMap()")

    def test_control_char_rejected(self):
        """Control character (non-printable) must be rejected."""
        with pytest.raises(SDKGuardViolation, match="INJECTION_CONTROL_CHARS"):
            self.guard.validate("g.V().hasLabel('Case')\x01.valueMap()")

    def test_clean_query_passes(self):
        """A clean query should still pass the injection guard."""
        result = self.guard.validate("g.V().hasLabel('Case').valueMap(true)")
        assert result  # rewritten query returned

    def test_clean_query_with_bindings_passes(self):
        """Query with parameterised values (no injection chars) should pass."""
        result = self.guard.validate(
            "g.V().hasLabel('Case').has('status', st).valueMap(true)"
        )
        assert result
