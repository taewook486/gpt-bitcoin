---
spec_id: SPEC-REFACTOR-PYTHON-001
title: Legacy Python Code Modernization
created: 2026-03-02
status: Planned
priority: High
lifecycle_level: spec-anchored
tags: [refactoring, python, modernization, type-hints, testing, async]
---

# SPEC-REFACTOR-PYTHON-001: Legacy Python Code Modernization

## Problem Analysis

### Current State

gpt-bitcoin 자동거래 시스템은 2년 전에 개발되어 방치된 상태입니다. 코드베이스는 다음과 같은 문제점들을 가지고 있습니다:

**기술 부채 현황:**
- Python 3.8 수준의 코드 (3.12+ 미활용)
- 타입 힌트 0% 적용
- 테스트 커버리지 0%
- 의존성 버전 고정 없음
- 글로벌 변수 남용
- 동기식 I/O 처리
- 로깅 시스템 부재
- 문서화 부재

**식별된 파일:**
- `autotrade.py` (v1): 158 lines - 기본 기능
- `autotrade_v2.py` (v2): 325 lines - 뉴스 데이터 추가
- `autotrade_v3.py` (v3): 388 lines - 비전 분석 추가
- `streamlit_app.py`: 48 lines - 모니터링 대시보드
- `requirements.txt`: 9개 의존성, 버전 고정 없음

### Root Cause Analysis (Five Whys)

1. **표면 문제**: 코드가 구식이고 유지보수가 어려움
2. **첫 번째 이유**: 2년간 업데이트 없음
3. **두 번째 이유**: 초기 개발 시 모범 사례 미적용
4. **세 번째 이유**: 빠른 프로토타이핑에 집중하여 품질 부채 축적
5. **근본 원인**: 테스트, 타이핑, 문서화를 포함한 지속 가능한 개발 프로세스 부재

### Assumptions Audit

| Assumption | Confidence | Risk if Wrong | Validation Method |
|------------|------------|---------------|-------------------|
| Python 3.12 호환 환경 | High | 의존성 호환性问题 | 의존성 호환성 테스트 |
| 기존 API 동작 보존 필요 | High | 프로덕션 중단 | 사용자 확인 |
| 점진적 마이그레이션 가능 | Medium | 긴 다운타임 | 단계적 배포 계획 |
| OpenAI API 호환성 유지 | High | 기능 손실 | API 호출 테스트 |
| Upbit API 안정성 | Medium | 거래 실패 | API 상태 확인 |

---

## EARS Requirements

### Environment (ENV)

**ENV-001: Python 버전**
시스템은 Python 3.12+ 환경에서 실행되어야 한다.

**ENV-002: 의존성 관리**
프로젝트는 `pyproject.toml`을 사용하여 의존성을 관리해야 한다.

**ENV-003: 가상 환경**
개발 및 프로덕션 환경은 격리된 가상 환경을 사용해야 한다.

---

### Ubiquitous Requirements (UBQ)

**UBQ-001: 타입 힌트**
The system **shall** provide type hints for all function signatures.

```
# 모든 함수는 타입 힌트를 포함해야 함
def get_current_status() -> dict[str, Any]:
    ...

def execute_buy(amount: Decimal) -> OrderResult:
    ...
```

**UBQ-002: 로깅**
The system **shall** use structured logging with loguru or structlog.

```
# print() 대신 구조화된 로깅 사용
logger.info("order_executed", ticker="KRW-BTC", amount=5000, order_id="xxx")
```

**UBQ-003: 에러 처리**
The system **shall** handle exceptions with proper error types and messages.

```
# 구체적인 예외 타입 사용
class TradingError(Exception):
    """거래 관련 기본 예외"""
    pass

class InsufficientBalanceError(TradingError):
    """잔고 부족 예외"""
    pass
```

**UBQ-004: 설정 관리**
The system **shall** load configuration from environment variables with Pydantic settings.

```
# Pydantic Settings를 사용한 설정 관리
class Settings(BaseSettings):
    openai_api_key: SecretStr
    upbit_access_key: SecretStr
    upbit_secret_key: SecretStr

    model_config = SettingsConfigDict(env_file=".env")
```

---

### Event-Driven Requirements (EVD)

**EVD-001: 비동기 API 호출**
**WHEN** 외부 API 호출이 필요할 때, **THEN** 시스템은 async/await를 사용해야 한다.

```
# 동기식 (현재)
response = client.chat.completions.create(...)

# 비동기식 (목표)
response = await async_client.chat.completions.create(...)
```

**EVD-002: 주기적 작업 실행**
**WHEN** 스케줄된 시간에 도달하면, **THEN** 시스템은 거래 결정을 수행해야 한다.

```
# schedule 대신 asyncio 기반 스케줄러 사용
async def scheduled_task():
    while True:
        await make_decision_and_execute()
        await asyncio.sleep(3600)  # 1시간
```

**EVD-003: 거래 실행**
**WHEN** AI가 buy/sell 결정을 내리면, **THEN** 시스템은 검증 후 거래를 실행해야 한다.

```
# 결정 검증 포함
async def execute_decision(decision: TradingDecision) -> ExecutionResult:
    validated = await validate_decision(decision)
    if validated.is_valid:
        return await execute_order(validated.order)
    return ExecutionResult(success=False, reason=validated.reason)
```

---

### State-Driven Requirements (STD)

**STD-001: 잔고 확인**
**IF** KRW 잔고가 5,000원 이상이면, **THEN** 시스템은 매수 주문을 실행할 수 있다.

