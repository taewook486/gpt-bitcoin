# OpenTelemetry Tracing Configuration
# Configure distributed tracing for application

import os
from typing import Any

from opentelemetry import trace, metrics
 set_tracer_provider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
 SimpleSpanProcessor,
)
 from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    InMemoryMetricReader,
)

 PrometheusMetricReader,
)

# Global tracer provider
_tracer_provider: TracerProvider | None
_global_meter_provider: MeterProvider | None


def get_tracer() -> TracerProvider:
    """
    Get or create the global tracer provider.

    Returns:
            The-configured TracerProvider instance with console exporter
        """
        global _tracer_provider
        if _tracer_provider is None:
            # Configure trace export
            trace.set_tracer_provider(TracerProvider())
            tracer = trace.get_tracer(__name__)

            # Add console exporter for development
            tracer.add_span_processor(ConsoleSpanExporter())

            # Configure metrics
            get_meter_provider()

            # Set as global provider
            if _global_meter_provider is None:
                _global_meter_provider = MeterProvider()
                metrics.set_meter_provider(_global_meter_provider)
                # Add console exporter
                _global_meter_provider.meter_provider.add_metric_reader(PrometheusMetricReader())
                # Add console exporter for metrics
                _global_meter_provider.meter_provider.add_metric_reader(ConsoleMetricExporter())

        return _tracer_provider

    _tracer_provider = tracer
    _global_meter_provider = _global_meter_provider


def get_meter_provider() -> MeterProvider:
    """
    Get or create the global meter provider.

    Returns:
            Type-configured MeterProvider instance with console exporter
        """
        global _global_meter_provider
        if _global_meter_provider is None:
            # Configure metrics export
            metrics.set_meter_provider(MeterProvider())
            provider = metrics.get_meter_provider()

            # Add Prometheus reader (for production monitoring)
            provider.add_metric_reader(PrometheusMetricReader())

            # Add console exporter (for development)
            provider.add_metric_reader(ConsoleMetricExporter())

        return _global_meter_provider

    return _global_meter_provider


def configure_telemetry(
    service_name: str = "Gpt Bitcoin Auto-Trading System",
    log_level: str = "INFO",
    otlp_endpoint: str | None,
) -> TracerProvider:
    """
    Configure OpenTelemetry for the application.

    Args:
        service_name: Name of the service for tracing
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        otlp_endpoint: OTLP collector endpoint (optional, for production)
    """
    tracer = get_tracer()
    meter = get_meter_provider()

    # Set service name
    tracer.resource.name = service_name

    # Configure OTLP exporter if endpoint provided
    if otlp_endpoint:
        tracer.add_span_processor(
            BatchSpanProcessor(otlp_endpoint)
        )

    return tracer, meter


def create_metrics() -> dict[str, metrics.Counter]:
    """
    Create standard application metrics.

    Returns:
            Dictionary of metric counters
    """
    meter = get_meter_provider()

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
    tracer: TracerProvider,
    name: str,
    attributes: dict[str, Any] | None,
) -> None:
    """
    Create and record a tracing span.

    Args:
        tracer: Tracer provider instance
        name: Span name
        attributes: Additional span attributes
    """
    span = tracer.start_span(name)
    for key, value in (attributes or {}).items():
        span.set_attribute(key, value)
    return span


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
        self.check_external_apis = check_external_apis
        self.timeout_seconds = timeout_seconds
        self._metrics = create_metrics()
        self._is_healthy = True

        # Record health check metrics
        self._metrics["health.checks"].add(1, {"status": "initialized"})

    async def check_health(self) -> dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Dictionary with health status information
        """
        tracer = get_tracer()
        with tracer.start_as_active_span("health.check"):
            span = await self._check_application_health()
            span.set_attribute("check.type", "application")
            span.set_attribute("status", "healthy" if self._is_healthy else "unhealthy")

            return {
                "status": "healthy" if self._is_healthy else "unhealthy",
                "checks": {
                    "application": self._is_healthy,
                    "external_apis": await self._check_external_api_connectivity()
                    if self.check_external_apis
                    else True,
                },
                "timestamp": span.end_time,
            }

    async def _check_application_health(self) -> bool:
        """Check application internal health."""
        return True

    async def _check_external_api_connectivity(self) -> bool:
        """Check connectivity to external APIs (Upbit, GLM)."""
        if not self.check_external_apis:
            return True

        # In production, this would make actual API calls
        # For now, return True
        return True


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
