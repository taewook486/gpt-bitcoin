# SPEC-TRADING-001: Upbit 실제 거래 기능 구현

**SPEC ID**: SPEC-TRADING-001
**제목**: Upbit 실제 거래 기능 구현 (Upbit Real Trading Implementation)
**생성일**: 2026-03-04
**상태**: Planned
**우선순위**: High
**담당**: manager-ddd (implementation), expert-backend (consultation)
**라이프사이클**: spec-anchored (SPEC maintained alongside implementation)

---

## 1. 문제 분석 (Problem Analysis)

### 1.1 현황 (Current State)

시스템은 현재 시뮬레이션 모드로 운영 중이며, 실제 거래 기능이 구현되지 않은 상태입니다.

**현 코드 분석 (web_ui.py lines 415-426)**:
```python
# Line 415-418: 매수 주문 TODO
if st.button("매수 주문", type="primary", key="buy_button"):
    with st.spinner("매수 주문 처리 중..."):
        # TODO: Implement actual buy order
        st.success(f"매수 주문: {buy_amount:,.0f} KRW - {ticker} (시뮬레이션)")

# Line 423-426: 매도 주문 TODO
if st.button("매도 주문", type="primary", key="sell_button"):
    with st.spinner("매도 주문 처리 중..."):
        # TODO: Implement actual sell order
        st.success(f"매도 주문: {sell_amount} {ticker} - KRW (시뮬레이션)")
```

**기존 구현된 기능 (upbit_client.py)**:
- `buy_market_order()` - 시장가 매수 주문 실행 (Line 496-542)
- `sell_market_order()` - 시장가 매도 주문 실행 (Line 544-593)
- `cancel_order()` - 주문 취소 (Line 595-617)
- `get_order()` - 주문 조회 (Line 619-636)
- `get_balances()` - 잔액 조회 (Line 457-478)
- JWT 인증 시스템 (Line 194-236)
- Rate Limiting (Line 238-255)

### 1.2 근본 원인 (Root Cause Analysis)

**Five Whys 분석**:
1. **Why 1**: 왜 실제 거래가 안 되는가? → UI가 UpbitClient의 주문 메서드를 호출하지 않음
2. **Why 2**: 왜 호출하지 않는가? → 거래 승인/인증 시스템이 없어서 안전장치 없이 호출할 수 없음
3. **Why 3**: 왜 승인 시스템이 없는가? → 초기 개발 시 시뮬레이션 모드로만 설계됨
4. **Why 4**: 왜 시뮬레이션만 있었나? → 실거래 위험성 때문에 안전하게 시작
5. **Why 5 (Root Cause)**: 실거래 전환을 위한 안전한 인증/승인 프레임워크 부재

### 1.3 가정 분석 (Assumption Analysis)

| 가정 | 신뢰도 | 근거 | 위험 | 검증 방법 |
|------|--------|------|------|-----------|
| 사용자가 Upbit API 키를 보유 | High | 이미 잔액 조회에 사용 중 | Low | Settings 검증 |
| JWT 인증이 안전함 | High | 업계 표준 (HS256) | Medium | 보안 리뷰 필요 |
| Rate Limiting이 충분함 | Medium | Upbit 10 req/s 준수 | Low | 부하 테스트 |
| 사용자가 실거래 위험을 이해 | Medium | UI에 경고 필요 | High | 명시적 동의 필요 |

---

## 2. 환경 (Environment)

### 2.1 시스템 컨텍스트

