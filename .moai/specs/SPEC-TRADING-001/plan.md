# SPEC-TRADING-001: 구현 계획 (Implementation Plan)

**SPEC ID**: SPEC-TRADING-001
**제목**: Upbit 실제 거래 기능 구현
**생성일**: 2026-03-04
**버전**: 1.0.0

---

## 1. 구현 마일스톤 (Implementation Milestones)

### 1.1 Milestone 1: 도메인 레이어 구축 (Primary Goal)

**목표**: 거래 도메인 모델 및 서비스 구현

**작업 항목**:
- [ ] `src/gpt_bitcoin/domain/trading_state.py` - TradingState enum 정의
- [ ] `src/gpt_bitcoin/domain/trading.py` - 도메인 모델 (TradeRequest, TradeApproval, TradeResult)
- [ ] `src/gpt_bitcoin/domain/trading.py` - TradingService 인터페이스 및 구현
- [ ] 잔액 검증 로직 구현
- [ ] 승인 워크플로우 구현
- [ ] DI 컨테이너에 TradingService 등록

**완료 기준**:
- 모든 도메인 모델 Pydantic 검증 통과
- TradingService 단위 테스트 커버리지 85% 이상
- 정적 타입 검사 (mypy) 통과

### 1.2 Milestone 2: UI 통합 (Primary Goal)

**목표**: Web UI (Streamlit)에 실제 거래 기능 연동

**작업 항목**:
- [ ] web_ui.py 매수 주문 TODO 제거 및 구현 (Lines 415-418)
- [ ] web_ui.py 매도 주문 TODO 제거 및 구현 (Lines 423-426)
- [ ] 승인 다이얼로그 UI 컴포넌트 구현
- [ ] 에러 처리 및 사용자 피드백 UI
- [ ] 잔액 자동 새로고침 기능

**완료 기준**:
- 매수/매도 주문이 실제 Upbit API 호출
- 승인 없이 거래 실행되지 않음
- 에러 발생 시 한국어 메시지 표시

### 1.3 Milestone 3: 에러 처리 및 안전장치 (Secondary Goal)

**목표**: 견고한 에러 처리 및 사용자 보호

**작업 항목**:
- [ ] 거래 관련 커스텀 예외 클래스 추가
- [ ] 네트워크 장애 대응 로직
- [ ] 동시성 문제 방지 (잔액 검증)
- [ ] 로깅 및 모니터링 강화

**완료 기준**:
- 모든 예외 케이스에 대한 테스트 커버리지
- 에러 메시지가 사용자 친화적 (한국어)
- 로그에 민감 정보 (API 키) 미포함

### 1.4 Milestone 4: CLI 통합 (Optional Goal)

**목표**: CLI (main.py)에 거래 기능 추가

**작업 항목**:
- [ ] main.py에 매수/매도 명령어 추가
- [ ] CLI용 승인 프롬프트 구현
- [ ] 결과 출력 포맷팅

**완료 기준**:
- CLI로 매수/매도 주문 가능
- 승인 절차가 UI와 동일하게 작동

---

## 2. 기술 접근법 (Technical Approach)

### 2.1 아키텍처 패턴

**Domain-Driven Design (DDD)**:
- Domain Layer: TradingService, 도메인 모델
- Infrastructure Layer: UpbitClient (기존)
- Application Layer: Web UI, CLI

**의존성 방향**:
```
UI Layer (web_ui.py)
    ↓
Domain Layer (TradingService)
    ↓
Infrastructure Layer (UpbitClient)
```

### 2.2 상태 관리

**거래 상태 머신**:
```
IDLE → VALIDATING → PENDING_APPROVAL → EXECUTING → COMPLETED
  ↓         ↓              ↓               ↓
  └─────────┴──────────────┴───────────────→ FAILED/CANCELLED
```

**Session State (Streamlit)**:
```python
# st.session_state 구조
{
    "trade_state": TradingState.IDLE,
    "pending_approval": TradeApproval | None,
    "last_trade_result": TradeResult | None,
}
```

### 2.3 에러 처리 전략

**계층별 에러 처리**:

1. **Infrastructure Layer**: UpbitAPIError, NetworkError
2. **Domain Layer**: InsufficientBalanceError, ValidationError, TradeNotAllowedError
3. **UI Layer**: 사용자 친화적 메시지 변환

