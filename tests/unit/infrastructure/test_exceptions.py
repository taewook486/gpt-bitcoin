"""
Unit tests for custom exception hierarchy.

Tests cover:
- Exception inheritance
- Context data storage
- Specific exception types
"""

from gpt_bitcoin.infrastructure.exceptions import (
    AnalysisError,
    CircuitBreakerOpenError,
    ConfigurationError,
    DataFetchError,
    DecisionError,
    ExecutionError,
    GLMAPIError,
    InsufficientBalanceError,
    RateLimitError,
    SerpApiError,
    TradingError,
    UpbitAPIError,
)


class TestTradingErrorBase:
    """Test base TradingError class."""

    def test_basic_message(self):
        """TradingError should store message."""
        error = TradingError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"

    def test_context_storage(self):
        """TradingError should store context data."""
        error = TradingError("Error", context={"key": "value", "count": 42})
        assert error.context["key"] == "value"
        assert error.context["count"] == 42

    def test_default_empty_context(self):
        """TradingError should have empty context by default."""
        error = TradingError("Error")
        assert error.context == {}


class TestUpbitAPIError:
    """Test UpbitAPIError."""

    def test_with_status_code(self):
        """UpbitAPIError should store status code."""
        error = UpbitAPIError("API failed", status_code=500)
        assert error.status_code == 500
        assert error.context["status_code"] == 500

    def test_with_response_data(self):
        """UpbitAPIError should store response data."""
        response = {"error": "Invalid request"}
        error = UpbitAPIError("API failed", response_data=response)
        assert error.response_data == response


class TestGLMAPIError:
    """Test GLMAPIError."""

    def test_with_model_info(self):
        """GLMAPIError should store model name."""
        error = GLMAPIError("GLM failed", model="glm-4.6v", status_code=429)
        assert error.model == "glm-4.6v"
        assert error.status_code == 429


class TestInsufficientBalanceError:
    """Test InsufficientBalanceError."""

    def test_with_balance_info(self):
        """InsufficientBalanceError should store balance details."""
        error = InsufficientBalanceError(
            currency="KRW",
            available=1000.0,
            required=5000.0,
        )
        assert error.currency == "KRW"
        assert error.available == 1000.0
        assert error.required == 5000.0
        assert "KRW" in str(error)
        assert "1000" in str(error)


class TestRateLimitError:
    """Test RateLimitError."""

    def test_with_retry_after(self):
        """RateLimitError should store retry_after."""
        error = RateLimitError("Rate limited", retry_after=60)
        assert error.retry_after == 60


class TestCircuitBreakerOpenError:
    """Test CircuitBreakerOpenError."""

    def test_with_service_info(self):
        """CircuitBreakerOpenError should store service info."""
        error = CircuitBreakerOpenError(
            service_name="upbit-api",
            recovery_time=12345.0,
        )
        assert error.service_name == "upbit-api"
        assert error.recovery_time == 12345.0
        assert "upbit-api" in str(error)


class TestExecutionError:
    """Test ExecutionError."""

    def test_with_order_info(self):
        """ExecutionError should store order details."""
        error = ExecutionError(
            "Order failed",
            order_type="buy",
            ticker="KRW-BTC",
        )
        assert error.order_type == "buy"
        assert error.ticker == "KRW-BTC"


class TestExceptionInheritance:
    """Test exception inheritance chain."""

    def test_all_exceptions_inherit_from_trading_error(self):
        """All custom exceptions should inherit from TradingError."""
        exceptions = [
            UpbitAPIError("test"),
            GLMAPIError("test"),
            SerpApiError("test"),
            ConfigurationError("test"),
            DataFetchError("test"),
            AnalysisError("test"),
            DecisionError("test"),
            ExecutionError("test"),
            InsufficientBalanceError("KRW", 0, 100),
            RateLimitError("test"),
            CircuitBreakerOpenError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, TradingError)
            assert isinstance(exc, Exception)