```
┌─────────────────────────────────────────────────────────────┐
│                    Web UI (Streamlit)                        │
│  - 매수/매도 주문 입력                                        │
│  - 거래 승인 요청                                             │
│  - 결과 표시                                                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Trading Service (New Domain Layer)              │
│  - 주문 검증                                                  │
│  - 승인 상태 관리                                             │
│  - 잔액 동기화                                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   UpbitClient (Existing)                     │
│  - buy_market_order()                                        │
│  - sell_market_order()                                       │
│  - get_balances()                                            │
│  - JWT Authentication                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Upbit API (/v1/orders)                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 기술 스택

- **Backend**: Python 3.13+, FastAPI 패턴 (현재 Streamlit)
- **DI Framework**: dependency-injector
- **Validation**: Pydantic v2
- **HTTP Client**: aiohttp (기존)
- **API**: Upbit REST API v1

### 2.3 제약 조건

**하드 제약 (Hard Constraints)**:
- 최소 주문 금액: 5,000 KRW (Upbit 정책)
- Rate Limit: 10 requests/second (Private endpoints)
- JWT 인증 필수 (모든 주문 API)
- 실거래는 명시적 사용자 승인 필요

**소프트 제약 (Soft Constraints)**:
- 잔액 동기화 지연 최소화 (< 1초)
- UI 응답성 유지
- 에러 메시지 한국어 지원

---

## 3. 요구사항 (Requirements)

### 3.1 EARS Ubiquitous Requirements (시스템 전체 항상 적용)

**REQ-001**: 시스템은 모든 거래 작업에 대해 JWT 기반 인증을 항상 수행해야 한다.
```
The system shall always perform JWT-based authentication for all trading operations.
```

**REQ-002**: 시스템은 Rate Limit (10 req/s)을 항상 준수해야 한다.
```
The system shall always respect the Upbit rate limit of 10 requests per second.
```

**REQ-003**: 시스템은 모든 주문 실행 전 사용자 잔액을 항상 검증해야 한다.
```
The system shall always verify user balance before executing any order.
```

### 3.2 EARS Event-Driven Requirements (이벤트 기반)

**REQ-010**: WHEN 사용자가 매수 주문을 요청하면 THEN 시스템은 승인 대기 상태로 전환하고 사용자 확인을 요청해야 한다.
```
WHEN user requests a buy order THEN the system shall transition to pending approval state and request user confirmation.
```

**REQ-011**: WHEN 사용자가 거래를 승인하면 THEN 시스템은 Upbit API /v1/orders를 호출하여 실제 주문을 실행해야 한다.
```
WHEN user approves the trade THEN the system shall call Upbit API /v1/orders to execute the actual order.
```

**REQ-012**: WHEN 주문이 성공하면 THEN 시스템은 잔액을 즉시 동기화하고 성공 메시지를 표시해야 한다.
```
WHEN order succeeds THEN the system shall immediately synchronize balance and display success message.
```

**REQ-013**: WHEN 주문이 실패하면 THEN 시스템은 에러 원인을 한국어로 표시하고 재시도 옵션을 제공해야 한다.
```
WHEN order fails THEN the system shall display error reason in Korean and provide retry option.
```

**REQ-014**: WHEN 사용자가 매도 주문을 요청하면 THEN 시스템은 해당 코인 보유량을 확인하고 승인을 요청해야 한다.
```
WHEN user requests a sell order THEN the system shall verify coin holdings and request approval.
```

### 3.3 EARS State-Driven Requirements (상태 기반)

**REQ-020**: IF 잔액이 주문 금액보다 부족하면 THEN 시스템은 주문을 차단하고 "잔액 부족" 메시지를 표시해야 한다.
```
IF balance is insufficient for the order THEN the system shall block the order and display "insufficient balance" message.
```

**REQ-021**: IF 승인이 대기 중인 상태에서 사용자가 취소하면 THEN 시스템은 주문을 실행하지 않고 초기 상태로 복귀해야 한다.
```
IF user cancels during pending approval THEN the system shall not execute the order and return to initial state.
```

**REQ-022**: IF API 호출이 Rate Limit에 도달하면 THEN 시스템은 자동으로 대기 후 재시도해야 한다.
```
IF API calls reach rate limit THEN the system shall automatically wait and retry.
```

**REQ-023**: IF 네트워크 연결이 불안정하면 THEN 시스템은 재시도 로직을 적용하고 최대 3회까지 재시도해야 한다.
```
IF network connection is unstable THEN the system shall apply retry logic with maximum 3 retries.
```

### 3.4 EARS Unwanted Behavior Requirements (금지 사항)

**REQ-030**: 시스템은 사용자 승인 없이 실제 거래를 실행해서는 안 된다.
```
The system shall not execute real trades without explicit user approval.
```

**REQ-031**: 시스템은 최소 주문 금액 (5,000 KRW) 미만의 주문을 실행해서는 안 된다.
```
The system shall not execute orders below the minimum order amount (5,000 KRW).
```

**REQ-032**: 시스템은 API 키를 로그에 기록하거나 노출해서는 안 된다.
```
The system shall not log or expose API keys.
```

**REQ-033**: 시스템은 잔액 검증 없이 주문을 실행해서는 안 된다.
```
The system shall not execute orders without balance verification.
```

### 3.5 EARS Optional Requirements (선택 사항)

**REQ-040**: WHERE 가능하면 시스템은 주문 실행 전 현재 시세를 표시하여 사용자 의사결정을 지원해야 한다.
```
Where possible, the system shall display current market price before order execution to support user decision.
```

**REQ-041**: WHERE 가능하면 시스템은 주문 히스토리를 저장하여 사용자가 거래 내역을 조회할 수 있게 해야 한다.
```
Where possible, the system shall store order history for user trade history lookup.
```

---

## 4. 명세 (Specifications)

### 4.1 도메인 모델 (Domain Models)

#### 4.1.1 TradingState (거래 상태)

```python
class TradingState(str, Enum):
    """거래 상태 열거형"""
    IDLE = "idle"                    # 초기 상태
    VALIDATING = "validating"        # 검증 중
    PENDING_APPROVAL = "pending"     # 승인 대기
    EXECUTING = "executing"          # 실행 중
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    CANCELLED = "cancelled"          # 취소됨
```

#### 4.1.2 TradeRequest (거래 요청)

```python
class TradeRequest(BaseModel):
    """거래 요청 모델"""
    ticker: str                      # 마켓 코드 (e.g., "KRW-BTC")
    side: Literal["buy", "sell"]     # 매수/매도
    amount: float                    # 금액 (매수) 또는 수량 (매도)
    order_type: Literal["market"] = "market"  # 주문 타입 (현재 시장가만)
    timestamp: datetime              # 요청 시간

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "KRW-BTC",
                "side": "buy",
                "amount": 10000.0,
                "order_type": "market",
                "timestamp": "2026-03-04T12:00:00Z"
            }
        }
    )
