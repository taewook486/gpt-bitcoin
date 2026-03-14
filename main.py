"""
GPT Bitcoin Auto-Trading System - Modern Entry Point

모듈형 아키텍처를 기반으로 한 최신 자동거래 시스템 진입점.

Features:
- 암호화폐 선택 (BTC, ETH, SOL, XRP, ADA, DOGE, AVAX, DOT)
- 거래 전략 선택 (Conservative, Balanced, Aggressive)
- GLM-5/GLM-4.6V 모델 통합
- 구조화된 로깅 및 상관관계 ID 추적

Usage:
    # Basic usage (interactive mode)
    python main.py

    # Command-line arguments
    python main.py --coin BTC --strategy balanced
    python main.py --coin ETH --strategy aggressive --dry-run

    # List available options
    python main.py --list-coins
    python main.py --list-strategies

Author: GPT Bitcoin Trading System
Version: 4.0.0
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from gpt_bitcoin.config.settings import get_settings
from gpt_bitcoin.dependencies.container import get_container
from gpt_bitcoin.domain import (
    CoinManager,
    Cryptocurrency,
    StrategyManager,
    TradingStrategy,
)
from gpt_bitcoin.infrastructure.instructions import InstructionManager
from gpt_bitcoin.infrastructure.logging import get_logger
from gpt_bitcoin.infrastructure.observability.tracing import set_correlation_id

if TYPE_CHECKING:
    from gpt_bitcoin.domain.security import SecurityService
    from gpt_bitcoin.domain.trading import TradeApproval, TradeResult, TradingService
    from gpt_bitcoin.infrastructure.external.glm_client import GLMClient

logger = get_logger(__name__)

# Rich console for formatted output
console = Console()


# =============================================================================
# ASCII Art Banner
# =============================================================================

BANNER = """
============================================================
  GPT Bitcoin Auto-Trading System v4.0
  Modular Architecture with GLM-5/GLM-4.6V