**재시도 전략** (기존 UpbitClient 구현 활용):
- 최대 3회 재시도
- Exponential backoff (1s, 2s, 4s)
- 네트워크 에러만 재시도 (비즈니스 에러 제외)

### 2.4 보안 고려사항

**API 키 보호**:
- 환경 변수에서만 로드 (.env 파일)
- 로그에 API 키 마스킹
- JWT 토큰은 메모리에서만 유지

**사용자 승인 필수**:
- 모든 실거래 전 명시적 승인 단계
- 승인 유효 시간: 30초 (이후 자동 만료)
- 승인 정보에 예상 체결가 포함

---

## 3. 파일 수정 계획 (File Modification Plan)

### 3.1 신규 생성 파일

#### 3.1.1 `src/gpt_bitcoin/domain/trading_state.py`

```python
# 예상 구조
from enum import Enum

class TradingState(str, Enum):
    """거래 상태 열거형"""
    IDLE = "idle"
    VALIDATING = "validating"
    PENDING_APPROVAL = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

#### 3.1.2 `src/gpt_bitcoin/domain/trading.py`

```python
# 예상 구조
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Literal

class TradeRequest(BaseModel):
    ...

class TradeApproval(BaseModel):
    ...

class TradeResult(BaseModel):
    ...

class TradingService:
    async def request_buy_order(...) -> TradeApproval: ...
    async def request_sell_order(...) -> TradeApproval: ...
    async def execute_approved_trade(...) -> TradeResult: ...
    async def sync_balances(...) -> list[Balance]: ...
```

### 3.2 수정 파일

#### 3.2.1 `web_ui.py` (Lines 412-426)

**Before**:
```python
# Line 415-418
if st.button("매수 주문", type="primary", key="buy_button"):
    with st.spinner("매수 주문 처리 중..."):
        # TODO: Implement actual buy order
        st.success(f"매수 주문: {buy_amount:,.0f} KRW - {ticker} (시뮬레이션)")

# Line 423-426
if st.button("매도 주문", type="primary", key="sell_button"):
    with st.spinner("매도 주문 처리 중..."):
        # TODO: Implement actual sell order
        st.success(f"매도 주문: {sell_amount} {ticker} - KRW (시뮬레이션)")
```

**After** (개념적):
```python
# Line 415-450 (예상)
if st.button("매수 주문", type="primary", key="buy_button"):
    try:
        # 1. TradingService에 주문 요청
        approval = await trading_service.request_buy_order(ticker, buy_amount)

        # 2. 승인 다이얼로그 표시
        st.session_state.pending_approval = approval
        st.session_state.trade_state = TradingState.PENDING_APPROVAL

        # 3. 승인 대기 UI
        display_approval_dialog(approval)

    except InsufficientBalanceError as e:
        st.error(f"잔액이 부족합니다: {e}")
    except ValidationError as e:
        st.error(f"주문 정보가 올바르지 않습니다: {e}")

# 승인 확인 버튼
if st.button("거래 승인", key="approve_trade"):
    with st.spinner("주문 실행 중..."):
        result = await trading_service.execute_approved_trade(approval)
        if result.success:
            st.success(f"주문 완료: {result.order_uuid}")
            await sync_and_refresh_balances()
        else:
            st.error(f"주문 실패: {result.error_message}")
```

#### 3.2.2 `src/gpt_bitcoin/dependencies/container.py`

**추가 내용**:
```python
from gpt_bitcoin.domain.trading import TradingService

class Container(containers.DeclarativeContainer):
    # ... 기존 코드 ...

    # Trading Service - Factory for per-request isolation
    trading_service: providers.Provider[TradingService] = providers.Factory(
        TradingService,
        upbit_client=upbit_client,
        settings=settings,
    )
```

#### 3.2.3 `src/gpt_bitcoin/infrastructure/exceptions.py`

**추가 내용**:
```python
class TradeNotAllowedError(Exception):
    """거래가 허용되지 않는 상태"""
    def __init__(self, message: str, current_state: str):
        self.current_state = current_state
        super().__init__(message)

class ApprovalExpiredError(Exception):
    """승인이 만료됨"""
    def __init__(self, message: str = "승인이 만료되었습니다. 다시 시도해주세요."):
        super().__init__(message)
