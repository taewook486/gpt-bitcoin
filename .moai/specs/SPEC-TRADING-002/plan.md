# Implementation Plan: SPEC-TRADING-002 (Trading History)

## Overview

이 문서는 SPEC-TRADING-002 거래 내역 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Foundation (Primary Goal)

**Objective**: 데이터베이스 기본 구조 및 핵심 저장 기능 구현

#### Tasks

1. **Database Infrastructure**
   - Priority: Critical
   - Create `infrastructure/persistence/` package structure
   - Implement `database.py` with SQLite connection management
   - Create database schema (trades table)
   - Add indexes for performance

2. **TradeRecord Model**
   - Priority: Critical
   - Define `TradeRecord` dataclass in `domain/trade_history.py`
   - Map to database schema
   - Add validation with Pydantic

3. **TradeRepository**
   - Priority: High
   - Implement CRUD operations (Create, Read only - no Update/Delete)
   - Implement filter-based queries
   - Handle duplicate detection (UNIQUE constraint)

4. **TradeHistoryService**
   - Priority: High
   - Implement `save_trade_result()` method
   - Implement `get_trades()` with filters
   - Implement `get_trade_count()` for pagination

5. **DI Container Integration**
   - Priority: High
   - Register TradeHistoryService in `dependencies/container.py`
   - Add `db_history_path` to Settings

6. **Unit Tests - Core**
   - Priority: High
   - Test TradeRecord creation and validation
   - Test TradeRepository insert and query
   - Test TradeHistoryService save and retrieve

**Deliverables**:
- Working persistence layer
- All core tests passing
- Database file created with correct schema

---

### Phase 2: Web UI Integration (Secondary Goal)

**Objective**: Web UI에 거래 내역 탭 추가 및 데이터 표시

#### Tasks

1. **Trade History Tab**
   - Priority: High
   - Add new tab to Streamlit UI
   - Create filter controls (coin, side, date range)
   - Display trades in DataFrame

2. **Pagination**
   - Priority: Medium
   - Implement page navigation
   - Configure 50 rows per page
   - Add page info display

3. **Empty State Handling**
   - Priority: Medium
   - Display "거래 내역이 없습니다" when no records
   - Handle loading states

4. **Integration Tests**
   - Priority: Medium
   - Test UI renders correctly
   - Test filter interactions
   - Test pagination

**Deliverables**:
- Web UI with Trade History tab
- Filtering and pagination working
- User-friendly empty states

---

### Phase 3: Export and Analysis (Final Goal)

**Objective**: CSV 내보내기 및 수익/손실 계산 기능

#### Tasks

1. **CSV Export**
   - Priority: Medium
   - Implement `export_to_csv()` in TradeHistoryService
   - Add bilingual headers (Korean/English)
   - Generate filename with timestamp
   - Add export button to UI

2. **Profit/Loss Calculation**
   - Priority: Low
   - Implement FIFO matching algorithm
   - Calculate realized P/L
   - Track unrealized quantity
   - Display P/L summary in UI

3. **CSV Export Tests**
   - Priority: Medium
   - Test export format
   - Test special characters handling
   - Test large dataset export

4. **P/L Calculation Tests**
   - Priority: Low
   - Test FIFO matching
   - Test edge cases (no sells, partial sells)
   - Test fee accounting

**Deliverables**:
- CSV export functionality
- P/L calculation for closed positions
- Complete test coverage

---

### Phase 4: Integration with SPEC-TRADING-001 (Optional)

**Objective**: TradingService와 자동 연동

#### Tasks

1. **Event-Based Storage**
   - Priority: Low
   - Hook into TradingService.execute_approved_trade()
   - Call TradeHistoryService.save_trade_result() on success
   - Handle storage failures gracefully

2. **Integration Tests**
   - Priority: Low
   - Test end-to-end flow: trade → save → query
   - Test failure scenarios

**Deliverables**:
- Automatic trade history recording
- Graceful error handling

---

## Technical Approach

### Database Strategy

