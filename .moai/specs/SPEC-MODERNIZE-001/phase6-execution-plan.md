# Phase 6 Execution Plan: Multi-Coin/Strategy Extension

**SPEC**: SPEC-MODERNIZE-001
**Phase**: 6 - Multi-Coin/Strategy Extension
**Duration**: 7 days
**Status**: Ready to Start
**Created**: 2026-03-03

---

## Overview

Extend the single-coin (BTC) trading system to support multiple cryptocurrencies (BTC, ETH, SOL, XRP, ADA) with multiple trading strategies (conservative, balanced, aggressive, vision_aggressive).

---

## Architecture Design

### Domain Model

```python
# src/gpt_bitcoin/domain/models/cryptocurrency.py
from enum import Enum

class Cryptocurrency(str, Enum):
    """Supported cryptocurrencies for trading."""
    BTC = "BTC"  # Bitcoin
    ETH = "ETH"  # Ethereum
    SOL = "SOL"  # Solana
    XRP = "XRP"  # Ripple
    ADA = "ADA"  # Cardano

    @property
    def upbit_ticker(self) -> str:
        """Get Upbit ticker symbol."""
        return f"{self.value}-KRW"

    @property
    def display_name(self) -> str:
        """Get display name in Korean."""
        names = {
            "BTC": "비트코인",
            "ETH": "이더리움",
            "SOL": "솔라나",
            "XRP": "리플",
            "ADA": "에이다"
        }
        return names[self.value]

class TradingStrategy(str, Enum):
    """Available trading strategies."""
    CONSERVATIVE = "conservative"      # New: Low risk, steady growth
    BALANCED = "balanced"              # v1 based
    AGGRESSIVE = "aggressive"          # v2 based (fear/greed)
    VISION_AGGRESSIVE = "vision_aggressive"  # v3 based (vision + ROI)

    @property
    def instruction_file(self) -> str:
        """Get instruction file path."""
        return f"instructions/current/{self.value}.md"

    @property
    def display_name(self) -> str:
        """Get display name in Korean."""
        names = {
            "conservative": "보수적",
            "balanced": "균형적",
            "aggressive": "공격적",
            "vision_aggressive": "비전 공격적"
        }
        return names[self.value]

@dataclass
class CoinPreference:
    """User preference for a specific coin."""
    coin: Cryptocurrency
    enabled: bool
    percentage: float  # Portfolio allocation (0-100)
    strategy: TradingStrategy

@dataclass
class UserPreferences:
    """User trading preferences."""
    default_strategy: TradingStrategy
    coins: list[CoinPreference]
    auto_trade: bool
    daily_trading_limit_krw: float
```

### File Structure

```
instructions/
├── base.md                    # Common base template
├── current/
│   ├── conservative.md        # New: Low risk strategy
│   ├── balanced.md           # v1 based
│   ├── aggressive.md         # v2 based (fear/greed)
│   └── vision_aggressive.md   # v3 based (vision + ROI)
└── coin_specific/
    ├── BTC/
    │   ├── conservative.md
    │   ├── balanced.md
    │   ├── aggressive.md
    │   └── vision_aggressive.md
    ├── ETH/
    │   └── ... (same structure)
    ├── SOL/
    │   └── ...
    ├── XRP/
    │   └── ...
    └── ADA/
        └── ...
```

### Database Schema

```sql
-- User preferences table
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    default_strategy TEXT NOT NULL,  -- TradingStrategy enum value
    auto_trade BOOLEAN DEFAULT FALSE,
    daily_trading_limit_krw REAL DEFAULT 100000.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Coin preferences table
CREATE TABLE coin_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,  -- Cryptocurrency enum value
    enabled BOOLEAN DEFAULT TRUE,
    percentage REAL DEFAULT 20.0,  -- Portfolio allocation
    strategy TEXT NOT NULL,  -- TradingStrategy enum value
    UNIQUE(coin)
);

-- Portfolio tracking table
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,
    balance REAL DEFAULT 0.0,
    avg_buy_price REAL DEFAULT 0.0,
    current_price_krw REAL DEFAULT 0.0,
    value_krw REAL DEFAULT 0.0,
    profit_loss_krw REAL DEFAULT 0.0,
    profit_loss_percentage REAL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coin)
);
```

