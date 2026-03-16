"""
Tests for TradeHistory module (SPEC-TRADING-002).

This test module covers:
- TradeRecord data model with FIFO profit/loss calculation
- TradeHistoryService for trade history management
- CSV export functionality

@MX:NOTE: Test-first approach - RED phase before implementation.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO

import pytest

from gpt_bitcoin.domain.trade_history import (
    TradeHistoryService,
    TradeRecord,
    TradeType,
)

# =============================================================================
# TradeRecord Model Tests
# =============================================================================


class TestTradeRecord:
    """Test cases for TradeRecord domain model."""

    def test_trade_record_creation_buy(self) -> None:
        """Test creating a buy trade record."""
        record = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.001,
            fee=25.0,
            timestamp=datetime(2026, 3, 5, 10, 0, 0),
        )

        assert record.ticker == "KRW-BTC"
        assert record.trade_type == TradeType.BUY
        assert record.price == 50000000.0
        assert record.quantity == 0.001
        assert record.fee == 25.0
        assert record.total_cost() == 50000000.0 * 0.001 + 25.0

    def test_trade_record_creation_sell(self) -> None:
        """Test creating a sell trade record."""
        record = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.SELL,
            price=55000000.0,
            quantity=0.001,
            fee=27.5,
            timestamp=datetime(2026, 3, 5, 11, 0, 0),
        )

        assert record.ticker == "KRW-BTC"
        assert record.trade_type == TradeType.SELL
        assert record.price == 55000000.0
        assert record.quantity == 0.001
        assert record.fee == 27.5
        assert record.total_revenue() == 55000000.0 * 0.001 - 27.5

    def test_total_cost_calculation(self) -> None:
        """Test total cost calculation for buy trades."""
        record = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.002,
            fee=50.0,
        )

        expected = 50000000.0 * 0.002 + 50.0  # price * quantity + fee
        assert record.total_cost() == expected

    def test_total_revenue_calculation(self) -> None:
        """Test total revenue calculation for sell trades."""
        record = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.SELL,
            price=55000000.0,
            quantity=0.002,
            fee=55.0,
        )

        expected = 55000000.0 * 0.002 - 55.0  # price * quantity - fee
        assert record.total_revenue() == expected

    def test_to_dict_format(self) -> None:
        """Test TradeRecord serialization to dict."""
        timestamp = datetime(2026, 3, 5, 10, 0, 0)
        record = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.001,
            fee=25.0,
            timestamp=timestamp,
        )

        result = record.to_dict()

        assert result["ticker"] == "KRW-BTC"
        assert result["trade_type"] == "buy"
        assert result["price"] == 50000000.0
        assert result["quantity"] == 0.001
        assert result["fee"] == 25.0
        assert result["timestamp"] == timestamp.isoformat()

    def test_from_dict_deserialization(self) -> None:
        """Test TradeRecord deserialization from dict."""
        timestamp = datetime(2026, 3, 5, 10, 0, 0)
        data = {
            "ticker": "KRW-BTC",
            "trade_type": "buy",
            "price": 50000000.0,
            "quantity": 0.001,
            "fee": 25.0,
            "timestamp": timestamp.isoformat(),
        }

        record = TradeRecord.from_dict(data)

        assert record.ticker == "KRW-BTC"
        assert record.trade_type == TradeType.BUY
        assert record.price == 50000000.0
        assert record.quantity == 0.001
        assert record.fee == 25.0
        assert record.timestamp == timestamp


# =============================================================================
# TradeHistoryService Tests (FIFO Calculation)
# =============================================================================


class MockTradeRepository:
    """Mock repository for testing TradeHistoryService."""

    def __init__(self) -> None:
        self._trades: list[TradeRecord] = []

    def add_trade(self, trade: TradeRecord) -> None:
        self._trades.append(trade)

    def get_trades(
        self,
        ticker: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TradeRecord]:
        trades = self._trades

        if ticker:
            trades = [t for t in trades if t.ticker == ticker]
        if start_date:
            trades = [t for t in trades if t.timestamp >= start_date]
        if end_date:
            trades = [t for t in trades if t.timestamp <= end_date]

        return trades


class TestTradeHistoryService:
    """Test cases for TradeHistoryService."""

    def test_calculate_fifo_profit_simple(self) -> None:
        """Test simple FIFO profit calculation: one buy, one sell."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Buy 0.001 BTC at 50,000 KRW
        buy_trade = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.001,
            fee=25.0,
            timestamp=datetime(2026, 3, 5, 10, 0, 0),
        )
        repo.add_trade(buy_trade)

        # Sell 0.001 BTC at 55,000 KRW
        sell_trade = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.SELL,
            price=55000000.0,
            quantity=0.001,
            fee=27.5,
            timestamp=datetime(2026, 3, 5, 11, 0, 0),
        )
        repo.add_trade(sell_trade)

        # Calculate profit
        profit = service.calculate_fifo_profit("KRW-BTC")

        # Expected: (55000000 * 0.001 - 27.5) - (50000000 * 0.001 + 25.0)
        # = 54972.5 - 50025 = 4947.5 KRW
        assert profit == pytest.approx(4947.5)

    def test_calculate_fifo_profit_multiple_buys(self) -> None:
        """Test FIFO profit with multiple buy trades."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Buy 0.001 BTC at 50,000 KRW
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        # Buy 0.002 BTC at 52,000 KRW
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=52000000.0,
                quantity=0.002,
                fee=52.0,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        # Sell 0.002 BTC at 55,000 KRW (should use FIFO)
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.SELL,
                price=55000000.0,
                quantity=0.002,
                fee=55.0,
                timestamp=datetime(2026, 3, 5, 12, 0, 0),
            )
        )

        profit = service.calculate_fifo_profit("KRW-BTC")

        # FIFO: First 0.001 from first buy (50M), remaining 0.001 from second buy (52M)
        # Cost: (50M * 0.001 + 25) + (52M * 0.001 + 26) = 50025 + 52026 = 102051
        # Revenue: 55M * 0.002 - 55 = 109945
        # Profit: 109945 - 102051 = 7894
        assert profit == pytest.approx(7894.0)

    def test_calculate_fifo_profit_partial_sell(self) -> None:
        """Test FIFO profit when sell quantity is less than buy quantity."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Buy 0.003 BTC
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.003,
                fee=75.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        # Sell 0.001 BTC (partial)
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.SELL,
                price=55000000.0,
                quantity=0.001,
                fee=27.5,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        profit = service.calculate_fifo_profit("KRW-BTC")

        # Only 0.001 sold, 0.002 remaining
        # Cost: 50M * 0.001 + 25 = 50025
        # Revenue: 55M * 0.001 - 27.5 = 54972.5
        # Profit: 54972.5 - 50025 = 4947.5
        assert profit == pytest.approx(4947.5)

    def test_calculate_fifo_profit_no_trades(self) -> None:
        """Test FIFO profit calculation with no trades."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        profit = service.calculate_fifo_profit("KRW-BTC")

        assert profit == 0.0

    def test_calculate_fifo_profit_only_buys(self) -> None:
        """Test FIFO profit with only buy trades (no sells)."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
            )
        )

        profit = service.calculate_fifo_profit("KRW-BTC")

        # No sells yet, profit should be 0 (no realized profit)
        assert profit == 0.0

    def test_export_to_csv(self) -> None:
        """Test CSV export functionality."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Add some trades
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.SELL,
                price=55000000.0,
                quantity=0.001,
                fee=27.5,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        # Export to string buffer
        output = StringIO()
        service.export_to_csv(output, "KRW-BTC")

        # Verify CSV content
        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["ticker"] == "KRW-BTC"
        assert rows[0]["trade_type"] == "buy"
        assert rows[0]["price"] == "50000000.0"
        assert rows[1]["trade_type"] == "sell"
        assert rows[1]["price"] == "55000000.0"

    def test_export_to_csv_with_dates(self) -> None:
        """Test CSV export with date filtering."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Add trades on different dates
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 1, 10, 0, 0),
            )
        )

        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=51000000.0,
                quantity=0.001,
                fee=25.5,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        # Export with date filter
        output = StringIO()
        service.export_to_csv(
            output,
            "KRW-BTC",
            start_date=datetime(2026, 3, 2),
            end_date=datetime(2026, 3, 6),
        )

        output.seek(0)
        reader = csv.DictReader(output)
        rows = list(reader)

        # Should only include the March 5 trade
        assert len(rows) == 1
        assert rows[0]["price"] == "51000000.0"

    def test_get_trade_summary(self) -> None:
        """Test getting trade summary statistics."""
        repo = MockTradeRepository()
        service = TradeHistoryService(repo)

        # Add trades
        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        repo.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.SELL,
                price=55000000.0,
                quantity=0.001,
                fee=27.5,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        summary = service.get_trade_summary("KRW-BTC")

        assert summary["total_trades"] == 2
        assert summary["total_buy_quantity"] == pytest.approx(0.001)
        assert summary["total_sell_quantity"] == pytest.approx(0.001)
        assert summary["realized_profit"] == pytest.approx(4947.5)
