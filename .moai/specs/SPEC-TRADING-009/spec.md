# SPEC-TRADING-009: API Rate Limiting

## Metadata

- **SPEC ID**: SPEC-TRADING-009
- **Title**: API Rate Limiting (API 속도 제한)
- **Created**: 2026-03-05
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: None (Independent infrastructure)
- **Lifecycle Level**: spec-first

---

## Problem Analysis

### Current State

SPEC-TRADING-001에서 TradingService가 OpenAI API와 Upbit API를 호출합니다. 그러나 API 호출에 대한 속도 제한이 구현되지 않아 다음과 같은 문제가 발생합니다:

1. **API 할당량 초과 위험**: OpenAI, Upbit API의 속도 제한을 초과하여 차단될 수 있음
2. **비용 통제 불가**: OpenAI API 호출 횟수 제한이 없어 예상치 못한 비용 발생
3. **서비스 장애**: 외부 API 장애 시 시스템 전체가 영향을 받음
4. **재시도 로직 부재**: 일시적 장애 시 적절한 재시도 메커니즘 없음

### Root Cause Analysis (Five Whys)

1. **Why?** API 호출에 대한 속도 제한 및 장애 처리가 구현되지 않음
2. **Why?** 초기 구현에서 핵심 기능에 집중하여 안정성 레이어 제외
3. **Why?** API 클라이언트가 직접 호출만 담당, 보호 계층 없음
4. **Why?** 인프라 계층의 책임이 명확히 분리되지 않음
5. **Root Cause**: API 호출 보호 계층이 독립적인 인프라 서비스로 설계 필요

### Desired State

모든 외부 API 호출이 토큰 버킷 알고리즘으로 속도 제한되고, 실패 시 지수 백오프로 재시도하며, 서킷 브레이커로 장애 격리가 구현됩니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Rate Limiter | Token Bucket | Custom | 토큰 버킷 알고리즘 |
| Retry | Exponential Backoff | Custom | 재시도 전략 |
| Circuit Breaker | Circuit Breaker Pattern | Custom | 장애 격리 |
| Async | asyncio | Built-in | 비동기 처리 |

### Integration Points

```
External APIs (OpenAI, Upbit)
        ↑ Rate-limited calls
SPEC-TRADING-009 (RateLimiter, CircuitBreaker)
        ↑ Protected calls
    API Clients (GLMClient, UpbitClient)
        ↑
    Domain Services
```

### Constraints

1. **OpenAI API**: 3 RPM (free tier) / 60 RPM (paid tier)
2. **Upbit API**: 10 requests/second, 600 requests/minute
3. **Memory**: Rate limiter 버킷 메모리 10MB 이하
4. **Latency**: 속도 제한 확인 1ms 이하

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-RATE-001**: 시스템은 모든 외부 API 호출에 대해 속도 제한을 적용해야 한다 (The system shall apply rate limiting to all external API calls).

```
The system shall rate limit:
- OpenAI API calls: configurable (default 60/hour)
- Upbit API calls: 10/second, 600/minute
- Custom limits per API endpoint
```

**REQ-RATE-002**: 시스템은 속도 제한 통계를 기록해야 한다 (The system shall log rate limiting statistics).

```
The system shall track:
- Total requests per API
- Rate-limited (rejected) requests
- Current bucket level
- Last request timestamp
```

### Event-Driven Requirements

**REQ-RATE-003**: WHEN 속도 제한에 도달하면 THEN 시스템은 요청을 대기열에 추가하거나 거부해야 한다.

```
WHEN rate limit reached (bucket empty)
THEN the system shall:
    AND return RateLimitError with retry_after hint
    OR wait until token available (configurable)
    AND log rate limit event
```

**REQ-RATE-004**: WHEN API 호출이 실패하면 THEN 시스템은 지수 백오프로 재시도해야 한다.