---

## Implementation Phases

### Phase 6.1: Domain Models & Enums (Day 1)

**Tasks:**
1. Create `Cryptocurrency` enum with 5 coins
2. Create `TradingStrategy` enum with 4 strategies
3. Create `CoinPreference` and `UserPreferences` dataclasses
4. Add Pydantic validation for percentage limits
5. Write unit tests for enums and models

**Files:**
- `src/gpt_bitcoin/domain/models/cryptocurrency.py`
- `src/gpt_bitcoin/domain/models/user_preferences.py`
- `tests/unit/domain/test_cryptocurrency.py`
- `tests/unit/domain/test_user_preferences.py`

**Acceptance Criteria:**
- All enums have proper string values
- Display names work correctly in Korean
- Portfolio allocation validates to 100% total
- 85%+ test coverage

---

### Phase 6.2: User Preferences Repository (Day 1-2)

**Tasks:**
1. Create SQLite schema for user preferences
2. Implement `UserPreferencesRepository` with CRUD operations
3. Add migration scripts for existing single-coin setup
4. Implement preference caching with TTL
5. Write integration tests for database operations

**Files:**
- `src/gpt_bitcoin/infrastructure/database/preferences_repository.py`
- `src/gpt_bitcoin/infrastructure/database/migrations/001_add_preferences.sql`
- `tests/integration/database/test_preferences_repository.py`

**API Design:**
```python
class UserPreferencesRepository(ABC):
    @abstractmethod
    async def get_preferences(self) -> UserPreferences:
        """Get current user preferences."""

    @abstractmethod
    async def update_preferences(self, prefs: UserPreferences) -> None:
        """Update user preferences."""

    @abstractmethod
    async def add_coin(self, coin: CoinPreference) -> None:
        """Add a coin to user preferences."""

    @abstractmethod
    async def remove_coin(self, coin: Cryptocurrency) -> None:
        """Remove a coin from user preferences."""

    @abstractmethod
    async def update_coin_strategy(
        self,
        coin: Cryptocurrency,
        strategy: TradingStrategy
    ) -> None:
        """Update strategy for a specific coin."""
```

**Acceptance Criteria:**
- CRUD operations work correctly
- Portfolio allocation validates to 100%
- Migration from single-coin works
- 85%+ test coverage

---

### Phase 6.3: Strategy Manager (Day 2-3)

**Tasks:**
1. Create `StrategyManager` for instruction file loading
2. Implement instruction template system with base template
3. Add strategy-specific instruction overrides
4. Create coin-specific instruction support
5. Implement instruction caching with file watcher
6. Write unit tests for strategy loading

**Files:**
- `src/gpt_bitcoin/application/strategy_manager.py`
- `instructions/base.md`
- `instructions/current/conservative.md`
- `instructions/current/balanced.md`
- `instructions/current/aggressive.md`
- `instructions/current/vision_aggressive.md`
- `tests/unit/application/test_strategy_manager.py`

**API Design:**
```python
class StrategyManager:
    async def get_instruction(
        self,
        coin: Cryptocurrency,
        strategy: TradingStrategy
    ) -> str:
        """
        Get instruction text for coin+strategy combination.

        Priority:
        1. coin_specific/{coin}/{strategy}.md
        2. current/{strategy}.md
        3. base.md (fallback)
        """

    async def reload_instructions(self) -> None:
        """Reload all instruction files (cache invalidation)."""

    async def list_available_strategies(
        self,
        coin: Cryptocurrency
    ) -> list[TradingStrategy]:
        """List strategies available for a specific coin."""
```

