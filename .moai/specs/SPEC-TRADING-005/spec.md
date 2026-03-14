# SPEC-TRADING-005: Testnet Environment Support

## Metadata

- **SPEC ID**: SPEC-TRADING-005
- **Title**: Testnet Environment Support (테스트넷 환경 지원)
- **Created**: 2026-03-04
- **Status**: Completed
- **Priority**: High
- **Depends On**: SPEC-TRADING-001 (TradingService infrastructure)
- **Lifecycle Level**: spec-anchored

---

## Problem Analysis

### Current State

현재 시스템은 실제 Upbit API를 통해서만 거래를 실행할 수 있으며, 테스트넷(가상 거래 환경)을 지원하지 않습니다.

**Key Issues**:
1. **실거래 위험**: 모든 테스트는 실제 자금으로 수행되어 자금 손실 위험 존재
2. **전략 검증 불가**: 새로운 거래 전략을 안전하게 테스트할 수 없음
3. **초기 사용자 온보딩 부담**: 실거래에 대한 두려움으로 시스템 사용을 꺼릴 수 있음
4. **버그 테스트 어려움**: 실거래 환경에서만 발생하는 버그를 안전하게 재현할 수 없음

**Important Constraint**: Upbit는 공식적인 Testnet API를 제공하지 않음 → Mock/Simulation 방식 필수

### Root Cause Analysis (Five Whys)

1. **Why 1**: 왜 테스트넷이 없는가? → 초기 개발 시 실거래 API만 고려
2. **Why 2**: 왜 테스트넷 요구사항이 누락되었나? → Upbit 공식 testnet 부재를 확인하지 않음
3. **Why 3**: 왜 대안 설계가 없었나? → Mock/Simulation 접근 방식이 고려되지 않음
4. **Why 4**: 왜 Mock 방식이 필요한가? → 안전한 테스트 환경이 실제 거래 시스템 개발에 필수적
5. **Root Cause**: Testnet/Simulation 환경에 대한 아키텍처 설계 부재

### Desired State

Mock UpbitClient를 통한 시뮬레이션 환경 지원:
- 가상 잔액 관리
- 시뮬레이션된 거래 실행
- 별도 테스트넷 DB
- 명확한 UI 표시

---

## Environment

### System Context

```
Web UI (Streamlit)
    └── Mode Switcher (Production/Testnet)
            ├── Production Mode → UpbitClient (Real API)
            └── Testnet Mode → MockUpbitClient (Simulation)
```

### Technology Stack

- **Backend**: Python 3.13+
- **DI Framework**: dependency-injector (기존과 동일)
- **Database**: SQLite (testnet_trades.db)
- **API Simulation**: MockUpbitClient (내부 구현)

### Constraints

**Hard Constraints**:
- Upbit 공식 Testnet API 없음 → Mock 방식 필수
- Testnet DB와 Production DB 완전 분리 필수
- DI Container를 통한 런타임 클라이언트 교체 필수
- Testnet 모드 UI에 명확한 표시 필수

**Soft Constraints**:
- Testnet 초기 잔액 설정 가능 (기본: 10,000,000 KRW)
- Testnet 데이터 Export 기능

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-TEST-001**: 시스템은 testnet 모드에서 모든 거래를 시뮬레이션해야 한다.

```
The system shall simulate all trades in testnet mode:
- No real API calls to Upbit
- Virtual balance management
- Simulated order execution
- Separate database (testnet_trades.db)
```

**REQ-TEST-002**: 시스템은 testnet 모드임을 UI에 항상 명확히 표시해야 한다.

```
The system shall always clearly indicate testnet mode in UI:
- Red/Yellow "TESTNET MODE" banner at top
- Mode indicator in all trade confirmation dialogs
```

### Event-Driven Requirements

**REQ-TEST-010**: WHEN 사용자가 testnet 모드로 전환하면 THEN 시스템은 MockUpbitClient로 교체하고 가상 잔액을 초기화해야 한다.

```
WHEN user switches to testnet mode
THEN the system shall:
    - Replace UpbitClient with MockUpbitClient in DI container
    - Initialize virtual balance (default: 10,000,000 KRW)
    - Switch database to testnet_trades.db
    - Display TESTNET MODE banner
```

**REQ-TEST-011**: WHEN testnet 모드에서 거래가 실행되면 THEN 시스템은 가상 잔액을 업데이트하고 시뮬레이션 결과를 반환해야 한다.

```
WHEN trade is executed in testnet mode
THEN the system shall:
    - Update virtual balance (no real API call)
    - Generate simulated order UUID
    - Calculate simulated fees
    - Return TradeResult with testnet flag
```

### State-Driven Requirements

**REQ-TEST-020**: IF testnet 모드에서 잔액이 부족하면 THEN 시스템은 가상 잔액 추가 옵션을 제공해야 한다.