```
WHEN API call fails with retryable error (5xx, network timeout)
THEN the system shall:
    AND retry with exponential backoff
    AND max retries = 3 (configurable)
    AND backoff: 1s, 2s, 4s
    AND raise error after max retries
```

### State-Driven Requirements

**REQ-RATE-005**: IF 서킷 브레이커가 OPEN 상태이면 THEN 시스템은 즉시 요청을 거부해야 한다.

```
IF circuit_breaker.state == OPEN
THEN the system shall:
    AND reject all requests immediately
    AND return CircuitOpenError
    AND not attempt actual API call
    AND wait for recovery timeout
```

**REQ-RATE-006**: IF 연속 실패 횟수가 임계값을 초과하면 THEN 서킷 브레이커를 OPEN해야 한다.

```
IF consecutive_failures >= failure_threshold (default 5)
THEN circuit_breaker.state = OPEN
    AND start recovery_timer (default 60 seconds)
    AND log circuit open event with ERROR level
```

### Optional Requirements

**REQ-RATE-007**: Where possible, 시스템은 속도 제한 상태를 UI에 표시해야 한다.

```
Where possible, the system shall display:
- Current API quota remaining
- Time until quota reset
- Warning when approaching limit (80%)
```

**REQ-RATE-008**: Where possible, 시스템은 API 호출 비용을 추적해야 한다.

```
Where possible, the system shall track:
- OpenAI token usage
- Estimated cost per call
- Daily/monthly cost accumulation
```

### Unwanted Behavior Requirements

**REQ-RATE-009**: 시스템은 속도 제한을 무시해서는 안 된다 (The system shall not bypass rate limiting).

```
The system shall NOT:
- Make API calls without rate limit check
- Allow configuration to disable rate limiting in production
- Reset bucket artificially to allow more requests

Exception: Testing environment with mock APIs
```

**REQ-RATE-010**: 시스템은 무한 재시도를 해서는 안 된다 (The system shall not retry infinitely).

```
The system shall NOT:
- Retry without maximum attempt limit
- Retry non-retryable errors (4xx)
- Retry with zero backoff (spam protection)

AND shall respect Retry-After header if provided by API
```

---

## Specifications

### Data Model

#### RateLimiterConfig

```python
@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""
    api_name: str  # e.g., "openai", "upbit"
    requests_per_second: float | None = None
    requests_per_minute: int | None = None
    requests_per_hour: int | None = None
    bucket_capacity: int = 10  # Token bucket size
    refill_rate: float = 1.0  # Tokens per second

@dataclass
class RateLimitStats:
    """Statistics for rate limiter."""
    api_name: str
    total_requests: int
    rejected_requests: int
    current_tokens: float
    last_request_at: datetime | None
    last_rejection_at: datetime | None
```

#### CircuitBreakerState

```python
class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject all
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    api_name: str
    failure_threshold: int = 5  # Failures before open
    recovery_timeout: int = 60  # Seconds before half-open
    half_open_max_calls: int = 3  # Test calls in half-open

@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    api_name: str
    state: CircuitState
    consecutive_failures: int
    total_failures: int
    last_failure_at: datetime | None
    last_state_change_at: datetime | None
```

#### RetryConfig

```python
@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # Seconds
    max_delay: float = 60.0  # Seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add random jitter

@dataclass
class RetryStats:
    """Statistics for retry behavior."""
    api_name: str
    total_retries: int
    successful_retries: int
    failed_after_retries: int
```

### Component Architecture

```
src/gpt_bitcoin/
├── infrastructure/
│   ├── rate_limiting/
│   │   ├── __init__.py (NEW)
│   │   ├── token_bucket.py (NEW)
│   │   ├── rate_limiter.py (NEW)
│   │   ├── circuit_breaker.py (NEW)
│   │   └── retry_handler.py (NEW)
│   └── external/
│       ├── glm_client.py (MODIFY - add rate limiting)
│       └── mock_upbit_client.py (MODIFY - add rate limiting)
└── config/
    └── settings.py (MODIFY - add rate limit configs)
```

