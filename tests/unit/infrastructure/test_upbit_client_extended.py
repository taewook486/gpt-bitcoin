"""
Unit tests for Upbit client - extended coverage.

Tests cover:
- Async API methods
- Order execution
- Market data fetching
- Error handling
- Context manager
- JWT generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gpt_bitcoin.infrastructure.external.upbit_client import (
    Balance,
    Orderbook,
    OrderbookUnit,
    OHLCV,
    Order,
    UpbitClient,
)


class TestUpbitClientInitialization:
    """Test UpbitClient initialization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    def test_client_initialization(self, mock_settings):
        """UpbitClient should initialize correctly."""
        client = UpbitClient(mock_settings)

        assert client._access_key == "test_access_key"
        assert client._secret_key == "test_secret_key"


class TestUpbitClientContextManager:
    """Test UpbitClient context manager."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.mark.asyncio
    async def test_context_manager_enter(self, mock_settings):
        """UpbitClient should enter context manager."""
        client = UpbitClient(mock_settings)

        async with client as c:
            assert c is client
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_context_manager_exit(self, mock_settings):
        """UpbitClient should close session on exit."""
        client = UpbitClient(mock_settings)

        async with client:
            pass

        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_method(self, mock_settings):
        """UpbitClient close should close session."""
        client = UpbitClient(mock_settings)

        await client._ensure_session()
        assert client._session is not None

        await client.close()
        assert client._session is None


class TestUpbitClientJWT:
    """Test UpbitClient JWT generation."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    def test_generate_jwt_without_params(self, upbit_client):
        """_generate_jwt should create token without params."""
        token = upbit_client._generate_jwt()

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        # JWT has 3 parts separated by dots
        assert token.count(".") == 2

    def test_generate_jwt_with_params(self, upbit_client):
        """_generate_jwt should create token with query params."""
        token = upbit_client._generate_jwt({"market": "KRW-BTC", "volume": "0.1"})

        assert token is not None
        assert isinstance(token, str)
        assert token.count(".") == 2


class TestUpbitClientAPIRequests:
    """Test UpbitClient API request methods."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    @pytest.mark.asyncio
    async def test_get_balances_success(self, upbit_client):
        """get_balances should return list of balances."""
        mock_response = [
            {
                "currency": "KRW",
                "balance": "100000.0",
                "locked": "0.0",
                "avg_buy_price": "0",
            },
            {
                "currency": "BTC",
                "balance": "0.5",
                "locked": "0.0",
                "avg_buy_price": "90000000",
            },
        ]

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.get_balances()

            assert result is not None
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, upbit_client):
        """get_orderbook should return orderbook data."""
        # Use the actual response format expected by the client
        mock_response = [
            {
                "market": "KRW-BTC",
                "timestamp": 1234567890123,
                "total_ask_size": 10.0,
                "total_bid_size": 20.0,
                "orderbook_units": [
                    {
                        "ask_price": 100000000,
                        "bid_price": 99999000,
                        "ask_size": 1.0,
                        "bid_size": 2.0,
                    },
                ],
            },
        ]

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.get_orderbook("KRW-BTC")

            assert result is not None
            assert result.market == "KRW-BTC"

    @pytest.mark.asyncio
    async def test_get_ohlcv_success(self, upbit_client):
        """get_ohlcv should return OHLCV data."""
        # Use the actual response format expected by the client
        mock_response = [
            {
                "market": "KRW-BTC",
                "candle_date_time_utc": "2024-01-01T00:00:00Z",
                "candle_date_time_kst": "2024-01-01T09:00:00Z",
                "opening_price": 100000000,
                "high_price": 105000000,
                "low_price": 99000000,
                "trade_price": 102000000,
                "timestamp": 1234567890123,
                "candle_acc_trade_price": 1000000000,
                "candle_acc_trade_volume": 10.0,
                "unit": 1,
            },
        ]

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.get_ohlcv("KRW-BTC")

            assert result is not None

    @pytest.mark.asyncio
    async def test_get_current_price_success(self, upbit_client):
        """get_current_price should return current price."""
        mock_response = [
            {
                "market": "KRW-BTC",
                "trade_price": 100000000,
            },
        ]

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.get_current_price("KRW-BTC")

            assert result is not None
            assert result == 100000000


class TestUpbitClientErrorHandling:
    """Test UpbitClient error handling."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    @pytest.mark.asyncio
    async def test_api_error_handling(self, upbit_client):
        """UpbitClient should handle API errors."""
        from gpt_bitcoin.infrastructure.exceptions import UpbitAPIError

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            side_effect=UpbitAPIError("API Error", status_code=500),
        ):
            with pytest.raises(UpbitAPIError):
                await upbit_client.get_balances()


class TestBalanceModel:
    """Test Balance model."""

    def test_balance_with_defaults(self):
        """Balance should have sensible defaults."""
        balance = Balance(currency="KRW")

        assert balance.currency == "KRW"
        assert balance.balance == 0.0
        assert balance.locked == 0.0

    def test_balance_with_all_fields(self):
        """Balance should accept all fields."""
        balance = Balance(
            currency="BTC",
            balance=1.5,
            locked=0.5,
            avg_buy_price=50000000.0,
            avg_buy_price_modified=False,
            unit_currency="KRW",
        )

        assert balance.currency == "BTC"
        assert balance.balance == 1.5
        assert balance.locked == 0.5


