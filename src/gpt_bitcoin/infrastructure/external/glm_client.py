"""
ZhipuAI GLM API client for AI-powered trading analysis.

This module provides an async client for interacting with ZhipuAI's GLM models,
including text analysis (GLM-5) and vision analysis (GLM-4.6V).

Features:
- Structured Outputs with Pydantic models
- Rate limiting and token monitoring
- Automatic retry with exponential backoff
- Support for both text and vision models
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any, Literal

from pydantic import BaseModel, Field
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from zhipuai import ZhipuAI

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.infrastructure.exceptions import GLMAPIError, RateLimitError
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


# Cost tracking imports (optional)
try:
    from gpt_bitcoin.infrastructure.monitoring.cost_tracker import (
        CostTracker,
        CostTrackerConfig,
        get_cost_tracker,
    )

    _cost_tracker: CostTracker | None = None
    _cost_tracker_initialized: bool = False
except ImportError:
    _cost_tracker = None
    _cost_tracker_initialized = False
    logger.debug("Cost tracker not available")


# Cost tracking imports (optional)
try:
    from gpt_bitcoin.infrastructure.monitoring.cost_tracker import (
        CostTracker,
        CostTrackerConfig,
        get_cost_tracker,
    )
    _cost_tracker: CostTracker | None = None
    _cost_tracker_initialized: bool = False
except ImportError:
    _cost_tracker = None
    _cost_tracker_initialized = False
    logger.debug("Cost tracker not available")


# =============================================================================
# Pydantic Models for Structured Outputs
# =============================================================================


class TradingDecision(BaseModel):
    """
    Structured output model for trading decisions.

    This model represents the AI's trading decision with validation
    and type safety provided by Pydantic.
    """

    decision: Literal["buy", "sell", "hold"] = Field(
        ...,
        description="Trading decision: buy, sell, or hold",
    )
    percentage: float = Field(
        default=100.0,
        ge=0,
        le=100,
        description="Percentage of balance to trade (0-100)",
    )
    reason: str = Field(
        default="",
        description="Reasoning behind the trading decision",
    )
    confidence: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="Confidence level of the decision (0-1)",
    )

    # Optional market analysis fields
    market_sentiment: str | None = Field(
        default=None,
        description="Overall market sentiment analysis",
    )
    risk_level: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Assessed risk level for the trade",
    )


class TokenUsage(BaseModel):
    """Token usage statistics for API calls."""

    prompt_tokens: int = Field(default=0, description="Number of prompt tokens")
    completion_tokens: int = Field(default=0, description="Number of completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens used")


class GLMResponse(BaseModel):
    """Response from GLM API with metadata."""

    content: str = Field(..., description="Raw response content")
    parsed: TradingDecision | None = Field(
        default=None,
        description="Parsed trading decision if available",
    )
    model: str = Field(..., description="Model used for the request")
    usage: TokenUsage = Field(default_factory=TokenUsage, description="Token usage stats")
    latency_ms: float = Field(default=0, description="Request latency in milliseconds")


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Implements a sliding window rate limiter to prevent API rate limit errors.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100000,
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._request_times: list[float] = []
        self._token_usage: list[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """
        Acquire permission to make an API call.

        Args:
            estimated_tokens: Estimated tokens for the upcoming request

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        async with self._lock:
            now = time.time()
            window_start = now - 60  # 1 minute window

            # Clean old entries
            self._request_times = [t for t in self._request_times if t > window_start]
            self._token_usage = [(t, tokens) for t, tokens in self._token_usage if t > window_start]

            # Check request limit
            if len(self._request_times) >= self.requests_per_minute:
                oldest = self._request_times[0]
                wait_time = oldest + 60 - now
                raise RateLimitError(
                    f"Request rate limit exceeded. Retry after {wait_time:.1f}s",
                    retry_after=int(wait_time) + 1,
                )

            # Check token limit
            current_tokens = sum(tokens for _, tokens in self._token_usage)
            if current_tokens + estimated_tokens > self.tokens_per_minute:
                oldest = self._token_usage[0][0]
                wait_time = oldest + 60 - now
                raise RateLimitError(
                    f"Token rate limit exceeded. Retry after {wait_time:.1f}s",
                    retry_after=int(wait_time) + 1,
                )

            # Record this request
            self._request_times.append(now)

    def record_usage(self, tokens: int) -> None:
        """Record actual token usage after API call."""
        self._token_usage.append((time.time(), tokens))


# =============================================================================
# GLM Client
# =============================================================================


