"""
backend/src/middleware/request_context.py
FastAPI middleware that manages X-Request-ID and X-Correlation-ID per request.

Usage:
    app.add_middleware(RequestContextMiddleware)
    request_id = get_request_id()  # from any code in the same async task
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# ContextVars — one per request task
# ---------------------------------------------------------------------------

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_logger = logging.getLogger("govflow.request_context")

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_request_id() -> str:
    """Return the current request ID or a new UUID if none is set."""
    return _request_id_var.get(None) or str(uuid.uuid4())


def get_correlation_id() -> str | None:
    """Return the current correlation ID, or None."""
    return _correlation_id_var.get(None)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Reads ``X-Request-ID`` from the incoming request (generates uuid4 if missing),
    stores in a ContextVar and echoes back in the response.

    Also forwards ``X-Correlation-ID`` if present.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID")

        # Set ContextVars for this request task
        token_req = _request_id_var.set(req_id)
        token_corr = _correlation_id_var.set(corr_id)

        try:
            response: Response = await call_next(request)
        finally:
            _request_id_var.reset(token_req)
            _correlation_id_var.reset(token_corr)

        # Echo back in response headers
        response.headers["X-Request-ID"] = req_id
        if corr_id:
            response.headers["X-Correlation-ID"] = corr_id

        return response


# ---------------------------------------------------------------------------
# LogRecord factory injection
# ---------------------------------------------------------------------------
# Replaces the default LogRecord factory so every record automatically
# contains the current request_id and correlation_id.

_original_factory = logging.getLogRecordFactory()


def _govflow_record_factory(*args, **kwargs):  # type: ignore[no-untyped-def]
    record = _original_factory(*args, **kwargs)
    record.request_id = _request_id_var.get(None)
    record.correlation_id = _correlation_id_var.get(None)
    return record


logging.setLogRecordFactory(_govflow_record_factory)