============================================================
"""


# =============================================================================
# Configuration Classes
# =============================================================================


class TradingConfig:
    """
    Trading session configuration.

    Attributes:
        coin: Selected cryptocurrency
        strategy: Trading strategy
        testnet_mode: If True, use testnet (MockUpbitClient)
        dry_run: If True, simulate trades without execution
        instruction_version: AI instruction version (v1, v2, v3)
        trade_mode: "simulation" or "real" (defaults to simulation for safety)
        auto_approve: If True, skip approval prompts (dangerous)
    """

    def __init__(
        self,
        coin: Cryptocurrency | None = None,
        strategy: TradingStrategy | None = None,
        testnet_mode: bool = False,
        dry_run: bool = False,
        instruction_version: str | None = None,
        trade_mode: Literal["simulation", "real"] = "simulation",
        auto_approve: bool = False,
    ):
        # Initialize managers
        self.coin_manager = CoinManager()
        self.strategy_manager = StrategyManager()

        # Set coin if provided
        if coin is not None:
            self.coin_manager.set_coin(coin)

        # Set strategy if provided
        if strategy is not None:
            self.strategy_manager.set_strategy(strategy)

        # @MX:WARN: 기본값은 simulation 모드로 안전하게 설정
        # @MX:REASON: 실거래 모드는 명시적으로 --trade-mode real을 지정해야 함
        self.testnet_mode = testnet_mode
        self.dry_run = dry_run
        self.instruction_version = instruction_version or "v1"
        self.trade_mode = trade_mode
        self.auto_approve = auto_approve

    @property
    def coin(self) -> Cryptocurrency:
        """Get selected cryptocurrency."""
        return self.coin_manager.get_current_coin()

    @property
    def strategy(self) -> TradingStrategy:
        """Get trading strategy."""
        return self.strategy_manager.current_strategy

    def display_summary(self) -> None:
        """Display configuration summary."""
        coin_info = self.coin_manager.get_coin_info(self.coin)
        strategy_config = self.strategy_manager.get_config()

        # Version descriptions
        version_info = {
            "v1": "기본 (Basic)",
            "v2": "멀티코인+뉴스 (Multi-coin+News)",
            "v3": "비전 분석 (Vision Analysis)",
        }

        print("\n" + "-" * 60)
        print("  거래 설정 요약 (Trading Configuration Summary)")
        print("-" * 60)
        print(f"  암호화폐 (Coin):       {coin_info['name']} ({self.coin.value})")
        print(f"  전략 (Strategy):      {self.strategy.value}")
        print(
            f"  AI 지침 버전:         {self.instruction_version} - {version_info.get(self.instruction_version, '')}"
        )
        mode_str = (
            "테스트넷 (Testnet)"
            if self.testnet_mode
            else ("시뮬레이션 (Dry Run)" if self.dry_run else "실거래 (Live Trading)")
        )
        print(f"  모드 (Mode):          {mode_str}")
        print("\n  전략 파라미터 (Strategy Parameters):")
        print(f"    - 최대 매수 비율:    {strategy_config.max_buy_percentage}%")
        print(f"    - 최대 매도 비율:    {strategy_config.max_sell_percentage}%")
        print(f"    - RSI 과매도 기준:   {strategy_config.rsi_oversold}")
        print(f"    - RSI 과매수 기준:   {strategy_config.rsi_overbought}")
        print(f"    - 손절률:            {strategy_config.stop_loss_percentage}%")
        print(f"    - 익절률:            {strategy_config.take_profit_percentage}%")
        print("-" * 60)


# =============================================================================
# Interactive Mode
# =============================================================================


def select_coin_interactive() -> Cryptocurrency:
    """
    Interactive cryptocurrency selection.

    Returns:
        Selected Cryptocurrency enum value
    """
    manager = CoinManager()
    coins = manager.get_supported_coins()

    print("\n" + "-" * 60)
    print("  암호화폐 선택 (Select Cryptocurrency)")
    print("-" * 60)

    for i, coin in enumerate(coins, 1):
        info = manager.get_coin_info(coin)
        print(f"  {i}. {info['name']:12} ({coin.value:10}) - {info['description']}")

    while True:
        try:
            choice = input(f"\n선택 (1-{len(coins)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(coins):
                selected = coins[index]
                info = manager.get_coin_info(selected)
                print(f"\n선택됨: {info['name']} ({selected.value})")
                return selected
            print("잘못된 선택입니다. 다시 선택해주세요.")
        except (ValueError, KeyboardInterrupt):
            print("\n기본값(BTC)으로 설정합니다.")
            return Cryptocurrency.BTC


def select_strategy_interactive() -> TradingStrategy:
    """
    Interactive trading strategy selection.

    Returns:
        Selected TradingStrategy enum value
    """
    print("\n" + "-" * 60)
    print("  거래 전략 선택 (Select Trading Strategy)")
    print("-" * 60)

    strategies = [
        (TradingStrategy.conservative, "Conservative", "안정 지향, 낮은 리스크"),
        (TradingStrategy.balanced, "Balanced", "균형 잡힌 리스크/수익"),
        (TradingStrategy.aggressive, "Aggressive", "공격적인 거래, 높은 수익 목표"),
    ]

    for i, (strategy, name, desc) in enumerate(strategies, 1):
        strategy_manager = StrategyManager(strategy=strategy)
        config = strategy_manager.get_config_for_strategy(strategy)
        print(f"\n  {i}. {name}")
        print(f"     {desc}")
        print(
            f"     최대 매수: {config.max_buy_percentage}% | 최대 매도: {config.max_sell_percentage}%"
        )

    while True:
        try:
            choice = input("\n선택 (1-3): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(strategies):
                selected = strategies[index][0]
                print(f"\n선택됨: {selected.value}")
                return selected
            print("잘못된 선택입니다. 다시 선택해주세요.")
        except (ValueError, KeyboardInterrupt):
            print("\n기본값(balanced)으로 설정합니다.")
            return TradingStrategy.balanced


def confirm_dry_run() -> bool:
    """
    Ask user if they want to run in dry-run mode.

    Returns:
        True if dry-run mode selected
    """
    while True:
        try:
            choice = input("\n시뮬레이션 모드로 실행하시겠습니까? (y/N): ").strip().lower()
            if choice in ("y", "yes", "예"):
                return True
            elif choice in ("n", "no", "아니오", ""):
                return False
            print("y 또는 n을 입력해주세요.")
        except KeyboardInterrupt:
            print("\n시뮬레이션 모드로 설정합니다.")
            return True


# =============================================================================
# Interactive Approval
# =============================================================================


def interactive_approval(approval: TradeApproval) -> bool:
    """
    Display approval panel and get user confirmation.

    Args:
        approval: Trade approval request to display

    Returns:
        True if user approves, False otherwise

    @MX:NOTE: 사용자 승인을 받기 위한 대화형 함수
    """
    # Build approval panel content
    side_korean = "매수" if approval.side == "buy" else "매도"
    content_lines = [
        f"[bold]거래 유형:[/] {side_korean} ({approval.side.upper()})",
        f"[bold]티커:[/] {approval.ticker}",
        f"[bold]수량/금액:[/] {approval.amount:,.8f}"
        if approval.side == "sell"
        else f"[bold]금액:[/] {approval.amount:,.0f} KRW",
    ]

    if approval.estimated_price:
        content_lines.append(f"[bold]예상 가격:[/] {approval.estimated_price:,.0f} KRW")
    if approval.estimated_quantity:
        content_lines.append(f"[bold]예상 수량:[/] {approval.estimated_quantity:.8f}")
    if approval.fee_estimate:
        content_lines.append(f"[bold]예상 수수료:[/] {approval.fee_estimate:,.2f} KRW")

    content_lines.append("")
    content_lines.append(f"[dim]요청 ID: {approval.request_id}[/]")
    if approval.expires_at:
        content_lines.append(f"[dim]만료: {approval.expires_at.strftime('%H:%M:%S')}[/]")

    # Display panel
    panel = Panel(
        "\n".join(content_lines),
        title="[bold yellow]거래 승인 요청[/]",
        border_style="yellow",
    )
    console.print(panel)

    # Get user confirmation
    try:
        result = Confirm.ask(
            "\n이 거래를 승인하시겠습니까?",
            default=False,
        )
        return result
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]승인이 취소되었습니다.[/]")
        return False


# =============================================================================
# Trade Execution Helpers
# =============================================================================


async def execute_manual_buy(
    trading_service: TradingService,
    ticker: str,
    amount_krw: float,
    auto_approve: bool = False,
) -> TradeResult | None:
    """
    Execute a manual buy order with approval workflow.

    Args:
        trading_service: Trading service instance
        ticker: Market ticker (e.g., "KRW-BTC")
        amount_krw: Amount in KRW to buy
        auto_approve: If True, skip approval prompt

    Returns:
        TradeResult on success, None on cancellation

    @MX:ANCHOR: Manual buy entry point
        fan_in: 2 (CLI, test)
        @MX:REASON: Centralizes manual buy logic with approval workflow
    """
    try:
        # Request buy order approval
        approval = await trading_service.request_buy_order(ticker, amount_krw)

        # Handle auto-approve mode
        if auto_approve:
            console.print(
                Panel(
                    "[bold red]자동 승인 모드 활성화됨[/]\n사용자 승인 없이 거래가 실행됩니다.",
                    title="[red]경고[/]",
                    border_style="red",
                )
            )
            approval.mark_approved()
        else:
            # Get user approval
            approved = interactive_approval(approval)

            if not approved:
                trading_service.cancel_pending_request()
                console.print("[yellow]거래가 취소되었습니다.[/]")
                return None

            approval.mark_approved()

        # Execute approved trade
        result = await trading_service.execute_approved_trade(approval)
        display_trade_result(result)
        return result

    except ValueError as e:
        console.print(f"[red]오류: {e}[/]")
        return None
    except Exception as e:
        logger.error("Manual buy failed", error=str(e), ticker=ticker)
        console.print(f"[red]거래 실행 중 오류 발생: {e}[/]")
        return None


async def execute_manual_sell(
    trading_service: TradingService,
    ticker: str,
    quantity: float,
    auto_approve: bool = False,
) -> TradeResult | None:
    """
    Execute a manual sell order with approval workflow.

    Args:
        trading_service: Trading service instance
        ticker: Market ticker (e.g., "KRW-BTC")
        quantity: Quantity of coins to sell
        auto_approve: If True, skip approval prompt

    Returns:
        TradeResult on success, None on cancellation

    @MX:ANCHOR: Manual sell entry point
        fan_in: 2 (CLI, test)
        @MX:REASON: Centralizes manual sell logic with approval workflow
    """
    try:
        # Request sell order approval
        approval = await trading_service.request_sell_order(ticker, quantity)

        # Handle auto-approve mode
        if auto_approve:
            console.print(
                Panel(
                    "[bold red]자동 승인 모드 활성화됨[/]\n사용자 승인 없이 거래가 실행됩니다.",
                    title="[red]경고[/]",
                    border_style="red",
                )
            )
            approval.mark_approved()
        else:
            # Get user approval
            approved = interactive_approval(approval)

            if not approved:
                trading_service.cancel_pending_request()
                console.print("[yellow]거래가 취소되었습니다.[/]")
                return None

            approval.mark_approved()

        # Execute approved trade
        result = await trading_service.execute_approved_trade(approval)
        display_trade_result(result)
        return result

    except ValueError as e:
        console.print(f"[red]오류: {e}[/]")
        return None
    except Exception as e:
        logger.error("Manual sell failed", error=str(e), ticker=ticker)
        console.print(f"[red]거래 실행 중 오류 발생: {e}[/]")
        return None


async def execute_ai_driven_trade(
    trading_service: TradingService,
    ticker: str,
    ai_decision: Any,
    krw_balance: float,
    coin_balance: float,
    auto_approve: bool = False,
) -> TradeResult | None:
    """
    Execute an AI-driven trade based on AI decision.

    Args:
        trading_service: Trading service instance
        ticker: Market ticker (e.g., "KRW-BTC")
        ai_decision: AI trading decision object
        krw_balance: Current KRW balance
        coin_balance: Current coin balance
        auto_approve: If True, skip approval prompt

    Returns:
        TradeResult on success, None on hold or cancellation

    @MX:NOTE: AI 결정에 따른 자동 거래 실행 함수
    """
    # Skip hold decisions
    if ai_decision.decision == "hold":
        console.print("[dim]AI 결정: 보류 (HOLD)[/]")
        return None

    try:
        if ai_decision.decision == "buy":
            # Calculate buy amount from percentage
            buy_amount = krw_balance * (ai_decision.percentage / 100)
            console.print(
                f"\n[cyan]AI 결정: 매수 {ai_decision.percentage}% ({buy_amount:,.0f} KRW)[/]"
            )
            console.print(f"[dim]이유: {ai_decision.reason}[/]")

            return await execute_manual_buy(
                trading_service=trading_service,
                ticker=ticker,
                amount_krw=buy_amount,
                auto_approve=auto_approve,
            )

        elif ai_decision.decision == "sell":
            # Calculate sell quantity from percentage
            sell_quantity = coin_balance * (ai_decision.percentage / 100)
            console.print(
                f"\n[cyan]AI 결정: 매도 {ai_decision.percentage}% ({sell_quantity:.8f})[/]"
            )
            console.print(f"[dim]이유: {ai_decision.reason}[/]")

            return await execute_manual_sell(
                trading_service=trading_service,
                ticker=ticker,
                quantity=sell_quantity,
                auto_approve=auto_approve,
            )

    except Exception as e:
        logger.error("AI-driven trade failed", error=str(e), ticker=ticker)
        console.print(f"[red]AI 거래 실행 중 오류 발생: {e}[/]")
        return None

    return None


async def execute_simulation_trade(
    ticker: str,
    decision: str,
    amount: float,
) -> None:
    """
    Execute a simulated trade without actual API calls.

    Args:
        ticker: Market ticker
        decision: Trade decision ("buy" or "sell")
        amount: Trade amount

    @MX:NOTE: 시뮬레이션 모드 - 실제 거래 없이 로그만 출력
    """
    decision_korean = "매수" if decision == "buy" else "매도"

    console.print(
        Panel(
            f"[bold cyan]시뮬레이션 모드[/]\n\n"
            f"거래 유형: {decision_korean}\n"
            f"티커: {ticker}\n"
            f"금액/수량: {amount:,.8f}\n\n"
            f"[dim]실제 거래는 실행되지 않습니다.[/]",
            title="[cyan]시뮬레이션 거래[/]",
            border_style="cyan",
        )
    )

    logger.info(
        "Simulation trade executed",
        ticker=ticker,
        decision=decision,
        amount=amount,
    )

    return None


def display_trade_result(result: TradeResult) -> None:
    """
    Display trade execution result.

    Args:
        result: Trade execution result

    @MX:NOTE: 거래 결과를 Rich 패널로 표시
    """
    if result.success:
        side_korean = "매수" if result.side == "buy" else "매도"
        content_lines = [
            "[bold green]거래 성공[/]",
            "",
            f"[bold]주문 ID:[/] {result.order_id}",
            f"[bold]거래 유형:[/] {side_korean}",
            f"[bold]티커:[/] {result.ticker}",
        ]

        if result.executed_price:
            content_lines.append(f"[bold]실행 가격:[/] {result.executed_price:,.0f} KRW")
        if result.executed_amount:
            content_lines.append(f"[bold]실행 수량:[/] {result.executed_amount:.8f}")
        if result.fee:
            content_lines.append(f"[bold]수수료:[/] {result.fee:,.2f} KRW")

        panel = Panel(
            "\n".join(content_lines),
            title="[green]거래 완료[/]",
            border_style="green",
        )
    else:
        panel = Panel(
            f"[bold red]거래 실패[/]\n\n[red]{result.error_message or '알 수 없는 오류'}[/]",
            title="[red]오류[/]",
            border_style="red",
        )

    console.print(panel)


# =============================================================================
# Main Trading Application
# =============================================================================


async def run_trading_session(config: TradingConfig) -> None:
    """
    Run a trading session with the given configuration.

    Args:
        config: Trading configuration
    """
    # Set correlation ID for this session
    set_correlation_id(f"trading-{config.coin.symbol}-{config.strategy.value}")

    logger.info(
        "Trading session started",
        coin=config.coin.value,
        strategy=config.strategy.value,
        dry_run=config.dry_run,
    )

    # Get container and clients
    container = get_container()
    settings = get_settings()
    glm_client: GLMClient = container.glm_client()

    # @MX:NOTE: testnet_mode에 따라 적절한 클라이언트 선택
    if config.testnet_mode:
        upbit_client = container.mock_upbit_client()
        logger.info("Using MockUpbitClient (testnet mode)")
    else:
        upbit_client = container.upbit_client()
        logger.info("Using UpbitClient (production mode)")

    try:
        # Display configuration
        config.display_summary()

        # Get strategy configuration
        strategy_config = config.strategy_manager.get_config()

        # Fetch market data
        ticker = config.coin_manager.get_ticker()
        logger.info("Fetching market data", ticker=ticker)

        async with upbit_client:
            ohlcv_data = await upbit_client.get_ohlcv(
                ticker=ticker,
                interval="day",
                count=30,
            )
            current_price = await upbit_client.get_current_price(ticker=ticker)

        if not ohlcv_data:
            logger.error("No market data available", ticker=ticker)
            return

        logger.info(
            "Current price retrieved",
            ticker=ticker,
            price=current_price,
        )

        # Calculate price change
        price_change = 0.0
        if len(ohlcv_data) >= 2:
            price_change = ((current_price / ohlcv_data[-1].close) - 1) * 100

        # Calculate average price for RSI approximation
        avg_recent_price = sum(candle.close for candle in ohlcv_data[-14:]) / min(
            len(ohlcv_data), 14
        )

        # Load instructions using InstructionManager
        instruction_manager = InstructionManager(base_path=Path(__file__).parent)

        # Determine instruction file based on version
        inst_file = "instructions.md"
        if config.instruction_version == "v2":
            inst_file = "instructions_v2.md"
        elif config.instruction_version == "v3":
            inst_file = "instructions_v3.md"

        # Build context-specific instructions
        base_instructions = instruction_manager.load(inst_file)
        if base_instructions is None:
            # Fallback to simple prompt if instructions file not found
            base_instructions = "You are a cryptocurrency trading assistant."

        # Prepare analysis prompt with context
        context_addition = f"""

