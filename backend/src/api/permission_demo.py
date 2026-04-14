"""
Three demo endpoints that showcase each permission tier.
Used in live demo and integration tests.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/demo/permissions", tags=["demo"])


@router.post("/scene-a/sdk-guard-rejection")
async def scene_a_sdk_guard():
    """
    Scene A: Summarizer agent tries to access national_id property.
    SDK Guard rejects because national_id is in forbidden_properties.

    Expected: 403 with SDKGuardViolation detail.
    """
    from ..agents.profile import load_profile
    from ..graph.sdk_guard import SDKGuard, SDKGuardViolation

    profile = load_profile("summary_agent").to_permission_profile()
    guard = SDKGuard(profile)

    query = "g.V().hasLabel('Case').values('national_id')"
    try:
        guard.validate(query)
        return {"status": "ERROR", "message": "Should have been rejected"}
    except SDKGuardViolation as e:
        return {
            "status": "DENIED",
            "tier": "SDK_GUARD",
            "agent": e.agent_id,
            "violation": e.violation_type,
            "detail": e.detail,
        }


@router.post("/scene-b/rbac-rejection")
async def scene_b_rbac():
    """
    Scene B: LegalSearch agent tries to CREATE a Gap vertex.
    RBAC rejects because legal_search_agent has no INSERT on Gap label.

    Expected: 403 with RBAC denial detail.
    """
    from ..agents.profile import load_profile
    from ..graph.rbac_simulator import RBACSimulator
    from ..graph.sdk_guard import SDKGuard

    profile = load_profile("legal_search_agent").to_permission_profile()
    guard = SDKGuard(profile)
    rbac = RBACSimulator(profile)

    query = "g.addV('Gap').property('severity', 'critical').property('case_id', 'C-001')"
    parsed = guard.parse_query(query)

    try:
        rbac.check_execution_privilege(query, parsed)
        return {"status": "ERROR", "message": "Should have been rejected"}
    except PermissionError as e:
        return {
            "status": "DENIED",
            "tier": "GDB_RBAC",
            "agent": profile.agent_id,
            "detail": str(e),
        }


@router.post("/scene-c/clearance-elevation")
async def scene_c_clearance_elevation():
    """
    Scene C: User with UNCLASSIFIED clearance sees masked properties.
    After elevation to CONFIDENTIAL, the property mask dissolves.

    Expected: Before = [CLASSIFIED:CONFIDENTIAL], After = actual value.
    """
    from ..graph.property_mask import PropertyMask
    from ..models.enums import ClearanceLevel

    mask = PropertyMask()
    record = {
        "case_id": "C-2026-0042",
        "applicant_name": "Nguyen Van Minh",
        "home_address": "12 Le Loi, Q1, TP.HCM",
        "national_id": "079201001234",
        "status": "processing",
    }

    before = mask.apply(record, ClearanceLevel.UNCLASSIFIED)
    after = mask.apply(record, ClearanceLevel.CONFIDENTIAL)

    return {
        "status": "OK",
        "tier": "PROPERTY_MASK",
        "before_elevation": before,
        "after_elevation": after,
        "dissolved_fields": [
            k for k in record
            if before.get(k) != after.get(k)
        ],
    }
