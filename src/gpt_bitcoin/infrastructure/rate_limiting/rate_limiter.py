"""
Rate Limiter with multiple token buckets.

This module provides:
- RateLimiter: Manages multiple token buckets by key

@MX:NOTE: Rate limiter - manages per-key rate limiting
"""

from __future__ import annotations

from typing import Any

from gpt_bitcoin.infrastructure.rate_limiting.token_bucket import TokenBucket

# =============================================================================
# RateLimiter
# =============================================================================


class RateLimiter:
    """
    Rate limiter managing multiple token buckets.

    REQ-RATE-001: Apply rate limiting to all external API calls.

    Each key (e.g., API key, user ID) gets its own token bucket.
    Buckets are created on-demand and reused for subsequent requests.

    Attributes:
        default_capacity: Default token bucket capacity
        default_refill_rate: Default token refill rate (tokens/second)
        buckets: Dictionary of key -> TokenBucket

    @MX:ANCHOR: RateLimiter.check_rate_limit
        fan_in: 2+ (UpbitClient, ZhipuAIClient)
        @MX:REASON: Centralizes rate limit checking for all API clients.
    """

    def __init__(
        self,
        default_capacity: float = 100.0,
        default_refill_rate: float = 10.0,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            default_capacity: Default bucket capacity (tokens)
            default_refill_rate: Default refill rate (tokens/second)
        """
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: dict[str, TokenBucket] = {}

    def get_bucket(self, key: str) -> TokenBucket:
        """
        Get or create token bucket for key.

        Args:
            key: Identifier for the bucket (e.g., API key, user ID)

        Returns:
            TokenBucket: The bucket for this key
        """
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=self.default_capacity,
                refill_rate=self.default_refill_rate,
            )

        return self._buckets[key]

    def check_rate_limit(
        self,
        key: str,
        tokens: int = 1,
    ) -> dict[str, Any]:
        """
        Check and consume tokens for rate limiting.

        REQ-RATE-001: Apply rate limiting to API calls.
        REQ-RATE-003: Reject when rate limit reached.

        Args:
            key: Identifier for the bucket
            tokens: Number of tokens to consume

        Returns:
            Dictionary with:
                - allowed (bool): Whether request is allowed
                - tokens_remaining (float): Remaining tokens
                - retry_after (float | None): Seconds to wait if not allowed
        """
        bucket = self.get_bucket(key)

        # Try to consume tokens
        if bucket.consume(tokens):
            return {
                "allowed": True,
                "tokens_remaining": bucket.tokens,
                "retry_after": None,
            }

        # Calculate retry time
        tokens_needed = tokens - bucket.tokens
        retry_after = tokens_needed / bucket.refill_rate

        return {
            "allowed": False,
            "tokens_remaining": bucket.tokens,
            "retry_after": retry_after,
        }

    def get_statistics(self) -> dict[str, dict[str, float | int]]:
        """
        Get statistics for all buckets.

        REQ-RATE-002: Track rate limiting statistics.

        Returns:
            Dictionary mapping key to bucket statistics
        """
        return {key: bucket.get_statistics() for key, bucket in self._buckets.items()}


__all__ = ["RateLimiter"]