```

#### 4.1.3 TradeApproval (거래 승인)

```python
class TradeApproval(BaseModel):
    """거래 승인 모델"""
    request_id: str                  # 요청 ID (UUID)
    trade_request: TradeRequest      # 원본 요청
    estimated_price: float           # 예상 체결가
    estimated_quantity: float        # 예상 수량
    fee_estimate: float              # 예상 수수료
    warnings: list[str]              # 경고 메시지 목록
    approved: bool = False           # 승인 여부
    approved_at: datetime | None     # 승인 시간
```

#### 4.1.4 TradeResult (거래 결과)

```python
class TradeResult(BaseModel):
    """거래 실행 결과"""
    success: bool                    # 성공 여부
    order_uuid: str | None           # 주문 UUID
    ticker: str                      # 마켓 코드
    side: Literal["buy", "sell"]     # 매수/매도
    executed_price: float | None     # 체결 가격
    executed_quantity: float | None  # 체결 수량
    fee: float | None                # 수수료
    error_message: str | None        # 에러 메시지
    timestamp: datetime              # 실행 시간
```

### 4.2 서비스 인터페이스 (Service Interfaces)

#### 4.2.1 TradingService

```python
class TradingService:
    """거래 서비스 인터페이스"""

    async def request_buy_order(
        self,
        ticker: str,
        amount_krw: float,
    ) -> TradeApproval:
        """
        매수 주문 요청 및 승인 정보 생성

        Args:
            ticker: 마켓 코드 (e.g., "KRW-BTC")
            amount_krw: 매수 금액 (KRW)

        Returns:
            TradeApproval: 승인 대기 정보

        Raises:
            InsufficientBalanceError: 잔액 부족
            ValidationError: 금액 검증 실패
        """

    async def request_sell_order(
        self,
        ticker: str,
        quantity: float,
    ) -> TradeApproval:
        """
        매도 주문 요청 및 승인 정보 생성

        Args:
            ticker: 마켓 코드 (e.g., "KRW-BTC")
            quantity: 매도 수량

        Returns:
            TradeApproval: 승인 대기 정보

        Raises:
            InsufficientBalanceError: 보유 수량 부족
            ValidationError: 수량 검증 실패
        """

    async def execute_approved_trade(
        self,
        approval: TradeApproval,
    ) -> TradeResult:
        """
        승인된 거래 실행

        Args:
            approval: 사용자가 승인한 거래 정보

        Returns:
            TradeResult: 실행 결과

        Raises:
            UpbitAPIError: API 호출 실패
            InsufficientBalanceError: 잔액 부족 (동시성 문제)
        """

    async def sync_balances(self) -> list[Balance]:
        """
        잔액 실시간 동기화

        Returns:
            list[Balance]: 업데이트된 잔액 목록
        """