## Current Context

Current Strategy: {config.strategy.value}
Max Buy Percentage: {strategy_config.max_buy_percentage}%
Max Sell Percentage: {strategy_config.max_sell_percentage}%
RSI Oversold Threshold: {strategy_config.rsi_oversold}
RSI Overbought Threshold: {strategy_config.rsi_overbought}

Cryptocurrency: {config.coin.value}
Current Price: {current_price:,.0f} KRW

## Response Format

Respond with a JSON object containing:
{{
    "decision": "buy" | "sell" | "hold",
    "percentage": <number 0-100>,
    "reason": "<explanation>",
    "confidence": <number 0-1>
}}
"""

        system_prompt = base_instructions + context_addition

        # Format market data for AI
        recent_candles = ohlcv_data[-5:] if len(ohlcv_data) >= 5 else ohlcv_data
        candle_lines = []
        for candle in recent_candles:
            candle_lines.append(
                f"  Open: {candle.open:,.0f} | High: {candle.high:,.0f} | Low: {candle.low:,.0f} | Close: {candle.close:,.0f} | Volume: {candle.volume:,.2f}"
            )

        market_summary = f"""
Recent Price Data (last {len(recent_candles)} days):
{chr(10).join(candle_lines)}

Current Technical Indicators:
- Current Price: {current_price:,.0f} KRW
- Price Change (24h): {price_change:+.2f}%
- Average Price (14d): {avg_recent_price:,.0f} KRW
"""

        # Call GLM API
        logger.info("Requesting AI analysis")
        response = await glm_client.analyze_text(
            system_prompt=system_prompt,
            user_message=market_summary,
        )

        # Display results
        print("\n" + "-" * 60)
        print("  AI 거래 분석 결과 (AI Trading Analysis)")
        print("-" * 60)

        if response.parsed:
            decision = response.parsed
            print(f"\n  결정 (Decision):     {decision.decision.upper()}")
            print(f"  비율 (Percentage):    {decision.percentage}%")
            print(f"  이유 (Reason):        {decision.reason}")
            print(f"  확신도 (Confidence):  {decision.confidence:.2%}")
        else:
            print(f"\n  원본 응답 (Raw Response):\n{response.content}")

        print("-" * 60)

        # Execute trade if not dry run
        if not config.dry_run and response.parsed:
            logger.info(
                "Trade execution",
                decision=response.parsed.decision,
                percentage=response.parsed.percentage,
            )

            # Get TradingService from container
            trading_service: TradingService = container.trading_service()

            # Get balances for trade calculation
            krw_balance = await upbit_client.get_balance("KRW")
            coin_symbol = ticker.split("-")[1] if "-" in ticker else ticker
            coin_balance = await upbit_client.get_balance(coin_symbol)

            # Execute AI-driven trade
            await execute_ai_driven_trade(
                trading_service=trading_service,
                ticker=ticker,
                ai_decision=response.parsed,
                krw_balance=krw_balance,
                coin_balance=coin_balance,
                auto_approve=config.auto_approve,
            )
        elif config.dry_run and response.parsed:
            # Simulation mode
            decision = response.parsed.decision
            amount = response.parsed.percentage
            await execute_simulation_trade(
                ticker=ticker,
                decision=decision,
                amount=amount,
            )

    except Exception as e:
        logger.error("Trading session error", error=str(e))
        raise

    finally:
        # Cleanup
        await upbit_client.close()
        logger.info("Trading session completed")


# =============================================================================
# CLI Interface
# =============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="GPT Bitcoin Auto-Trading System v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive mode
  python main.py --coin BTC --strategy balanced
  python main.py --coin ETH --strategy aggressive --dry-run
  python main.py --list-coins
  python main.py --list-strategies
  python main.py --buy KRW-BTC --amount 10000
  python main.py --sell KRW-BTC --quantity 0.001
  python main.py --trade-mode real --auto-approve
        """,
    )

    # Coin and strategy selection
    parser.add_argument(
        "--coin",
        type=str.upper,
        choices=[c.value for c in Cryptocurrency],
        help="Cryptocurrency to trade (e.g., KRW-BTC, KRW-ETH)",
    )

    parser.add_argument(
        "--strategy",
        type=str,
        choices=[s.value for s in TradingStrategy],
        help="Trading strategy (conservative, balanced, aggressive)",
    )

    # Trading mode
    parser.add_argument(
        "--testnet",
        action="store_true",
        help="Use testnet mode (MockUpbitClient with virtual balance)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate trades without actual execution",
    )

    parser.add_argument(
        "--trade-mode",
        type=str,
        choices=["simulation", "real"],
        default="simulation",
        help="Trading mode: simulation (default, safe) or real (live trading)",
    )

    # Manual trading mode
    parser.add_argument(
        "--buy",
        type=str,
        metavar="TICKER",
        help="Manual buy mode: ticker to buy (e.g., KRW-BTC)",
    )

    parser.add_argument(
        "--sell",
        type=str,
        metavar="TICKER",
        help="Manual sell mode: ticker to sell (e.g., KRW-BTC)",
    )

    parser.add_argument(
        "--amount",
        type=float,
        metavar="KRW",
        help="Amount in KRW for buy orders",
    )

    parser.add_argument(
        "--quantity",
        type=float,
        metavar="QTY",
        help="Quantity for sell orders",
    )

    # Auto-approve option (use with caution)
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip approval prompts (DANGEROUS - auto-executes trades)",
    )

    # List options
    parser.add_argument(
        "--list-coins",
        action="store_true",
        help="List all supported cryptocurrencies",
    )

    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List all trading strategies with parameters",
    )

    # Security commands (2FA)
    parser.add_argument(
        "--setup-pin",
        action="store_true",
        help="Setup 2FA PIN for secure trading",
    )

    parser.add_argument(
        "--change-pin",
        action="store_true",
        help="Change existing 2FA PIN",
    )

    parser.add_argument(
        "--security-status",
        action="store_true",
        help="Show security status (PIN, lock status, limits)",
    )

    # PIN input for secure trading (used with --buy or --sell)
    parser.add_argument(
        "--pin",
        type=str,
        metavar="PIN",
        help="4-digit PIN for secure trading (required with --buy/--sell)",
    )

    # AI instruction version
    parser.add_argument(
        "--inst-v",
        "--instruction-version",
        type=str,
        dest="instruction_version",
        choices=["v1", "v2", "v3"],
        default=None,
        help="AI instruction version: v1 (basic), v2 (multi-coin+news), v3 (v2+vision)",
    )

    return parser.parse_args()


