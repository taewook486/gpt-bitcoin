# SPEC-TRADING-001: 코드베이스 분석 결과 (Research Findings)

**SPEC ID**: SPEC-TRADING-001
**분석일**: 2026-03-04
**분석자**: manager-spec agent

---

## 1. 코드베이스 구조 분석

### 1.1 프로젝트 전체 구조

```
gpt-bitcoin/
├── src/gpt_bitcoin/
│   ├── config/
│   │   └── settings.py                 # Pydantic 설정 관리
│   ├── dependencies/
│   │   └── container.py                # DI 컨테이너 (dependency-injector)
│   ├── domain/                         # 도메인 레이어 (현재 비어있음)
│   ├── infrastructure/
│   │   ├── external/
│   │   │   ├── upbit_client.py         # Upbit API 클라이언트
│   │   │   └── glm_client.py           # GLM AI 클라이언트
│   │   ├── exceptions.py               # 커스텀 예외
│   │   ├── logging/                    # 로깅 모듈
│   │   └── resilience/                 # Circuit Breaker, Retry
│   └── application/
│       └── scheduler.py                # 스케줄러
├── web_ui.py                           # Streamlit 웹 UI (주요 수정 대상)
├── main.py                             # CLI 진입점
└── tests/                              # 테스트 코드
    ├── unit/
    │   ├── infrastructure/
    │   │   ├── test_upbit_client.py
    │   │   └── test_upbit_client_extended.py
    │   └── domain/
    └── integration/
```

### 1.2 주요 발견 사항

**긍정적 발견 (이미 구현됨)**:
1. ✅ UpbitClient에 이미 `buy_market_order()`, `sell_market_order()` 메서드 구현됨
2. ✅ JWT 인증 시스템 완전 구현됨 (HS256 알고리즘)
3. ✅ Rate Limiting 구현됨 (10 req/s)
4. ✅ 재시도 로직 구현됨 (tenacity 라이브러리)
5. ✅ DI 컨테이너 구축됨 (dependency-injector)
6. ✅ Pydantic v2 모델 사용 중

**개선 필요 사항**:
1. ❌ Web UI (web_ui.py)가 시뮬레이션 모드로만 작동 (Lines 417-418, 425-426 TODO)
2. ❌ 도메인 레이어가 비어있음 (Infrastructure만 존재)
3. ❌ 거래 승인/인증 시스템 없음
4. ❌ 잔액 실시간 동기화 로직 없음

---

## 2. 상세 코드 분석

### 2.1 upbit_client.py 분석 (Lines 1-651)

**주요 메서드**:

| 메서드 | 라인 | 용도 | 상태 |
|--------|------|------|------|
| `_generate_jwt()` | 194-236 | JWT 토큰 생성 | ✅ 완료 |
| `_check_rate_limit()` | 238-255 | Rate Limit 검사 | ✅ 완료 |
| `_request()` | 257-347 | HTTP 요청 (재시도 포함) | ✅ 완료 |
| `get_balances()` | 457-478 | 잔액 조회 | ✅ 완료 |
| `get_balance()` | 480-494 | 특정 통화 잔액 | ✅ 완료 |
| `buy_market_order()` | 496-542 | 시장가 매수 | ✅ 완료 |
| `sell_market_order()` | 544-593 | 시장가 매도 | ✅ 완료 |
| `cancel_order()` | 595-617 | 주문 취소 | ✅ 완료 |
| `get_order()` | 619-636 | 주문 조회 | ✅ 완료 |

**주요 발견**:
- JWT 토큰 생성 시 query_hash 포함 (SHA512)
- 잔액 검증을 사전에 수행 (`InsufficientBalanceError` 발생)
- 재시도 로직: 최대 3회, exponential backoff

### 2.2 web_ui.py 분석 (Lines 412-426)

**현재 구현 (시뮬레이션)**:

```python
# Line 412-418: 매수 주문
with col1:
    st.markdown("#### 🟢 매수 (Buy)")
    buy_amount = st.number_input("매수 금액 (KRW)", min_value=5000, value=10000, step=1000, key="buy_amount")
    if st.button("매수 주문", type="primary", key="buy_button"):
        with st.spinner("매수 주문 처리 중..."):
            # TODO: Implement actual buy order
            st.success(f"매수 주문: {buy_amount:,.0f} KRW - {ticker} (시뮬레이션)")

# Line 420-426: 매도 주문
with col2:
    st.markdown("#### 🔴 매도 (Sell)")
    sell_amount = st.number_input("매도 수량", min_value=0.0, value=0.1, step=0.01, key="sell_amount")
    if st.button("매도 주문", type="primary", key="sell_button"):
        with st.spinner("매도 주문 처리 중..."):
            # TODO: Implement actual sell order
            st.success(f"매도 주문: {sell_amount} {ticker} - KRW (시뮬레이션)")
```

**수정 필요 사항**:
1. TODO 제거
2. TradingService 호출 추가
3. 승인 다이얼로그 구현
4. 에러 처리 추가
5. 잔액 새로고침 추가

### 2.3 container.py 분석 (Lines 1-159)

**현재 DI 구조**:

```python
class Container(containers.DeclarativeContainer):
    settings: providers.Provider[Settings] = providers.Singleton(get_settings)
    glm_client: providers.Provider[GLMClient] = providers.Singleton(GLMClient, settings=settings)
    upbit_client: providers.Provider[UpbitClient] = providers.Factory(UpbitClient, settings=settings)
```

