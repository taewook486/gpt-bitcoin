"""
Unit tests for CoinManager.

Tests cover:
- Parallel market data fetching
- Portfolio status aggregation
- Coin balance retrieval
- Error handling for failed coins
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from gpt_bitcoin.application.coin_manager import (
    CoinManager,
    CoinPosition,
    MarketData,
    PortfolioStatus,
)
from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency


class TestMarketData:
    """Tests for MarketData dataclass."""

    def test_market_data_creation(self):
        """Test creating MarketData instance."""
        data = MarketData(
            coin=Cryptocurrency.BTC,
            ticker="BTC-KRW",
            current_price=50000000.0,
            price_change_24h=2.5,
            volume_24h=1000000000.0,
            high_24h=51000000.0,
            low_24h=49000000.0,
        )

        assert data.coin == Cryptocurrency.BTC
        assert data.ticker == "BTC-KRW"
        assert data.current_price == 50000000.0
        assert data.price_change_24h == 2.5
        assert isinstance(data.timestamp, datetime)

    def test_market_data_default_timestamp(self):
        """Test that timestamp is auto-generated."""
        before = datetime.now()
        data = MarketData(
            coin=Cryptocurrency.ETH,
            ticker="ETH-KRW",
            current_price=3000000.0,
        )
        after = datetime.now()

        assert before <= data.timestamp <= after


class TestCoinPosition:
    """Tests for CoinPosition dataclass."""

    def test_coin_position_creation(self):
        """Test creating CoinPosition instance."""
        position = CoinPosition(
            coin=Cryptocurrency.BTC,
            balance=0.1,
            avg_buy_price=45000000.0,
        )

        assert position.coin == Cryptocurrency.BTC
        assert position.balance == 0.1
        assert position.avg_buy_price == 45000000.0
        assert position.value_krw == 0.0

    def test_update_with_price_profit(self):
        """Test updating position with current price (profit)."""
        position = CoinPosition(
            coin=Cryptocurrency.BTC,
            balance=0.1,
            avg_buy_price=45000000.0,
        )

        position.update_with_price(50000000.0)

        assert position.current_price == 50000000.0
        assert position.value_krw == 5000000.0  # 0.1 * 50000000
        assert position.profit_loss_krw == 500000.0  # 5000000 - 4500000
        assert position.profit_loss_percentage == pytest.approx(11.11, rel=0.01)

    def test_update_with_price_loss(self):
        """Test updating position with current price (loss)."""
        position = CoinPosition(
            coin=Cryptocurrency.ETH,
            balance=1.0,
            avg_buy_price=3500000.0,
        )

        position.update_with_price(3000000.0)

        assert position.current_price == 3000000.0
        assert position.value_krw == 3000000.0
        assert position.profit_loss_krw == -500000.0
        assert position.profit_loss_percentage == pytest.approx(-14.29, rel=0.01)

    def test_update_with_zero_avg_buy_price(self):
        """Test updating position when avg_buy_price is zero."""
        position = CoinPosition(
            coin=Cryptocurrency.SOL,
            balance=10.0,
            avg_buy_price=0.0,
        )

        position.update_with_price(150000.0)

        assert position.current_price == 150000.0
        assert position.value_krw == 1500000.0
        assert position.profit_loss_krw == 0.0
        assert position.profit_loss_percentage == 0.0


class TestPortfolioStatus:
    """Tests for PortfolioStatus dataclass."""

    def test_portfolio_status_creation(self):
        """Test creating PortfolioStatus instance."""
        btc_position = CoinPosition(
            coin=Cryptocurrency.BTC,
            balance=0.1,
            avg_buy_price=45000000.0,
        )
        btc_position.update_with_price(50000000.0)

        status = PortfolioStatus(
            total_value_krw=5000000.0,
            total_profit_loss_krw=500000.0,
            total_profit_loss_percentage=10.0,
            positions={Cryptocurrency.BTC: btc_position},
            allocation_percentages={Cryptocurrency.BTC: 100.0},
        )

        assert status.total_value_krw == 5000000.0
        assert status.total_profit_loss_krw == 500000.0
        assert len(status.positions) == 1

    def test_get_position_existing(self):
        """Test getting existing position."""
        btc_position = CoinPosition(coin=Cryptocurrency.BTC, balance=0.1)
        status = PortfolioStatus(positions={Cryptocurrency.BTC: btc_position})

        result = status.get_position(Cryptocurrency.BTC)

        assert result == btc_position

    def test_get_position_non_existing(self):
        """Test getting non-existing position."""
        status = PortfolioStatus()

        result = status.get_position(Cryptocurrency.ETH)

        assert result is None


class TestCoinManager:
    """Tests for CoinManager class."""

    @pytest.fixture
    def mock_upbit_client(self):
        """Create mock Upbit client."""
        client = MagicMock()
        client.get_ticker = MagicMock()
        client.get_accounts = MagicMock()
        return client

    @pytest.fixture
    def coin_manager(self, mock_upbit_client):
        """Create CoinManager instance."""
        return CoinManager(
            upbit_client=mock_upbit_client,
            request_timeout=5.0,
            max_concurrent_requests=3,
        )

    def test_coin_manager_initialization(self, mock_upbit_client):
        """Test CoinManager initialization."""
        manager = CoinManager(
            upbit_client=mock_upbit_client,
            request_timeout=10.0,
            max_concurrent_requests=5,
        )

        assert manager.request_timeout == 10.0
        assert manager.max_concurrent_requests == 5

    @pytest.mark.asyncio
    async def test_fetch_market_data_single_coin(self, coin_manager, mock_upbit_client):
        """Test fetching market data for a single coin."""
        mock_upbit_client.get_ticker.return_value = {
            "market": "KRW-BTC",
            "trade_price": 50000000.0,
            "signed_change_rate": 0.025,
            "acc_trade_price_24h": 1000000000.0,
            "high_price": 51000000.0,
            "low_price": 49000000.0,
        }

        result = await coin_manager.fetch_market_data([Cryptocurrency.BTC])

        assert Cryptocurrency.BTC in result
        data = result[Cryptocurrency.BTC]
        assert data.coin == Cryptocurrency.BTC
        assert data.current_price == 50000000.0
        assert data.price_change_24h == 2.5

    @pytest.mark.asyncio
    async def test_fetch_market_data_multiple_coins(self, coin_manager, mock_upbit_client):
        """Test fetching market data for multiple coins in parallel."""
        ticker_data = {
            "BTC-KRW": {
                "market": "BTC-KRW",
                "trade_price": 50000000.0,
                "signed_change_rate": 0.02,
                "acc_trade_price_24h": 1000000000.0,
                "high_price": 51000000.0,
                "low_price": 49000000.0,
            },
            "ETH-KRW": {
                "market": "ETH-KRW",
                "trade_price": 3000000.0,
                "signed_change_rate": 0.01,
                "acc_trade_price_24h": 500000000.0,
                "high_price": 3100000.0,
                "low_price": 2900000.0,
            },
        }

        def get_ticker_side_effect(ticker):
            return ticker_data.get(ticker)

        mock_upbit_client.get_ticker.side_effect = get_ticker_side_effect

        result = await coin_manager.fetch_market_data([Cryptocurrency.BTC, Cryptocurrency.ETH])

        assert len(result) == 2
        assert Cryptocurrency.BTC in result
        assert Cryptocurrency.ETH in result
        assert result[Cryptocurrency.BTC].current_price == 50000000.0
        assert result[Cryptocurrency.ETH].current_price == 3000000.0

    @pytest.mark.asyncio
    async def test_fetch_market_data_partial_failure(self, coin_manager, mock_upbit_client):
        """Test that failed coins don't affect successful ones."""
        call_count = 0

        def get_ticker_side_effect(ticker):
            nonlocal call_count
            call_count += 1
            if ticker == "BTC-KRW":  # Correct ticker format
                return {
                    "market": "KRW-BTC",
                    "trade_price": 50000000.0,
                    "signed_change_rate": 0.0,
                    "acc_trade_price_24h": 0.0,
                    "high_price": 0.0,
                    "low_price": 0.0,
                }
            else:
                raise Exception("API error")

        mock_upbit_client.get_ticker.side_effect = get_ticker_side_effect

        result = await coin_manager.fetch_market_data([Cryptocurrency.BTC, Cryptocurrency.ETH])

        # BTC should succeed, ETH should fail
        assert len(result) == 1
        assert Cryptocurrency.BTC in result
        assert Cryptocurrency.ETH not in result

    @pytest.mark.asyncio
    async def test_get_portfolio_status(self, coin_manager, mock_upbit_client):
        """Test portfolio status aggregation."""
        mock_upbit_client.get_ticker.return_value = {
            "market": "KRW-BTC",
            "trade_price": 50000000.0,
            "signed_change_rate": 0.0,
            "acc_trade_price_24h": 0.0,
            "high_price": 0.0,
            "low_price": 0.0,
        }

        positions = {
            Cryptocurrency.BTC: CoinPosition(
                coin=Cryptocurrency.BTC,
                balance=0.1,
                avg_buy_price=45000000.0,
            ),
        }

        status = await coin_manager.get_portfolio_status(positions)

        assert status.total_value_krw == 5000000.0  # 0.1 * 50000000
        assert status.total_profit_loss_krw == 500000.0
        assert Cryptocurrency.BTC in status.allocation_percentages

    @pytest.mark.asyncio
    async def test_get_coin_balances(self, coin_manager, mock_upbit_client):
        """Test fetching coin balances."""
        mock_upbit_client.get_accounts.return_value = [
            {"currency": "BTC", "balance": "0.1"},
            {"currency": "ETH", "balance": "1.5"},
            {"currency": "KRW", "balance": "1000000"},  # Should be ignored
        ]

        result = await coin_manager.get_coin_balances([Cryptocurrency.BTC, Cryptocurrency.ETH])

        assert result[Cryptocurrency.BTC] == 0.1
        assert result[Cryptocurrency.ETH] == 1.5

    @pytest.mark.asyncio
    async def test_get_coin_balances_missing_coin(self, coin_manager, mock_upbit_client):
        """Test that missing coins return zero balance."""
        mock_upbit_client.get_accounts.return_value = [
            {"currency": "BTC", "balance": "0.1"},
        ]

        result = await coin_manager.get_coin_balances([Cryptocurrency.BTC, Cryptocurrency.ETH])

        assert result[Cryptocurrency.BTC] == 0.1
        assert result[Cryptocurrency.ETH] == 0.0  # Missing coin defaults to 0

    @pytest.mark.asyncio
    async def test_get_coin_balances_api_failure(self, coin_manager, mock_upbit_client):
        """Test handling API failure when fetching balances."""
        mock_upbit_client.get_accounts.side_effect = Exception("API error")

        result = await coin_manager.get_coin_balances([Cryptocurrency.BTC, Cryptocurrency.ETH])

        # Should return zero balances for all coins on failure
        assert result[Cryptocurrency.BTC] == 0.0
        assert result[Cryptocurrency.ETH] == 0.0