def list_coins() -> None:
    """Display all supported cryptocurrencies."""
    manager = CoinManager()
    coins = manager.get_supported_coins()

    print("\n지원되는 암호화폐 (Supported Cryptocurrencies):")
    print("-" * 60)

    for coin in coins:
        info = manager.get_coin_info(coin)
        print(f"  {coin.value:12} | {info['name']:12} | {info['description']}")


def list_strategies() -> None:
    """Display all trading strategies with parameters."""
    print("\n거래 전략 (Trading Strategies):")
    print("-" * 60)

    for strategy in TradingStrategy:
        if strategy == TradingStrategy.custom:
            continue
        strategy_manager = StrategyManager(strategy=strategy)
        config = strategy_manager.get_config_for_strategy(strategy)
        print(f"\n  {strategy.value.upper()}:")
        print(f"    최대 매수:     {config.max_buy_percentage}%")
        print(f"    최대 매도:     {config.max_sell_percentage}%")
        print(f"    RSI 과매도:    {config.rsi_oversold}")
        print(f"    RSI 과매수:    {config.rsi_overbought}")
        print(f"    손절률:        {config.stop_loss_percentage}%")
        print(f"    익절률:        {config.take_profit_percentage}%")


# =============================================================================
# Security Commands (2FA)
# =============================================================================