```
# 명시적인 상태 검증
async def can_buy(krw_balance: Decimal) -> bool:
    MIN_ORDER_AMOUNT = Decimal("5000")
    return krw_balance >= MIN_ORDER_AMOUNT
```

**STD-002: 매도 조건**
**IF** BTC 보유 수량 × 현재 가격이 5,000원 이상이면, **THEN** 시스템은 매도 주문을 실행할 수 있다.

```
async def can_sell(btc_balance: Decimal, current_price: Decimal) -> bool:
    MIN_ORDER_AMOUNT = Decimal("5000")
    return (btc_balance * current_price) >= MIN_ORDER_AMOUNT
```

**STD-003: API 연결 상태**
**IF** API 연결이 끊어지면, **THEN** 시스템은 재시도 후 알림을 보내야 한다.

```
async def with_retry(func: Callable, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await func()
        except APIError as e:
            if attempt == max_retries - 1:
                await send_alert(f"API 연결 실패: {e}")
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

---

### Optional Requirements (OPT)

**OPT-001: 모니터링 대시보드**
**WHERE POSSIBLE**, 시스템은 실시간 모니터링 대시보드를 제공해야 한다.

```
# Streamlit 대신 FastAPI + WebSocket 또는 Prometheus + Grafana 고려
```

**OPT-002: 뉴스 분석 통합**
**WHERE POSSIBLE**, v2의 뉴스 분석 기능을 유지해야 한다.

```
# 선택적 기능으로 모듈화
class NewsAnalyzer:
    async def analyze(self, ticker: str) -> NewsSentiment | None:
        if not self.enabled:
            return None
        ...
```

**OPT-003: 비전 분석 통합**
**WHERE POSSIBLE**, v3의 차트 이미지 분석 기능을 유지해야 한다.

```
# 선택적 기능으로 모듈화
class ChartVisionAnalyzer:
    async def analyze_chart_image(self, image_path: Path) -> ChartAnalysis | None:
        if not self.enabled:
            return None
        ...
```

---

### Unwanted Behavior (UNW)

**UNW-001: 하드코딩된 비밀**
The system **shall NOT** store API keys or secrets in source code.

```
# 잘못된 예 (현재)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 올바른 예 (목표)
settings = Settings()  # Pydantic Settings
client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
```

**UNW-002: 뮤터블 기본 인자**
The system **shall NOT** use mutable default arguments.

```
# 잘못된 예
def process_data(data: list = []):  # X

# 올바른 예
def process_data(data: list | None = None):
    data = data or []
```

**UNW-003: 베어 익셉션**
The system **shall NOT** use bare except clauses.

```
# 잘못된 예 (현재)
try:
    ...
except Exception as e:
    print(f"Error: {e}")

# 올바른 예
try:
    ...
except UpbitAPIError as e:
    logger.error("upbit_api_error", error=str(e), ticker=ticker)
    raise TradingError(f"거래 실패: {e}") from e
```

**UNW-004: 글로벌 상태**
The system **shall NOT** use global variables for mutable state.

```
# 잘못된 예 (현재)
client = OpenAI(api_key=...)
upbit = pyupbit.Upbit(...)

# 올바른 예
class TradingBot:
    def __init__(self, settings: Settings):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.upbit = UpbitExchange(settings.upbit_access_key, settings.upbit_secret_key)
```

---

## Constraints

### Technical Constraints

1. **Python 버전**: 3.12 이상 필수 (3.13 권장)
2. **의존성**: 모든 의존성은 버전 고정 필요
3. **API 호환성**: OpenAI API, Upbit API 호환성 유지
4. **데이터베이스**: SQLite에서 PostgreSQL 또는 TimescaleDB로 마이그레이션 고려

### Business Constraints

1. **다운타임**: 최소화 (점진적 마이그레이션)
2. **기능 보존**: 기존 거래 기능 100% 유지
3. **데이터 보존**: 기존 거래 이력 데이터 보존

### Security Constraints

1. **비밀 관리**: 환경 변수 + SecretStr 사용
2. **입력 검증**: 모든 외부 입력에 Pydantic 검증 적용
3. **감사 로그**: 모든 거래에 대한 감사 로그 유지

---

## Traceability Matrix

| Requirement ID | Source | Priority | Risk |
|----------------|--------|----------|------|
| ENV-001 | Python 3.12+ features | High | Low |
| ENV-002 | Dependency management | High | Medium |
| UBQ-001 | Type safety | High | Medium |
| UBQ-002 | Debugging/Monitoring | Medium | Low |
| UBQ-003 | Error handling | High | High |
| UBQ-004 | Configuration | High | Low |
| EVD-001 | Performance | High | Medium |
| EVD-002 | Scheduling | Medium | Low |
| EVD-003 | Trading logic | High | High |
| STD-001 | Business rule | High | Low |
| STD-002 | Business rule | High | Low |
| STD-003 | Reliability | High | Medium |
| UNW-001 | Security | Critical | High |
| UNW-002 | Code quality | Medium | Low |
| UNW-003 | Debugging | High | Medium |
| UNW-004 | Architecture | High | High |

---

## References

- Python 3.12 Documentation: https://docs.python.org/3.12/
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic v2 Documentation: https://docs.pydantic.dev/latest/
- pytest Documentation: https://docs.pytest.org/
- OpenAI API Reference: https://platform.openai.com/docs/
- Upbit API Reference: https://docs.upbit.com/
