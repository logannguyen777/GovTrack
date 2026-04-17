# Import all agent implementations to trigger register_agent() calls
from . import (
    classifier,  # noqa: F401
    compliance,  # noqa: F401
    consult,  # noqa: F401
    dispatch_router,  # noqa: F401
    doc_analyzer,  # noqa: F401
    drafter,  # noqa: F401
    intake,  # noqa: F401
    legal_lookup,  # noqa: F401
    planner,  # noqa: F401
    router,  # noqa: F401
    security_officer,  # noqa: F401
    summarizer,  # noqa: F401
)