async def handle_setup_pin() -> int:
    """Handle PIN setup command."""
    from rich.prompt import Prompt

    container = get_container()
    settings = get_settings()
    security_service: SecurityService = container.security_service()

    # Check if PIN is already set
    if settings.security.pin_hash is not None:
        console.print(
            Panel(
                "[yellow]PIN이 이미 설정되어 있습니다.[/yellow]\n"
                "PIN을 변경하려면 --change-pin을 사용하세요.",
                title="[bold yellow]PIN 설정됨[/bold yellow]",
                border_style="yellow",
            )
        )
        return 1

    console.print(
        Panel(
            "보안을 위해 4자리 PIN을 설정합니다.\n"
            "PIN은 연속되거나 반복되는 숫자(1234, 1111 등)는 사용할 수 없습니다.",
            title="[bold cyan]PIN 설정[/bold cyan]",
            border_style="cyan",
        )
    )

    # Get PIN twice for confirmation
    pin = Prompt.ask("[cyan]PIN 입력 (4자리 숫자)[/cyan]", console=console)
    pin_confirm = Prompt.ask("[cyan]PIN 확인 (재입력)[/cyan]", console=console)

    if pin != pin_confirm:
        console.print(
            Panel(
                "[red]PIN이 일치하지 않습니다.[/red]",
                title="[bold red]오류[/bold red]",
                border_style="red",
            )
        )
        return 1

    try:
        await security_service.setup_pin(pin)
        console.print(
            Panel(
                "[green]✓ PIN이 성공적으로 설정되었습니다.[/green]",
                title="[bold green]설정 완료[/bold green]",
                border_style="green",
            )
        )
        return 0
    except ValueError as e:
        console.print(
            Panel(
                f"[red]{e}[/red]",
                title="[bold red]PIN 설정 실패[/bold red]",
                border_style="red",
            )
        )
        return 1


