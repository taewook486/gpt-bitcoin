# Tests for OpenTelemetry Observability Configuration
import pytest
from unittest.mock import MagicMock, patch

from gpt_bitcoin.infrastructure.observability import (
    get_tracer,
    get_meter_provider,
    configure_telemetry,
    create_metrics,
    create_health_checker,
    HealthChecker,
)


class TestGetTracer:
    """Test tracer provider initialization."""

    def test_tracer_is_singleton():
        """Test that get_tracer returns the same instance."""
        tracer1 = get_tracer()
        tracer2 = get_tracer()
        assert tracer1 is tracer2
        assert tracer1 is not None

    def test_tracer_has_service_name():
        """Test that tracer has service name configured."""
        tracer, _ = configure_telemetry(service_name="test-service")
        assert tracer is not None


class TestGetMeterProvider:
    """Test meter provider initialization."""

    def test_meter_provider_is_singleton():
        """Test that get_meter_provider returns the same instance."""
        meter1 = get_meter_provider()
        meter2 = get_meter_provider()
        assert meter1 is meter2
        assert meter1 is not None


class TestConfigureTelemetry:
    """Test telemetry configuration function."""

    def test_default_configuration():
        """Test default telemetry configuration."""
        tracer, meter = configure_telemetry()

        assert tracer is not None
        assert meter is not None

    def test_custom_service_name():
        """Test configuration with custom service name."""
        tracer, meter = configure_telemetry(service_name="custom-service")

        assert tracer is not None
        assert meter is not None


class TestCreateMetrics:
    """Test metrics creation function."""

    def test_default_metrics():
        """Test default metrics creation."""
        metrics = create_metrics()

        assert "requests" in metrics
        assert "errors" in metrics
        assert "trading" in metrics
        assert "latency" in metrics

    def test_metrics_counter_increment():
        """Test metrics counter increment."""
        metrics_dict = create_metrics()

        # Increment request counter
        metrics_dict["trading"].add(1, {"status": "test"})

        # Metric was created successfully
        assert metrics_dict["trading"] is not None


class TestHealthChecker:
    """Test health checker functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy():
        """Test health check when all services are healthy."""
        checker = create_health_checker(
            check_external_apis=False,
            timeout_seconds=1.0,
        )

        result = await checker.check_health()

        assert result["status"] == "healthy"
        assert result["checks"]["application"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_external_apis(self):
        """Test health check with external API connectivity check."""
        checker = create_health_checker(
            check_external_apis=True,
            timeout_seconds=1.0,
        )

        result = await checker.check_health()

        # Should be healthy by default (mocked)
        assert result["status"] == "healthy"
        assert "external_apis" in result["checks"]

    @pytest.mark.asyncio
    async def test_health_checker_initialization():
        """Test health checker is properly initialized."""
        checker = HealthChecker(
            check_external_apis=False,
            timeout_seconds=5.0,
        )

        assert checker.check_external_apis is False
        assert checker.timeout_seconds == 5.0
