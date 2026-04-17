"""
20+ negative test scenarios for the 3-tier permission engine.
Each test verifies a specific denial and confirms correct behavior.
"""

import pytest

from src.graph.property_mask import PropertyMask
from src.graph.rbac_simulator import RBACSimulator
from src.graph.sdk_guard import SDKGuard, SDKGuardViolation
from src.models.enums import Role
from src.models.schemas import AgentProfile, ClearanceLevel


def make_profile(**overrides) -> AgentProfile:
    defaults = dict(
        agent_id="test_agent", agent_name="Test",
        clearance=ClearanceLevel.UNCLASSIFIED,
        read_node_labels=["Case"], write_node_labels=["Task"],
        read_edge_types=["HAS_DOCUMENT"], write_edge_types=["PRODUCED"],
        forbidden_properties=["national_id", "tax_id"],
        max_traversal_depth=3,
    )
    defaults.update(overrides)
    return AgentProfile(**defaults)


# --- Tier 1: SDK Guard ---

class TestSDKGuardDenials:
    def test_01_read_forbidden_label(self):
        guard = SDKGuard(make_profile(read_node_labels=["Case"]))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('Secret').values('name')")

    def test_02_read_forbidden_property(self):
        guard = SDKGuard(make_profile())
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('national_id')")

    def test_03_write_forbidden_label(self):
        guard = SDKGuard(make_profile(write_node_labels=["Task"]))
        with pytest.raises(SDKGuardViolation, match="WRITE_LABEL_DENIED"):
            guard.validate("g.addV('Gap').property('severity','high')")

    def test_04_traverse_forbidden_edge(self):
        guard = SDKGuard(make_profile(read_edge_types=["HAS_DOCUMENT"]))
        with pytest.raises(SDKGuardViolation, match="READ_EDGE_DENIED"):
            guard.validate("g.V().hasLabel('Case').outE('SECRET_LINK').inV()")

    def test_05_depth_exceeded(self):
        guard = SDKGuard(make_profile(max_traversal_depth=2))
        deep_q = (  # noqa: E501
            "g.V().hasLabel('Case')"
            ".out('HAS_DOCUMENT').out('HAS_DOCUMENT').out('HAS_DOCUMENT')"
        )
        with pytest.raises(SDKGuardViolation, match="DEPTH_EXCEEDED"):
            guard.validate(deep_q)

    def test_06_write_forbidden_edge(self):
        guard = SDKGuard(make_profile(write_edge_types=["PRODUCED"]))
        with pytest.raises(SDKGuardViolation, match="WRITE_EDGE_DENIED"):
            guard.validate("g.V('a').addE('ADMIN_OVERRIDE').to(V('b'))")

    def test_07_multiple_forbidden_labels(self):
        guard = SDKGuard(make_profile(read_node_labels=["Case"]))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('Secret').out().hasLabel('TopSecret')")

    def test_08_tax_id_forbidden(self):
        guard = SDKGuard(make_profile())
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('tax_id')")

    def test_09_allowed_read_passes(self):
        guard = SDKGuard(make_profile())
        result = guard.validate("g.V().hasLabel('Case').values('status')")
        assert "classification" in result  # auto_rewrite injected filter

    def test_10_allowed_write_passes(self):
        guard = SDKGuard(make_profile())
        result = guard.validate("g.addV('Task').property('name','t1')")
        assert result  # no exception


# --- Tier 2: RBAC Simulator ---

class TestRBACDenials:
    def test_11_create_unauthorized_vertex(self):
        profile = make_profile(write_node_labels=["Task"])
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Gap').property('x','y')")
        with pytest.raises(PermissionError, match="lacks INSERT on Gap"):
            rbac.check_execution_privilege("g.addV('Gap')", parsed)

    def test_12_read_unauthorized_label(self):
        profile = make_profile(read_node_labels=["Case"])
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.V().hasLabel('Secret')")
        parsed.accessed_labels = {"Secret"}
        with pytest.raises(PermissionError, match="lacks SELECT on Secret"):
            rbac.check_execution_privilege("g.V()", parsed)

    def test_13_legal_agent_cant_create_gap(self):
        profile = make_profile(
            agent_id="legal_search_agent",
            write_node_labels=["Citation", "Task"],
        )
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Gap')")
        with pytest.raises(PermissionError):
            rbac.check_execution_privilege("g.addV('Gap')", parsed)

    def test_14_summary_agent_cant_write_anything(self):
        profile = make_profile(
            agent_id="summary_agent",
            write_node_labels=[],
        )
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Task')")
        with pytest.raises(PermissionError):
            rbac.check_execution_privilege("g.addV('Task')", parsed)


# --- Tier 3: Property Mask (original tests preserved) ---