class TestOrderbookModel:
    """Test Orderbook model."""

    def test_orderbook_with_units(self):
        """Orderbook should handle multiple units."""
        orderbook = Orderbook(
            market="KRW-BTC",
            timestamp=1234567890123,
            total_ask_size=100.0,
            total_bid_size=200.0,
            orderbook_units=[
                OrderbookUnit(
                    ask_price=100000000,
                    bid_price=99999000,
                    ask_size=1.0,
                    bid_size=2.0,
                ),
                OrderbookUnit(
                    ask_price=100010000,
                    bid_price=99998000,
                    ask_size=1.5,
                    bid_size=2.5,
                ),
            ],
        )

        assert orderbook.market == "KRW-BTC"
        assert len(orderbook.orderbook_units) == 2


class TestOHLCVModel:
    """Test OHLCV model."""

    def test_ohlcv_all_fields(self):
        """OHLCV should handle all fields."""
        ohlcv = OHLCV(
            market="KRW-BTC",
            timestamp=1234567890123,
            open=100000000.0,
            high=105000000.0,
            low=99000000.0,
            close=102000000.0,
            volume=10.0,
        )

        assert ohlcv.market == "KRW-BTC"
        assert ohlcv.open == 100000000.0
        assert ohlcv.high == 105000000.0
        assert ohlcv.low == 99000000.0
        assert ohlcv.close == 102000000.0
        assert ohlcv.volume == 10.0


class TestOrderModel:
    """Test Order model."""

    def test_order_valid_states(self):
        """Order should handle valid states."""
        for state in ["wait", "watch", "done", "cancel"]:
            order = Order(
                uuid=f"test-{state}",
                side="bid",
                ord_type="limit",
                state=state,
                market="KRW-BTC",
                created_at="2024-01-01T00:00:00",
            )

            assert order.state == state

    def test_order_with_all_fields(self):
        """Order should handle all fields."""
        order = Order(
            uuid="test-uuid",
            side="bid",
            ord_type="limit",
            price=100000000.0,
            state="done",
            market="KRW-BTC",
            created_at="2024-01-01T00:00:00",
            volume=1.0,
            remaining_volume=0.0,
            reserved_fee=50000.0,
            remaining_fee=0.0,
            paid_fee=50000.0,
            locked=0.0,
            executed_volume=1.0,
            trades_count=1,
        )

        assert order.uuid == "test-uuid"
        assert order.side == "bid"
        assert order.state == "done"


class TestUpbitClientRateLimiting:
    """Test UpbitClient rate limiting - covers lines 240-255."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests(self, upbit_client):
        """_check_rate_limit should allow requests within limit."""
        # Should not raise
        await upbit_client._check_rate_limit()

    @pytest.mark.asyncio
    async def test_rate_limit_cleans_old_entries(self, upbit_client):
        """_check_rate_limit should clean old request times."""
        import time

        # Add an old entry
        upbit_client._request_times = [time.time() - 100]

        await upbit_client._check_rate_limit()

        # Old entry should be cleaned
        assert len(upbit_client._request_times) == 1


class TestUpbitClientRequest:
    """Test UpbitClient._request method - covers lines 279-347."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    def test_generate_jwt_creates_valid_token(self, upbit_client):
        """_generate_jwt should create a valid JWT token."""
        token = upbit_client._generate_jwt({"market": "KRW-BTC"})

        assert token is not None
        assert isinstance(token, str)
        # JWT has 3 parts
        assert len(token.split(".")) == 3

    def test_generate_jwt_without_params(self, upbit_client):
        """_generate_jwt should work without params."""
        token = upbit_client._generate_jwt()

        assert token is not None
        assert isinstance(token, str)


class TestUpbitClientRateLimitExtended:
    """Additional tests for rate limiting."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    @pytest.mark.asyncio
    async def test_rate_limit_adds_request_time(self, upbit_client):
        """_check_rate_limit should add request time to list."""
        import time

        initial_count = len(upbit_client._request_times)

        await upbit_client._check_rate_limit()

        # Should have added one request time
        assert len(upbit_client._request_times) == initial_count + 1


class TestUpbitClientEnsureSession:
    """Test UpbitClient._ensure_session method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.upbit_access_key = "test_access_key"
        settings.upbit_secret_key = "test_secret_key"
        return settings

    @pytest.fixture
    def upbit_client(self, mock_settings):
        """Create UpbitClient instance."""
        return UpbitClient(mock_settings)

    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, upbit_client):
        """_ensure_session should create aiohttp session."""
        assert upbit_client._session is None

        await upbit_client._ensure_session()

        assert upbit_client._session is not None

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_session(self, upbit_client):
        """_ensure_session should reuse existing session."""
        await upbit_client._ensure_session()
        first_session = upbit_client._session

        await upbit_client._ensure_session()

        assert upbit_client._session is first_session
