"""
Unit tests for observability module.

Tests cover:
- Tracer provider configuration
- Meter provider configuration
- Metrics creation
- Span recording
- Health checker

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest

from gpt_bitcoin.infrastructure.observability import (
    HealthChecker,
    configure_telemetry,
    create_health_check_endpoint,
    create_metrics,
    get_meter_provider,
    get_tracer,
    record_span,
)


class TestGetTracer:
    """Test get_tracer function."""

    def test_get_tracer_creates_provider(self):
        """get_tracer should create a tracer provider."""
        # Reset global state
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None

        from opentelemetry.sdk.trace import TracerProvider

        tracer = get_tracer()

        assert tracer is not None
        assert isinstance(tracer, TracerProvider)

    def test_get_tracer_returns_same_instance(self):
        """get_tracer should return cached instance."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None

        tracer1 = get_tracer()
        tracer2 = get_tracer()

        assert tracer1 is tracer2


class TestGetMeterProvider:
    """Test get_meter_provider function."""

    def test_get_meter_provider_creates_provider(self):
        """get_meter_provider should create a meter provider."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._global_meter_provider = None

        from opentelemetry.sdk.metrics import MeterProvider

        meter = get_meter_provider()

        assert meter is not None
        assert isinstance(meter, MeterProvider)

    def test_get_meter_provider_returns_same_instance(self):
        """get_meter_provider should return cached instance."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._global_meter_provider = None

        meter1 = get_meter_provider()
        meter2 = get_meter_provider()

        assert meter1 is meter2


class TestConfigureTelemetry:
    """Test configure_telemetry function."""

    def test_configure_telemetry_default(self):
        """configure_telemetry should configure with defaults."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None
        obs_module._global_meter_provider = None

        tracer, meter = configure_telemetry()

        assert tracer is not None
        assert meter is not None

    def test_configure_telemetry_with_service_name(self):
        """configure_telemetry should accept service name."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None
        obs_module._global_meter_provider = None

        tracer, meter = configure_telemetry(service_name="Test Service")

        assert tracer is not None
        assert meter is not None

    def test_configure_telemetry_with_log_level(self):
        """configure_telemetry should accept log level."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None
        obs_module._global_meter_provider = None

        tracer, meter = configure_telemetry(log_level="DEBUG")

        assert tracer is not None
        assert meter is not None

    def test_configure_telemetry_with_otlp_endpoint(self):
        """configure_telemetry should handle OTLP endpoint."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None
        obs_module._global_meter_provider = None

        tracer, meter = configure_telemetry(otlp_endpoint="http://localhost:4317")

        assert tracer is not None
        assert meter is not None


class TestCreateMetrics:
    """Test create_metrics function."""

    def test_create_metrics_returns_dict(self):
        """create_metrics should return metrics dictionary."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._global_meter_provider = None

        metrics = create_metrics()

        assert isinstance(metrics, dict)
        assert "requests" in metrics
        assert "errors" in metrics
        assert "trading" in metrics
        assert "latency" in metrics

    def test_create_metrics_counter_types(self):
        """create_metrics counters should be callable."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._global_meter_provider = None

        metrics = create_metrics()

        # Counters should have add method
        assert hasattr(metrics["requests"], "add")
        assert hasattr(metrics["errors"], "add")
        assert hasattr(metrics["trading"], "add")

        # Histogram should have record method
        assert hasattr(metrics["latency"], "record")


class TestRecordSpan:
    """Test record_span function."""

    def test_record_span_creates_span(self):
        """record_span should create and return a span."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None

        tracer = get_tracer()
        span = record_span(tracer, "test_span")

        assert span is not None

    def test_record_span_with_attributes(self):
        """record_span should set attributes on span."""
        import gpt_bitcoin.infrastructure.observability as obs_module

        obs_module._tracer_provider = None

        tracer = get_tracer()
        span = record_span(tracer, "test_span", attributes={"key": "value", "number": 123})

        assert span is not None


class TestHealthChecker:
    """Test HealthChecker class."""

    def test_initialization_default(self):
        """HealthChecker should initialize with defaults."""
        checker = HealthChecker()

        assert checker.check_external_apis is True
        assert checker.timeout_seconds == 5.0
        assert checker._is_healthy is True

    def test_initialization_custom(self):
        """HealthChecker should accept custom settings."""
        checker = HealthChecker(
            check_external_apis=False,
            timeout_seconds=10.0,
        )

        assert checker.check_external_apis is False
        assert checker.timeout_seconds == 10.0

    @pytest.mark.asyncio
    async def test_check_health_returns_dict(self):
        """check_health should return health status dict."""
        checker = HealthChecker()

        result = await checker.check_health()

        assert isinstance(result, dict)
        assert "status" in result
        assert "checks" in result

    @pytest.mark.asyncio
    async def test_check_health_healthy_status(self):
        """check_health should return healthy status when healthy."""
        checker = HealthChecker()
        checker._is_healthy = True

        result = await checker.check_health()

        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_health_unhealthy_status(self):
        """check_health should return unhealthy status when external API check fails."""
        checker = HealthChecker(check_external_apis=True)

        # Mock the external API check to raise an exception
        async def failing_check():
            raise Exception("API failure")

        with pytest.MonkeyPatch.context() as m:
            m.setattr(checker, "_check_external_api_connectivity", failing_check)
            result = await checker.check_health()

        assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_health_with_external_apis(self):
        """check_health should check external APIs when enabled."""
        checker = HealthChecker(check_external_apis=True)

        result = await checker.check_health()

        assert "external_apis" in result["checks"]

    @pytest.mark.asyncio
    async def test_check_health_without_external_apis(self):
        """check_health should skip external API check when disabled."""
        checker = HealthChecker(check_external_apis=False)

        result = await checker.check_health()

        # external_apis should not be in checks when disabled
        assert "external_apis" not in result["checks"]

    @pytest.mark.asyncio
    async def test_check_application_health(self):
        """_check_application_health should return True."""
        checker = HealthChecker()

        result = await checker._check_application_health()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_external_api_connectivity_enabled(self):
        """_check_external_api_connectivity should return True when enabled."""
        checker = HealthChecker(check_external_apis=True)

        result = await checker._check_external_api_connectivity()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_external_api_connectivity_disabled(self):
        """_check_external_api_connectivity should return True when disabled."""
        checker = HealthChecker(check_external_apis=False)

        result = await checker._check_external_api_connectivity()

        assert result is True


class TestCreateHealthCheckEndpoint:
    """Test create_health_check_endpoint function."""

    def test_creates_health_checker(self):
        """create_health_check_endpoint should create HealthChecker."""
        checker = create_health_check_endpoint()

        assert isinstance(checker, HealthChecker)

    def test_default_configuration(self):
        """create_health_check_endpoint should use default configuration."""
        checker = create_health_check_endpoint()

        assert checker.check_external_apis is True
        assert checker.timeout_seconds == 5.0