class GLMClient:
    """
    Async client for ZhipuAI GLM API.

    Provides high-level interface for text and vision analysis with:
    - Structured outputs via Pydantic models
    - Automatic rate limiting
    - Retry with exponential backoff
    - Token usage monitoring

    Example:
        ```python
        client = GLMClient(settings)
        response = await client.analyze_with_vision(
            system_prompt="You are a trading assistant.",
            messages=["Analyze this chart", image_base64],
        )
        decision = response.parsed  # TradingDecision object
        ```
    """

    # Model constants
    MODEL_TEXT = "glm-5"  # Text-only model
    MODEL_VISION = "glm-4.6v"  # Vision-capable model

    def __init__(
        self,
        settings: Settings | None = None,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100000,
        max_retries: int = 3,
    ):
        """
        Initialize GLM client.

        Args:
            settings: Application settings (uses global if not provided)
            requests_per_minute: Rate limit for requests
            tokens_per_minute: Rate limit for tokens
            max_retries: Maximum retry attempts for failed calls
        """
        self._settings = settings or get_settings()
        self._client = ZhipuAI(api_key=self._settings.zhipuai_api_key)
        self._rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            tokens_per_minute=tokens_per_minute,
        )
        self._max_retries = max_retries

        # Initialize cost tracker (optional)
        global _cost_tracker, _cost_tracker_initialized
        if _cost_tracker is not None and not _cost_tracker_initialized:
            try:
                config = CostTrackerConfig(database_path="data/glm_usage.db")
                _cost_tracker = get_cost_tracker(config)
                _cost_tracker_initialized = True
                logger.debug("Cost tracker initialized for GLM client")
            except Exception as e:
                logger.warning(f"Failed to initialize cost tracker: {e}")
                _cost_tracker = None

        logger.info(
            "GLM client initialized",
            text_model=self._settings.glm_text_model,
            vision_model=self._settings.glm_vision_model,
        )

    async def analyze_text(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
    ) -> GLMResponse:
        """
        Analyze text using GLM text model.

        Args:
            system_prompt: System instruction for the AI
            user_message: User message to analyze
            temperature: Sampling temperature (0-1)

        Returns:
            GLMResponse with content and parsed decision

        Raises:
            GLMAPIError: If API call fails after retries
        """
        return await self._call_api(
            model=self._settings.glm_text_model,
            system_prompt=system_prompt,
            messages=[{"type": "text", "text": user_message}],
            temperature=temperature,
        )

    async def analyze_with_vision(
        self,
        system_prompt: str,
        text_messages: list[str],
        image_base64: str,
        temperature: float = 0.7,
    ) -> GLMResponse:
        """
        Analyze text and image using GLM vision model.

        Args:
            system_prompt: System instruction for the AI
            text_messages: List of text messages to analyze
            image_base64: Base64-encoded image data
            temperature: Sampling temperature (0-1)

        Returns:
            GLMResponse with content and parsed decision

        Raises:
            GLMAPIError: If API call fails after retries
        """
        # Build message content with text and image
        content: list[dict[str, Any]] = []
        for text in text_messages:
            content.append({"type": "text", "text": text})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
        })

        return await self._call_api(
            model=self._settings.glm_vision_model,
            system_prompt=system_prompt,
            messages=content,
            temperature=temperature,
        )

    async def _call_api(
        self,
        model: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> GLMResponse:
        """
        Make API call with retry logic.

        Args:
            model: Model identifier
            system_prompt: System instruction
            messages: Message content
            temperature: Sampling temperature

        Returns:
            GLMResponse with result

        Raises:
            GLMAPIError: If all retries fail
        """
        # Estimate tokens (rough: 4 chars per token)
        estimated_tokens = len(system_prompt) // 4 + sum(
            len(str(m)) // 4 for m in messages
        ) + 500  # Buffer for response

        try:
            await self._rate_limiter.acquire(estimated_tokens)
        except RateLimitError as e:
            logger.warning(
                "Rate limit hit, waiting",
                retry_after=e.retry_after,
            )
            if e.retry_after:
                await asyncio.sleep(e.retry_after)
                await self._rate_limiter.acquire(estimated_tokens)

        start_time = time.time()

        try:
            retryer = AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type((ConnectionError, TimeoutError)),
                reraise=True,
            )

            async for attempt in retryer:
                with attempt:
                    # Run sync API in thread pool
                    response = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": messages},
                            ],
                            response_format={"type": "json_object"},
                            temperature=temperature,
                        ),
                    )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response data
            content = response.choices[0].message.content
            usage = response.usage

            # Record actual token usage
            if usage:
                self._rate_limiter.record_usage(usage.total_tokens)

            # Parse JSON response
            parsed = None
            try:
                import json
                data = json.loads(content)
                parsed = TradingDecision(**data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    "Failed to parse trading decision",
                    error=str(e),
                    content=content[:200],
                )

            token_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )

            # Track cost with cost tracker (optional)
            if _cost_tracker is not None and usage:
                try:
                    await _cost_tracker.log_usage(
                        model=model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        metadata={"latency_ms": str(latency_ms)},
                    )
                except Exception as e:
                    logger.warning(f"Failed to log usage to cost tracker: {e}")

            logger.info(
                "GLM API call successful",
                model=model,
                latency_ms=latency_ms,
                total_tokens=token_usage.total_tokens,
                decision=parsed.decision if parsed else None,
            )

            return GLMResponse(
                content=content,
                parsed=parsed,
                model=model,
                usage=token_usage,
                latency_ms=latency_ms,
            )

        except RetryError as e:
            logger.error(
                "GLM API call failed after retries",
                model=model,
                error=str(e),
            )
            raise GLMAPIError(
                f"GLM API call failed after {self._max_retries} retries: {e}",
                model=model,
            ) from e

        except Exception as e:
            logger.error(
                "GLM API call failed",
                model=model,
                error=str(e),
            )
            raise GLMAPIError(
                f"GLM API call failed: {e}",
                model=model,
            ) from e

    async def health_check(self) -> bool:
        """
        Check if GLM API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = await self.analyze_text(
                system_prompt="You are a helpful assistant.",
                user_message="Say 'ok' if you can hear me.",
            )
            return bool(response.content)
        except Exception as e:
            logger.error("GLM health check failed", error=str(e))
            return False

    @staticmethod
    def encode_image_to_base64(image_path: str) -> str:
        """
        Encode an image file to base64 string.

        Args:
            image_path: Path to the image file

        Returns:
            Base64-encoded image string
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