```python
# infrastructure/persistence/database.py

import aiosqlite
from pathlib import Path

class Database:
    """Async SQLite database manager."""

    def __init__(self, db_path: str = "trades.db"):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create tables if not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def get_connection(self) -> aiosqlite.Connection:
        """Get or create connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.db_path)
            # Enable WAL mode for better concurrency
            await self._connection.execute("PRAGMA journal_mode=WAL")
        return self._connection
```

### Repository Pattern

```python
# infrastructure/persistence/trade_repository.py

class TradeRepository:
    """Repository for trade persistence."""

    def __init__(self, db: Database):
        self._db = db

    async def insert(self, record: TradeRecord) -> int:
        """
        Insert trade record.

        @MX:NOTE: Uses INSERT OR IGNORE for duplicate safety.
        """
        query = """
            INSERT OR IGNORE INTO trades
            (order_uuid, ticker, side, executed_price, executed_quantity, fee, total_krw, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        async with await self._db.get_connection() as conn:
            cursor = await conn.execute(query, (
                record.order_uuid,
                record.ticker,
                record.side,
                record.executed_price,
                record.executed_quantity,
                record.fee,
                record.total_krw,
                record.timestamp.isoformat(),
            ))
            await conn.commit()
            return cursor.lastrowid
```

### Service Layer

```python
# domain/trade_history.py

class TradeHistoryService:
    """Trade history management service."""

    def __init__(self, repository: TradeRepository):
        self._repository = repository

    async def save_trade_result(self, result: TradeResult) -> int:
        """
        Save TradeResult to history.

        @MX:ANCHOR: Single entry point for trade persistence.
            fan_in: 2+ (TradingService, CLI)
            @MX:REASON: Centralizes all trade history writes.
        """
        if not result.success or not result.order_id:
            # Don't save failed trades
            return -1

        record = TradeRecord(
            id=0,  # Auto-assigned
            order_uuid=result.order_id,
            ticker=result.ticker,
            side=result.side,
            executed_price=result.executed_price or 0,
            executed_quantity=result.executed_amount or 0,
            fee=result.fee or 0,
            total_krw=(result.executed_price or 0) * (result.executed_amount or 0),
            timestamp=result.timestamp,
        )
        return await self._repository.insert(record)
```

---

## Architecture Design

### Package Structure

```
src/gpt_bitcoin/
├── domain/
│   ├── trading.py              # [EXISTING] TradingService
│   ├── trading_state.py        # [EXISTING] TradingState enum
│   └── trade_history.py        # [NEW] TradeHistoryService
│
├── infrastructure/
│   └── persistence/            # [NEW PACKAGE]
│       ├── __init__.py
│       ├── database.py         # SQLite connection
│       └── trade_repository.py # TradeRecord repository
│
├── config/
│   └── settings.py             # [MODIFY] Add db_history_path
│
├── dependencies/
│   └── container.py            # [MODIFY] Register services
│
└── web_ui.py                   # [MODIFY] Add Trade History tab
```

### Data Flow

```
┌──────────────────┐
│ TradingService   │
│ (SPEC-001)       │
└────────┬─────────┘
         │ TradeResult
         ▼
┌──────────────────┐
│ TradeHistory     │
│ Service          │
└────────┬─────────┘
         │ TradeRecord
         ▼
┌──────────────────┐
│ TradeRepository  │
└────────┬─────────┘
         │ SQL
         ▼
┌──────────────────┐
│ SQLite DB        │
│ (trades.db)      │
└────────┬─────────┘
         │ Query Results
         ▼
┌──────────────────┐
│ Web UI / CLI     │
└──────────────────┘
```

---

## Configuration Changes

### Settings Additions

```python
# config/settings.py additions

class Settings(BaseSettings):
    # ... existing settings ...

    # Trading History Settings
    db_history_path: str = Field(
        default="trades.db",
        description="Path to trading history SQLite database",
    )
    history_page_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Number of records per page in history view",
    )
```

### Container Registration