async def handle_change_pin() -> int:
    """Handle PIN change command."""
    from rich.prompt import Prompt

    container = get_container()
    security_service: SecurityService = container.security_service()

    console.print(
        Panel(
            "기존 PIN을 변경합니다.",
            title="[bold cyan]PIN 변경[/bold cyan]",
            border_style="cyan",
        )
    )

    # Get old PIN
    old_pin = Prompt.ask("[cyan]기존 PIN 입력[/cyan]", console=console)

    # Verify old PIN first
    if not await security_service.verify_pin(old_pin):
        console.print(
            Panel(
                "[red]기존 PIN이 올바르지 않습니다.[/red]",
                title="[bold red]인증 실패[/bold red]",
                border_style="red",
            )
        )
        return 1

    # Get new PIN twice for confirmation
    new_pin = Prompt.ask("[cyan]새 PIN 입력 (4자리 숫자)[/cyan]", console=console)
    new_pin_confirm = Prompt.ask("[cyan]새 PIN 확인 (재입력)[/cyan]", console=console)

    if new_pin != new_pin_confirm:
        console.print(
            Panel(
                "[red]새 PIN이 일치하지 않습니다.[/red]",
                title="[bold red]오류[/bold red]",
                border_style="red",
            )
        )
        return 1

    try:
        result = await security_service.change_pin(old_pin, new_pin)
        if result:
            console.print(
                Panel(
                    "[green]✓ PIN이 성공적으로 변경되었습니다.[/green]",
                    title="[bold green]변경 완료[/bold green]",
                    border_style="green",
                )
            )
            return 0
        else:
            console.print(
                Panel(
                    "[red]PIN 변경에 실패했습니다.[/red]",
                    title="[bold red]변경 실패[/bold red]",
                    border_style="red",
                )
            )
            return 1
    except ValueError as e:
        console.print(
            Panel(
                f"[red]{e}[/red]",
                title="[bold red]PIN 변경 실패[/bold red]",
                border_style="red",
            )
        )
        return 1


