# SPEC-TRADING-002: Trading History Feature

## Metadata

- **SPEC ID**: SPEC-TRADING-002
- **Title**: Trading History Feature (거래 내역 기능)
- **Created**: 2026-03-04
- **Status**: Completed
- **Priority**: Medium
- **Depends On**: SPEC-TRADING-001 (Completed), SPEC-TRADING-003 (CLI Integration)
- **Lifecycle Level**: spec-anchored

---

## Problem Analysis

### Current State

SPEC-TRADING-001에서 TradingService와 TradeResult 모델이 구현되었으나, 거래 실행 결과가 영구적으로 저장되지 않습니다. 모든 TradeResult는 메모리에서 즉시 소멸되어 다음과 같은 문제가 발생합니다:

1. **거래 추적 불가**: 사용자가 자신의 거래 내역을 조회할 수 없음
2. **수익 분석 불가**: 매도 후 수익/손실 계산을 위한 매수 가격 정보 누락
3. **감사 기능 부재**: 거래 이력에 대한 audit trail 부재
4. **규제 준수 문제**: 거래 기록 보관 의무 불이행 가능성

### Root Cause Analysis (Five Whys)

1. **Why?** TradeResult가 저장소에 저장되지 않음
2. **Why?** TradingService에 persistence layer가 없음
3. **Why?** 초기 구현에서 핵심 거래 로직에 집중하여 부가 기능 제외
4. **Why?** SPEC-TRADING-001 범위가 실시간 거래 실행에 한정됨
5. **Root Cause**: 거래 내역 저장 및 조회 요구사항이 별도 SPEC으로 분리 필요

### Desired State

모든 거래 실행 결과가 SQLite 데이터베이스에 저장되며, 사용자는 Web UI와 CLI를 통해 거래 내역을 조회, 필터링, 내보낼 수 있습니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Database | SQLite | 3.45+ | 파일 기반 로컬 DB, 외부 서버 불필요 |
| ORM | SQLAlchemy | 2.0+ | Async 지원, Type-safe 쿼리 |
| Data Export | pandas + csv | 2.2+ | 표준 CSV 형식 지원 |
| UI Integration | Streamlit | 1.30+ | 기존 web_ui.py와 통합 |

### Integration Points

```
SPEC-TRADING-001 (TradingService)
        ↓ TradeResult 발생 시 이벤트
SPEC-TRADING-002 (TradeHistoryService)
        ↓ 저장
    SQLite DB (trades.db)
        ↓ 조회
    Web UI / CLI
```

### Constraints

1. **Performance**: 거래 내역 조회 1초 이내 (최근 1000건 기준)
2. **Storage**: 연간 최대 100,000건 거래 저장 가정 (약 50MB)
3. **Concurrency**: 단일 사용자 로컬 환경 (동시성 제어 단순화)
4. **Backup**: 사용자가 수동으로 DB 파일 백업 가능해야 함

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-HIST-001**: 시스템은 모든 거래 실행 결과를 영구 저장해야 한다 (The system shall persist all trade execution results).

```
The system shall persist all trade execution results to SQLite database
with complete TradeResult data including:
- order_uuid, ticker, side, executed_price, executed_quantity, fee, timestamp
```

**REQ-HIST-002**: 시스템은 거래 내역 조회 시 역순 정렬을 제공해야 한다 (The system shall provide reverse chronological ordering for trade history queries).

```
The system shall return trade history records ordered by timestamp DESC
by default, with most recent trades appearing first.
```

### Event-Driven Requirements

**REQ-HIST-003**: WHEN TradeResult가 생성되면 THEN 시스템은 자동으로 거래 내역을 저장해야 한다.

```
WHEN TradingService.execute_approved_trade() returns TradeResult
THEN TradeHistoryService.save_trade_result() shall be called automatically
    AND the record shall include all TradeResult fields
    AND storage failure shall not block the original trade execution
```

**REQ-HIST-004**: WHEN 사용자가 거래 내역 탭을 선택하면 THEN 시스템은 저장된 거래 목록을 표시해야 한다.

```
WHEN user navigates to "거래 내역 (Trade History)" tab in Web UI
THEN the system shall query trades from database
    AND display in tabular format with pagination (50 rows per page)
    AND support filtering by date range, ticker, and side
```

### State-Driven Requirements

**REQ-HIST-005**: IF 데이터베이스 연결에 실패하면 THEN 시스템은 거래 실행을 차단하지 않고 로그에 기록해야 한다.

```
IF database connection fails during save_trade_result()
THEN the system shall log the error with ERROR level
    AND continue normal operation without blocking trade execution
    AND retry storage on next successful connection
```

**REQ-HIST-006**: IF 조회 조건에 결과가 없으면 THEN 시스템은 빈 결과를 반환해야 한다.

```
IF query parameters match no records
THEN the system shall return empty list []
    AND display "거래 내역이 없습니다" message in UI
```

### Optional Requirements

