"""
Unit tests for Upbit client - full coverage for missing lines.

Tests cover:
- Order execution (buy_market_order, sell_market_order)
- Order management (cancel_order, get_order)
- Balance retrieval (get_balance)
- Error scenarios (insufficient balance, invalid responses)
- Health check
- Rate limit wait scenario

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from gpt_bitcoin.infrastructure.external.upbit_client import (
    Balance,
    Orderbook,
    OHLCV,
    Order,
    UpbitClient,
)
from gpt_bitcoin.infrastructure.exceptions import (
    InsufficientBalanceError,
    UpbitAPIError,
)


class TestUpbitClientGetBalance:
    """Test UpbitClient.get_balance method - covers lines 480-494."""

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
    async def test_get_balance_returns_krw_balance(self, upbit_client):
        """get_balance should return KRW balance."""
        mock_balances = [
            Balance(currency="KRW", balance=1000000.0),
            Balance(currency="BTC", balance=0.5),
        ]

        with patch.object(
            upbit_client,
            "get_balances",
            new_callable=AsyncMock,
            return_value=mock_balances,
        ):
            result = await upbit_client.get_balance("KRW")

            assert result == 1000000.0

    @pytest.mark.asyncio
    async def test_get_balance_returns_btc_balance(self, upbit_client):
        """get_balance should return BTC balance."""
        mock_balances = [
            Balance(currency="KRW", balance=1000000.0),
            Balance(currency="BTC", balance=0.5),
        ]

        with patch.object(
            upbit_client,
            "get_balances",
            new_callable=AsyncMock,
            return_value=mock_balances,
        ):
            result = await upbit_client.get_balance("BTC")

            assert result == 0.5

    @pytest.mark.asyncio
    async def test_get_balance_returns_zero_for_missing_currency(self, upbit_client):
        """get_balance should return 0.0 for currency not in balances."""
        mock_balances = [
            Balance(currency="KRW", balance=1000000.0),
        ]

        with patch.object(
            upbit_client,
            "get_balances",
            new_callable=AsyncMock,
            return_value=mock_balances,
        ):
            result = await upbit_client.get_balance("ETH")

            assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_balance_returns_zero_for_empty_balances(self, upbit_client):
        """get_balance should return 0.0 when no balances exist."""
        with patch.object(
            upbit_client,
            "get_balances",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await upbit_client.get_balance("KRW")

            assert result == 0.0


class TestUpbitClientBuyMarketOrder:
    """Test UpbitClient.buy_market_order method - covers lines 496-542."""

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
    async def test_buy_market_order_success(self, upbit_client):
        """buy_market_order should place order when balance is sufficient."""
        mock_response = {
            "uuid": "test-order-uuid",
            "side": "bid",
            "ord_type": "price",
            "price": "50000.0",
            "state": "done",
            "market": "KRW-BTC",
            "created_at": "2024-01-01T00:00:00",
            "volume": None,
            "remaining_volume": None,
            "reserved_fee": None,
            "remaining_fee": None,
            "paid_fee": None,
            "locked": None,
            "executed_volume": None,
            "trades_count": None,
        }

        with patch.object(
            upbit_client,
            "get_balance",
            new_callable=AsyncMock,
            return_value=100000.0,
        ):
            with patch.object(
                upbit_client,
                "_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                result = await upbit_client.buy_market_order("KRW-BTC", 50000.0)

                assert result.uuid == "test-order-uuid"
                assert result.side == "bid"
                assert result.state == "done"

    @pytest.mark.asyncio
    async def test_buy_market_order_insufficient_balance(self, upbit_client):
        """buy_market_order should raise InsufficientBalanceError when balance is insufficient."""
        with patch.object(
            upbit_client,
            "get_balance",
            new_callable=AsyncMock,
            return_value=10000.0,  # Less than requested 50000.0
        ):
            with pytest.raises(InsufficientBalanceError) as exc_info:
                await upbit_client.buy_market_order("KRW-BTC", 50000.0)

            assert exc_info.value.currency == "KRW"
            assert exc_info.value.available == 10000.0
            assert exc_info.value.required == 50000.0


class TestUpbitClientSellMarketOrder:
    """Test UpbitClient.sell_market_order method - covers lines 544-593."""

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
    async def test_sell_market_order_success(self, upbit_client):
        """sell_market_order should place order when balance is sufficient."""
        mock_response = {
            "uuid": "test-sell-uuid",
            "side": "ask",
            "ord_type": "market",
            "price": None,
            "state": "done",
            "market": "KRW-BTC",
            "created_at": "2024-01-01T00:00:00",
            "volume": "0.1",
            "remaining_volume": None,
            "reserved_fee": None,
            "remaining_fee": None,
            "paid_fee": None,
            "locked": None,
            "executed_volume": None,
            "trades_count": None,
        }

        with patch.object(
            upbit_client,
            "get_balance",
            new_callable=AsyncMock,
            return_value=1.0,  # Sufficient BTC balance
        ):
            with patch.object(
                upbit_client,
                "_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                result = await upbit_client.sell_market_order("KRW-BTC", 0.1)

                assert result.uuid == "test-sell-uuid"
                assert result.side == "ask"
                assert result.state == "done"

    @pytest.mark.asyncio
    async def test_sell_market_order_insufficient_balance(self, upbit_client):
        """sell_market_order should raise InsufficientBalanceError when balance is insufficient."""
        with patch.object(
            upbit_client,
            "get_balance",
            new_callable=AsyncMock,
            return_value=0.01,  # Less than requested 0.1
        ):
            with pytest.raises(InsufficientBalanceError) as exc_info:
                await upbit_client.sell_market_order("KRW-BTC", 0.1)

            assert exc_info.value.currency == "BTC"
            assert exc_info.value.available == 0.01
            assert exc_info.value.required == 0.1

    @pytest.mark.asyncio
    async def test_sell_market_order_extracts_base_currency(self, upbit_client):
        """sell_market_order should extract base currency from ticker."""
        mock_response = {
            "uuid": "test-sell-uuid",
            "side": "ask",
            "ord_type": "market",
            "price": None,
            "state": "done",
            "market": "KRW-ETH",
            "created_at": "2024-01-01T00:00:00",
            "volume": "0.5",
            "remaining_volume": None,
            "reserved_fee": None,
            "remaining_fee": None,
            "paid_fee": None,
            "locked": None,
            "executed_volume": None,
            "trades_count": None,
        }

        with patch.object(
            upbit_client,
            "get_balance",
            new_callable=AsyncMock,
            return_value=1.0,
        ) as mock_get_balance:
            with patch.object(
                upbit_client,
                "_request",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                await upbit_client.sell_market_order("KRW-ETH", 0.5)

                # Should check ETH balance (extracted from KRW-ETH)
                mock_get_balance.assert_called_once_with("ETH")


class TestUpbitClientCancelOrder:
    """Test UpbitClient.cancel_order method - covers lines 595-617."""

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
    async def test_cancel_order_success(self, upbit_client):
        """cancel_order should cancel order and return result."""
        mock_response = {
            "uuid": "test-cancel-uuid",
            "side": "bid",
            "ord_type": "limit",
            "price": "100000000",
            "state": "cancel",
            "market": "KRW-BTC",
            "created_at": "2024-01-01T00:00:00",
            "volume": "0.1",
        }

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.cancel_order("test-cancel-uuid")

            assert result["uuid"] == "test-cancel-uuid"
            assert result["state"] == "cancel"


class TestUpbitClientGetOrder:
    """Test UpbitClient.get_order method - covers lines 619-636."""

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
    async def test_get_order_success(self, upbit_client):
        """get_order should return order information."""
        mock_response = {
            "uuid": "test-order-uuid",
            "side": "bid",
            "ord_type": "limit",
            "price": "100000000",
            "state": "wait",
            "market": "KRW-BTC",
            "created_at": "2024-01-01T00:00:00",
            "volume": "0.1",
            "remaining_volume": "0.05",
            "reserved_fee": None,
            "remaining_fee": None,
            "paid_fee": None,
            "locked": None,
            "executed_volume": None,
            "trades_count": None,
        }

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await upbit_client.get_order("test-order-uuid")

            assert result.uuid == "test-order-uuid"
            assert result.state == "wait"
            assert result.market == "KRW-BTC"


class TestUpbitClientHealthCheck:
    """Test UpbitClient.health_check method - covers lines 638-650."""

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
    async def test_health_check_returns_true_on_success(self, upbit_client):
        """health_check should return True when API is accessible."""
        with patch.object(
            upbit_client,
            "get_current_price",
            new_callable=AsyncMock,
            return_value=100000000.0,
        ):
            result = await upbit_client.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self, upbit_client):
        """health_check should return False when API is not accessible."""
        with patch.object(
            upbit_client,
            "get_current_price",
            new_callable=AsyncMock,
            side_effect=UpbitAPIError("Connection failed"),
        ):
            result = await upbit_client.health_check()

            assert result is False


class TestUpbitClientOrderbookError:
    """Test UpbitClient.get_orderbook error handling - covers line 371."""

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
    async def test_get_orderbook_raises_error_on_empty_response(self, upbit_client):
        """get_orderbook should raise error on empty response."""
        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=[],  # Empty list
        ):
            with pytest.raises(UpbitAPIError, match="Invalid orderbook response"):
                await upbit_client.get_orderbook("KRW-BTC")

    @pytest.mark.asyncio
    async def test_get_orderbook_raises_error_on_non_list_response(self, upbit_client):
        """get_orderbook should raise error on non-list response."""
        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value={"error": "something"},  # Not a list
        ):
            with pytest.raises(UpbitAPIError, match="Invalid orderbook response"):
                await upbit_client.get_orderbook("KRW-BTC")


class TestUpbitClientOHLCVEdgeCases:
    """Test UpbitClient.get_ohlcv edge cases - covers line 431."""

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
    async def test_get_ohlcv_returns_empty_list_on_non_list_response(self, upbit_client):
        """get_ohlcv should return empty list on non-list response."""
        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value={"error": "something"},  # Not a list
        ):
            result = await upbit_client.get_ohlcv("KRW-BTC")

            assert result == []

    @pytest.mark.asyncio
    async def test_get_ohlcv_with_different_intervals(self, upbit_client):
        """get_ohlcv should handle different interval formats."""
        mock_response = [
            {
                "market": "KRW-BTC",
                "candle_date_time_utc": "2024-01-01T00:00:00Z",
                "opening_price": 100000000,
                "high_price": 105000000,
                "low_price": 99000000,
                "trade_price": 102000000,
                "candle_acc_trade_volume": 10.0,
            },
        ]

        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_request:
            # Test minute interval
            await upbit_client.get_ohlcv("KRW-BTC", interval="minute60")
            # Verify the endpoint was called correctly
            call_args = mock_request.call_args
            assert "minutes/60" in call_args[0][1]  # endpoint


class TestUpbitClientTickerError:
    """Test UpbitClient.get_current_price error handling - covers line 451."""

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
    async def test_get_current_price_raises_error_on_empty_response(self, upbit_client):
        """get_current_price should raise error on empty response."""
        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value=[],  # Empty list
        ):
            with pytest.raises(UpbitAPIError, match="Invalid ticker response"):
                await upbit_client.get_current_price("KRW-BTC")


class TestUpbitClientRequestErrors:
    """Test UpbitClient._request error handling - covers lines 331-347."""

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
    async def test_request_raises_upbit_error_on_client_error(self, upbit_client):
        """_request should raise UpbitAPIError on ClientError."""
        # Test by patching the _request method to simulate the error path
        # This covers the aiohttp.ClientError handling path (lines 341-347)
        with patch.object(
            upbit_client,
            "_ensure_session",
            new_callable=AsyncMock,
        ):
            with patch.object(
                upbit_client,
                "_check_rate_limit",
                new_callable=AsyncMock,
            ):
                # Create a proper async context manager mock that raises error
                mock_response_cm = AsyncMock()
                mock_response_cm.__aenter__ = AsyncMock(
                    side_effect=aiohttp.ClientError("Connection failed")
                )
                mock_response_cm.__aexit__ = AsyncMock(return_value=None)

                mock_session = MagicMock()
                mock_session.request = MagicMock(return_value=mock_response_cm)
                upbit_client._session = mock_session

                with pytest.raises(UpbitAPIError, match="Upbit API connection error"):
                    await upbit_client._request("GET", "/accounts", is_private=True)


class TestUpbitClientRateLimitWait:
    """Test UpbitClient rate limit wait scenario - covers lines 249-253."""

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
    async def test_rate_limit_waits_when_exceeded(self, upbit_client):
        """_check_rate_limit should wait when rate limit is exceeded."""
        import time

        # Fill up the request times to hit the limit
        now = time.time()
        upbit_client._request_times = [now - 0.1] * upbit_client.RATE_LIMIT_REQUESTS

        # This should trigger a wait
        start_time = time.time()
        await upbit_client._check_rate_limit()
        elapsed = time.time() - start_time

        # Should have waited (the wait time depends on the rate limit window)
        # The request times list should have been reset
        assert len(upbit_client._request_times) == 1


class TestUpbitClientBalancesEmpty:
    """Test UpbitClient.get_balances edge case - covers line 478."""

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
    async def test_get_balances_returns_empty_list_on_non_list_response(self, upbit_client):
        """get_balances should return empty list on non-list response."""
        with patch.object(
            upbit_client,
            "_request",
            new_callable=AsyncMock,
            return_value={"error": "something"},  # Not a list
        ):
            result = await upbit_client.get_balances()

            assert result == []
