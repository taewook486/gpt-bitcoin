"""
Unit tests for GLM Client.

Tests cover:
- TradingDecision model validation
- Rate limiter behavior
- Token usage tracking
"""

import pytest

from gpt_bitcoin.infrastructure.external.glm_client import (
    GLMResponse,
    RateLimiter,
    TokenUsage,
    TradingDecision,
)


class TestTradingDecision:
    """Test TradingDecision Pydantic model."""

    def test_valid_buy_decision(self):
        """Should accept valid buy decision."""
        decision = TradingDecision(
            decision="buy",
            percentage=50.0,
            reason="Market looking bullish",
        )
        assert decision.decision == "buy"
        assert decision.percentage == 50.0
        assert decision.confidence == 0.5  # Default

    def test_valid_sell_decision(self):
        """Should accept valid sell decision."""
        decision = TradingDecision(
            decision="sell",
            percentage=100.0,
            reason="Taking profit",
        )
        assert decision.decision == "sell"

    def test_valid_hold_decision(self):
        """Should accept valid hold decision."""
        decision = TradingDecision(decision="hold", reason="Waiting for signal")
        assert decision.decision == "hold"

    def test_percentage_bounds(self):
        """Percentage must be between 0 and 100."""
        with pytest.raises(ValueError):
            TradingDecision(decision="buy", percentage=150.0)

        with pytest.raises(ValueError):
            TradingDecision(decision="sell", percentage=-10.0)

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            TradingDecision(decision="buy", confidence=1.5)

        with pytest.raises(ValueError):
            TradingDecision(decision="buy", confidence=-0.1)

    def test_optional_fields(self):
        """Optional fields should have defaults."""
        decision = TradingDecision(decision="hold")
        assert decision.percentage == 100.0
        assert decision.reason == ""
        assert decision.confidence == 0.5
        assert decision.market_sentiment is None
        assert decision.risk_level is None

    def test_with_all_fields(self):
        """Should accept all optional fields."""
        decision = TradingDecision(
            decision="buy",
            percentage=75.0,
            reason="Strong uptrend",
            confidence=0.85,
            market_sentiment="bullish",
            risk_level="medium",
        )
        assert decision.market_sentiment == "bullish"
        assert decision.risk_level == "medium"


class TestTokenUsage:
    """Test TokenUsage model."""

    def test_default_values(self):
        """Should have zero defaults."""
        usage = TokenUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self):
        """Should accept custom values."""
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
        """Should create basic response."""
        response = GLMResponse(
            content='{"decision": "buy"}',
            model="glm-4.6v",
        )
        assert response.content == '{"decision": "buy"}'
        assert response.model == "glm-4.6v"
        assert response.parsed is None

    def test_response_with_parsed_decision(self):
        """Should include parsed decision."""
        decision = TradingDecision(decision="sell", percentage=50.0)
        response = GLMResponse(
            content='{"decision": "sell"}',
            parsed=decision,
            model="glm-4.6v",
        )
        assert response.parsed == decision
        assert response.parsed.decision == "sell"


class TestRateLimiter:
    """Test RateLimiter functionality."""

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        """Should allow requests within rate limit."""
        limiter = RateLimiter(requests_per_minute=10)

        # Should not raise
        await limiter.acquire(estimated_tokens=100)

    @pytest.mark.asyncio
    async def test_records_token_usage(self):
        """Should record actual token usage."""
        limiter = RateLimiter(tokens_per_minute=1000)

        await limiter.acquire(estimated_tokens=100)
        limiter.record_usage(150)

        # Token usage should be recorded
        assert len(limiter._token_usage) == 1

    @pytest.mark.asyncio
    async def test_blocks_when_request_limit_exceeded(self):
        """Should block when request limit exceeded."""
        limiter = RateLimiter(requests_per_minute=2)

        # First two should succeed
        await limiter.acquire(100)
        await limiter.acquire(100)

        # Third should raise RateLimitError
        with pytest.raises(Exception):  # RateLimitError
            await limiter.acquire(100)