**Acceptance Criteria:**
- Instruction loading follows priority chain
- File watcher detects changes and reloads
- Coin-specific instructions override base
- 85%+ test coverage

---

### Phase 6.4: Coin Manager (Day 3-4)

**Tasks:**
1. Create `CoinManager` for multi-coin data collection
2. Implement parallel data fetching for all enabled coins
3. Add coin-specific market data normalization
4. Implement portfolio aggregation logic
5. Add coin-specific error handling
6. Write integration tests for multi-coin scenarios

**Files:**
- `src/gpt_bitcoin/application/coin_manager.py`
- `tests/integration/application/test_coin_manager.py`

**API Design:**
```python
class CoinManager:
    async def fetch_market_data(
        self,
        coins: list[Cryptocurrency]
    ) -> dict[Cryptocurrency, MarketData]:
        """
        Fetch market data for multiple coins in parallel.

        Returns dict with coin as key, market data as value.
        Skips failed coins but continues with others.
        """

    async def get_portfolio_status(
        self,
        coins: list[Cryptocurrency]
    ) -> PortfolioStatus:
        """
        Get aggregated portfolio status across all coins.

        Returns:
        - Total value KRW
        - Total profit/loss KRW
        - Coin-wise breakdown
        - Asset allocation percentages
        """

    async def update_portfolio_values(
        self,
        coins: list[Cryptocurrency]
    ) -> None:
        """Update portfolio values for all coins."""
```

**Acceptance Criteria:**
- Parallel fetching works without blocking
- Failed coins don't affect others
- Portfolio aggregation is accurate
- 85%+ test coverage

---

### Phase 6.5: Instruction File Migration (Day 4-5)

**Tasks:**
1. Migrate existing instructions.md → balanced.md
2. Migrate instructions_v2.md → aggressive.md
3. Migrate instructions_v3.md → vision_aggressive.md
4. Create new conservative.md strategy
5. Create coin-specific instruction templates
6. Add instruction validation tests

**Files:**
- `instructions/current/conservative.md` (new)
- `instructions/current/balanced.md` (migrated)
- `instructions/current/aggressive.md` (migrated)
- `instructions/current/vision_aggressive.md` (migrated)
- `instructions/base.md` (new)
- `tests/instructions/test_instruction_migration.py`

**Migration Strategy:**
```python
# Migration script
async def migrate_to_v6():
    """Migrate from v3 single-coin to v6 multi-coin."""

    # 1. Backup existing instructions
    # 2. Create new directory structure
    # 3. Migrate files with transformations
    # 4. Create default user preferences
    # 5. Update database schema
    # 6. Verify migration success
```

**Acceptance Criteria:**
- All v3 instructions preserved in v6 format
- Conservative strategy created
- Base template extracted
- Migration script idempotent
- 85%+ test coverage

---

### Phase 6.6: Streamlit UI (Day 5-6)

**Tasks:**
1. Create coin selection UI (multi-select)
2. Create strategy selection UI (per-coin dropdowns)
3. Add portfolio allocation slider
4. Implement real-time portfolio display
5. Add preferences save/load buttons
6. Create trading controls (start/stop)
7. Write UI integration tests

**Files:**
- `src/gpt_bitcoin/presentation/streamlit_ui.py`
- `tests/integration/presentation/test_streamlit_ui.py`

