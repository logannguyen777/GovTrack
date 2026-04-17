"""
Tier 3: Post-execution property redaction.
Applied to all query results before they reach the caller.
Rules are gated by clearance level AND/OR role.
Role check is applied FIRST — if the user's role is not in allowed_roles,
the field is redacted regardless of clearance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..models.enums import ClearanceLevel, Role


class MaskAction(str, Enum):  # noqa: UP042 — StrEnum not available in 3.10 compat code
    REDACT = "redact"  # Remove field entirely (replace with [REDACTED])
    MASK_PARTIAL = "mask_partial"  # Show last 4 chars: "***1234"
    CLASSIFICATION_GATED = "classification_gated"  # Show only if clearance >= gate_level


@dataclass
class MaskRule:
    property_name: str
    action: MaskAction
    gate_level: ClearanceLevel | None = None  # For CLASSIFICATION_GATED
    allowed_roles: set[Role] | None = None  # Role whitelist; None = any role allowed


# Default rules — role-sensitive fields are gated to specific roles
# as well as clearance levels.
DEFAULT_MASK_RULES: list[MaskRule] = [
    # Always-redacted PII (no clearance or role can see plain value)
    MaskRule("national_id", MaskAction.REDACT),
    MaskRule("tax_id", MaskAction.REDACT),
    # Applicant vertex uses shorter keys — also redact/partial-mask these
    MaskRule("id_number", MaskAction.REDACT),
    # Partial mask regardless of clearance
    MaskRule("phone_number", MaskAction.MASK_PARTIAL),
    MaskRule("phone", MaskAction.MASK_PARTIAL),
    MaskRule("email", MaskAction.MASK_PARTIAL),
    # Clearance-gated (any role with sufficient clearance)
    MaskRule("home_address", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.CONFIDENTIAL),
    MaskRule("address", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.CONFIDENTIAL),
    MaskRule("bank_account", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
    MaskRule("internal_assessment", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
    # Role-AND-clearance gated: sensitive personal/investigative data
    # Only SECURITY, LEGAL, and ADMIN roles can ever see these fields —
    # even TOP_SECRET clearance in other roles is insufficient.
    MaskRule(
        "criminal_record",
        MaskAction.CLASSIFICATION_GATED,
        ClearanceLevel.TOP_SECRET,
        allowed_roles={Role.SECURITY, Role.LEGAL, Role.ADMIN},
    ),
    MaskRule(
        "investigation_notes",
        MaskAction.CLASSIFICATION_GATED,
        ClearanceLevel.TOP_SECRET,
        allowed_roles={Role.SECURITY, Role.LEGAL, Role.ADMIN},
    ),
    MaskRule(
        "medical_history",
        MaskAction.CLASSIFICATION_GATED,
        ClearanceLevel.SECRET,
        allowed_roles={Role.SECURITY, Role.LEGAL, Role.ADMIN},
    ),
    MaskRule(
        "mental_health_assessment",
        MaskAction.CLASSIFICATION_GATED,
        ClearanceLevel.SECRET,
        allowed_roles={Role.SECURITY, Role.LEGAL, Role.ADMIN},
    ),
]


class PropertyMask:
    """Post-query field redaction engine."""

    def __init__(self, rules: list[MaskRule] | None = None):
        self.rules = {r.property_name: r for r in (rules or DEFAULT_MASK_RULES)}

    def _unwrap(self, value: Any) -> Any:
        """Unwrap Gremlin valueMap list wrappers so mask operates on scalar."""
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        return value

    def _mask_partial(self, value: Any) -> str:
        s = str(self._unwrap(value))
        if len(s) <= 4:
            return "****"
        return "*" * (len(s) - 4) + s[-4:]

    def apply(
        self,
        record: dict[str, Any],
        clearance: ClearanceLevel,
        role: str | None = None,
    ) -> dict[str, Any]:
        """
        Apply mask rules to a single result record.

        Role check is applied FIRST: if a rule specifies ``allowed_roles`` and the
        user's role is not in that set, the field is redacted regardless of clearance.

        Recursively masks nested dicts and lists.
        Returns a new dict with redacted/masked fields.
        """
        result = {}
        for key, value in record.items():
            rule = self.rules.get(key)

            if rule is not None:
                # Role gate: check before clearance
                if rule.allowed_roles is not None:
                    try:
                        user_role = Role(role) if role else None
                    except ValueError:
                        user_role = None
                    if user_role not in rule.allowed_roles:
                        result[key] = "[REDACTED:ROLE]"
                        continue

                # Apply masking action
                if rule.action == MaskAction.REDACT:
                    result[key] = "[REDACTED]"
                elif rule.action == MaskAction.MASK_PARTIAL:
                    result[key] = self._mask_partial(value)
                elif rule.action == MaskAction.CLASSIFICATION_GATED:
                    if rule.gate_level is not None and clearance >= rule.gate_level:
                        result[key] = value
                    else:
                        gate_name = rule.gate_level.name if rule.gate_level else "UNKNOWN"
                        result[key] = f"[CLASSIFIED:{gate_name}]"
            elif isinstance(value, dict):
                result[key] = self.apply(value, clearance, role)
            elif isinstance(value, list):
                result[key] = [
                    self.apply(item, clearance, role) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def apply_batch(
        self,
        records: list[dict[str, Any]],
        clearance: ClearanceLevel,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Apply mask rules to a list of result records."""
        return [self.apply(r, clearance, role) for r in records]
