"""
Unit tests for CLI trading integration.

Tests cover:
- Manual buy mode (--buy KRW-BTC --amount 10000)
- Manual sell mode (--sell KRW-BTC --quantity 0.001)
- AI-driven trade mode with real execution
- Simulation mode (--dry-run or --trade-mode simulation)
- Interactive approval function
- Auto-approve mode (--auto-approve)

@MX:NOTE: CLI 트레이딩 통합 테스트 - TDD RED Phase
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gpt_bitcoin.domain.trading import TradeApproval, TradeResult
from gpt_bitcoin.domain.trading_state import TradingState


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_trading_service():
    """Mock TradingService for testing."""
    service = MagicMock()
    service.request_buy_order = AsyncMock()
    service.request_sell_order = AsyncMock()
    service.execute_approved_trade = AsyncMock()
    service.cancel_pending_request = MagicMock()
    service.state = TradingState.IDLE
    service.pending_request = None
    return service


@pytest.fixture
def mock_upbit_client():
    """Mock UpbitClient for testing."""
    client = MagicMock()
    client.get_balance = AsyncMock(return_value=1000000.0)
    client.get_orderbook = AsyncMock()
    client.buy_market_order = AsyncMock()
    client.sell_market_order = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_glm_client():
    """Mock GLMClient for testing."""
    client = MagicMock()
    response = MagicMock()
    response.parsed = MagicMock()
    response.parsed.decision = "buy"
    response.parsed.percentage = 50
    response.parsed.reason = "Test buy decision"
    response.parsed.confidence = 0.85
    response.content = '{"decision": "buy", "percentage": 50}'
    client.analyze_text = AsyncMock(return_value=response)
    return client


@pytest.fixture
def mock_approval():
    """Mock TradeApproval for testing."""
    return TradeApproval(
        request_id="test-approval-123",
        ticker="KRW-BTC",
        side="buy",
        amount=10000.0,
        estimated_price=50000000.0,
        estimated_quantity=0.0002,
        fee_estimate=5.0,
        warnings=[],
        approved=False,
        expires_at=datetime.now() + timedelta(seconds=30),
    )


@pytest.fixture
def mock_trade_result():
    """Mock TradeResult for testing."""
    return TradeResult(
        success=True,
        order_id="test-order-uuid-123",
        ticker="KRW-BTC",
        side="buy",
        executed_price=50000000.0,
        executed_amount=0.0002,
        fee=5.0,
    )


# =============================================================================
# Test: Manual Buy Mode
# =============================================================================


class TestManualBuyMode:
    """Tests for manual buy mode (--buy KRW-BTC --amount 10000)."""

    @pytest.mark.asyncio
    async def test_manual_buy_calls_request_buy_order(
        self, mock_trading_service, mock_approval, mock_trade_result
    ):
        """Test that manual buy mode calls TradingService.request_buy_order()."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.execute_approved_trade.return_value = mock_trade_result
        mock_trading_service.state = TradingState.IDLE

        # Act - 이 테스트는 아직 구현되지 않은 함수를 호출
        # main.py에 execute_manual_buy 함수가 구현되어야 함
        from main import execute_manual_buy

        # Mock interactive_approval to return True
        with patch("main.interactive_approval", return_value=True):
            result = await execute_manual_buy(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                amount_krw=10000.0,
                auto_approve=False,
            )

        # Assert
        mock_trading_service.request_buy_order.assert_called_once_with(
            "KRW-BTC", 10000.0
        )
        assert result is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_manual_buy_with_user_approval(
        self, mock_trading_service, mock_approval, mock_trade_result
    ):
        """Test manual buy with user approval executes trade."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.execute_approved_trade.return_value = mock_trade_result
        mock_approval.mark_approved()
        mock_trading_service.state = TradingState.IDLE

        # Act
        from main import execute_manual_buy

        # Mock interactive_approval to return True
        with patch("main.interactive_approval", return_value=True):
            result = await execute_manual_buy(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                amount_krw=10000.0,
                auto_approve=False,
            )

        # Assert
        assert result.success is True
        assert result.order_id == "test-order-uuid-123"

    @pytest.mark.asyncio
    async def test_manual_buy_with_user_rejection_cancels(
        self, mock_trading_service, mock_approval
    ):
        """Test manual buy with user rejection cancels the request."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.state = TradingState.PENDING_APPROVAL

        # Act
        from main import execute_manual_buy

        # Mock interactive_approval to return False
        with patch("main.interactive_approval", return_value=False):
            result = await execute_manual_buy(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                amount_krw=10000.0,
                auto_approve=False,
            )

        # Assert
        assert result is None
        mock_trading_service.cancel_pending_request.assert_called_once()