async def handle_security_status() -> int:
    """Handle security status command."""
    settings = get_settings()

    status_lines = [
        f"[bold]PIN 설정:[/bold] {'✓ 설정됨' if settings.security.pin_hash else '✗ 未設定'}",
        f"[bold]잠금 상태:[/bold] {'✓ 잠금됨' if settings.security.locked_until else '정상'}",
    ]

    if settings.security.locked_until:
        from gpt_bitcoin.domain.security import SecurityService

        # Create temp service to get lock remaining time
        security_service = SecurityService(
            trading_service=None,  # Not needed for lock check
            settings=settings,
            audit_repository=None,  # Not needed for lock check
        )
        remaining_minutes = security_service.get_lock_remaining_seconds() // 60
        status_lines.append(f"[bold]잠금 해제까지:[/bold] {remaining_minutes}분")

    status_lines.extend(
        [
            "",
            "[bold]거래 한도 설정:[/bold]",
            f"  • 일일 최대 거래액: {settings.security.max_daily_volume_krw:,.0f} KRW",
            f"  • 일일 최대 거래횟수: {settings.security.max_daily_trades}회",
            f"  • 단일 거래 한도: {settings.security.max_single_trade_krw:,.0f} KRW",
            f"  • 고액 거래 기준: {settings.security.high_value_threshold_krw:,.0f} KRW 이상",
            f"  • 세션 최대 거래액: {settings.security.max_session_volume_krw:,.0f} KRW",
            f"  • 세션 최대 거래횟수: {settings.security.max_session_trades}회",
        ]
    )

    console.print(
        Panel(
            "\n".join(status_lines),
            title="[bold cyan]보안 상태[/bold cyan]",
            border_style="cyan",
        )
    )

    return 0


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    print(BANNER)

    # Parse arguments
    args = parse_arguments()

    # Handle list commands
    if args.list_coins:
        list_coins()
        return 0

    if args.list_strategies:
        list_strategies()
        return 0

    # Handle security commands
    if args.setup_pin:
        return asyncio.run(handle_setup_pin())

    if args.change_pin:
        return asyncio.run(handle_change_pin())

    if args.security_status:
        return asyncio.run(handle_security_status())

    # Handle manual trading modes
    if args.buy or args.sell:
        return asyncio.run(handle_manual_trade(args))

    # Create configuration
    coin = Cryptocurrency(args.coin) if args.coin else None
    strategy = TradingStrategy(args.strategy) if args.strategy else None

    # Interactive mode if not specified
    if coin is None:
        coin = select_coin_interactive()
    if strategy is None:
        strategy = select_strategy_interactive()

    # Determine testnet mode (overrides dry-run)
    # @MX:NOTE: --testnet이 설정되면 가상 잔액으로 시뮬레이션
    testnet_mode = args.testnet

    # Determine trade mode
    # @MX:NOTE: --dry-run is equivalent to --trade-mode simulation
    trade_mode = args.trade_mode
    if args.dry_run:
        trade_mode = "simulation"

    # Ask about dry-run if not specified and not in manual mode
    dry_run = args.dry_run
    if not args.dry_run and trade_mode == "simulation":
        dry_run = confirm_dry_run()

    # Create configuration
    config = TradingConfig(
        coin=coin,
        strategy=strategy,
        testnet_mode=testnet_mode,
        dry_run=dry_run,
        instruction_version=args.instruction_version,
        trade_mode=trade_mode,
        auto_approve=args.auto_approve,
    )

    # Run trading session
    try:
        asyncio.run(run_trading_session(config))
        return 0
    except KeyboardInterrupt:
        print("\n\n사용자 중단 (User interrupted)")
        return 130
    except Exception as e:
        print(f"\n오류 발생 (Error): {e}")
        return 1


