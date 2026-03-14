# Implementation Plan: SPEC-TRADING-009 (API Rate Limiting)

## Overview

이 문서는 SPEC-TRADING-009 API 속도 제한 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Token Bucket Rate Limiter (Primary Goal)

**Objective**: 토큰 버킷 알고리즘 구현 및 기본 속도 제한

#### Tasks

1. **TokenBucket Implementation**
   - Priority: Critical
   - Implement token bucket data structure
   - Implement async token consumption
   - Implement token refill logic
   - Add thread safety with asyncio.Lock

2. **RateLimiter Implementation**
   - Priority: Critical
   - Implement RateLimiterConfig
   - Implement RateLimitStats
   - Implement acquire() method
   - Implement wait mode

3. **Unit Tests - Rate Limiter**
   - Priority: High
   - Test token consumption
   - Test refill logic
   - Test concurrent access
   - Test statistics tracking

**Deliverables**:
- Working token bucket implementation
- Rate limiter with statistics
- All tests passing

---

### Phase 2: Retry Handler (Secondary Goal)

**Objective**: 지수 백오프 재시도 로직 구현

#### Tasks

1. **RetryConfig and Stats**
   - Priority: High
   - Define RetryConfig dataclass
   - Define RetryStats dataclass
   - Add configuration options

2. **RetryHandler Implementation**
   - Priority: High
   - Implement exponential backoff calculation
   - Implement jitter for retry storm prevention
   - Implement retryable error detection
   - Implement max retry limit

3. **Unit Tests - Retry**
   - Priority: High
   - Test exponential backoff timing
   - Test jitter randomness
   - Test retryable vs non-retryable errors
   - Test max retry enforcement

**Deliverables**:
- Working retry handler
- Configurable retry behavior
- All tests passing

---

### Phase 3: Circuit Breaker (Final Goal)

**Objective**: 서킷 브레이커 패턴 구현

#### Tasks

1. **CircuitBreaker Implementation**
   - Priority: High
   - Implement CircuitState enum
   - Implement state transitions
   - Implement failure counting
   - Implement recovery timeout

2. **ProtectedAPIClient Wrapper**
   - Priority: Medium
   - Combine rate limiter, retry, circuit breaker
   - Implement unified call interface
   - Add logging and metrics

3. **API Client Integration**
   - Priority: Medium
   - Wrap GLMClient with protection
   - Wrap UpbitClient with protection
   - Update dependency injection

4. **Integration Tests**
   - Priority: Medium
   - Test full protection stack
   - Test failure scenarios
   - Test recovery scenarios

**Deliverables**:
- Working circuit breaker
- Protected API clients
- Integration tests passing

---

## Technical Approach

### Token Bucket Algorithm

```python
# infrastructure/rate_limiting/token_bucket.py

import asyncio
from datetime import datetime

class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
    ):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens
            refill_rate: Tokens per second
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = datetime.now()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now()
        elapsed = (now - self._last_refill).total_seconds()
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        @MX:NOTE: Thread-safe via async lock.
        """
        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    async def wait_for_token(
        self,
        tokens: int = 1,
        timeout: float | None = None,
    ) -> bool:
        """Wait until tokens available."""
        start = datetime.now()
        while True:
            if await self.consume(tokens):
                return True

            if timeout:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed >= timeout:
                    return False

            # Calculate wait time
            async with self._lock:
                self._refill()
                needed = tokens - self._tokens
                wait_time = needed / self._refill_rate

            await asyncio.sleep(min(wait_time, 0.1))
```

### Exponential Backoff Retry