```

### 4.3 UI 컴포넌트 명세

#### 4.3.1 매수 주문 UI (Buy Order UI)

**Location**: web_ui.py, lines 412-418 (수정 필요)

**변경 사항**:
1. 기존 TODO 제거
2. TradingService 호출 추가
3. 승인 다이얼로그 표시
4. 결과 처리 로직 추가

**UI Flow**:
```
[매수 금액 입력]
       ↓
[매수 주문 버튼 클릭]
       ↓
[잔액 검증] → 실패 → [에러 메시지 표시]
       ↓ 성공
[승인 다이얼로그]
  - 예상 체결가 표시
  - 수수료 표시
  - 경고 메시지 (있으면)
  - [승인] [취소] 버튼
       ↓ 승인
[주문 실행 중...] (spinner)
       ↓
[성공/실패 결과 표시]
  - 성공: 주문 UUID, 체결가, 수량
  - 실패: 에러 메시지, 재시도 버튼
       ↓
[잔액 자동 새로고침]
```

#### 4.3.2 매도 주문 UI (Sell Order UI)

**Location**: web_ui.py, lines 420-426 (수정 필요)

**변경 사항**: 매수와 동일한 패턴, 수량 기반 주문

---

## 5. MX 태그 대상 (MX Tag Targets)

### 5.1 High Fan-In Functions (ANCHOR 대상)

| 함수 | 위치 | 호출자 수 | 이유 |
|------|------|-----------|------|
| `TradingService.request_buy_order` | 신규 | 2+ | Web UI, CLI |
| `TradingService.execute_approved_trade` | 신규 | 2+ | Buy, Sell 공통 |
| `UpbitClient.get_balances` | upbit_client.py:457 | 3+ | UI, Service, CLI |

### 5.2 Danger Zones (WARN 대상)

| 영역 | 위치 | 위험 요소 | @MX:REASON |
|------|------|-----------|------------|
| 실제 자금 거래 | TradingService.execute_approved_trade | 금전적 손실 가능성 | 실제 KRW/코인 거래 실행 |
| 잔액 검증 | TradingService._validate_balance | 동시성 문제 | 거래 중 잔액 변동 가능 |
| JWT 토큰 생성 | UpbitClient._generate_jwt | 보안 민감 | API 키 노출 위험 |

### 5.3 Context Delivery (NOTE 대상)

| 항목 | 위치 | 설명 |
|------|------|------|
| 최소 주문 금액 | Settings.min_order_value | Upbit 정책 5,000 KRW |
| Rate Limit | UpbitClient.RATE_LIMIT_REQUESTS | 10 req/s |

---

## 6. 수정 파일 목록 (Files to Modify)

### 6.1 신규 파일

| 파일 경로 | 용도 |
|-----------|------|
| `src/gpt_bitcoin/domain/trading.py` | TradingService, 도메인 모델 |
| `src/gpt_bitcoin/domain/trading_state.py` | TradingState enum |
| `tests/unit/domain/test_trading.py` | TradingService 단위 테스트 |
| `tests/integration/test_trading_flow.py` | 통합 테스트 |

### 6.2 수정 파일

| 파일 경로 | 수정 내용 | 영향도 |
|-----------|-----------|--------|
| `web_ui.py` | Lines 415-426: TODO → 실제 구현 | High |
| `src/gpt_bitcoin/dependencies/container.py` | TradingService 등록 | Medium |
| `src/gpt_bitcoin/infrastructure/exceptions.py` | 거래 관련 예외 추가 | Low |
| `main.py` | CLI 거래 기능 추가 (선택) | Medium |

### 6.3 파일 의존성 그래프

```
web_ui.py
    └── TradingService (domain/trading.py)
            ├── UpbitClient (infrastructure/external/upbit_client.py)
            │       └── Settings (config/settings.py)
            ├── TradeRequest, TradeApproval, TradeResult (domain/trading.py)
            └── InsufficientBalanceError (infrastructure/exceptions.py)