**UI Design:**
```
┌─────────────────────────────────────────────────┐
│  GPT Bitcoin Auto-Trading System v6.0          │
├─────────────────────────────────────────────────┤
│                                                 │
│  Portfolio Allocation                           │
│  ┌─────────────────────────────────────────┐   │
│  │ ☑ BTC  [20%] [Strategy: Balanced ▼]   │   │
│  │ ☑ ETH  [20%] [Strategy: Aggressive ▼] │   │
│  │ ☑ SOL  [20%] [Strategy: Conservative ▼]│   │
│  │ ☐ XRP  [20%] [Strategy: Balanced ▼]   │   │
│  │ ☐ ADA  [20%] [Strategy: Aggressive ▼] │   │
│  │                                       │   │
│  │ Total: 60% allocated                  │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Portfolio Status                               │
│  ┌─────────────────────────────────────────┐   │
│  │ Total Value:  ₩1,500,000               │   │
│  │ Total P/L:     +₩50,000 (+3.4%)        │   │
│  │                                         │   │
│  │ BTC:  ₩600,000 (0.01 BTC)  +₩20,000   │   │
│  │ ETH:  ₩600,000 (0.2 ETH)   +₩30,000   │   │
│  │ SOL:  ₩300,000 (1.5 SOL)   -₩10,000   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Trading Controls                               │
│  ┌─────────────────────────────────────────┐   │
│  │ Default Strategy: [Balanced ▼]         │   │
│  │ Auto-Trade: [☑ Enabled]                │   │
│  │ Daily Limit: ₩100,000                  │   │
│  │                                         │   │
│  │ [Save Settings]  [Start Trading]       │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- UI renders without errors
- Portfolio allocation validates to 100%
- Real-time updates work
- Save/load preferences works
- 85%+ test coverage

---

### Phase 6.7: Integration & Testing (Day 6-7)

**Tasks:**
1. End-to-end testing for multi-coin scenarios
2. Load testing with 5 coins simultaneously
3. Error injection testing (API failures)
4. Performance testing (async overhead)
5. User acceptance testing scenarios
6. Documentation updates

**Test Scenarios:**
```python
# Scenario 1: Multi-coin data collection
async def test_multi_coin_data_collection():
    """Verify all 5 coins can be fetched in parallel."""
    coins = [c for c in Cryptocurrency]
    manager = CoinManager()
    data = await manager.fetch_market_data(coins)
    assert len(data) == 5
    assert all(d.timestamp > 0 for d in data.values())

# Scenario 2: Strategy switching
async def test_strategy_switching():
    """Verify strategy switches correctly."""
    manager = StrategyManager()
    btc_balanced = await manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.BALANCED
    )
    btc_aggressive = await manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.AGGRESSIVE
    )
    assert btc_balanced != btc_aggressive

# Scenario 3: Portfolio allocation
async def test_portfolio_allocation():
    """Verify portfolio allocation validates correctly."""
    prefs = UserPreferences(
        default_strategy=TradingStrategy.BALANCED,
        coins=[
            CoinPreference(
                coin=Cryptocurrency.BTC,
                enabled=True,
                percentage=20.0,
                strategy=TradingStrategy.BALANCED
            ),
            CoinPreference(
                coin=Cryptocurrency.ETH,
                enabled=True,
                percentage=30.0,
                strategy=TradingStrategy.AGGRESSIVE
            ),
            CoinPreference(
                coin=Cryptocurrency.SOL,
                enabled=True,
                percentage=50.0,
                strategy=TradingStrategy.CONSERVATIVE
            )
        ],
        auto_trade=True,
        daily_trading_limit_krw=100000.0
    )
    total = sum(c.percentage for c in prefs.coins)
    assert total == 100.0
