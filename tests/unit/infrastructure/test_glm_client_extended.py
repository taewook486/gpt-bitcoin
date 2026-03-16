"""
Unit tests for GLM client - extended coverage.

Tests cover:
- analyze_text method
- analyze_with_vision method
- Error handling
- Rate limiting integration
- Client initialization
"""

from unittest.mock import MagicMock, patch

import pytest

from gpt_bitcoin.infrastructure.external.glm_client import (
    GLMClient,
    GLMResponse,
    RateLimiter,
    TokenUsage,
    TradingDecision,
)


class TestGLMClientInitialization:
    """Test GLMClient initialization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.zhipuai_api_key = "test_api_key"
        settings.glm_text_model = "glm-5"
        settings.glm_vision_model = "glm-4.6v"
        return settings

    def test_initialization_with_settings(self, mock_settings):
        """GLMClient should initialize with provided settings."""
        client = GLMClient(mock_settings)

        assert client._settings is mock_settings
        assert client._rate_limiter is not None

    def test_initialization_with_custom_params(self, mock_settings):
        """GLMClient should accept custom rate limit params."""
        client = GLMClient(
            mock_settings,
            requests_per_minute=30,
            tokens_per_minute=50000,
            max_retries=5,
        )

        assert client._max_retries == 5
        assert client._rate_limiter.requests_per_minute == 30


class TestGLMClientAnalyzeText:
    """Test GLMClient analyze_text method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.zhipuai_api_key = "test_api_key"
        settings.glm_text_model = "glm-5"
        settings.glm_vision_model = "glm-4.6v"
        return settings

    @pytest.fixture
    def glm_client(self, mock_settings):
        """Create GLMClient instance."""
        return GLMClient(mock_settings)

    @pytest.mark.asyncio
    async def test_analyze_text_success(self, glm_client):
        """analyze_text should return GLMResponse."""
        with patch.object(glm_client, "_call_api") as mock_call:
            mock_call.return_value = GLMResponse(
                content='{"decision": "buy", "percentage": 100, "reason": "test"}',
                model="glm-5",
                usage=TokenUsage(),
            )

            result = await glm_client.analyze_text(
                system_prompt="You are a trading assistant.",
                user_message="Should I buy Bitcoin?",
            )

            assert result is not None
            assert result.model == "glm-5"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_text_with_temperature(self, glm_client):
        """analyze_text should pass temperature parameter."""
        with patch.object(glm_client, "_call_api") as mock_call:
            mock_call.return_value = GLMResponse(
                content='{"decision": "hold", "percentage": 0, "reason": "test"}',
                model="glm-5",
                usage=TokenUsage(),
            )

            await glm_client.analyze_text(
                system_prompt="Test prompt",
                user_message="Test message",
                temperature=0.5,
            )

            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args.kwargs
            assert call_kwargs["temperature"] == 0.5