```

---

## 7. 위험 및 완화 전략 (Risks and Mitigation)

### 7.1 기술적 위험

| 위험 | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| 동시성 문제로 잔액 불일치 | Medium | High | DB 트랜잭션, 낙관적 락 |
| API 호출 실패 | Medium | Medium | 재시도 로직 (이미 구현됨) |
| JWT 토큰 만료 | Low | Medium | 토큰 갱신 로직 |
| 네트워크 지연 | Medium | Low | 타임아웃 설정 |

### 7.2 비즈니스 위험

| 위험 | 확률 | 영향 | 완화 전략 |
|------|------|------|-----------|
| 사용자 실수로 인한 손실 | High | High | 명시적 승인 단계, 경고 메시지 |
| 시장 급변으로 승인 가격과 실제 가격 차이 | Medium | Medium | 승인 유효 시간 설정 (30초) |
| 법적 규정 준수 | Low | High | 이용약관 동의, 면책 조항 |

---

## 8. 추적성 매트릭스 (Traceability Matrix)

| 요구사항 | 테스트 케이스 | 구현 위치 |
|----------|---------------|-----------|
| REQ-001 (JWT 인증) | test_jwt_authentication | upbit_client.py:194 |
| REQ-010 (매수 승인) | test_buy_order_approval | domain/trading.py |
| REQ-011 (주문 실행) | test_execute_approved_trade | domain/trading.py |
| REQ-020 (잔액 검증) | test_insufficient_balance | domain/trading.py |
| REQ-030 (승인 없는 거래 금지) | test_unauthorized_trade_blocked | domain/trading.py |

---

## 9. 참조 (References)

### 9.1 관련 문서

- Upbit API 문서: https://docs.upbit.com/
- Upbit 주문 API: https://docs.upbit.com/reference#order
- JWT 인증 가이드: https://docs.upbit.com/docs/making-requests

### 9.2 관련 SPEC

- N/A (첫 번째 거래 관련 SPEC)

### 9.3 Constitution 준수 확인

| 항목 | 준수 여부 | 비고 |
|------|-----------|------|
| Python 3.13+ | ✅ | 현재 프로젝트 사용 |
| Pydantic v2 | ✅ | 도메인 모델에 사용 |
| pytest | ✅ | 테스트 프레임워크 |
| dependency-injector | ✅ | DI 컨테이너 사용 |

---

## 10. 승인 이력 (Approval History)

| 일자 | 승인자 | 상태 | 비고 |
|------|--------|------|------|
| 2026-03-04 | manager-spec | Draft | 초기 작성 |

---

**버전**: 1.0.0
**마지막 수정**: 2026-03-04
**SPEC 라이프사이클**: spec-anchored (구현 후에도 유지 관리)
