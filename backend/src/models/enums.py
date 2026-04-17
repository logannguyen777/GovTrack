"""backend/src/models/enums.py"""

from enum import IntEnum, StrEnum


class ClearanceLevel(IntEnum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3


class CaseStatus(StrEnum):
    SUBMITTED = "submitted"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    GAP_CHECKING = "gap_checking"
    PENDING_SUPPLEMENT = "pending_supplement"
    LEGAL_REVIEW = "legal_review"
    DRAFTING = "drafting"
    LEADER_REVIEW = "leader_review"
    CONSULTATION = "consultation"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    FAILED = "failed"  # pipeline crash / retry-exhausted


class Role(StrEnum):
    ADMIN = "admin"
    LEADER = "leader"
    OFFICER = "officer"
    STAFF_INTAKE = "staff_intake"
    STAFF_PROCESSOR = "staff_processor"
    LEGAL = "legal"
    SECURITY = "security"
    PUBLIC_VIEWER = "public_viewer"


class NotificationCategory(StrEnum):
    INFO = "info"
    ACTION_REQUIRED = "action_required"
    ALERT = "alert"
    SYSTEM = "system"


class CaseType(StrEnum):
    CITIZEN_TTHC = "citizen_tthc"
    INTERNAL_DISPATCH = "internal_dispatch"