class TestPropertyMaskRedaction:
    def test_15_national_id_redacted(self):
        mask = PropertyMask()
        result = mask.apply(
            {"national_id": "079201001234", "name": "Test"},
            ClearanceLevel.TOP_SECRET,
        )
        assert result["national_id"] == "[REDACTED]"
        assert result["name"] == "Test"

    def test_16_phone_partial_mask(self):
        mask = PropertyMask()
        result = mask.apply(
            {"phone_number": "0901234567"},
            ClearanceLevel.TOP_SECRET,
        )
        assert result["phone_number"].endswith("4567")
        assert result["phone_number"].startswith("*")

    def test_17_classification_gate_denied(self):
        mask = PropertyMask()
        result = mask.apply(
            {"home_address": "12 Le Loi, Q1"},
            ClearanceLevel.UNCLASSIFIED,
        )
        assert "CLASSIFIED" in result["home_address"]

    def test_18_classification_gate_allowed(self):
        mask = PropertyMask()
        result = mask.apply(
            {"home_address": "12 Le Loi, Q1"},
            ClearanceLevel.CONFIDENTIAL,
        )
        assert result["home_address"] == "12 Le Loi, Q1"

    def test_19_top_secret_gate(self):
        """Security role with SECRET clearance is denied by clearance gate (not role)."""
        mask = PropertyMask()
        # Use the security role (passes role check) but only SECRET clearance
        # (fails the TOP_SECRET gate)
        result = mask.apply(
            {"criminal_record": "None"},
            ClearanceLevel.SECRET,
            role=Role.SECURITY,
        )
        assert "CLASSIFIED:TOP_SECRET" in result["criminal_record"]

    def test_20_top_secret_clearance_sees_all(self):
        """TOP_SECRET clearance + allowed role sees all fields."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "None", "home_address": "addr", "bank_account": "123"},
            ClearanceLevel.TOP_SECRET,
            role=Role.SECURITY,
        )
        assert result["criminal_record"] == "None"
        assert result["home_address"] == "addr"
        assert result["bank_account"] == "123"

    def test_21_batch_redaction(self):
        mask = PropertyMask()
        records = [
            {"national_id": "111", "name": "A"},
            {"national_id": "222", "name": "B"},
        ]
        results = mask.apply_batch(records, ClearanceLevel.UNCLASSIFIED)
        assert all(r["national_id"] == "[REDACTED]" for r in results)
        assert results[0]["name"] == "A"

    def test_22_clearance_elevation_dissolves_mask(self):
        mask = PropertyMask()
        record = {"home_address": "secret place", "name": "X"}
        before = mask.apply(record, ClearanceLevel.UNCLASSIFIED)
        after = mask.apply(record, ClearanceLevel.CONFIDENTIAL)
        assert "CLASSIFIED" in before["home_address"]
        assert after["home_address"] == "secret place"


# --- Tier 3 Extension: Role-gated properties (task 0.5) ---

class TestPropertyMaskRoleGating:
    """Verify that role check takes precedence over clearance."""

    def test_23_officer_top_secret_cannot_see_criminal_record(self):
        """Officer with TOP_SECRET clearance must NOT see criminal_record (role-gated)."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "Yes"},
            ClearanceLevel.TOP_SECRET,
            role=Role.OFFICER,
        )
        assert result["criminal_record"] == "[REDACTED:ROLE]", (
            "Officer role should be denied criminal_record regardless of clearance"
        )

    def test_24_leader_top_secret_cannot_see_investigation_notes(self):
        """Leader with TOP_SECRET cannot see investigation_notes (role-gated)."""
        mask = PropertyMask()
        result = mask.apply(
            {"investigation_notes": "Classified note"},
            ClearanceLevel.TOP_SECRET,
            role=Role.LEADER,
        )
        assert result["investigation_notes"] == "[REDACTED:ROLE]"

    def test_25_security_role_top_secret_sees_criminal_record(self):
        """Security role with TOP_SECRET CAN see criminal_record."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "Pending"},
            ClearanceLevel.TOP_SECRET,
            role=Role.SECURITY,
        )
        assert result["criminal_record"] == "Pending"

    def test_26_legal_role_top_secret_sees_criminal_record(self):
        """Legal role with TOP_SECRET CAN see criminal_record."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "None"},
            ClearanceLevel.TOP_SECRET,
            role=Role.LEGAL,
        )
        assert result["criminal_record"] == "None"

    def test_27_admin_role_top_secret_sees_criminal_record(self):
        """Admin role with TOP_SECRET CAN see criminal_record."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "None"},
            ClearanceLevel.TOP_SECRET,
            role=Role.ADMIN,
        )
        assert result["criminal_record"] == "None"

    def test_28_security_insufficient_clearance_still_denied(self):
        """Security role with insufficient clearance is still clearance-denied."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "Data"},
            ClearanceLevel.SECRET,  # below TOP_SECRET gate
            role=Role.SECURITY,
        )
        assert "CLASSIFIED:TOP_SECRET" in result["criminal_record"]

    def test_29_medical_history_role_gated(self):
        """medical_history requires security/legal/admin role."""
        mask = PropertyMask()
        for role in [Role.OFFICER, Role.STAFF_INTAKE, Role.STAFF_PROCESSOR, Role.PUBLIC_VIEWER]:
            result = mask.apply(
                {"medical_history": "Sensitive"},
                ClearanceLevel.TOP_SECRET,
                role=role,
            )
            assert result["medical_history"] == "[REDACTED:ROLE]", (
                f"Role {role} should be denied medical_history"
            )

    def test_30_no_role_provided_role_gated_field_denied(self):
        """Calling apply() with role=None should deny role-gated fields."""
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "X"},
            ClearanceLevel.TOP_SECRET,
            role=None,
        )
        assert result["criminal_record"] == "[REDACTED:ROLE]"
