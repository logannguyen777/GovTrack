"""
backend/src/metrics.py
Custom Prometheus metrics for GovFlow.

All metrics use the prometheus_client library (pulled in by
prometheus-fastapi-instrumentator).  Import this module early in main.py so
the metrics are registered before the first scrape.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Agent metrics ─────────────────────────────────────────────────────────────

agent_duration_seconds = Histogram(
    "govflow_agent_duration_seconds",
    "End-to-end wall-clock duration of an agent run (seconds)",
    labelnames=["agent_name", "status"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# ── DashScope / Qwen token metrics ────────────────────────────────────────────

dashscope_tokens_total = Counter(
    "govflow_dashscope_tokens_total",
    "Cumulative tokens sent to / received from DashScope",
    labelnames=["model", "direction"],  # direction: input | output
)

dashscope_cost_cny = Counter(
    "govflow_dashscope_cost_cny_total",
    "Estimated cumulative DashScope cost in CNY (uses public list price)",
    labelnames=["model"],
)

# ── Gremlin query metrics ─────────────────────────────────────────────────────

gremlin_query_duration_seconds = Histogram(
    "govflow_gremlin_query_duration_seconds",
    "Duration of Gremlin template query execution (seconds)",
    labelnames=["template_name", "status"],  # status: ok | error
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# ── Permission layer metrics ──────────────────────────────────────────────────

permission_denials_total = Counter(
    "govflow_permission_denials_total",
    "Number of graph access denials per permission tier",
    labelnames=["tier"],  # tier: sdk_guard | rbac | property_mask
)

# ── Audit reliability ─────────────────────────────────────────────────────────

audit_write_failures_total = Counter(
    "govflow_audit_write_failures_total",
    "Number of audit event write failures (Hologres or GDB)",
)

# ── Case pipeline ─────────────────────────────────────────────────────────────

cases_in_flight = Gauge(
    "govflow_cases_in_flight",
    "Number of case agent pipelines currently executing",
)


# ── Cost estimation constants (CNY per 1k tokens, approximate list price) ────
# Source: https://www.alibabacloud.com/en/product/modelstudio/pricing
# Update these when Alibaba Cloud revises pricing.
_COST_PER_1K_INPUT: dict[str, float] = {
    "qwen-max-latest": 0.04,
    "qwen-plus-latest": 0.008,
    "qwen-turbo-latest": 0.003,
    "qwen-vl-max-latest": 0.06,
    "qwen-vl-plus-latest": 0.008,
    "text-embedding-v3": 0.0007,
}
_COST_PER_1K_OUTPUT: dict[str, float] = {
    "qwen-max-latest": 0.12,
    "qwen-plus-latest": 0.02,
    "qwen-turbo-latest": 0.006,
    "qwen-vl-max-latest": 0.12,
    "qwen-vl-plus-latest": 0.008,
    "text-embedding-v3": 0.0,
}


# ── Helper functions ──────────────────────────────────────────────────────────


def record_agent_duration(agent_name: str, status: str, duration_seconds: float) -> None:
    """Record end-to-end duration for an agent run."""
    agent_duration_seconds.labels(agent_name=agent_name, status=status).observe(duration_seconds)


def record_tokens(model: str, input_tokens: int, output_tokens: int) -> None:
    """
    Record token usage and estimated CNY cost for a DashScope API call.

    Args:
        model:          Model ID as returned by DashScope (e.g. "qwen-max-latest").
        input_tokens:   Prompt / input token count.
        output_tokens:  Completion / output token count.
    """
    if input_tokens > 0:
        dashscope_tokens_total.labels(model=model, direction="input").inc(input_tokens)
    if output_tokens > 0:
        dashscope_tokens_total.labels(model=model, direction="output").inc(output_tokens)

    # Estimate cost
    cost = (input_tokens / 1000) * _COST_PER_1K_INPUT.get(model, 0.04) + (
        output_tokens / 1000
    ) * _COST_PER_1K_OUTPUT.get(model, 0.12)
    if cost > 0:
        dashscope_cost_cny.labels(model=model).inc(cost)


def record_gremlin_query(template_name: str, status: str, duration_seconds: float) -> None:
    """Record Gremlin template query duration."""
    gremlin_query_duration_seconds.labels(
        template_name=template_name, status=status
    ).observe(duration_seconds)


def record_permission_denial(tier: str) -> None:
    """Increment the denial counter for the given permission tier."""
    permission_denials_total.labels(tier=tier).inc()


def record_audit_write_failure() -> None:
    """Increment the audit write failure counter."""
    audit_write_failures_total.inc()


def cases_in_flight_inc() -> None:
    """Increment the cases-in-flight gauge (called by orchestrator on pipeline start)."""
    cases_in_flight.inc()


def cases_in_flight_dec() -> None:
    """Decrement the cases-in-flight gauge (called by orchestrator on pipeline end)."""
    cases_in_flight.dec()