```python
# dependencies/container.py additions

from gpt_bitcoin.domain.trade_history import TradeHistoryService
from gpt_bitcoin.infrastructure.persistence.database import Database
from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository

class Container(containers.DeclarativeContainer):
    # ... existing providers ...

    # Persistence
    database: providers.Provider[Database] = providers.Singleton(
        Database,
        db_path=settings.provided.db_history_path,
    )

    trade_repository: providers.Provider[TradeRepository] = providers.Factory(
        TradeRepository,
        db=database,
    )

    # Domain Services
    trade_history_service: providers.Provider[TradeHistoryService] = providers.Factory(
        TradeHistoryService,
        repository=trade_repository,
    )
```

---

## Testing Strategy

### Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|-----------------|----------|
| TradeRecord | 100% | Critical |
| TradeRepository | 95% | Critical |
| TradeHistoryService | 90% | High |
| Web UI Integration | 70% | Medium |

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - `domain/test_trade_history.py`: Service logic
   - `infrastructure/test_trade_repository.py`: Repository operations
   - `infrastructure/test_database.py`: Connection management

2. **Integration Tests** (`tests/integration/`)
   - `test_trade_flow.py`: End-to-end trade → save → query

3. **Characterization Tests**
   - None required (new feature)

### Key Test Cases

```python
# tests/unit/domain/test_trade_history.py

class TestTradeHistoryService:
    """Test TradeHistoryService."""

    @pytest.mark.asyncio
    async def test_save_successful_trade(self, service, mock_result):
        """Test saving a successful trade."""
        mock_result.success = True
        mock_result.order_id = "test-uuid"

        record_id = await service.save_trade_result(mock_result)

        assert record_id > 0

    @pytest.mark.asyncio
    async def test_dont_save_failed_trade(self, service, mock_result):
        """Test that failed trades are not saved."""
        mock_result.success = False

        record_id = await service.save_trade_result(mock_result)

        assert record_id == -1

    @pytest.mark.asyncio
    async def test_query_by_ticker(self, service, sample_records):
        """Test filtering by ticker."""
        records = await service.get_trades(ticker="KRW-BTC")

        assert all(r.ticker == "KRW-BTC" for r in records)

    @pytest.mark.asyncio
    async def test_query_date_range(self, service, sample_records):
        """Test filtering by date range."""
        start = datetime(2026, 3, 1)
        end = datetime(2026, 3, 5)

        records = await service.get_trades(start_date=start, end_date=end)

        for r in records:
            assert start <= r.timestamp <= end

    def test_csv_export(self, service, sample_records):
        """Test CSV export format."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            service.export_to_csv(sample_records, f.name)

            df = pd.read_csv(f.name)
            assert len(df) == len(sample_records)
            assert "order_uuid" in df.columns
```

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| aiosqlite | >=0.19.0 | Async SQLite support |
| pandas | >=2.2.0 | CSV export (already in project) |

### Existing Dependencies Used

| Package | Usage |
|---------|-------|
| pydantic | TradeRecord validation |
| pytest + pytest-asyncio | Testing |
| streamlit | UI |

---

## Rollback Plan

### Database Migration

If schema changes are needed:
1. Backup existing `trades.db`
2. Use SQLite `ALTER TABLE` for non-breaking changes
3. For breaking changes, create migration script to copy data

### Feature Toggle

```python
# If issues arise, disable via config
settings:
  enable_trade_history: false  # Disable auto-save
```

---

## Performance Considerations

### Expected Data Volume

- Trades per day: ~10-20 (conservative estimate)
- Annual trades: ~5,000
- Database size: ~2.5 MB/year
- Query time for 1000 records: < 100ms

### Optimization Strategies

1. **Indexes**: Already defined on ticker, timestamp, side
2. **Pagination**: Default 50 rows per page
3. **Connection Pooling**: Single connection with WAL mode
4. **Query Optimization**: Use parameterized queries, avoid SELECT *

---

## Security Considerations

### Data Protection

1. **File Permissions**: Database file readable only by owner
2. **No Encryption**: Initial MVP without encryption (local machine assumption)
3. **Backup**: Recommend users backup `trades.db` file

### Audit Trail

- All trades logged with timestamp
- Immutable records (no UPDATE/DELETE)
- Created_at field tracks record creation

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