```

---

## 4. 테스트 전략 (Testing Strategy)

### 4.1 단위 테스트 (Unit Tests)

**Location**: `tests/unit/domain/test_trading.py`

| 테스트 케이스 | 설명 | Mock 대상 |
|---------------|------|-----------|
| `test_request_buy_order_success` | 정상 매수 요청 | UpbitClient.get_balance |
| `test_request_buy_order_insufficient_balance` | 잔액 부족 | UpbitClient.get_balance |
| `test_request_sell_order_success` | 정상 매도 요청 | UpbitClient.get_balance |
| `test_execute_approved_trade_buy` | 승인된 매수 실행 | UpbitClient.buy_market_order |
| `test_execute_approved_trade_sell` | 승인된 매도 실행 | UpbitClient.sell_market_order |
| `test_execute_without_approval` | 승인 없는 실행 차단 | None |
| `test_approval_expiry` | 승인 만료 처리 | None |

### 4.2 통합 테스트 (Integration Tests)

**Location**: `tests/integration/test_trading_flow.py`

| 테스트 케이스 | 설명 |
|---------------|------|
| `test_full_buy_flow` | 매수 전체 플로우 (요청 → 승인 → 실행) |
| `test_full_sell_flow` | 매도 전체 플로우 |
| `test_concurrent_order_prevention` | 동시 주문 방지 |
| `test_api_failure_recovery` | API 실패 시 복구 |

### 4.3 테스트 커버리지 목표

- **Domain Layer (TradingService)**: 90%+
- **UI Layer (web_ui.py)**: 80%+
- **전체**: 85%+

---

## 5. 의존성 및 순서 (Dependencies and Sequencing)

### 5.1 작업 의존성 그래프

```
[Domain 모델 정의]
       ↓
[TradingService 구현] ← [예외 클래스 추가]
       ↓
[DI 컨테이너 등록]
       ↓
[UI 통합] ← [단위 테스트]
       ↓
[통합 테스트]
       ↓
[CLI 통합] (Optional)
```

### 5.2 병렬 가능 작업

**독립적으로 수행 가능**:
- 도메인 모델 정의 + 예외 클래스 추가
- 단위 테스트 작성 (TDD)
- UI 목업 디자인

**순차 수행 필요**:
- TradingService 구현 → DI 컨테이너 등록 → UI 통합

---

## 6. 롤백 계획 (Rollback Plan)

### 6.1 기능 플래그 (Feature Flag)

**Settings 추가**:
```python
# config/settings.py
enable_real_trading: bool = Field(
    default=False,
    description="실제 거래 활성화 (False 시 시뮬레이션 모드 유지)",
)
```

### 6.2 롤백 절차

1. `enable_real_trading = False` 설정
2. 시스템 재시작
3. 기존 시뮬레이션 모드로 복귀

---

## 7. 모니터링 및 로깅 (Monitoring and Logging)

### 7.1 로깅 전략

**거래 로그 항목**:
```python
logger.info(
    "Trade request created",
    ticker=ticker,
    side=side,
    amount=amount,
    request_id=request_id,
    # API 키 절대 로그하지 않음
)

logger.info(
    "Trade executed",
    order_uuid=order_uuid,
    ticker=ticker,
    executed_price=executed_price,
    executed_quantity=executed_quantity,
)
```

### 7.2 메트릭 (Metrics)

**수집 항목**:
- 거래 요청 수 (buy/sell별)
- 거래 성공/실패율
- 평균 실행 시간
- API 호출 지연 시간

---

## 8. 리스크 완화 (Risk Mitigation)

### 8.1 기술적 리스크

| 리스크 | 완화 조치 |
|--------|-----------|
| 동시성 문제 | 잔액 검증 시 DB 락 고려 |
| API 장애 | Circuit Breaker 패턴 (이미 구현됨) |
| 네트워크 지연 | 타임아웃 설정 (30초) |

### 8.2 사용자 보호

| 리스크 | 완화 조치 |
|--------|-----------|
| 실수로 인한 손실 | 명시적 승인 단계, 큰 금액 경고 |
| 시장 변동 | 승인 유효 시간 30초 |
| 시스템 오류 | 상세 에러 메시지, 재시도 옵션 |

---

**버전**: 1.0.0
**마지막 수정**: 2026-03-04
