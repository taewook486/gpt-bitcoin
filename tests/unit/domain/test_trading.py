"""
Unit tests for TradingService and related domain models.

Tests cover:
- TradeRequest dataclass
- TradeApproval model
- TradeResult model
- TradingService buy/sell workflows
- State transitions
- Error handling
- Edge cases

@MX:NOTE: Tests use asyncio for async TradingService methods.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from gpt_bitcoin.domain.trading import (
    TradeApproval,
    TradeRequest,
    TradeResult,
    TradingService,
)
from gpt_bitcoin.domain.trading_state import TradingState

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_upbit_client():
    """Mock UpbitClient for testing."""
    client = MagicMock()
    client.get_balance = AsyncMock()
    client.get_orderbook = AsyncMock()
    client.buy_market_order = AsyncMock()
    client.sell_market_order = AsyncMock()
    return client


@pytest.fixture
def mock_settings():
    """Mock Settings for testing."""
    settings = MagicMock()
    return settings


@pytest.fixture
def mock_logger():
    """Mock Logger for testing."""
    return MagicMock()


@pytest.fixture
def trading_service(mock_upbit_client, mock_settings, mock_logger):
    """Create TradingService instance with mocked dependencies."""
    return TradingService(mock_upbit_client, mock_settings, mock_logger)


@pytest.fixture
def mock_orderbook():
    """Mock orderbook response."""
    orderbook = MagicMock()
    orderbook.orderbook_units = [MagicMock(ask_price=50000000.0, bid_price=49990000.0)]
    return orderbook


@pytest.fixture
def mock_buy_order_response():
    """Mock successful buy order response."""
    order = MagicMock()
    order.uuid = "test-order-uuid-123"
    order.price = 50000000.0
    order.executed_volume = 0.0002
    order.volume = 0.0002
    order.fee = 5.0
    return order


@pytest.fixture
def mock_sell_order_response():
    """Mock successful sell order response."""
    order = MagicMock()
    order.uuid = "test-order-uuid-456"
    order.price = 50000000.0
    order.executed_volume = 0.0001
    order.volume = 0.0001
    order.fee = 2500.0
    return order


# =============================================================================
# TradeRequest Tests
# =============================================================================


class TestTradeRequest:
    """Tests for TradeRequest dataclass."""

    def test_trade_request_creation(self):
        """Test creating a TradeRequest."""
        request = TradeRequest(
            ticker="KRW-BTC",
            amount=10000.0,
            side="buy",
            timestamp=datetime.now(),
        )
        assert request.ticker == "KRW-BTC"
        assert request.amount == 10000.0
        assert request.side == "buy"

    def test_trade_request_default_timestamp(self):
        """Test that TradeRequest creates timestamp by default."""
        request = TradeRequest(ticker="KRW-BTC", amount=10000.0, side="buy")
        assert request.timestamp is not None
        assert isinstance(request.timestamp, datetime)


# =============================================================================
# TradeApproval Tests
# =============================================================================


class TestTradeApproval:
    """Tests for TradeApproval model."""

    def test_trade_approval_creation(self):
        """Test creating a TradeApproval."""
        approval = TradeApproval(
            request_id="test-123",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
        )
        assert approval.request_id == "test-123"
        assert approval.ticker == "KRW-BTC"
        assert approval.side == "buy"
        assert approval.approved is False

    def test_trade_approval_expiration(self):
        """Test TradeApproval expiration check."""
        # Expired approval
        expired_approval = TradeApproval(
            request_id="expired",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            expires_at=datetime.now() - timedelta(seconds=1),
        )
        assert expired_approval.is_expired() is True

        # Valid approval
        valid_approval = TradeApproval(
            request_id="valid",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
            expires_at=datetime.now() + timedelta(seconds=30),
        )
        assert valid_approval.is_expired() is False

    def test_mark_approved(self):
        """Test marking an approval as approved."""
        approval = TradeApproval(
            request_id="test",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
        )
        assert approval.approved is False
        assert approval.approved_at is None

        approval.mark_approved()

        assert approval.approved is True
        assert approval.approved_at is not None


# =============================================================================
# TradeResult Tests
# =============================================================================


class TestTradeResult:
    """Tests for TradeResult model."""

    def test_successful_trade_result(self):
        """Test creating a successful TradeResult."""
        result = TradeResult(
            success=True,
            order_id="order-123",
            ticker="KRW-BTC",
            side="buy",
            executed_price=50000000.0,
            executed_amount=0.0002,
            fee=5.0,
        )
        assert result.success is True
        assert result.order_id == "order-123"
        assert result.error_message is None

    def test_failed_trade_result(self):
        """Test creating a failed TradeResult."""
        result = TradeResult(
            success=False,
            ticker="KRW-BTC",
            side="buy",
            error_message="Insufficient balance",
        )
        assert result.success is False
        assert result.error_message == "Insufficient balance"
        assert result.order_id is None


# =============================================================================
# TradingService Tests - Buy Order Flow
# =============================================================================


class TestTradingServiceBuyOrder:
    """Tests for TradingService buy order flow."""

    @pytest.mark.asyncio
    async def test_request_buy_order_minimum_amount_validation(
        self,
        trading_service,
        mock_upbit_client,  # noqa: ARG002
    ):
        """Test that buy orders below minimum amount are rejected."""
        # Amount below 5000 KRW should be rejected
        with pytest.raises(ValueError, match="최소 주문 금액"):
            await trading_service.request_buy_order("KRW-BTC", 1000.0)

    @pytest.mark.asyncio
    async def test_request_buy_order_insufficient_balance(self, trading_service, mock_upbit_client):
        """Test that buy orders with insufficient balance are rejected."""
        # Mock balance response (less than requested amount)
        mock_upbit_client.get_balance.return_value = 1000.0

        with pytest.raises(ValueError, match="잔액 부족"):
            await trading_service.request_buy_order("KRW-BTC", 10000.0)

    @pytest.mark.asyncio
    async def test_request_buy_order_success(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test successful buy order approval request."""
        # Mock balance and orderbook
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook

        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        assert approval.ticker == "KRW-BTC"
        assert approval.side == "buy"
        assert approval.amount == 10000.0
        assert approval.approved is False
        assert approval.estimated_price == 50000000.0
        assert approval.estimated_quantity is not None
        assert approval.is_expired() is False
        assert trading_service.state == TradingState.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_execute_approved_buy_order_success(
        self,
        trading_service,
        mock_upbit_client,
        mock_orderbook,
        mock_buy_order_response,
    ):
        """Test successful execution of approved buy order."""
        # First request approval
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Approve and execute
        mock_upbit_client.buy_market_order.return_value = mock_buy_order_response
        approval.mark_approved()

        result = await trading_service.execute_approved_trade(approval)

        assert result.success is True
        assert result.order_id == "test-order-uuid-123"
        assert result.ticker == "KRW-BTC"
        assert result.side == "buy"
        assert trading_service.state == TradingState.IDLE

    @pytest.mark.asyncio
    async def test_execute_buy_order_without_approval_fails(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test that unapproved trades fail."""
        # Request approval but don't approve
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Execute without approval
        result = await trading_service.execute_approved_trade(approval)

        assert result.success is False
        assert "승인되지 않은 거래" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_buy_order_with_expired_approval_fails(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test that expired approvals fail."""
        # Request approval
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Manually expire the approval
        approval.expires_at = datetime.now() - timedelta(seconds=1)
        approval.mark_approved()

        result = await trading_service.execute_approved_trade(approval)

        assert result.success is False
        assert "승인이 만료" in result.error_message
        assert trading_service.state == TradingState.FAILED


# =============================================================================
# TradingService Tests - Sell Order Flow
# =============================================================================


class TestTradingServiceSellOrder:
    """Tests for TradingService sell order flow."""

    @pytest.mark.asyncio
    async def test_request_sell_order_invalid_quantity(
        self,
        trading_service,
        mock_upbit_client,  # noqa: ARG002
    ):
        """Test that sell orders with invalid quantity are rejected."""
        with pytest.raises(ValueError, match="매도 수량은 0보다 커야 합니다"):
            await trading_service.request_sell_order("KRW-BTC", 0.0)

    @pytest.mark.asyncio
    async def test_request_sell_order_insufficient_holdings(
        self, trading_service, mock_upbit_client
    ):
        """Test that sell orders with insufficient holdings are rejected."""
        # Mock balance response (less than requested)
        mock_upbit_client.get_balance.return_value = 0.00001

        with pytest.raises(ValueError, match="보유량 부족"):
            await trading_service.request_sell_order("KRW-BTC", 0.1)

    @pytest.mark.asyncio
    async def test_request_sell_order_success(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test successful sell order approval request."""
        # Mock balance and orderbook
        mock_upbit_client.get_balance.return_value = 0.5
        mock_upbit_client.get_orderbook.return_value = mock_orderbook

        approval = await trading_service.request_sell_order("KRW-BTC", 0.1)

        assert approval.ticker == "KRW-BTC"
        assert approval.side == "sell"
        assert approval.amount == 0.1
        assert approval.approved is False
        assert approval.estimated_price == 49990000.0
        assert trading_service.state == TradingState.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_execute_approved_sell_order_success(
        self,
        trading_service,
        mock_upbit_client,
        mock_orderbook,
        mock_sell_order_response,
    ):
        """Test successful execution of approved sell order."""
        # First request approval
        mock_upbit_client.get_balance.return_value = 0.5
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval = await trading_service.request_sell_order("KRW-BTC", 0.1)

        # Approve and execute
        mock_upbit_client.sell_market_order.return_value = mock_sell_order_response
        approval.mark_approved()

        result = await trading_service.execute_approved_trade(approval)

        assert result.success is True
        assert result.order_id == "test-order-uuid-456"
        assert result.ticker == "KRW-BTC"
        assert result.side == "sell"
        assert trading_service.state == TradingState.IDLE


# =============================================================================
# TradingService Tests - State Management
# =============================================================================


class TestTradingServiceStateManagement:
    """Tests for TradingService state management."""

    @pytest.mark.asyncio
    async def test_state_transitions_during_buy_order(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test state transitions during buy order flow."""
        # Initial state
        assert trading_service.state == TradingState.IDLE

        # Request order
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        await trading_service.request_buy_order("KRW-BTC", 10000.0)
        assert trading_service.state == TradingState.PENDING_APPROVAL

        # Cancel
        trading_service.cancel_pending_request()
        assert trading_service.state == TradingState.IDLE

    @pytest.mark.asyncio
    async def test_cancel_pending_request(self, trading_service, mock_upbit_client, mock_orderbook):
        """Test canceling a pending request."""
        # Create pending request
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        await trading_service.request_buy_order("KRW-BTC", 10000.0)

        assert trading_service.pending_request is not None

        # Cancel
        trading_service.cancel_pending_request()

        assert trading_service.state == TradingState.IDLE
        assert trading_service.pending_request is None

    def test_state_property(self, trading_service):
        """Test state property access."""
        assert trading_service.state == TradingState.IDLE

    def test_pending_request_property(self, trading_service):
        """Test pending_request property access."""
        assert trading_service.pending_request is None


# =============================================================================
# TradingService Tests - Error Handling
# =============================================================================


class TestTradingServiceErrorHandling:
    """Tests for TradingService error handling."""

    @pytest.mark.asyncio
    async def test_buy_order_api_failure(self, trading_service, mock_upbit_client, mock_orderbook):
        """Test handling of API failure during buy order."""
        # Request approval
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Mock API failure
        mock_upbit_client.buy_market_order.side_effect = Exception("API Error")
        approval.mark_approved()

        result = await trading_service.execute_approved_trade(approval)

        assert result.success is False
        assert "API Error" in result.error_message
        assert trading_service.state == TradingState.IDLE

    @pytest.mark.asyncio
    async def test_no_matching_pending_request(
        self,
        trading_service,
        mock_upbit_client,  # noqa: ARG002
    ):
        """Test execution when there's no matching pending request."""
        approval = TradeApproval(
            request_id="fake",
            ticker="KRW-BTC",
            side="buy",
            amount=10000.0,
        )
        approval.mark_approved()

        result = await trading_service.execute_approved_trade(approval)

        assert result.success is False
        assert "대기 중인 주문 요청이 없습니다" in result.error_message


# =============================================================================
# Integration Tests
# =============================================================================


class TestTradingServiceIntegration:
    """Integration-style tests for complete trading flows."""

    @pytest.mark.asyncio
    async def test_complete_buy_workflow(
        self,
        trading_service,
        mock_upbit_client,
        mock_orderbook,
        mock_buy_order_response,
    ):
        """Test complete buy workflow from request to execution."""
        # Setup mocks
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        mock_upbit_client.buy_market_order.return_value = mock_buy_order_response

        # Step 1: Request approval
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)
        assert approval.approved is False
        assert trading_service.state == TradingState.PENDING_APPROVAL

        # Step 2: User approves
        approval.mark_approved()
        assert approval.approved is True

        # Step 3: Execute
        result = await trading_service.execute_approved_trade(approval)
        assert result.success is True
        assert result.order_id == "test-order-uuid-123"

        # Verify state reset
        assert trading_service.state == TradingState.IDLE
        assert trading_service.pending_request is None

    @pytest.mark.asyncio
    async def test_complete_sell_workflow(
        self,
        trading_service,
        mock_upbit_client,
        mock_orderbook,
        mock_sell_order_response,
    ):
        """Test complete sell workflow from request to execution."""
        # Setup mocks
        mock_upbit_client.get_balance.return_value = 0.5
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        mock_upbit_client.sell_market_order.return_value = mock_sell_order_response

        # Step 1: Request approval
        approval = await trading_service.request_sell_order("KRW-BTC", 0.1)
        assert approval.approved is False
        assert trading_service.state == TradingState.PENDING_APPROVAL

        # Step 2: User approves
        approval.mark_approved()

        # Step 3: Execute
        result = await trading_service.execute_approved_trade(approval)
        assert result.success is True
        assert result.order_id == "test-order-uuid-456"

        # Verify state reset
        assert trading_service.state == TradingState.IDLE
        assert trading_service.pending_request is None

    @pytest.mark.asyncio
    async def test_cancel_and_retry_workflow(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test canceling a request and creating a new one."""
        # First request
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook
        approval1 = await trading_service.request_buy_order("KRW-BTC", 10000.0)

        # Cancel
        trading_service.cancel_pending_request()

        # New request
        approval2 = await trading_service.request_buy_order("KRW-BTC", 20000.0)
        assert approval2.request_id != approval1.request_id
        assert approval2.amount == 20000.0


# =============================================================================
# Edge Cases
# =============================================================================


class TestTradingServiceEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_exact_minimum_order_amount(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test order with exactly minimum amount (5000 KRW)."""
        mock_upbit_client.get_balance.return_value = 10000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook

        # Should succeed with exact minimum
        approval = await trading_service.request_buy_order("KRW-BTC", 5000.0)
        assert approval.amount == 5000.0

    @pytest.mark.asyncio
    async def test_orderbook_unavailable_fallback(self, trading_service, mock_upbit_client):
        """Test fallback when orderbook is unavailable."""
        # Mock balance but fail orderbook
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.side_effect = Exception("Orderbook unavailable")

        # Should still succeed without estimation
        approval = await trading_service.request_buy_order("KRW-BTC", 10000.0)
        assert approval.ticker == "KRW-BTC"
        assert approval.estimated_price is None
        assert approval.estimated_quantity is None

    @pytest.mark.asyncio
    async def test_concurrent_requests_not_supported(
        self, trading_service, mock_upbit_client, mock_orderbook
    ):
        """Test that concurrent requests are not supported."""
        mock_upbit_client.get_balance.return_value = 100000.0
        mock_upbit_client.get_orderbook.return_value = mock_orderbook

        # First request
        await trading_service.request_buy_order("KRW-BTC", 10000.0)
        assert trading_service.state == TradingState.PENDING_APPROVAL

        # Second request while first is pending (should fail or override)
        # Current implementation will override the pending request
        await trading_service.request_buy_order("KRW-BTC", 20000.0)
        # State remains PENDING_APPROVAL but request was replaced
        assert trading_service.state == TradingState.PENDING_APPROVAL