class TestGLMClientAnalyzeWithVision:
    """Test GLMClient analyze_with_vision method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.zhipuai_api_key = "test_api_key"
        settings.glm_text_model = "glm-5"
        settings.glm_vision_model = "glm-4.6v"
        return settings

    @pytest.fixture
    def glm_client(self, mock_settings):
        """Create GLMClient instance."""
        return GLMClient(mock_settings)

    @pytest.mark.asyncio
    async def test_analyze_with_vision_success(self, glm_client):
        """analyze_with_vision should return GLMResponse."""
        with patch.object(glm_client, "_call_api") as mock_call:
            mock_call.return_value = GLMResponse(
                content="Chart analysis result",
                model="glm-4.6v",
                usage=TokenUsage(),
            )

            result = await glm_client.analyze_with_vision(
                system_prompt="Analyze this chart",
                text_messages=["What pattern is this?"],
                image_base64="base64encodedstring",
            )

            assert result is not None
            assert result.model == "glm-4.6v"
            mock_call.assert_called_once()


class TestRateLimiter:
    """Test RateLimiter."""

    @pytest.mark.asyncio
    async def test_acquire_within_limits(self):
        """RateLimiter should allow requests within limits."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )

        # Should not raise
        await limiter.acquire(estimated_tokens=1000)

    def test_record_usage(self):
        """RateLimiter should record token usage."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )

        limiter.record_usage(100)
        limiter.record_usage(200)

        # Token tracking should be working
        assert len(limiter._token_usage) == 2

    @pytest.mark.asyncio
    async def test_request_rate_limit_exceeded(self):
        """RateLimiter should raise when request limit exceeded."""
        from gpt_bitcoin.infrastructure.exceptions import RateLimitError

        limiter = RateLimiter(
            requests_per_minute=2,
            tokens_per_minute=100000,
        )

        # Make requests up to limit
        await limiter.acquire(100)
        await limiter.acquire(100)

        # Next request should fail
        with pytest.raises(RateLimitError):
            await limiter.acquire(100)


class TestTradingDecision:
    """Test TradingDecision model."""

    def test_valid_buy_decision(self):
        """TradingDecision should accept valid buy decision."""
        td = TradingDecision(
            decision="buy",
            percentage=100,
            reason="Bullish trend",
        )
        assert td.decision == "buy"
        assert td.percentage == 100
        assert td.reason == "Bullish trend"

    def test_valid_sell_decision(self):
        """TradingDecision should accept valid sell decision."""
        td = TradingDecision(
            decision="sell",
            percentage=50,
            reason="Take profit",
        )
        assert td.decision == "sell"
        assert td.percentage == 50

    def test_valid_hold_decision(self):
        """TradingDecision should accept valid hold decision."""
        td = TradingDecision(
            decision="hold",
            percentage=0,
            reason="Wait for better entry",
        )
        assert td.decision == "hold"

    def test_confidence_default(self):
        """TradingDecision should have default confidence."""
        td = TradingDecision(
            decision="buy",
            percentage=100,
            reason="test",
        )
        assert td.confidence == 0.5

    def test_confidence_custom(self):
        """TradingDecision should accept custom confidence."""
        td = TradingDecision(
            decision="buy",
            percentage=100,
            reason="test",
            confidence=0.8,
        )
        assert td.confidence == 0.8


class TestTokenUsage:
    """Test TokenUsage model."""

    def test_default_values(self):
        """TokenUsage should have default values."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self):
        """TokenUsage should accept custom values."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestGLMResponse:
    """Test GLMResponse model."""

    def test_basic_response(self):
        """GLMResponse should store basic data."""
        response = GLMResponse(
            content="test content",
            model="glm-5",
            usage=TokenUsage(),
        )

        assert response.content == "test content"
        assert response.model == "glm-5"
        assert response.parsed is None

    def test_response_with_parsed_decision(self):
        """GLMResponse should store parsed decision."""
        decision = TradingDecision(
            decision="buy",
            percentage=100,
            reason="test",
        )

        response = GLMResponse(
            content='{"decision": "buy"}',
            parsed=decision,
            model="glm-5",
            usage=TokenUsage(),
        )

        assert response.parsed is not None
        assert response.parsed.decision == "buy"

    def test_response_with_latency(self):
        """GLMResponse should store latency."""
        response = GLMResponse(
            content="test",
            model="glm-5",
            usage=TokenUsage(),
            latency_ms=150.5,
        )

        assert response.latency_ms == 150.5


class TestGLMClientHealthCheck:
    """Test GLMClient health_check method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.zhipuai_api_key = "test_api_key"
        settings.glm_text_model = "glm-5"
        settings.glm_vision_model = "glm-4.6v"
        return settings

    @pytest.fixture
    def glm_client(self, mock_settings):
        """Create GLMClient instance."""
        return GLMClient(mock_settings)

    @pytest.mark.asyncio
    async def test_health_check_success(self, glm_client):
        """health_check should return True on success."""
        with patch.object(glm_client, "analyze_text") as mock_analyze:
            mock_analyze.return_value = GLMResponse(
                content="ok",
                model="glm-5",
                usage=TokenUsage(),
            )

            result = await glm_client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, glm_client):
        """health_check should return False on failure."""
        with patch.object(glm_client, "analyze_text") as mock_analyze:
            mock_analyze.side_effect = Exception("API error")

            result = await glm_client.health_check()

            assert result is False


class TestRateLimiterTokenLimit:
    """Test RateLimiter token limit functionality - covers lines 157-159."""

    @pytest.mark.asyncio
    async def test_token_rate_limit_exceeded(self):
        """RateLimiter should raise when token limit exceeded."""
        from gpt_bitcoin.infrastructure.exceptions import RateLimitError

        limiter = RateLimiter(
            requests_per_minute=100,
            tokens_per_minute=200,  # Very low token limit
        )

        # Use tokens up to limit
        limiter.record_usage(150)

        # Next request with large token estimate should fail
        with pytest.raises(RateLimitError) as exc_info:
            await limiter.acquire(estimated_tokens=100)

        assert "Token rate limit exceeded" in str(exc_info.value)


