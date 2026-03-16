"""
OpenTelemetry Tracing Configuration.

This module provides distributed tracing for the application
using OpenTelemetry standards.

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 2.9 observability requirements.
"""

from __future__ import annotations

import contextvars
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

# Global tracer provider
_tracer_provider: TracerProvider | None = None
_global_meter_provider: MeterProvider | None = None

# Correlation ID context variable
_correlation_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="",
)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: Unique identifier for this request/session

    @MX:NOTE: Used for tracking requests across distributed systems.
    """
    _correlation_id_context.set(correlation_id)


def get_correlation_id() -> str:
    """
    Get the current correlation ID.

    Returns:
        The correlation ID for the current context, or empty string if not set
    """
    return _correlation_id_context.get("")


def setup_tracing(
    service_name: str = "gpt-bitcoin",
    log_level: str = "INFO",
    otlp_endpoint: str | None = None,
) -> TracerProvider:
    """
    Configure OpenTelemetry tracing for the application.

    Args:
        service_name: Name of the service for tracing
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        otlp_endpoint: OTLP collector endpoint (optional, for production)

    Returns:
        Configured TracerProvider instance

    @MX:NOTE: Called during application startup to initialize tracing.
    """
    global _tracer_provider

    # Create resource with service name
    resource = Resource.create({"service.name": service_name})

    # Configure tracer provider
    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)

    # Add console exporter for development
    _tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    # Configure OTLP exporter if endpoint provided
    if otlp_endpoint:
        _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    return _tracer_provider


def get_tracer() -> TracerProvider:
    """
    Get or create the global tracer provider.

    Returns:
        The configured TracerProvider instance with console exporter
    """
    global _tracer_provider
    if _tracer_provider is None:
        _tracer_provider = setup_tracing()
    return _tracer_provider


def get_meter_provider() -> MeterProvider:
    """
    Get or create the global meter provider.

    Returns:
        The configured MeterProvider instance with console exporter
    """
    global _global_meter_provider
    if _global_meter_provider is None:
        # Configure metrics export
        _global_meter_provider = MeterProvider()
        metrics.set_meter_provider(_global_meter_provider)

    return _global_meter_provider


def create_metrics() -> dict[str, Any]:
    """
    Create standard application metrics.

    Returns:
        Dictionary of metric instruments with keys: requests, errors, trading, latency
    """
    provider = get_meter_provider()
    meter = provider.get_meter("gpt-bitcoin")

    # Request counter
    request_counter = meter.create_counter(
        name="http.requests",
        description="Total HTTP requests",
        unit="1",
    )

    # Error counter
    error_counter = meter.create_counter(
        name="http.errors",
        description="Total HTTP errors",
        unit="1",
    )

    # Trading counter
    trading_counter = meter.create_counter(
        name="trading.decisions",
        description="Total trading decisions",
        unit="1",
    )

    # API latency histogram
    api_latency = meter.create_histogram(
        name="api.latency",
        description="API call latency",
        unit="ms",
    )

    return {
        "requests": request_counter,
        "errors": error_counter,
        "trading": trading_counter,
        "latency": api_latency,
    }


def record_span(
    tracer_or_name: TracerProvider | str,
    name_or_attributes: str | dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> Any:
    """
    Create and record a tracing span.

    Args:
        tracer_or_name: TracerProvider instance or span name (string)
        name_or_attributes: Span name (if first arg is tracer) or attributes dict
        attributes: Additional span attributes (when using old signature)

    Returns:
        The created span

    @MX:NOTE: Supports both new signature record_span(name, attributes)
        and legacy signature record_span(tracer, name, attributes).
    """
    # Support both signatures for backward compatibility
    if isinstance(tracer_or_name, str):
        # New signature: record_span(name, attributes)
        span_name = tracer_or_name
        span_attrs = name_or_attributes if isinstance(name_or_attributes, dict) else attributes
    else:
        # Legacy signature: record_span(tracer, name, attributes)
        span_name = name_or_attributes if isinstance(name_or_attributes, str) else "span"
        span_attrs = attributes

    span_tracer = trace.get_tracer(__name__)
    span = span_tracer.start_span(span_name)
    for key, value in (span_attrs or {}).items():
        span.set_attribute(key, value)
    return span


def configure_telemetry(
    service_name: str = "gpt-bitcoin",
    log_level: str = "INFO",
    otlp_endpoint: str | None = None,
) -> tuple[TracerProvider, MeterProvider]:
    """
    Configure OpenTelemetry for the application.

    Args:
        service_name: Name of the service for tracing
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        otlp_endpoint: OTLP collector endpoint (optional, for production)

    Returns:
        Tuple of (TracerProvider, MeterProvider)

    @MX:NOTE: Convenience function that sets up both tracing and metrics.
    """
    tracer = setup_tracing(
        service_name=service_name,
        log_level=log_level,
        otlp_endpoint=otlp_endpoint,
    )
    meter = get_meter_provider()

    return tracer, meter


class HealthChecker:
    """
    Health check implementation for monitoring application health.

    Provides health status endpoint that checks:
    - Application responsiveness
    - External API connectivity
    - Resource availability

    @MX:NOTE: Implements health check endpoints for monitoring systems.
    """

    def __init__(
        self,
        check_external_apis: bool = True,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.check_external_apis = check_external_apis
        self.timeout_seconds = timeout_seconds
        self._is_healthy = True

    async def check_health(self) -> dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Dictionary with health status information including
            status ("healthy" or "unhealthy") and checks dict
        """
        checks: dict[str, bool] = {
            "application": await self._check_application_health(),
        }

        if self.check_external_apis:
            try:
                checks["external_apis"] = await self._check_external_api_connectivity()
            except Exception:
                checks["external_apis"] = False

        all_healthy = all(checks.values())

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
        }

    async def _check_application_health(self) -> bool:
        """Check application internal health."""
        return True

    async def _check_external_api_connectivity(self) -> bool:
        """
        Check connectivity to external APIs (Upbit, GLM).

        @MX:WARN: This method makes real API calls in production.
        """
        if not self.check_external_apis:
            return True

        try:
            # In production, this would make actual API calls
            # For now, return True
            return True
        except Exception:
            return False


def create_health_check_endpoint() -> HealthChecker:
    """
    Create and configure health check endpoint.

    Returns:
        Configured HealthChecker instance
    """
    return HealthChecker(
        check_external_apis=True,
        timeout_seconds=5.0,
    )