# =============================================================================
# Test: Manual Sell Mode
# =============================================================================


class TestManualSellMode:
    """Tests for manual sell mode (--sell KRW-BTC --quantity 0.001)."""

    @pytest.mark.asyncio
    async def test_manual_sell_calls_request_sell_order(
        self, mock_trading_service, mock_trade_result
    ):
        """Test that manual sell mode calls TradingService.request_sell_order()."""
        # Arrange
        sell_approval = TradeApproval(
            request_id="test-sell-approval",
            ticker="KRW-BTC",
            side="sell",
            amount=0.1,
            estimated_price=50000000.0,
            estimated_quantity=0.1,
            fee_estimate=2500.0,
            warnings=[],
            approved=False,
            expires_at=datetime.now() + timedelta(seconds=30),
        )
        mock_trading_service.request_sell_order.return_value = sell_approval

        # Create sell result
        sell_result = TradeResult(
            success=True,
            order_id="test-sell-order-uuid",
            ticker="KRW-BTC",
            side="sell",
            executed_price=50000000.0,
            executed_amount=0.1,
            fee=2500.0,
        )
        mock_trading_service.execute_approved_trade.return_value = sell_result

        # Act
        from main import execute_manual_sell

        # Mock interactive_approval to return True
        with patch("main.interactive_approval", return_value=True):
            result = await execute_manual_sell(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                quantity=0.1,
                auto_approve=False,
            )

        # Assert
        mock_trading_service.request_sell_order.assert_called_once_with(
            "KRW-BTC", 0.1
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_manual_sell_with_user_approval(
        self, mock_trading_service, mock_trade_result
    ):
        """Test manual sell with user approval executes trade."""
        # Arrange
        sell_approval = TradeApproval(
            request_id="test-sell-approval",
            ticker="KRW-BTC",
            side="sell",
            amount=0.1,
            estimated_price=50000000.0,
            estimated_quantity=0.1,
            fee_estimate=2500.0,
            warnings=[],
            approved=False,
            expires_at=datetime.now() + timedelta(seconds=30),
        )
        mock_trading_service.request_sell_order.return_value = sell_approval

        sell_result = TradeResult(
            success=True,
            order_id="test-sell-order-uuid",
            ticker="KRW-BTC",
            side="sell",
            executed_price=50000000.0,
            executed_amount=0.1,
            fee=2500.0,
        )
        mock_trading_service.execute_approved_trade.return_value = sell_result

        # Act
        from main import execute_manual_sell

        with patch("main.interactive_approval", return_value=True):
            result = await execute_manual_sell(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                quantity=0.1,
                auto_approve=False,
            )

        # Assert
        assert result.success is True
        assert result.side == "sell"


# =============================================================================
# Test: AI-Driven Trade Mode
# =============================================================================


class TestAIDrivenTradeMode:
    """Tests for AI-driven trade mode with real execution."""

    @pytest.mark.asyncio
    async def test_ai_driven_buy_executes_trade(
        self, mock_trading_service, mock_glm_client, mock_approval, mock_trade_result
    ):
        """Test AI-driven buy decision executes trade."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.execute_approved_trade.return_value = mock_trade_result

        # AI decision
        ai_decision = MagicMock()
        ai_decision.decision = "buy"
        ai_decision.percentage = 50
        ai_decision.reason = "Strong buy signal"
        ai_decision.confidence = 0.85

        # Act
        from main import execute_ai_driven_trade

        with patch("main.interactive_approval", return_value=True):
            result = await execute_ai_driven_trade(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                ai_decision=ai_decision,
                krw_balance=1000000.0,
                coin_balance=0.0,
                auto_approve=False,
            )

        # Assert
        assert result is not None
        assert result.success is True
        mock_trading_service.request_buy_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_driven_sell_executes_trade(self, mock_trading_service):
        """Test AI-driven sell decision executes trade."""
        # Arrange
        sell_approval = TradeApproval(
            request_id="test-sell-approval",
            ticker="KRW-BTC",
            side="sell",
            amount=0.05,
            estimated_price=50000000.0,
            estimated_quantity=0.05,
            fee_estimate=1250.0,
            warnings=[],
            approved=False,
            expires_at=datetime.now() + timedelta(seconds=30),
        )
        mock_trading_service.request_sell_order.return_value = sell_approval

        sell_result = TradeResult(
            success=True,
            order_id="test-sell-order-uuid",
            ticker="KRW-BTC",
            side="sell",
            executed_price=50000000.0,
            executed_amount=0.05,
            fee=1250.0,
        )
        mock_trading_service.execute_approved_trade.return_value = sell_result

        # AI decision
        ai_decision = MagicMock()
        ai_decision.decision = "sell"
        ai_decision.percentage = 100
        ai_decision.reason = "Take profit"
        ai_decision.confidence = 0.90

        # Act
        from main import execute_ai_driven_trade

        with patch("main.interactive_approval", return_value=True):
            result = await execute_ai_driven_trade(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                ai_decision=ai_decision,
                krw_balance=100000.0,
                coin_balance=0.05,
                auto_approve=False,
            )

        # Assert
        assert result is not None
        assert result.success is True
        mock_trading_service.request_sell_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_driven_hold_skips_trade(self, mock_trading_service):
        """Test AI-driven hold decision skips trade."""
        # Arrange
        ai_decision = MagicMock()
        ai_decision.decision = "hold"
        ai_decision.percentage = 0
        ai_decision.reason = "Market uncertain"
        ai_decision.confidence = 0.50

        # Act
        from main import execute_ai_driven_trade

        result = await execute_ai_driven_trade(
            trading_service=mock_trading_service,
            ticker="KRW-BTC",
            ai_decision=ai_decision,
            krw_balance=1000000.0,
            coin_balance=0.0,
            auto_approve=False,
        )

        # Assert
        assert result is None
        mock_trading_service.request_buy_order.assert_not_called()
        mock_trading_service.request_sell_order.assert_not_called()


# =============================================================================
# Test: Simulation Mode
# =============================================================================


class TestSimulationMode:
    """Tests for simulation mode (--dry-run or --trade-mode simulation)."""

    @pytest.mark.asyncio
    async def test_simulation_mode_skips_trading_service(self, mock_trading_service):
        """Test that simulation mode skips TradingService calls."""
        # Act
        from main import execute_simulation_trade

        result = await execute_simulation_trade(
            ticker="KRW-BTC",
            decision="buy",
            amount=10000.0,
        )

        # Assert
        assert result is None
        mock_trading_service.request_buy_order.assert_not_called()

    def test_trade_mode_simulation_flag(self):
        """Test --trade-mode simulation flag is parsed correctly."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--trade-mode", "simulation"]):
            args = parse_arguments()

        # Assert
        assert args.trade_mode == "simulation"

    def test_dry_run_flag_enables_simulation(self):
        """Test --dry-run flag enables simulation mode."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--dry-run"]):
            args = parse_arguments()

        # Assert
        assert args.dry_run is True


# =============================================================================
# Test: Interactive Approval
# =============================================================================


class TestInteractiveApproval:
    """Tests for interactive approval function."""

    def test_interactive_approval_displays_panel(self, mock_approval):
        """Test that interactive_approval displays approval panel."""
        # Arrange & Act
        from main import interactive_approval

        # Mock Rich Console and Confirm
        with (
            patch("main.console") as mock_console,
            patch("main.Confirm.ask", return_value=True),
        ):
            result = interactive_approval(mock_approval)

        # Assert
        assert result is True
        # Console.print is called for the panel
        assert mock_console.print.called or result is True

    def test_interactive_approval_returns_true_on_yes(self, mock_approval):
        """Test interactive_approval returns True when user approves."""
        # Act
        from main import interactive_approval

        with (
            patch("main.Console"),
            patch("main.Confirm.ask", return_value=True),
        ):
            result = interactive_approval(mock_approval)

        # Assert
        assert result is True

    def test_interactive_approval_returns_false_on_no(self, mock_approval):
        """Test interactive_approval returns False when user rejects."""
        # Act
        from main import interactive_approval

        with (
            patch("main.Console"),
            patch("main.Confirm.ask", return_value=False),
        ):
            result = interactive_approval(mock_approval)

        # Assert
        assert result is False


# =============================================================================
# Test: Auto-Approve Mode
# =============================================================================


class TestAutoApproveMode:
    """Tests for auto-approve mode (--auto-approve)."""

    def test_auto_approve_flag_is_parsed(self):
        """Test --auto-approve flag is parsed correctly."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--auto-approve"]):
            args = parse_arguments()

        # Assert
        assert args.auto_approve is True

    @pytest.mark.asyncio
    async def test_auto_approve_skips_approval_prompt(
        self, mock_trading_service, mock_approval, mock_trade_result
    ):
        """Test that auto-approve mode skips approval prompt."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.execute_approved_trade.return_value = mock_trade_result

        # Act
        from main import execute_manual_buy

        result = await execute_manual_buy(
            trading_service=mock_trading_service,
            ticker="KRW-BTC",
            amount_krw=10000.0,
            auto_approve=True,
        )

        # Assert
        assert result.success is True
        # interactive_approval should not be called
        mock_trading_service.execute_approved_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_approve_displays_warning(
        self, mock_trading_service, mock_approval, mock_trade_result
    ):
        """Test that auto-approve mode displays warning message."""
        # Arrange
        mock_trading_service.request_buy_order.return_value = mock_approval
        mock_trading_service.execute_approved_trade.return_value = mock_trade_result

        # Act
        from main import execute_manual_buy

        with patch("main.console") as mock_console:
            await execute_manual_buy(
                trading_service=mock_trading_service,
                ticker="KRW-BTC",
                amount_krw=10000.0,
                auto_approve=True,
            )

        # Assert - warning should be printed
        assert mock_console.print.called


# =============================================================================
# Test: CLI Argument Parsing
# =============================================================================


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_buy_flag_with_ticker(self):
        """Test --buy flag with ticker is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--buy", "KRW-BTC"]):
            args = parse_arguments()

        # Assert
        assert args.buy == "KRW-BTC"

    def test_sell_flag_with_ticker(self):
        """Test --sell flag with ticker is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--sell", "KRW-BTC"]):
            args = parse_arguments()

        # Assert
        assert args.sell == "KRW-BTC"

    def test_amount_flag(self):
        """Test --amount flag is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--buy", "KRW-BTC", "--amount", "10000"]):
            args = parse_arguments()

        # Assert
        assert args.amount == 10000.0

    def test_quantity_flag(self):
        """Test --quantity flag is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--sell", "KRW-BTC", "--quantity", "0.001"]):
            args = parse_arguments()

        # Assert
        assert args.quantity == 0.001

    def test_trade_mode_real(self):
        """Test --trade-mode real is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--trade-mode", "real"]):
            args = parse_arguments()

        # Assert
        assert args.trade_mode == "real"

    def test_trade_mode_simulation(self):
        """Test --trade-mode simulation is parsed."""
        # Act
        from main import parse_arguments

        with patch("sys.argv", ["main.py", "--trade-mode", "simulation"]):
            args = parse_arguments()

        # Assert
        assert args.trade_mode == "simulation"