**REQ-HIST-007**: Where possible, 시스템은 CSV 내보내기 기능을 제공해야 한다.

```
Where possible, the system shall provide CSV export functionality:
- Export filtered results or all records
- Include headers in Korean/English bilingual format
- Filename format: trading_history_YYYYMMDD_HHMMSS.csv
```

**REQ-HIST-008**: Where possible, 시스템은 수익/손실 계산 기능을 제공해야 한다.

```
Where possible, the system shall calculate profit/loss for closed positions:
- Match buy orders with corresponding sell orders (FIFO)
- Calculate: (sell_price - buy_price) * quantity - total_fees
- Display P/L per trade and total P/L summary
```

### Unwanted Behavior Requirements

**REQ-HIST-009**: 시스템은 거래 내역을 수정하거나 삭제해서는 안 된다 (The system shall not modify or delete trade history records).

```
The system shall NOT allow:
- UPDATE operations on existing trade records
- DELETE operations on trade records
- Alteration of any historical data

Exception: Administrative database maintenance with explicit user consent
```

**REQ-HIST-010**: 시스템은 중복 거래 기록을 생성해서는 안 된다 (The system shall not create duplicate trade records).

```
The system shall NOT create duplicate records:
- Check order_uuid uniqueness before insert
- Use INSERT OR IGNORE or UNIQUE constraint
- Log warning if duplicate insert attempted
```

---

## Specifications

### Data Model

#### TradeRecord Schema

```python
@dataclass
class TradeRecord:
    """Stored trade execution record."""
    id: int  # Auto-increment primary key
    order_uuid: str  # Unique Upbit order ID
    ticker: str  # Market ticker (e.g., "KRW-BTC")
    side: Literal["buy", "sell"]  # Trade side
    executed_price: float  # Actual execution price
    executed_quantity: float  # Actual quantity traded
    fee: float  # Trading fee charged
    total_krw: float  # Total KRW value (price * quantity)
    timestamp: datetime  # Execution timestamp
    created_at: datetime  # Record creation timestamp
```

#### SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_uuid TEXT UNIQUE NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    executed_price REAL NOT NULL,
    executed_quantity REAL NOT NULL,
    fee REAL NOT NULL DEFAULT 0.0,
    total_krw REAL NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_side ON trades(side);
