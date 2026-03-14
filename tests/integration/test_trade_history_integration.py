"""
Integration tests for Trade History feature.

Tests the complete flow from TradingService to TradeRepository
to ensure trades are properly saved and can be retrieved.
"""

from pathlib import Path

import pytest

from gpt_bitcoin.config.settings import Settings
from gpt_bitcoin.domain.trade_history import TradeType
from gpt_bitcoin.domain.trading import TradingService
from gpt_bitcoin.infrastructure.external.mock_upbit_client import MockUpbitClient
from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository


@pytest.fixture
async def test_db_path(tmp_path: Path) -> Path:
    """Create a temporary database file for testing."""
    return tmp_path / "test_trades.db"


@pytest.fixture
async def test_settings(test_db_path: Path) -> Settings:
    """Create test settings with temporary database."""
    return Settings(
        testnet_mode=True,
        db_path=str(test_db_path),
    )


@pytest.fixture
async def trade_repository(test_settings: Settings) -> TradeRepository:
    """Create a TradeRepository with test settings."""
    repo = TradeRepository(settings=test_settings)
    yield repo
    repo.close()  # close()는 async 함수가 아님


@pytest.fixture
def mock_upbit_client() -> MockUpbitClient:
    """Create a mock UpbitClient for testing."""
    return MockUpbitClient()


@pytest.fixture
async def trading_service(
    mock_upbit_client: MockUpbitClient,
    test_settings: Settings,
    trade_repository: TradeRepository,
) -> TradingService:
    """Create a TradingService with mocked dependencies."""
    service = TradingService(
        upbit_client=mock_upbit_client,
        settings=test_settings,
        trade_repository=trade_repository,
    )
    return service


@pytest.mark.asyncio
class TestTradeHistoryIntegration:
    """Integration tests for trade history saving and retrieval."""

    async def test_buy_trade_saved_to_repository(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test that a successful buy trade is saved to the repository."""
        # Request buy order
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Approve and execute
        approval.mark_approved()
        result = await trading_service.execute_approved_trade(approval)

        # Verify trade executed
        assert result.success is True, f"Trade failed: {result.error_message}"

        # Verify trade was saved to repository
        trades = trade_repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 1, f"Expected 1 trade, got {len(trades)}"
        assert trades[0].ticker == "KRW-BTC"
        assert trades[0].trade_type == TradeType.BUY
        assert trades[0].total_cost() >= 10000.0  # fee가 포함된 총 비용

    async def test_sell_trade_saved_to_repository(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test that a successful sell trade is saved to the repository."""
        # First buy some BTC to have balance
        buy_approval = await trading_service.request_buy_order("KRW-BTC", 50000.0)
        buy_approval.mark_approved()
        buy_result = await trading_service.execute_approved_trade(buy_approval)
        assert buy_result.success is True

        # Now sell some BTC
        approval = await trading_service.request_sell_order("KRW-BTC", 0.0005)

        # Approve and execute
        approval.mark_approved()
        result = await trading_service.execute_approved_trade(approval)

        # Verify trade executed
        assert result.success is True

        # Verify trade was saved to repository (should have 2 trades now: buy + sell)
        trades = trade_repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 2
        assert trades[1].ticker == "KRW-BTC"
        assert trades[1].trade_type == TradeType.SELL

    async def test_multiple_trades_saved_and_retrieved(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test that multiple trades are saved and can be retrieved together."""
        # Execute multiple buy trades
        for i in range(3):
            approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)
            approval.mark_approved()
            result = await trading_service.execute_approved_trade(approval)
            assert result.success is True

        # Verify all trades were saved
        trades = trade_repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 3
        assert all(t.ticker == "KRW-BTC" for t in trades)
        assert all(t.trade_type == TradeType.BUY for t in trades)

    async def test_failed_trade_not_saved(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test that a failed trade is not saved to the repository."""
        # Try to request buy order with insufficient balance
        # This should fail at the request stage
        try:
            approval = await trading_service.request_buy_order("KRW-BTC", 999999999.0)
            # If we get here, the request was approved (shouldn't happen with insufficient balance)
            approval.mark_approved()
            result = await trading_service.execute_approved_trade(approval)

            # Verify trade failed
            assert result.success is False
        except ValueError:
            # Expected: insufficient balance at request stage
            pass

        # Verify no trade was saved
        trades = trade_repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 0

    async def test_trade_persistence_across_retrievals(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test that trades persist across multiple retrievals."""
        # Execute a trade
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)
        approval.mark_approved()
        result = await trading_service.execute_approved_trade(approval)
        assert result.success is True

        # Retrieve trades multiple times
        for _ in range(3):
            trades = trade_repository.get_trades(ticker="KRW-BTC")
            assert len(trades) == 1
            assert trades[0].ticker == "KRW-BTC"

    async def test_filter_by_ticker(
        self,
        trading_service: TradingService,
        trade_repository: TradeRepository,
    ):
        """Test filtering trades by ticker."""
        # Execute trades for different tickers
        for ticker in ["KRW-BTC", "KRW-ETH", "KRW-BTC"]:
            approval = await trading_service.request_buy_order(ticker, 10000.0)
            approval.mark_approved()
            result = await trading_service.execute_approved_trade(approval)
            assert result.success is True

        # Verify filtering works
        btc_trades = trade_repository.get_trades(ticker="KRW-BTC")
        eth_trades = trade_repository.get_trades(ticker="KRW-ETH")

        assert len(btc_trades) == 2
        assert len(eth_trades) == 1
        assert all(t.ticker == "KRW-BTC" for t in btc_trades)
        assert all(t.ticker == "KRW-ETH" for t in eth_trades)
