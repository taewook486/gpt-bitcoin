"""
Unit tests for MockUpbitClient.

Tests cover:
- Simulated orderbook retrieval
- Simulated price retrieval
- Virtual balance management
- Simulated buy orders
- Simulated sell orders
- Balance updates and fee calculation

@MX:NOTE: MockUpbitClient 테스트 - TDD RED Phase
"""

from __future__ import annotations

import pytest

from gpt_bitcoin.domain.testnet_config import TestnetConfig
from gpt_bitcoin.infrastructure.external.mock_upbit_client import MockUpbitClient

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Create a MockUpbitClient with default config."""
    return MockUpbitClient()


@pytest.fixture
def custom_config_client():
    """Create a MockUpbitClient with custom config."""
    return TestnetConfig(
        initial_krw_balance=5_000_000.0,
        simulated_fee_rate=0.001,
        db_path="custom_testnet.db",
    )


@pytest.fixture
def custom_client():
    """Create a MockUpbitClient with custom config."""
    return MockUpbitClient(
        config=TestnetConfig(
            initial_krw_balance=5_000_000.0,
            simulated_fee_rate=0.001,
        )
    )


# =============================================================================
# Orderbook Tests
# =============================================================================


class TestOrderbook:
    """Tests for simulated orderbook functionality."""

    @pytest.mark.asyncio
    async def test_get_orderbook_returns_orderbook(self, mock_client: MockUpbitClient):
        """Test get_orderbook returns an orderbook object."""
        orderbook = await mock_client.get_orderbook("KRW-BTC")
        assert orderbook.ticker == "KRW-BTC"

    @pytest.mark.asyncio
    async def test_get_orderbook_has_simulated_prices(self, mock_client: MockUpbitClient):
        """Test orderbook contains simulated prices."""
        orderbook = await mock_client.get_orderbook("KRW-BTC")
        assert len(orderbook.orderbook_units) > 0
        unit = orderbook.orderbook_units[0]
        assert unit.ask_price > 0
        assert unit.bid_price > 0

    @pytest.mark.asyncio
    async def test_get_orderbook_different_tickers(self, mock_client: MockUpbitClient):
        """Test get_orderbook works for different tickers."""
        btc_orderbook = await mock_client.get_orderbook("KRW-BTC")
        eth_orderbook = await mock_client.get_orderbook("KRW-ETH")
        assert btc_orderbook.ticker == "KRW-BTC"
        assert eth_orderbook.ticker == "KRW-ETH"


# =============================================================================
# Price Tests
# =============================================================================


class TestPrice:
    """Tests for simulated price functionality."""

    @pytest.mark.asyncio
    async def test_get_current_price_returns_float(self, mock_client: MockUpbitClient):
        """Test get_current_price returns a float."""
        price = await mock_client.get_current_price("KRW-BTC")
        assert isinstance(price, float)
        assert price > 0

    @pytest.mark.asyncio
    async def test_get_current_price_btc(self, mock_client: MockUpbitClient):
        """Test get_current_price for BTC returns expected price."""
        price = await mock_client.get_current_price("KRW-BTC")
        assert price == 50_000_000.0

    @pytest.mark.asyncio
    async def test_get_current_price_different_tickers(self, mock_client: MockUpbitClient):
        """Test get_current_price returns different prices for different tickers."""
        btc_price = await mock_client.get_current_price("KRW-BTC")
        eth_price = await mock_client.get_current_price("KRW-ETH")
        assert btc_price != eth_price


# =============================================================================
# Balance Tests
# =============================================================================


class TestBalance:
    """Tests for virtual balance management."""

    @pytest.mark.asyncio
    async def test_get_balance_krw_returns_default(self, mock_client: MockUpbitClient):
        """Test get_balance for KRW returns default initial balance."""
        balance = await mock_client.get_balance("KRW")
        assert balance == 10_000_000.0

    @pytest.mark.asyncio
    async def test_get_balance_custom_initial(self, custom_client: MockUpbitClient):
        """Test get_balance returns custom initial balance."""
        balance = await custom_client.get_balance("KRW")
        assert balance == 5_000_000.0

    @pytest.mark.asyncio
    async def test_get_balance_coin_zero_initially(self, mock_client: MockUpbitClient):
        """Test get_balance for coin returns 0 initially."""
        balance = await mock_client.get_balance("BTC")
        assert balance == 0.0

    @pytest.mark.asyncio
    async def test_get_balances_includes_krw(self, mock_client: MockUpbitClient):
        """Test get_balances includes KRW balance."""
        balances = await mock_client.get_balances()
        currency_codes = [b.currency for b in balances]
        assert "KRW" in currency_codes

    @pytest.mark.asyncio
    async def test_get_balances_returns_list(self, mock_client: MockUpbitClient):
        """Test get_balances returns a list."""
        balances = await mock_client.get_balances()
        assert isinstance(balances, list)


# =============================================================================
# Buy Order Tests
# =============================================================================


class TestBuyOrder:
    """Tests for simulated buy order functionality."""

    @pytest.mark.asyncio
    async def test_buy_market_order_success(self, mock_client: MockUpbitClient):
        """Test buy_market_order executes successfully."""
        order = await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        assert order.side == "bid"
        assert order.ticker == "KRW-BTC"
        assert order.uuid is not None

    @pytest.mark.asyncio
    async def test_buy_market_order_deducts_krw(self, mock_client: MockUpbitClient):
        """Test buy_market_order deducts KRW balance."""
        initial_balance = await mock_client.get_balance("KRW")
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        final_balance = await mock_client.get_balance("KRW")
        assert final_balance < initial_balance

    @pytest.mark.asyncio
    async def test_buy_market_order_adds_coin_balance(self, mock_client: MockUpbitClient):
        """Test buy_market_order adds coin balance."""
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        btc_balance = await mock_client.get_balance("BTC")
        assert btc_balance > 0

    @pytest.mark.asyncio
    async def test_buy_market_order_calculates_fee(self, mock_client: MockUpbitClient):
        """Test buy_market_order includes fee in balance deduction."""
        fee_rate = mock_client.config.simulated_fee_rate
        order = await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        expected_fee = 100_000.0 * fee_rate
        assert order.fee == expected_fee

    @pytest.mark.asyncio
    async def test_buy_market_order_insufficient_balance_raises_error(
        self, mock_client: MockUpbitClient
    ):
        """Test buy_market_order raises ValueError for insufficient balance."""
        with pytest.raises(ValueError, match="잔액 부족"):
            await mock_client.buy_market_order("KRW-BTC", 999_999_999.0)


# =============================================================================
# Sell Order Tests
# =============================================================================


class TestSellOrder:
    """Tests for simulated sell order functionality."""

    @pytest.mark.asyncio
    async def test_sell_market_order_requires_prior_purchase(self, mock_client: MockUpbitClient):
        """Test sell_market_order requires prior purchase."""
        # First buy some BTC
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)

        # Then sell it
        order = await mock_client.sell_market_order("KRW-BTC", 0.001)
        assert order.side == "ask"
        assert order.ticker == "KRW-BTC"

    @pytest.mark.asyncio
    async def test_sell_market_order_adds_krw_balance(self, mock_client: MockUpClient):
        """Test sell_market_order adds KRW balance."""
        # First buy some BTC
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        initial_krw = await mock_client.get_balance("KRW")

        # Then sell it
        await mock_client.sell_market_order("KRW-BTC", 0.001)
        final_krw = await mock_client.get_balance("KRW")

        assert final_krw > initial_krw

    @pytest.mark.asyncio
    async def test_sell_market_order_deducts_coin_balance(self, mock_client: MockUpbitClient):
        """Test sell_market_order deducts coin balance."""
        # First buy some BTC
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        initial_btc = await mock_client.get_balance("BTC")

        # Then sell some
        await mock_client.sell_market_order("KRW-BTC", 0.0001)
        final_btc = await mock_client.get_balance("BTC")

        assert final_btc < initial_btc

    @pytest.mark.asyncio
    async def test_sell_market_order_insufficient_balance_raises_error(
        self, mock_client: MockUpbitClient
    ):
        """Test sell_market_order raises ValueError for insufficient coin balance."""
        with pytest.raises(ValueError, match="잔액 부족"):
            await mock_client.sell_market_order("KRW-BTC", 999999.0)


# =============================================================================
# Fee Calculation Tests
# =============================================================================


class TestFeeCalculation:
    """Tests for fee calculation in simulated orders."""

    @pytest.mark.asyncio
    async def test_buy_fee_calculation(self, mock_client: MockUpbitClient):
        """Test buy fee is calculated correctly."""
        order = await mock_client.buy_market_order("KRW-BTC", 100_000.0)
        expected_fee = 100_000.0 * mock_client.config.simulated_fee_rate
        assert order.fee == expected_fee

    @pytest.mark.asyncio
    async def test_sell_fee_calculation(self, mock_client: MockUpbitClient):
        """Test sell fee is calculated correctly."""
        # First buy some BTC
        await mock_client.buy_market_order("KRW-BTC", 100_000.0)

        # Then sell
        order = await mock_client.sell_market_order("KRW-BTC", 0.001)
        expected_amount = order.price * 0.001
        expected_fee = expected_amount * mock_client.config.simulated_fee_rate
        assert order.fee == expected_fee

    @pytest.mark.asyncio
    async def test_custom_fee_rate(self, custom_client: MockUpbitClient):
        """Test custom fee rate is used."""
        order = await custom_client.buy_market_order("KRW-BTC", 100_000.0)
        expected_fee = 100_000.0 * 0.001  # Custom fee rate
        assert order.fee == expected_fee