```

**Acceptance Criteria:**
- All integration tests pass
- 85%+ overall test coverage
- Load test handles 5 coins without timeout
- Error recovery works correctly
- Documentation complete

---

## Migration Path

### From Single-Coin (v5) to Multi-Coin (v6)

**Pre-Migration:**
1. Backup existing database
2. Export current settings
3. Note current strategy (v1/v2/v3)

**Migration Steps:**
1. Run migration script: `python -m gpt_bitcoin.migrations.migrate_to_v6`
2. Verify new directory structure created
3. Confirm instruction files migrated
4. Check default preferences created
5. Test with single coin (BTC) first

**Post-Migration:**
1. Verify BTC trading still works
2. Add second coin (ETH) for testing
3. Verify portfolio aggregation
4. Test strategy switching
5. Full multi-coin test

**Rollback Plan:**
- Keep v5 backup in `backup/v5/`
- Database rollback script: `migrations/rollback_to_v5.sql`
- Restore instructions from backup

---

## File Structure Summary

```
src/gpt_bitcoin/
├── domain/
│   └── models/
│       ├── cryptocurrency.py      (NEW)
│       └── user_preferences.py    (NEW)
├── application/
│   ├── strategy_manager.py        (NEW)
│   ├── coin_manager.py            (NEW)
│   └── cost_optimization.py       (existing)
├── infrastructure/
│   ├── database/
│   │   ├── preferences_repository.py  (NEW)
│   │   └── migrations/
│   │       ├── 001_add_preferences.sql   (NEW)
│   │       └── migrate_to_v6.py          (NEW)
│   └── external/
│       └── upbit_client.py         (modify for multi-coin)
├── presentation/
│   ├── streamlit_ui.py             (NEW)
│   └── alert_handlers.py           (existing)
└── migrations/
    └── migrate_to_v6.py            (NEW)

instructions/
├── base.md                         (NEW)
├── current/
│   ├── conservative.md             (NEW)
│   ├── balanced.md                 (migrated from v1)
│   ├── aggressive.md               (migrated from v2)
│   └── vision_aggressive.md        (migrated from v3)
└── coin_specific/
    ├── BTC/
    │   ├── conservative.md         (NEW)
    │   ├── balanced.md             (NEW)
    │   ├── aggressive.md           (NEW)
    │   └── vision_aggressive.md    (NEW)
    ├── ETH/                        (NEW)
    ├── SOL/                        (NEW)
    ├── XRP/                        (NEW)
    └── ADA/                        (NEW)

tests/
├── unit/
│   ├── domain/
│   │   ├── test_cryptocurrency.py  (NEW)
│   │   └── test_user_preferences.py (NEW)
│   ├── application/
│   │   ├── test_strategy_manager.py (NEW)
│   │   ├── test_coin_manager.py     (NEW)
│   │   └── test_cost_optimization.py (existing)
│   └── infrastructure/
│       └── database/
│           └── test_preferences_repository.py (NEW)
├── integration/
│   ├── application/
│   │   └── test_coin_manager.py    (NEW)
│   └── presentation/
│       └── test_streamlit_ui.py    (NEW)
└── instructions/
    └── test_instruction_migration.py (NEW)
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Supported coins | 5 | BTC, ETH, SOL, XRP, ADA |
| Supported strategies | 4 | conservative, balanced, aggressive, vision_aggressive |
| Test coverage | 85%+ | pytest --cov |
| Portfolio allocation accuracy | 100% | Sum equals 100% |
| Parallel fetch time | <2s | All 5 coins data |
| Strategy switching time | <100ms | File load + cache |
| Migration成功率 | 100% | v5 → v6 without data loss |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Upbit API rate limits | Medium | High | Implement request queuing, stagger parallel requests |
| Portfolio allocation errors | Low | High | Validation at save time, UI constraints |
| Instruction file conflicts | Low | Medium | Clear priority chain, coin-specific override |
| Migration data loss | Very Low | Critical | Backup before migration, rollback script |
| UI complexity | Medium | Medium | Progressive enhancement, user testing |

---

## Dependencies

**New Dependencies:**
- None required (use existing pydantic, aiosqlite)

**Existing Dependencies to Leverage:**
- pydantic: For UserPreferences validation
- aiosqlite: For preferences repository
- structlog: For logging multi-coin operations
- pytest: For testing
- streamlit: For UI (already in dev dependencies)

---

## Next Steps

1. Review and approve this plan
2. Create Phase 6.1 tasks (Cryptocurrency enum)
3. Begin implementation starting with domain models
4. Daily progress tracking against plan
5. Adjust timeline based on actual progress

---

**Document History:**
- 2026-03-03: Initial plan created (MoAI Orchestrator)
