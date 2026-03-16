# SPEC-TRADING-005: Research Findings

## Codebase Analysis

### Current Implementation

**DI Container** (src/gpt_bitcoin/dependencies/container.py):
```python
# Current - single UpbitClient
upbit_client: providers.Provider[UpbitClient] = providers.Factory(
    UpbitClient,
    settings=settings,
)

# Need - mode-aware client selection
```

**Settings** (src/gpt_bitcoin/config/settings.py):
- No testnet_mode flag currently
- No testnet configuration section

### Upbit Testnet API Status

**Finding**: Upbit does NOT provide official testnet/sandbox API

**Options**:
1. **Mock Client** (CHOSEN): Simulate API responses locally
2. **Demo Account**: Use real API with small amounts (not recommended)
3. **Third-party testnet**: No known reliable options

### Reference Implementations

**Mock Pattern** (from testing best practices):
```python
class MockUpbitClient(UpbitClient):
    """Mock implementation preserving interface."""
    def __init__(self, config: TestnetConfig):
        self._balance = MockBalance(initial_balance=config.initial_krw_balance)
        self._orders: list[Order] = []

    async def buy_market_order(self, ticker: str, amount: float) -> Order:
        # Simulate order execution
        price = await self._get_simulated_price(ticker)
        quantity = amount / price
        fee = amount * 0.0005

        # Update virtual balance
        self._balance.krw_balance -= (amount + fee)
        self._balance.coin_balances[ticker] += quantity

        return Order(
            uuid=f"mock-{uuid.uuid4()}",
            price=price,
            executed_volume=quantity,
            fee=fee,
        )
```

### Integration Strategy

**DI Container Pattern**:
```python
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Mode provider
    trading_mode: providers.Provider[TradingMode] = providers.Singleton(
        lambda: TradingMode.PRODUCTION
    )

    # Real client
    upbit_client: providers.Provider[UpbitClient] = providers.Factory(
        UpbitClient,
        settings=settings,
    )

    # Mock client
    mock_upbit_client: providers.Provider[MockUpbitClient] = providers.Factory(
        MockUpbitClient,
        config=testnet_config,
    )

    # Mode-aware selector
    @property
    def active_client(self) -> UpbitClient | MockUpbitClient:
        if self.trading_mode() == TradingMode.TESTNET:
            return self.mock_upbit_client()
        return self.upbit_client()
```

### Database Strategy

**Separate Files**:
- Production: `trades.db`
- Testnet: `testnet_trades.db`

**Migration**:
```python
# In TradeHistoryService
def get_db_path(mode: TradingMode) -> str:
    if mode == TradingMode.TESTNET:
        return "testnet_trades.db"
    return "trades.db"
```

### UI/UX Considerations

**Visual Differentiation**:
- Testnet: Yellow/Red warning banner
- Production: Normal theme

**Clear Messaging**:
- Testnet: "⚠️ TESTNET MODE - 시뮬레이션 환경입니다"
- Production: Standard headers

---

Version: 1.0.0
Last Updated: 2026-03-04
