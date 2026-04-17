"""
backend/src/logging_config.py
Structured JSON logging with PII redaction for GovFlow.

Uses python-json-logger (pythonjsonlogger) as a drop-in stdlib logging formatter.
Fields emitted per record:
  timestamp, level, logger, message, request_id, correlation_id,
  user_id, role, action, duration_ms
"""

from __future__ import annotations

import logging
import re
from typing import Any

# ---------------------------------------------------------------------------
# PII patterns — reuse from agents.pii_filters where possible
# ---------------------------------------------------------------------------

try:
    from .agents.pii_filters import _BARE_ID_PATTERN, _EMAIL_PATTERN, _PHONE_PATTERN
    _ID_PATTERN = _BARE_ID_PATTERN
    _PH_PATTERN = _PHONE_PATTERN
    _EM_PATTERN = _EMAIL_PATTERN
except Exception:
    # Fallback patterns if pii_filters is unavailable
    _ID_PATTERN = re.compile(r"\b0?\d{9,12}\b")
    _PH_PATTERN = re.compile(r"0[3579][\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2,3}")
    _EM_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_PII_SUBS: list[tuple[re.Pattern[str], str]] = [
    (_EM_PATTERN, "[REDACTED_EMAIL]"),
    (_PH_PATTERN, "[REDACTED_PHONE]"),
    (_ID_PATTERN, "[REDACTED_ID]"),
]


def _redact(value: str) -> str:
    """Apply PII redaction to a string value."""
    for pattern, replacement in _PII_SUBS:
        value = pattern.sub(replacement, value)
    return value


def _deep_redact(obj: Any) -> Any:
    """Recursively redact PII from str, dict, list."""
    if isinstance(obj, str):
        return _redact(obj)
    if isinstance(obj, dict):
        return {k: _deep_redact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_redact(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# PII Redaction Filter (stdlib logging.Filter)
# ---------------------------------------------------------------------------


class PIIRedactionFilter(logging.Filter):
    """
    Logging filter that scrubs PII from log record message and extra fields.

    Runs on every LogRecord before it reaches any handler.
    Mutates ``record.msg`` and any string extra attributes in-place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Scrub main message
        if isinstance(record.msg, str):
            record.msg = _redact(record.msg)

        # Scrub args (used by %-style formatting)
        if isinstance(record.args, dict):
            record.args = {k: _deep_redact(v) for k, v in record.args.items()}
        elif isinstance(record.args, tuple):
            record.args = tuple(_deep_redact(a) for a in record.args)

        # Scrub any extra fields attached to the record
        for attr in list(vars(record).keys()):
            if attr.startswith("_") or attr in {
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info", "exc_text",
                "stack_info", "lineno", "funcName", "created", "msecs",
                "relativeCreated", "thread", "threadName", "processName",
                "process", "message",
            }:
                continue
            val = getattr(record, attr)
            if isinstance(val, str):
                setattr(record, attr, _redact(val))

        return True  # always pass the record through


# ---------------------------------------------------------------------------
# JSON Formatter using pythonjsonlogger
# ---------------------------------------------------------------------------


def _build_formatter() -> logging.Formatter:
    """Build a JSON formatter.

    Tries pythonjsonlogger first; falls back to a minimal JSON formatter so
    the module is importable even if the package is not installed yet.
    """
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

        class _GovFlowJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(
                self,
                log_record: dict[str, Any],
                record: logging.LogRecord,
                message_dict: dict[str, Any],
            ) -> None:
                super().add_fields(log_record, record, message_dict)

                # Inject request context from ContextVar (best-effort)
                try:
                    from .middleware.request_context import (
                        _correlation_id_var,
                        _request_id_var,
                    )

                    log_record["request_id"] = _request_id_var.get(None)
                    log_record["correlation_id"] = _correlation_id_var.get(None)
                except Exception:
                    pass

                # Rename fields to canonical names
                log_record.setdefault("timestamp", log_record.pop("asctime", None))
                log_record.setdefault("level", log_record.pop("levelname", record.levelname))
                log_record.setdefault("logger", record.name)

        return _GovFlowJsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S.%fZ",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
    except ImportError:
        # Minimal fallback — plain text JSON lines
        import json as _json

        class _FallbackFormatter(logging.Formatter):  # type: ignore[assignment]
            def format(self, record: logging.LogRecord) -> str:
                record.message = record.getMessage()
                d: dict[str, Any] = {
                    "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.message,
                }
                return _json.dumps(d, ensure_ascii=False)

        return _FallbackFormatter()


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatter and PII redaction filter.

    Call once from lifespan startup.  Safe to call multiple times (idempotent).

    Args:
        level: Logging level string, e.g. "DEBUG", "INFO", "WARNING".
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()

    # Avoid double-registration if called multiple times
    if any(isinstance(h, logging.StreamHandler) and getattr(h, "_govflow_json", False)
           for h in root.handlers):
        root.setLevel(numeric_level)
        return

    # Remove any default handlers (uvicorn sets these before lifespan)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
    handler.addFilter(PIIRedactionFilter())
    handler._govflow_json = True  # type: ignore[attr-defined]

    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Suppress overly verbose third-party loggers
    logging.getLogger("gremlin_python").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