async def handle_manual_trade(args: argparse.Namespace) -> int:
    """
    Handle manual buy/sell trading modes.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for error)

    @MX:NOTE: 수동 거래 모드 처리 함수
        @MX:REASON: PIN 인증과 SecurityService를 통한 보안 거래 실행
    """
    container = get_container()
    settings = get_settings()
    security_service: SecurityService = container.security_service()
    trading_service: TradingService = container.trading_service()

    # Check if PIN is set for real trading
    is_real_trading = (args.trade_mode == "real" and not args.dry_run) or (
        args.buy and args.amount and not (args.trade_mode == "simulation" or args.dry_run)
    )

    if is_real_trading and settings.security.pin_hash is None:
        console.print(
            Panel(
                "[yellow]PIN이 설정되지 않았습니다.[/yellow]\n"
                "실제 거래를 위해 먼저 PIN을 설정해주세요:\n"
                "  python main.py --setup-pin",
                title="[bold yellow]PIN 필요[/bold yellow]",
                border_style="yellow",
            )
        )
        return 1

    try:
        # Handle manual buy
        if args.buy:
            ticker = args.buy
            amount = args.amount

            if amount is None:
                console.print("[red]오류: --amount를 지정해야 합니다[/]")
                return 1

            # Check if simulation mode
            if args.trade_mode == "simulation" or args.dry_run:
                await execute_simulation_trade(
                    ticker=ticker,
                    decision="buy",
                    amount=amount,
                )
                return 0

            # Real trading requires PIN
            if not args.pin:
                console.print(
                    Panel(
                        "[yellow]실제 거래는 PIN 인증이 필요합니다.[/yellow]\n"
                        "사용법: python main.py --buy KRW-BTC --amount 10000 --pin 1234",
                        title="[bold yellow]PIN 필요[/bold yellow]",
                        border_style="yellow",
                    )
                )
                return 1

            # Execute secure buy
            approval = await security_service.secure_request_buy(
                ticker=ticker,
                amount_krw=amount,
                pin=args.pin,
                session_id="cli-manual-trade",
            )

            # Auto-approve for CLI
            approval.mark_approved()

            result = await security_service.secure_execute_trade(
                approval=approval,
                high_value_confirmed=True,  # CLI trading implies confirmation
                session_id="cli-manual-trade",
            )

            return 0 if result and result.success else 1

        # Handle manual sell
        if args.sell:
            ticker = args.sell
            quantity = args.quantity

            if quantity is None:
                console.print("[red]오류: --quantity를 지정해야 합니다[/]")
                return 1

            # Check if simulation mode
            if args.trade_mode == "simulation" or args.dry_run:
                await execute_simulation_trade(
                    ticker=ticker,
                    decision="sell",
                    amount=quantity,
                )
                return 0

            # Real trading requires PIN
            if not args.pin:
                console.print(
                    Panel(
                        "[yellow]실제 거래는 PIN 인증이 필요합니다.[/yellow]\n"
                        "사용법: python main.py --sell KRW-BTC --quantity 0.001 --pin 1234",
                        title="[bold yellow]PIN 필요[/bold yellow]",
                        border_style="yellow",
                    )
                )
                return 1

            # Execute secure sell
            approval = await security_service.secure_request_sell(
                ticker=ticker,
                quantity=quantity,
                pin=args.pin,
                session_id="cli-manual-trade",
            )

            # Auto-approve for CLI
            approval.mark_approved()

            result = await security_service.secure_execute_trade(
                approval=approval,
                high_value_confirmed=True,  # CLI trading implies confirmation
                session_id="cli-manual-trade",
            )

            return 0 if result and result.success else 1

    except ValueError as e:
        console.print(f"[red]거래 오류: {e}[/]")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]거래가 취소되었습니다.[/]")
        trading_service.cancel_pending_request()
        return 130
    except Exception as e:
        logger.error("Manual trade failed", error=str(e))
        console.print(f"[red]오류 발생: {e}[/]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