class TestGLMClientCallApi:
    """Test GLMClient._call_api method - covers lines 320-423."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.zhipuai_api_key = "test_api_key"
        settings.glm_text_model = "glm-5"
        settings.glm_vision_model = "glm-4.6v"
        return settings

    @pytest.fixture
    def glm_client(self, mock_settings):
        """Create GLMClient instance."""
        return GLMClient(mock_settings)

    @pytest.mark.asyncio
    async def test_call_api_rate_limit_with_retry_after(self, glm_client):
        """_call_api should handle rate limit with retry_after."""
        from gpt_bitcoin.infrastructure.exceptions import RateLimitError

        # Mock rate limiter to raise then succeed
        call_count = [0]

        async def mock_acquire(tokens):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RateLimitError("Rate limited", retry_after=1)

        glm_client._rate_limiter.acquire = mock_acquire
        glm_client._rate_limiter.record_usage = MagicMock()

        # Mock the actual API call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"decision": "hold", "percentage": 0, "reason": "test"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        with patch.object(glm_client._client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            result = await glm_client._call_api(
                model="glm-5",
                system_prompt="Test",
                messages="Test message",
                temperature=0.7,
            )

            assert result is not None
            assert result.parsed is not None

    @pytest.mark.asyncio
    async def test_call_api_connection_error_retry(self, glm_client):
        """_call_api should retry on connection errors."""

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '{"decision": "hold", "percentage": 0, "reason": "test"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        call_count = [0]

        def mock_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Network error")
            return mock_response

        with patch.object(glm_client._client.chat.completions, "create", side_effect=mock_create):
            result = await glm_client._call_api(
                model="glm-5",
                system_prompt="Test",
                messages="Test message",
                temperature=0.7,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_call_api_max_retries_exceeded(self, glm_client):
        """_call_api should raise after max retries."""
        from tenacity import RetryError

        from gpt_bitcoin.infrastructure.external.glm_client import GLMAPIError

        with patch.object(glm_client._client.chat.completions, "create") as mock_create:
            mock_create.side_effect = ConnectionError("Network error")

            with pytest.raises((GLMAPIError, RetryError)):
                await glm_client._call_api(
                    model="glm-5",
                    system_prompt="Test",
                    messages="Test message",
                    temperature=0.7,
                )

    @pytest.mark.asyncio
    async def test_call_api_generic_exception(self, glm_client):
        """_call_api should handle generic exceptions."""
        from gpt_bitcoin.infrastructure.external.glm_client import GLMAPIError

        with patch.object(glm_client._client.chat.completions, "create") as mock_create:
            mock_create.side_effect = ValueError("Invalid parameter")

            with pytest.raises(GLMAPIError) as exc_info:
                await glm_client._call_api(
                    model="glm-5",
                    system_prompt="Test",
                    messages="Test message",
                    temperature=0.7,
                )

            assert "GLM API call failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_api_json_parse_failure(self, glm_client):
        """_call_api should handle JSON parse failures gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        with patch.object(glm_client._client.chat.completions, "create") as mock_create:
            mock_create.return_value = mock_response

            result = await glm_client._call_api(
                model="glm-5",
                system_prompt="Test",
                messages="Test message",
                temperature=0.7,
            )

            assert result is not None
            assert result.parsed is None  # Should be None when JSON parse fails


class TestEncodeImageToBase64:
    """Test GLMClient.encode_image_to_base64 - covers lines 456-457."""

    def test_encode_image_to_base64_success(self, tmp_path):
        """encode_image_to_base64 should encode image file correctly."""
        import base64

        # Create a test image file
        test_content = b"fake image content"
        test_file = tmp_path / "test_image.png"
        test_file.write_bytes(test_content)

        result = GLMClient.encode_image_to_base64(str(test_file))

        # Verify the result is base64 encoded
        expected = base64.b64encode(test_content).decode("utf-8")
        assert result == expected

    def test_encode_image_to_base64_file_not_found(self):
        """encode_image_to_base64 should raise for non-existent file."""
        with pytest.raises(FileNotFoundError):
            GLMClient.encode_image_to_base64("/nonexistent/path/image.png")