### Class Design

#### TokenBucket

```python
class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Thread-safe, async-compatible token bucket.

    @MX:NOTE: Standard token bucket algorithm.
        Refills tokens at constant rate.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,
    ):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = datetime.now()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens consumed, False if insufficient
        """
        pass

    async def wait_for_token(self, timeout: float | None = None) -> bool:
        """
        Wait until token is available.

        Returns:
            True if token acquired, False if timeout
        """
        pass

    def get_current_tokens(self) -> float:
        """Get current token count (approximate)."""
        pass
```

#### RateLimiter

```python
class RateLimiter:
    """
    Rate limiter using token bucket algorithm.

    @MX:ANCHOR: Primary rate limiting entry point.
        fan_in: 2+ (OpenAI client, Upbit client)
        @MX:REASON: Centralizes all rate limit checks.
    """

    def __init__(self, config: RateLimiterConfig):
        self._config = config
        self._bucket = TokenBucket(
            capacity=config.bucket_capacity,
            refill_rate=config.refill_rate,
        )
        self._stats = RateLimitStats(
            api_name=config.api_name,
            total_requests=0,
            rejected_requests=0,
            current_tokens=config.bucket_capacity,
            last_request_at=None,
            last_rejection_at=None,
        )

    async def acquire(self, wait: bool = False) -> bool:
        """
        Acquire rate limit permission.

        Args:
            wait: If True, wait for token; if False, fail immediately

        Returns:
            True if allowed, False if rate limited

        Raises:
            RateLimitError: If rate limited and wait=False
        """
        pass

    def get_stats(self) -> RateLimitStats:
        """Get current statistics."""
        pass
```

#### CircuitBreaker

```python
class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    @MX:NOTE: Implements circuit breaker pattern.
        Protects against cascading failures.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self._config = config
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_at: datetime | None = None
        self._state_changed_at = datetime.now()

    async def call[T](
        self,
        func: Callable[[], Awaitable[T]],
    ) -> T:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitOpenError: If circuit is open
            OriginalError: If function fails
        """
        pass

    def _on_success(self) -> None:
        """Handle successful call."""
        pass

    def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        pass

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        pass
```

#### RetryHandler

```python
class RetryHandler:
    """
    Retry handler with exponential backoff.

    @MX:WARN: Retry logic complexity.
        @MX:REASON: Multiple failure modes, state tracking.
    """

    def __init__(self, config: RetryConfig):
        self._config = config

    async def execute[T](
        self,
        func: Callable[[], Awaitable[T]],
        is_retryable: Callable[[Exception], bool] | None = None,
    ) -> T:
        """
        Execute with retry logic.

        Args:
            func: Async function to execute
            is_retryable: Function to determine if error is retryable

        Returns:
            Result of func

        Raises:
            LastError: After all retries exhausted
        """
        pass

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with jitter."""
        delay = self._config.base_delay * (
            self._config.exponential_base ** attempt
        )
        if self._config.jitter:
            delay *= random.uniform(0.5, 1.5)
        return min(delay, self._config.max_delay)
```

#### ProtectedAPIClient (Decorator Pattern)

