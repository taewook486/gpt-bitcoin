"""
Token Bucket algorithm for rate limiting.

This module provides:
- TokenBucket: Token bucket rate limiter implementation

@MX:NOTE: Token bucket algorithm - tokens refill at constant rate
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

# =============================================================================
# TokenBucket
# =============================================================================


@dataclass
class TokenBucket:
    """
    Token bucket rate limiter.

    Tokens are added at a constant rate (refill_rate) up to capacity.
    Each request consumes tokens. If insufficient tokens, request is denied.

    Attributes:
        capacity: Maximum number of tokens
        refill_rate: Tokens added per second
        tokens: Current token count
        last_refill_timestamp: Last time tokens were refilled

    @MX:ANCHOR: TokenBucket.consume
        fan_in: 3+ (RateLimiter, UpbitClient, direct API calls)
        @MX:REASON: Central rate limiting algorithm for all API calls.
    """

    capacity: float
    refill_rate: float
    tokens: float = field(init=False)
    last_refill_timestamp: float = field(default_factory=time.time)
    consumed_total: int = field(default=0)

    def __post_init__(self) -> None:
        """Initialize token bucket to full capacity."""
        self.tokens = float(self.capacity)

    def _refill(self) -> None:
        """
        Refill tokens based on elapsed time.

        @MX:NOTE: Internal method - called before each consume operation.
        """
        now = time.time()
        elapsed = now - self.last_refill_timestamp

        # Calculate tokens to add
        tokens_to_add = elapsed * self.refill_rate

        # Add tokens up to capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)

        # Update timestamp
        self.last_refill_timestamp = now

    def consume(self, tokens: int) -> bool:
        """
        Consume tokens if available.

        REQ-RATE-003: Reject if insufficient tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            bool: True if consumed, False if insufficient tokens

        Raises:
            ValueError: If tokens is negative
        """
        if tokens < 0:
            raise ValueError("tokens must be non-negative")

        # Refill first
        self._refill()

        # Check if enough tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            self.consumed_total += tokens
            return True

        return False

    def wait_for_token(self, tokens: int = 1, timeout: float = 1.0) -> bool:
        """
        Wait for tokens to become available.

        REQ-RATE-003: Wait (with timeout) for token refill.

        Args:
            tokens: Number of tokens needed
            timeout: Maximum time to wait in seconds

        Returns:
            bool: True if tokens acquired, False if timeout
        """
        start = time.time()

        while (time.time() - start) < timeout:
            # Refill and check
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                self.consumed_total += tokens
                return True

            # Sleep a bit before retrying
            time.sleep(0.01)

        return False

    def get_statistics(self) -> dict[str, float | int]:
        """
        Get bucket statistics.

        REQ-RATE-002: Track rate limiting statistics.

        Returns:
            Dictionary with bucket statistics
        """
        self._refill()

        return {
            "capacity": self.capacity,
            "available_tokens": round(self.tokens, 2),
            "refill_rate": self.refill_rate,
            "consumed_total": self.consumed_total,
        }


__all__ = ["TokenBucket"]
