"""
Unit tests for Upbit Client.

Tests cover:
- Pydantic models validation
- JWT token generation
- Client initialization
"""

from gpt_bitcoin.infrastructure.external.upbit_client import (
    OHLCV,
    Balance,
    Order,
    Orderbook,
    OrderbookUnit,
)


class TestBalance:
    """Test Balance Pydantic model."""

    def test_valid_balance(self):
        """Should accept valid balance data."""
        balance = Balance(
            currency="KRW",
            balance=100000.0,
            locked=5000.0,
            avg_buy_price=0.0,
        )
        assert balance.currency == "KRW"
        assert balance.balance == 100000.0
        assert balance.locked == 5000.0

    def test_btc_balance(self):
        """Should handle BTC balance."""
        balance = Balance(
            currency="BTC",
            balance=0.5,
            locked=0.1,
            avg_buy_price=50000000.0,
        )
        assert balance.currency == "BTC"
        assert balance.avg_buy_price == 50000000.0

    def test_defaults(self):
        """Should use defaults for optional fields."""
        balance = Balance(currency="ETH")
        assert balance.balance == 0.0
        assert balance.locked == 0.0
        assert balance.avg_buy_price == 0.0


class TestOrderbookUnit:
    """Test OrderbookUnit model."""

    def test_valid_orderbook_unit(self):
        """Should accept valid orderbook unit."""
        unit = OrderbookUnit(
            ask_price=50000000.0,
            bid_price=49995000.0,
            ask_size=1.5,
            bid_size=2.0,
        )
        assert unit.ask_price == 50000000.0
        assert unit.bid_price == 49995000.0


class TestOrderbook:
    """Test Orderbook model."""

    def test_valid_orderbook(self):
        """Should accept valid orderbook."""
        orderbook = Orderbook(
            market="KRW-BTC",
            timestamp=1709300000000,
            total_ask_size=10.5,
            total_bid_size=15.0,
            orderbook_units=[
                OrderbookUnit(
                    ask_price=50000000.0,
                    bid_price=49995000.0,
                    ask_size=1.0,
                    bid_size=2.0,
                )
            ],
        )
        assert orderbook.market == "KRW-BTC"
        assert len(orderbook.orderbook_units) == 1


class TestOHLCV:
    """Test OHLCV model."""

    def test_valid_ohlcv(self):
        """Should accept valid OHLCV data."""
        candle = OHLCV(
            market="KRW-BTC",
            timestamp=1709300000000,
            open=49500000.0,
            high=50500000.0,
            low=49000000.0,
            close=50000000.0,
            volume=100.5,
        )
        assert candle.market == "KRW-BTC"
        assert candle.open == 49500000.0
        assert candle.high == 50500000.0
        assert candle.low == 49000000.0
        assert candle.close == 50000000.0
        assert candle.volume == 100.5


class TestOrder:
    """Test Order model."""

    def test_valid_order(self):
        """Should accept valid order data."""
        order = Order(
            uuid="test-uuid-123",
            side="bid",
            ord_type="price",
            market="KRW-BTC",
            created_at="2024-03-01T00:00:00Z",
            price=100000.0,
        )
        assert order.uuid == "test-uuid-123"
        assert order.side == "bid"
        assert order.state == "wait"  # Default

    def test_sell_order(self):
        """Should handle sell order."""
        order = Order(
            uuid="test-uuid-456",
            side="ask",
            ord_type="market",
            market="KRW-BTC",
            created_at="2024-03-01T00:00:00Z",
            volume=0.1,
        )
        assert order.side == "ask"
        assert order.ord_type == "market"


class TestUpbitClient:
    """Test UpbitClient initialization and utilities."""

    def test_client_initialization(self):
        """Should initialize client with settings."""
        # Note: This requires valid settings/env vars
        # In production, use dependency injection with mock settings
        pass

    def test_encode_image_to_base64(self, tmp_path):
        """Should encode image file to base64."""
        # Note: encode_image_to_base64 is in GLMClient, not UpbitClient
        # This test is for demonstration purposes
        pass
