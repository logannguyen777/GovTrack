"""
backend/src/telemetry.py
OpenTelemetry tracing setup for GovFlow.

Instruments FastAPI, asyncpg, and httpx automatically.
gremlinpython has no OTel instrumentation — gremlin spans are added manually
in permitted_client.py.

Call once from lifespan:
    setup_tracing(service_name="govflow-backend", endpoint=settings.otel_endpoint)
"""

from __future__ import annotations

import logging

_logger = logging.getLogger("govflow.telemetry")

_SERVICE_VERSION = "0.1.0"


def setup_tracing(service_name: str, endpoint: str | None) -> None:
    """Configure OpenTelemetry TracerProvider.

    Args:
        service_name: Logical service name (e.g. "govflow-backend").
        endpoint:     OTLP gRPC endpoint (e.g. "grpc://otel-collector:4317").
                      If None or empty, a NoopSpanProcessor is used (dev mode).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from .config import settings as _settings

        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": _SERVICE_VERSION,
                "deployment.environment": _settings.govflow_env,
            }
        )

        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                # Strip scheme prefix if present (some configs use "grpc://")
                _endpoint = endpoint.replace("grpc://", "").replace("http://", "")
                exporter = OTLPSpanExporter(endpoint=_endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                _logger.info("OTel tracing: OTLP exporter -> %s", _endpoint)
            except Exception as exc:
                _logger.warning("OTel OTLP exporter failed (%s) — using noop", exc)
                _use_noop(provider)
        else:
            _use_noop(provider)

        trace.set_tracer_provider(provider)

        _instrument_fastapi()
        _instrument_asyncpg()
        _instrument_httpx()

        _logger.info("OTel tracing configured for service=%s", service_name)

    except ImportError as exc:
        _logger.warning("opentelemetry packages not installed (%s) — tracing disabled", exc)


def _use_noop(provider: TracerProvider) -> None:  # noqa: F821
    """Add a no-op span processor (dev mode — no export)."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    # InMemorySpanExporter is safe and drops spans when buffer full — low overhead
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))


def _instrument_fastapi() -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor().instrument()
        _logger.debug("OTel: FastAPI instrumented")
    except Exception as exc:
        _logger.debug("OTel FastAPI instrumentation skipped: %s", exc)


def _instrument_asyncpg() -> None:
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
        _logger.debug("OTel: asyncpg instrumented")
    except Exception as exc:
        _logger.debug("OTel asyncpg instrumentation skipped: %s", exc)


def _instrument_httpx() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        _logger.debug("OTel: httpx instrumented")
    except Exception as exc:
        _logger.debug("OTel httpx instrumentation skipped: %s", exc)


def get_tracer(name: str = "govflow") -> _NoopTracer:  # type: ignore[return-value]
    """Return a named Tracer from the global provider.

    Falls back to a noop tracer if OTel is not installed.
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return _NoopTracer()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Minimal noop tracer for environments without opentelemetry installed
# ---------------------------------------------------------------------------


class _NoopSpan:
    """A span that does nothing."""

    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def set_attribute(self, key: str, value: object) -> None:  # noqa: ARG002
        pass

    def record_exception(self, exc: BaseException, **_: object) -> None:  # noqa: ARG002
        pass

    def set_status(self, *_: object) -> None:
        pass


class _NoopTracer:
    """A tracer that does nothing."""

    def start_as_current_span(self, name: str, **kwargs: object):  # noqa: ARG002
        return _NoopSpan()

    def start_span(self, name: str, **kwargs: object) -> _NoopSpan:  # noqa: ARG002
        return _NoopSpan()
