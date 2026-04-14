"""
Tier 3: Post-execution property redaction.
Applied to all query results before they reach the caller.
Rules are defined per-property and gated by clearance level.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..models.enums import ClearanceLevel


class MaskAction(str, Enum):
    REDACT = "redact"                    # Remove field entirely
    MASK_PARTIAL = "mask_partial"        # Show last 4 chars: "***1234"
    CLASSIFICATION_GATED = "classification_gated"  # Show only if clearance >= level


@dataclass
class MaskRule:
    property_name: str
    action: MaskAction
    gate_level: ClearanceLevel | None = None  # For CLASSIFICATION_GATED


# Default rules -- extend per deployment
DEFAULT_MASK_RULES: list[MaskRule] = [
    MaskRule("national_id", MaskAction.REDACT),
    MaskRule("tax_id", MaskAction.REDACT),
    MaskRule("phone_number", MaskAction.MASK_PARTIAL),
    MaskRule("email", MaskAction.MASK_PARTIAL),
    MaskRule("home_address", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.CONFIDENTIAL),
    MaskRule("bank_account", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
    MaskRule("criminal_record", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.TOP_SECRET),
    MaskRule("investigation_notes", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.TOP_SECRET),
    MaskRule("internal_assessment", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
]


class PropertyMask:
    """Post-query field redaction engine."""

    def __init__(self, rules: list[MaskRule] | None = None):
        self.rules = {r.property_name: r for r in (rules or DEFAULT_MASK_RULES)}

    def _mask_partial(self, value: Any) -> str:
        s = str(value)
        if len(s) <= 4:
            return "****"
        return "*" * (len(s) - 4) + s[-4:]

    def apply(self, record: dict[str, Any], clearance: ClearanceLevel) -> dict[str, Any]:
        """
        Apply mask rules to a single result record.
        Recursively masks nested dicts and lists.
        Returns a new dict with redacted/masked fields.
        """
        result = {}
        for key, value in record.items():
            rule = self.rules.get(key)

            if rule is not None:
                # Apply masking rule
                if rule.action == MaskAction.REDACT:
                    result[key] = "[REDACTED]"
                elif rule.action == MaskAction.MASK_PARTIAL:
                    result[key] = self._mask_partial(value)
                elif rule.action == MaskAction.CLASSIFICATION_GATED:
                    if clearance >= rule.gate_level:
                        result[key] = value
                    else:
                        result[key] = f"[CLASSIFIED:{rule.gate_level.name}]"
            elif isinstance(value, dict):
                # Recurse into nested dicts
                result[key] = self.apply(value, clearance)
            elif isinstance(value, list):
                # Recurse into list items
                result[key] = [
                    self.apply(item, clearance) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def apply_batch(
        self, records: list[dict[str, Any]], clearance: ClearanceLevel
    ) -> list[dict[str, Any]]:
        """Apply mask rules to a list of result records."""
        return [self.apply(r, clearance) for r in records]
