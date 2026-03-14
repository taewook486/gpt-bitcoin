"""
Observability module for the trading system.

Provides OpenTelemetry-based tracing, metrics, and health checking.

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 2.9 observability requirements.
"""

from gpt_bitcoin.infrastructure.observability.tracing import (
    HealthChecker,
    configure_telemetry,
    create_health_check_endpoint,
    create_metrics,
    get_correlation_id,
    get_meter_provider,
    get_tracer,
    record_span,
    set_correlation_id,
    setup_tracing,
)

__all__ = [
    "HealthChecker",
    "configure_telemetry",
    "create_health_check_endpoint",
    "create_metrics",
    "get_correlation_id",
    "get_meter_provider",
    "get_tracer",
    "record_span",
    "set_correlation_id",
    "setup_tracing",
]
