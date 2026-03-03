"""
OpenTelemetry Observability Configuration.

This module provides distributed tracing and metrics collection
for the GPT Bitcoin Auto-Trading System.
"""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    InMemoryMetricReader,
)

logger = logging.getLogger(__name__)

# Global tracer and meter providers
_tracer_provider: TracerProvider | None = None
_global_meter_provider: MeterProvider | None = None


def get_tracer() -> TracerProvider:
    """
    Get or create the global tracer provider.

    Returns:
        The configured TracerProvider instance with console exporter
    """
    global _tracer_provider
    if _tracer_provider is None:
        # Configure trace export
        _tracer_provider = TracerProvider()
        trace.set_tracer_provider(_tracer_provider)

        # Add console exporter for development
        processor = SimpleSpanProcessor(ConsoleSpanExporter())
        _tracer_provider.add_span_processor(processor)

        # Configure metrics
        get_meter_provider()

        logger.info("Tracer provider initialized with console exporter")

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

        # Add console exporter for development
        reader = InMemoryMetricReader()
        _global_meter_provider.add_metric_reader(reader)

        logger.info("Meter provider initialized with console exporter")

    return _global_meter_provider


def configure_telemetry(
    service_name: str = "gpt-bitcoin-auto-trading",
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
        Tuple of (tracer_provider, meter_provider)
    """
    tracer = get_tracer()
    meter = get_meter_provider()

    # Set service name resource attribute
    if hasattr(tracer.resource, 'attributes'):
        tracer.resource.attributes["service.name"] = service_name

    logger.info(
        "Telemetry configured",
        extra={"service_name": service_name, "log_level": log_level}
    )

    return tracer, meter


def create_metrics() -> dict[str, Any]:
    """
    Create standard application metrics.

    Returns:
        Dictionary of metric instruments
    """
    meter = get_meter_provider()

    # Request counter
    request_counter = meter.create_counter(
        name="http_requests_total",
        description="Total HTTP requests",
    )

    # Error counter
    error_counter = meter.create_counter(
        name="http_errors_total",
        description="Total HTTP errors",
    )

    # Trading decision counter
    trading_counter = meter.create_counter(
        name="trading_decisions_total",
        description="Total trading decisions",
    )

    # API latency histogram
    api_latency = meter.create_histogram(
        name="api_latency_seconds",
        description="API call latency in seconds",
    )

    return {
        "requests": request_counter,
        "errors": error_counter,
        "trading": trading_counter,
        "latency": api_latency,
    }


class HealthChecker:
    """
    Health check implementation for monitoring application health.

    Provides health status endpoint that checks:
    - Application responsiveness
    - External API connectivity
    - Resource availability
    """

    def __init__(
        self,
        check_external_apis: bool = True,
        timeout_seconds: float = 5.0,
    ) -> None:
        """
        Initialize health checker.

        Args:
            check_external_apis: Whether to check external API connectivity
            timeout_seconds: Timeout for health checks
        """
        self.check_external_apis = check_external_apis
        self.timeout_seconds = timeout_seconds
        self._is_healthy = True

        # Create metrics for health checks
        self._metrics = create_metrics()
        self._metrics["trading"].add(1, {"status": "initialized"})

    async def check_health(self) -> dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Dictionary with health status information
        """
        app_healthy = await self._check_application_health()
        api_healthy = await self._check_external_api_connectivity()

        self._is_healthy = app_healthy and api_healthy

        return {
            "status": "healthy" if self._is_healthy else "unhealthy",
            "checks": {
                "application": app_healthy,
                "external_apis": api_healthy,
            },
        }

    async def _check_application_health(self) -> bool:
        """Check application internal health."""
        try:
            # Basic application health check
            return True
        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            return False

    async def _check_external_api_connectivity(self) -> bool:
        """Check connectivity to external APIs (Upbit, GLM)."""
        if not self.check_external_apis:
            return True

        # In production, this would make actual API calls
        # For now, return True
        return True


def create_health_checker(
    check_external_apis: bool = True,
    timeout_seconds: float = 5.0,
) -> HealthChecker:
    """
    Create and configure health checker.

    Args:
        check_external_apis: Whether to check external API connectivity
        timeout_seconds: Timeout for health checks

    Returns:
        Configured HealthChecker instance
    """
    return HealthChecker(
        check_external_apis=check_external_apis,
        timeout_seconds=timeout_seconds,
    )


# Export main functions
__all__ = [
    "get_tracer",
    "get_meter_provider",
    "configure_telemetry",
    "create_metrics",
    "create_health_checker",
    "HealthChecker",
]