```

### Component Architecture

```
src/gpt_bitcoin/
├── domain/
│   ├── trading.py (existing - SPEC-TRADING-001)
│   └── trade_history.py (NEW)
│       ├── TradeRecord (dataclass)
│       └── TradeHistoryService
├── infrastructure/
│   └── persistence/
│       ├── __init__.py (NEW)
│       ├── database.py (NEW)
│       └── trade_repository.py (NEW)
└── web_ui.py (MODIFY - add Trade History tab)
```

### Class Design

#### TradeHistoryService

```python
class TradeHistoryService:
    """
    Domain service for trade history management.

    Responsibilities:
    - Save trade execution results
    - Query trade history with filters
    - Calculate profit/loss for closed positions
    - Export trade history to CSV

    @MX:NOTE: Uses SQLite for local persistence.
        Thread-safe through async database operations.
    """

    def __init__(self, db_path: str = "trades.db"):
        """Initialize with database path."""
        pass

    async def save_trade_result(self, result: TradeResult) -> int:
        """
        Save a trade result to history.

        Returns:
            int: Record ID

        @MX:ANCHOR: Single entry point for all trade persistence.
            fan_in: 2 (TradingService, CLI manual entry)
            @MX:REASON: Centralizes all trade history writes.
        """
        pass

    async def get_trades(
        self,
        ticker: str | None = None,
        side: Literal["buy", "sell"] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TradeRecord]:
        """
        Query trade history with filters.

        Returns:
            list[TradeRecord]: Matching records, newest first
        """
        pass

    async def get_trade_count(
        self,
        ticker: str | None = None,
        side: Literal["buy", "sell"] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Get total count of matching records."""
        pass

    async def calculate_profit_loss(
        self,
        ticker: str,
    ) -> dict:
        """
        Calculate profit/loss for a specific ticker.

        Uses FIFO (First In First Out) matching.

        Returns:
            dict: {
                "ticker": str,
                "total_buy_krw": float,
                "total_sell_krw": float,
                "total_fees": float,
                "realized_pl": float,
                "unrealized_quantity": float,
            }
        """
        pass

    def export_to_csv(
        self,
        records: list[TradeRecord],
        filepath: str,
    ) -> None:
        """Export trade records to CSV file."""
        pass
```

#### TradeRepository

```python
class TradeRepository:
    """
    Repository for trade record persistence.

    @MX:NOTE: Implements Repository pattern for clean separation.
    """

    async def insert(self, record: TradeRecord) -> int:
        """Insert a new trade record."""
        pass

    async def find_by_uuid(self, order_uuid: str) -> TradeRecord | None:
        """Find trade by order UUID."""
        pass

    async def find_with_filters(
        self,
        filters: dict,
        limit: int,
        offset: int,
    ) -> list[TradeRecord]:
        """Query with dynamic filters."""
        pass

    async def count_with_filters(self, filters: dict) -> int:
        """Count with dynamic filters."""
        pass
```

### UI Design (Web UI)

#### Trade History Tab Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 거래 내역 (Trade History)                                    │
├─────────────────────────────────────────────────────────────────┤
│ Filters:                                                        │
│ [코인: 전체 ▼] [구분: 전체 ▼] [시작일: □] [종료일: □] [조회]  │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────┬──────────┬──────┬────────┬────────┬─────────┬────────┐ │
│ │ 번호│ 일시      │ 코인 │ 구분   │ 수량    │ 체결가   │ 수수료 │ │
│ ├─────┼──────────┼──────┼────────┼────────┼─────────┼────────┤ │
│ │ 1   │ 03/04    │ BTC  │ 매수   │ 0.0002 │ 50,000K │ 5 KRW  │ │
│ │ 2   │ 03/03    │ BTC  │ 매도   │ 0.0001 │ 51,000K │ 2.5 KRW│ │
│ │ ... │ ...      │ ...  │ ...    │ ...    │ ...     │ ...    │ │
│ └─────┴──────────┴──────┴────────┴────────┴─────────┴────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ [이전] 1 / 10 [다음]                    [CSV 내보내기] [P/L 계산]│
└─────────────────────────────────────────────────────────────────┘
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `TradeHistoryService.save_trade_result()` | 2+ | @MX:ANCHOR | domain/trade_history.py |
| `TradeRepository.find_with_filters()` | 2+ | @MX:ANCHOR | infrastructure/persistence/trade_repository.py |
| `get_db_connection()` | 3+ | @MX:ANCHOR | infrastructure/persistence/database.py |

### Danger Zones (Complexity >= 15 or Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `calculate_profit_loss()` | Algorithm complexity | @MX:WARN | FIFO matching logic, division by zero risk |
| Database migrations | Data integrity | @MX:WARN | Schema changes require backup |
| CSV export | Data exposure | @MX:NOTE | File may contain sensitive trading data |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/trade_history.py` | TradeHistoryService, TradeRecord | ~200 |
| `src/gpt_bitcoin/infrastructure/persistence/__init__.py` | Package init | ~10 |
| `src/gpt_bitcoin/infrastructure/persistence/database.py` | SQLite connection management | ~80 |
| `src/gpt_bitcoin/infrastructure/persistence/trade_repository.py` | TradeRepository implementation | ~150 |
| `tests/unit/domain/test_trade_history.py` | Unit tests | ~400 |
| `tests/unit/infrastructure/test_trade_repository.py` | Repository tests | ~250 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `src/gpt_bitcoin/web_ui.py` | Add Trade History tab | +150 |
| `src/gpt_bitcoin/dependencies/container.py` | Register TradeHistoryService | +10 |
| `src/gpt_bitcoin/config/settings.py` | Add db_history_path setting | +5 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DB file corruption | Low | High | Regular backup recommendation in UI |
| Performance degradation with large datasets | Medium | Medium | Add pagination, index optimization |
| Disk space exhaustion | Low | Medium | Add max records limit, archival feature |
| Migration failures | Low | High | Use alembic for versioned migrations |
| Concurrent write conflicts | Low | Low | Single-user assumption, WAL mode |

### Technical Debt Considerations

1. **Initial Implementation**: Simple synchronous SQLite for MVP
2. **Future Enhancement**: Async SQLAlchemy with connection pooling
3. **Future Enhancement**: Encrypted database for sensitive data

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-HIST-001 | TradeHistoryService.save_trade_result() | test_save_trade_result() |
| REQ-HIST-002 | TradeRepository.find_with_filters() | test_query_ordering() |
| REQ-HIST-003 | TradingService integration | test_auto_save_on_execution() |
| REQ-HIST-004 | web_ui.py Trade History tab | test_ui_trade_list_display() |
| REQ-HIST-005 | Error handling in save | test_db_failure_graceful_handling() |
| REQ-HIST-006 | Empty result handling | test_empty_result_display() |
| REQ-HIST-007 | CSV export | test_csv_export_format() |
| REQ-HIST-008 | P/L calculation | test_profit_loss_calculation() |
| REQ-HIST-009 | Immutable records | test_no_update_delete() |
| REQ-HIST-010 | Duplicate prevention | test_duplicate_uuid_handling() |

---

## Success Criteria

1. **Functional**: All 10 requirements implemented and passing tests
2. **Performance**: Query 1000 records < 1 second
3. **Coverage**: Minimum 85% test coverage
4. **Integration**: Web UI displays trade history correctly
5. **Export**: CSV export produces valid, parseable files
6. **P/L**: Profit/loss calculation matches manual calculation

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService foundation (Completed)
- **SPEC-TRADING-003**: CLI Integration (depends on this for data source)
- **SPEC-TRADING-004**: Security Enhancements (audit log integration)

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