```python
class ProtectedAPIClient:
    """
    API client with rate limiting, circuit breaker, and retry.

    Combines all protection mechanisms.

    @MX:ANCHOR: Protected API client wrapper.
        fan_in: 2+ (GLMClient, UpbitClient)
        @MX:REASON: Single entry point for protected calls.
    """

    def __init__(
        self,
        client: Any,  # Original API client
        rate_limiter: RateLimiter,
        circuit_breaker: CircuitBreaker,
        retry_handler: RetryHandler,
    ):
        self._client = client
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker
        self._retry_handler = retry_handler

    async def call[T](
        self,
        func_name: str,
        *args,
        **kwargs,
    ) -> T:
        """
        Execute protected API call.

        Flow:
        1. Check circuit breaker
        2. Acquire rate limit
        3. Execute with retry
        4. Update circuit breaker state
        """
        # Check circuit breaker
        if self._circuit_breaker.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit open for {self._rate_limiter._config.api_name}"
            )

        # Acquire rate limit
        await self._rate_limiter.acquire(wait=True)

        # Execute with retry
        async def _execute():
            return await getattr(self._client, func_name)(*args, **kwargs)

        try:
            result = await self._circuit_breaker.call(
                lambda: self._retry_handler.execute(_execute)
            )
            return result
        except Exception as e:
            logger.error(f"Protected API call failed: {e}")
            raise
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `RateLimiter.acquire()` | 2+ | @MX:ANCHOR | infrastructure/rate_limiting/rate_limiter.py |
| `ProtectedAPIClient.call()` | 2+ | @MX:ANCHOR | infrastructure/rate_limiting/protected_client.py |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `RetryHandler.execute()` | Retry complexity | @MX:WARN | Multiple failure modes, state tracking |
| `CircuitBreaker._on_failure()` | State transitions | @MX:WARN | Concurrent state modification risk |
| `TokenBucket.consume()` | Thread safety | @MX:NOTE | Async lock usage |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/infrastructure/rate_limiting/__init__.py` | Package init | ~10 |
| `src/gpt_bitcoin/infrastructure/rate_limiting/token_bucket.py` | Token bucket | ~80 |
| `src/gpt_bitcoin/infrastructure/rate_limiting/rate_limiter.py` | Rate limiter | ~120 |
| `src/gpt_bitcoin/infrastructure/rate_limiting/circuit_breaker.py` | Circuit breaker | ~150 |
| `src/gpt_bitcoin/infrastructure/rate_limiting/retry_handler.py` | Retry handler | ~100 |
| `tests/unit/infrastructure/test_rate_limiting.py` | Unit tests | ~400 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/infrastructure/external/glm_client.py` | Add ProtectedAPIClient wrapper | +30 |
| `src/gpt_bitcoin/infrastructure/external/mock_upbit_client.py` | Add rate limiting | +30 |
| `src/gpt_bitcoin/config/settings.py` | Add rate limit configs | +20 |
| `src/gpt_bitcoin/dependencies/container.py` | Register rate limiters | +20 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Rate limiter too strict | Medium | Medium | Configurable limits, monitoring |
| Circuit breaker stuck open | Low | High | Manual reset capability, auto-recovery |
| Retry storm during recovery | Medium | Medium | Jitter, max delay cap |
| Memory leak in token buckets | Low | Low | Cleanup old buckets, TTL |

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-RATE-001 | RateLimiter | test_rate_limit_enforcement() |
| REQ-RATE-002 | RateLimitStats | test_stats_tracking() |
| REQ-RATE-003 | RateLimiter.acquire() | test_rate_limit_rejection() |
| REQ-RATE-004 | RetryHandler | test_exponential_backoff_retry() |
| REQ-RATE-005 | CircuitBreaker | test_open_circuit_rejection() |
| REQ-RATE-006 | CircuitBreaker | test_consecutive_failure_threshold() |
| REQ-RATE-007 | Web UI | test_quota_display() |
| REQ-RATE-008 | Cost tracking | test_cost_tracking() |
| REQ-RATE-009 | Rate limiter bypass prevention | test_no_bypass() |
| REQ-RATE-010 | Retry limit | test_max_retry_limit() |

---

## Success Criteria

1. **Functional**: All 10 requirements implemented and passing tests
2. **Coverage**: Minimum 85% test coverage
3. **Performance**: Rate limit check < 1ms
4. **Integration**: API clients properly protected
5. **Reliability**: Circuit breaker prevents cascading failures

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService (API client usage)
- **SPEC-TRADING-007**: Notification System (similar rate limiting patterns)

---

Version: 1.0.0
Last Updated: 2026-03-05
Author: MoAI SPEC Builder
