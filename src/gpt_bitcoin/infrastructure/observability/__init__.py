"""
Observability module for the trading system.

Provides OpenTelemetry-based tracing, metrics, and health checking.

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 2.9 observability requirements.
"""

from gpt_bitcoin.infrastructure.observability.tracing import (
    get_tracer,
    setup_tracing,
    create_metrics,
    record_span,
    HealthChecker,
    create_health_check_endpoint,
    get_meter_provider,
    configure_telemetry,
    set_correlation_id,
    get_correlation_id,
)

__all__ = [
    "get_tracer",
    "setup_tracing",
    "create_metrics",
    "record_span",
    "HealthChecker",
    "create_health_check_endpoint",
    "get_meter_provider",
    "configure_telemetry",
    "set_correlation_id",
    "get_correlation_id",
]