**추가 필요**:
```python
trading_service: providers.Provider[TradingService] = providers.Factory(
    TradingService,
    upbit_client=upbit_client,
    settings=settings,
)
```

### 2.4 settings.py 분석 (Lines 1-143)

**거래 관련 설정**:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `trading_percentage` | 100.0 | 거래 비율 (0-100) |
| `min_order_value` | 5000.0 | 최소 주문 금액 (KRW) |
| `max_retries` | 5 | 최대 재시도 횟수 |
| `retry_delay_seconds` | 5 | 재시도 간격 |

**추가 필요**:
```python
enable_real_trading: bool = Field(default=False, description="실제 거래 활성화")
approval_timeout_seconds: int = Field(default=30, description="승인 유효 시간")
```

---

## 3. 기존 테스트 코드 분석

### 3.1 test_upbit_client.py 분석

**기존 테스트 커버리지**:
- `get_balances()` 테스트 존재
- `get_orderbook()` 테스트 존재
- `get_ohlcv()` 테스트 존재
- `buy_market_order()` 테스트 존재
- `sell_market_order()` 테스트 존재

**결론**: UpbitClient는 이미 충분히 테스트됨

### 3.2 추가 필요 테스트

| 테스트 파일 | 필요 테스트 |
|-------------|-------------|
| `test_trading.py` (신규) | TradingService 전체 |
| `test_trading_flow.py` (신규) | 통합 플로우 |
| `test_web_ui_trading.py` (신규) | UI 통합 |

---

## 4. 외부 API 분석

### 4.1 Upbit API 엔드포인트

| 엔드포인트 | 메서드 | 용도 | 인증 |
|------------|--------|------|------|
| `/v1/accounts` | GET | 잔액 조회 | JWT |
| `/v1/orders` | POST | 주문 생성 | JWT |
| `/v1/order` | GET | 주문 조회 | JWT |
| `/v1/order` | DELETE | 주문 취소 | JWT |

### 4.2 Rate Limit 정책

- Private 엔드포인트: 10 requests/second
- Public 엔드포인트: 10 requests/second
- 초과 시: 429 Too Many Requests

### 4.3 최소 주문 금액

- KRW 마켓: 5,000 KRW
- BTC 마켓: 0.0001 BTC
- USDT 마켓: 10 USDT

---

## 5. 참조 구현 (Reference Implementations)

### 5.1 유사 패턴 분석

**기존 GLMClient 사용 패턴** (web_ui.py):
```python
# Line 432-438: AI 추천 요청
response, current_price = get_ai_recommendation(
    ticker,
    st.session_state.selected_strategy,
    st.session_state.instruction_version,
)
```

**적용 가능 패턴**:
```python
# 거래 서비스 사용 패턴 (제안)
container = get_container()
trading_service = container.trading_service()

approval = await trading_service.request_buy_order(ticker, buy_amount)
# ... 승인 UI ...
result = await trading_service.execute_approved_trade(approval)
```

---

## 6. 리스크 분석

### 6.1 기술적 리스크

| 리스크 | 현재 상태 | 완화 필요 |
|--------|-----------|-----------|
| JWT 만료 | 자동 갱신 없음 | ❌ 필요 |
| 동시성 문제 | 잠금 없음 | ❌ 필요 |
| 네트워크 장애 | 재시도 있음 | ✅ 완료 |
| Rate Limit | 구현됨 | ✅ 완료 |

### 6.2 비즈니스 리스크

| 리스크 | 현재 상태 | 완화 필요 |
|--------|-----------|-----------|
| 실거래 실수 | 시뮬레이션만 됨 | ❌ 승인 시스템 필요 |
| 금액 오입력 | 검증 없음 | ❌ 검증 필요 |
| 동시 주문 | 차단 없음 | ❌ 상태 관리 필요 |

---

## 7. 권장 구현 순서

### 7.1 Phase 1: 도메인 레이어 구축

1. `src/gpt_bitcoin/domain/trading_state.py` - 상태 enum
2. `src/gpt_bitcoin/domain/trading.py` - 도메인 모델 + TradingService
3. `src/gpt_bitcoin/infrastructure/exceptions.py` - 거래 예외 추가

### 7.2 Phase 2: DI 통합

1. `src/gpt_bitcoin/dependencies/container.py` - TradingService 등록

### 7.3 Phase 3: UI 통합

1. `web_ui.py` - 매수/매도 TODO 제거 및 실제 구현

### 7.4 Phase 4: 테스트

1. `tests/unit/domain/test_trading.py` - 단위 테스트
2. `tests/integration/test_trading_flow.py` - 통합 테스트

---

## 8. 결론

### 8.1 핵심 발견

**좋은 소식**:
- Upbit API 클라이언트가 이미 완전히 구현되어 있음
- JWT 인증, Rate Limiting, 재시도 로직 모두 완비
- DI 컨테이너 구축되어 있어 확장 용이

**해결 필요**:
- Web UI가 시뮬레이션 모드만 지원 (TODO 2개)
- 거래 승인 시스템 전무
- 도메인 레이어 비어있음

### 8.2 구현 난이도 평가

| 작업 | 난이도 | 예상 노력 |
|------|--------|-----------|
| 도메인 모델 생성 | Low | 작음 |
| TradingService 구현 | Medium | 중간 |
| UI 통합 | Medium | 중간 |
| 테스트 작성 | Low | 작음 |
| **전체** | **Medium** | **중간** |

---

**분석 완료일**: 2026-03-04
**다음 단계**: SPEC-TRADING-001 구현 (/moai:2-run SPEC-TRADING-001)