```python
# infrastructure/rate_limiting/retry_handler.py

import asyncio
import random
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

class RetryHandler:
    """Retry with exponential backoff."""

    def __init__(self, config: RetryConfig):
        self._config = config

    async def execute[T](
        self,
        func: Callable[[], Awaitable[T]],
        is_retryable: Callable[[Exception], bool] | None = None,
    ) -> T:
        """
        Execute with retry.

        @MX:WARN: Retry logic complexity.
        """
        last_error: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_error = e

                # Check if retryable
                if is_retryable and not is_retryable(e):
                    raise

                # Non-retryable status codes
                if self._is_non_retryable(e):
                    raise

                # Last attempt, don't wait
                if attempt == self._config.max_retries:
                    raise

                # Calculate delay with jitter
                delay = self._calculate_delay(attempt)
                await asyncio.sleep(delay)

        raise last_error

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with jitter."""
        delay = self._config.base_delay * (
            self._config.exponential_base ** attempt
        )
        if self._config.jitter:
            delay *= random.uniform(0.5, 1.5)
        return min(delay, self._config.max_delay)

    def _is_non_retryable(self, error: Exception) -> bool:
        """Check if error should not be retried."""
        # 4xx client errors (except 429)
        if hasattr(error, 'status_code'):
            code = error.status_code
            return 400 <= code < 500 and code != 429
        return False
```

### Circuit Breaker

```python
# infrastructure/rate_limiting/circuit_breaker.py

import asyncio
from datetime import datetime, timedelta
from typing import TypeVar, Callable, Awaitable

T = TypeVar('T')

class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, config: CircuitBreakerConfig):
        self._config = config
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_at: datetime | None = None
        self._state_changed_at = datetime.now()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state."""
        self._check_recovery()
        return self._state

    async def call[T](
        self,
        func: Callable[[], Awaitable[T]],
    ) -> T:
        """
        Execute through circuit breaker.

        @MX:NOTE: State machine pattern.
        """
        self._check_recovery()

        if self._state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit open for {self._config.api_name}"
            )

        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        self._consecutive_failures = 0
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)

    def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        self._consecutive_failures += 1
        self._last_failure_at = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._consecutive_failures >= self._config.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _check_recovery(self) -> None:
        """Check if recovery timeout passed."""
        if self._state == CircuitState.OPEN:
            elapsed = (datetime.now() - self._state_changed_at).total_seconds()
            if elapsed >= self._config.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        logger.info(
            f"Circuit breaker {self._config.api_name}: "
            f"{self._state.value} -> {new_state.value}"
        )
        self._state = new_state
        self._state_changed_at = datetime.now()
        self._half_open_calls = 0
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── infrastructure/
│   ├── rate_limiting/
│   │   ├── __init__.py
│   │   ├── token_bucket.py
│   │   ├── rate_limiter.py
│   │   ├── circuit_breaker.py
│   │   ├── retry_handler.py
│   │   └── protected_client.py
│   └── external/
│       ├── glm_client.py (MODIFY)
│       └── mock_upbit_client.py (MODIFY)
├── config/
│   └── settings.py (MODIFY)
└── dependencies/
    └── container.py (MODIFY)
```

### Data Flow

```
+------------------+
| Domain Service   |
+--------+---------+
         | API call
         v
+------------------+
| ProtectedAPI     |
| Client           |
+--------+---------+
         |
         +-----> Check Circuit Breaker
         |       (OPEN? -> reject)
         |
         +-----> Acquire Rate Limit
         |       (limit exceeded? -> wait/reject)
         |
         +-----> Execute with Retry
         |       (fail? -> backoff retry)
         v
+------------------+
| Original API     |
| Client           |
+------------------+
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Rate Limiting - OpenAI
    openai_rate_limit_rpm: int = Field(
        default=60,
        description="OpenAI requests per minute",
    )
    openai_rate_limit_rph: int = Field(
        default=3600,
        description="OpenAI requests per hour",
    )

    # Rate Limiting - Upbit
    upbit_rate_limit_rps: int = Field(
        default=10,
        description="Upbit requests per second",
    )
    upbit_rate_limit_rpm: int = Field(
        default=600,
        description="Upbit requests per minute",
    )

    # Circuit Breaker
    circuit_failure_threshold: int = Field(
        default=5,
        description="Failures before circuit opens",
    )
    circuit_recovery_timeout: int = Field(
        default=60,
        description="Seconds before circuit half-open",
    )

    # Retry
    retry_max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts",
    )
    retry_base_delay: float = Field(
        default=1.0,
        description="Base retry delay in seconds",
    )
```