```
IF balance is insufficient in testnet mode
THEN the system shall offer option to:
    - Add virtual KRW (e.g., +1,000,000 KRW)
    - Reset to default balance (10,000,000 KRW)
```

### Unwanted Behavior Requirements

**REQ-TEST-030**: 시스템은 testnet 모드에서 실제 Upbit API를 호출해서는 안 된다.

```
The system shall NOT:
- Make real HTTP requests to api.upbit.com in testnet mode
- Use real API keys for testnet trades
- Affect real account balance
```

**REQ-TEST-031**: 시스템은 testnet 데이터를 production DB에 저장해서는 안 된다.

```
The system shall NOT:
- Store testnet trades in trades.db
- Mix testnet and production data
```

---

## Specifications

### Domain Models

#### TradingMode Enum

```python
class TradingMode(StrEnum):
    """거래 모드 열거형"""
    PRODUCTION = "production"
    TESTNET = "testnet"
```

#### MockBalance

```python
@dataclass
class MockBalance:
    """Testnet용 가상 잔액 관리"""
    krw_balance: float = 10_000_000.0
    coin_balances: dict[str, float] = field(default_factory=dict)
    avg_buy_prices: dict[str, float] = field(default_factory=dict)
```

#### TestnetConfig

```python
class TestnetConfig(BaseModel):
    """테스트넷 환경 설정"""
    initial_krw_balance: float = 10_000_000.0
    simulated_fee_rate: float = 0.0005
    db_path: str = "testnet_trades.db"
```

### Service Interface

#### MockUpbitClient

```python
class MockUpbitClient:
    """
    Upbit API Mock 클라이언트 for Testnet.
    실제 UpbitClient와 동일한 인터페이스를 제공하며,
    모든 작업을 메모리 내에서 시뮬레이션합니다.

    @MX:NOTE: This client simulates all Upbit API operations.
        No real HTTP requests are made.
    """

    async def get_balances(self) -> list[Balance]
    async def buy_market_order(ticker: str, amount: float) -> Order
    async def sell_market_order(ticker: str, volume: float) -> Order
    async def get_orderbook(ticker: str) -> Orderbook
    async def get_current_price(ticker: str) -> float
```

### DI Container Modification

```python
class Container(containers.DeclarativeContainer):
    # Mode selector
    trading_mode: providers.Provider[TradingMode] = providers.Singleton(
        lambda: TradingMode.PRODUCTION
    )

    # Mock client for testnet
    mock_upbit_client: providers.Provider[MockUpbitClient] = providers.Factory(
        MockUpbitClient,
        config=testnet_config,
    )

    def get_upbit_client(self) -> UpbitClient | MockUpbitClient:
        """Get appropriate client based on mode."""
        if self.trading_mode() == TradingMode.TESTNET:
            return self.mock_upbit_client()
        return self.upbit_client()
```

---

## MX Tag Targets

### High Fan-In Functions

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `MockUpbitClient.buy_market_order` | 2+ | @MX:ANCHOR | mock_upbit_client.py |
| `MockUpbitClient.sell_market_order` | 2+ | @MX:ANCHOR | mock_upbit_client.py |
| `Container.get_upbit_client` | 3+ | @MX:ANCHOR | container.py |

### Danger Zones

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| Mode 전환 | Confusion | @MX:WARN | Production/Testnet 전환 시 명확한 표시 필요 |
| Testnet DB | Data mixing | @MX:WARN | Testnet/Production DB 분리 필수 |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/trading_mode.py` | TradingMode enum | ~20 |
| `src/gpt_bitcoin/infrastructure/external/mock_upbit_client.py` | MockUpbitClient | ~300 |
| `src/gpt_bitcoin/domain/testnet_config.py` | TestnetConfig, MockBalance | ~80 |
| `tests/unit/infrastructure/test_mock_upbit_client.py` | Unit tests | ~400 |

### Modified Files

| File Path | Changes | Impact |
|-----------|---------|--------|
| `src/gpt_bitcoin/dependencies/container.py` | Testnet support | High |
| `src/gpt_bitcoin/config/settings.py` | testnet_mode setting | Medium |
| `web_ui.py` | Testnet banner, mode switcher | High |
| `main.py` | --testnet flag | Medium |

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-TEST-001 | MockUpbitClient | test_testnet_simulation |
| REQ-TEST-002 | web_ui.py | test_testnet_banner_display |
| REQ-TEST-010 | container.py | test_mode_switching |
| REQ-TEST-011 | MockUpbitClient | test_virtual_balance_update |
| REQ-TEST-020 | web_ui.py | test_add_virtual_balance |
| REQ-TEST-030 | test_mock_upbit_client.py | test_no_real_api_calls |

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService foundation (dependency)
- **SPEC-TRADING-002**: Trading History (DB separation)
- **SPEC-TRADING-003**: CLI Integration (--testnet flag)

---

Version: 1.0.0
Last Updated: 2026-03-04