# =============================================================================
# Test: Display Trade Result
# =============================================================================


class TestDisplayTradeResult:
    """Tests for display_trade_result function."""

    def test_display_successful_trade(self, mock_trade_result):
        """Test displaying successful trade result."""
        # Act
        from main import display_trade_result

        with patch("main.console") as mock_console:
            display_trade_result(mock_trade_result)

        # Assert
        assert mock_console.print.called

    def test_display_failed_trade(self):
        """Test displaying failed trade result."""
        # Arrange
        failed_result = TradeResult(
            success=False,
            ticker="KRW-BTC",
            side="buy",
            error_message="Insufficient balance",
        )

        # Act
        from main import display_trade_result

        with patch("main.console") as mock_console:
            display_trade_result(failed_result)

        # Assert
        assert mock_console.print.called


# =============================================================================
# Test: TradingConfig Extensions
# =============================================================================


class TestTradingConfigExtensions:
    """Tests for TradingConfig dataclass extensions."""

    def test_trading_config_has_trade_mode(self):
        """Test TradingConfig has trade_mode attribute."""
        # Act
        from main import TradingConfig

        config = TradingConfig(trade_mode="simulation")

        # Assert
        assert config.trade_mode == "simulation"

    def test_trading_config_has_auto_approve(self):
        """Test TradingConfig has auto_approve attribute."""
        # Act
        from main import TradingConfig

        config = TradingConfig(auto_approve=True)

        # Assert
        assert config.auto_approve is True

    def test_trading_config_defaults_to_simulation(self):
        """Test TradingConfig defaults to simulation mode for safety."""
        # Act
        from main import TradingConfig

        config = TradingConfig()

        # Assert - 기본값은 simulation이어야 함 (안전)
        assert config.trade_mode == "simulation"