### Container Registration

```python
# dependencies/container.py additions

from gpt_bitcoin.infrastructure.rate_limiting import (
    RateLimiter,
    CircuitBreaker,
    RetryHandler,
    ProtectedAPIClient,
)

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    # Rate Limiters
    openai_rate_limiter: providers.Provider[RateLimiter] = providers.Singleton(
        RateLimiter,
        config=RateLimiterConfig(
            api_name="openai",
            requests_per_minute=settings.provided.openai_rate_limit_rpm,
        ),
    )

    upbit_rate_limiter: providers.Provider[RateLimiter] = providers.Singleton(
        RateLimiter,
        config=RateLimiterConfig(
            api_name="upbit",
            requests_per_second=settings.provided.upbit_rate_limit_rps,
        ),
    )

    # Circuit Breakers
    openai_circuit_breaker: providers.Provider[CircuitBreaker] = providers.Singleton(
        CircuitBreaker,
        config=CircuitBreakerConfig(
            api_name="openai",
            failure_threshold=settings.provided.circuit_failure_threshold,
        ),
    )

    # Retry Handlers
    retry_handler: providers.Provider[RetryHandler] = providers.Factory(
        RetryHandler,
        config=RetryConfig(
            max_retries=settings.provided.retry_max_attempts,
        ),
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| TokenBucket | 100% | Critical |
| RateLimiter | 95% | Critical |
| CircuitBreaker | 95% | Critical |
| RetryHandler | 95% | High |
| ProtectedAPIClient | 90% | High |

### Key Test Cases

```python
# tests/unit/infrastructure/test_rate_limiting.py

class TestTokenBucket:
    """Test TokenBucket."""

    @pytest.mark.asyncio
    async def test_consume_tokens(self):
        """Test basic token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert await bucket.consume(5) is True
        assert bucket.get_current_tokens() == 5

    @pytest.mark.asyncio
    async def test_consume_more_than_available(self):
        """Test consumption when insufficient tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert await bucket.consume(15) is False

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """Test token refill."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        await bucket.consume(10)

        # Wait for refill
        await asyncio.sleep(1.0)

        assert bucket.get_current_tokens() > 0

class TestCircuitBreaker:
    """Test CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_open_after_failures(self):
        """Test circuit opens after threshold."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            api_name="test",
            failure_threshold=3,
        ))

        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(lambda: exec('raise Exception("fail")'))

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reject_when_open(self):
        """Test rejection when circuit open."""
        cb = CircuitBreaker(CircuitBreakerConfig(
            api_name="test",
            failure_threshold=1,
        ))

        # Trigger open
        with pytest.raises(Exception):
            await cb.call(lambda: exec('raise Exception("fail")'))

        # Should reject
        with pytest.raises(CircuitOpenError):
            await cb.call(lambda: "success")

class TestRetryHandler:
    """Test RetryHandler."""

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test backoff timing."""
        handler = RetryHandler(RetryConfig(
            max_retries=3,
            base_delay=1.0,
            jitter=False,
        ))

        times = []
        async def failing_func():
            times.append(datetime.now())
            raise Exception("fail")

        with pytest.raises(Exception):
            await handler.execute(failing_func)

        # Check delays
        assert len(times) == 4  # Initial + 3 retries
```

---

## Performance Considerations

### Rate Limit Check Overhead

- Token check: < 1ms (in-memory)
- Lock acquisition: < 0.1ms (async)

### Memory Usage

- Token bucket: ~100 bytes per API
- Circuit breaker: ~200 bytes per API
- Total overhead: < 1KB per protected API

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
