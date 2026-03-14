# SPEC-TRADING-003: CLI Integration

## Metadata

- **SPEC ID**: SPEC-TRADING-003
- **Title**: CLI Integration (CLI 실거래 연동)
- **Created**: 2026-03-04
- **Status**: Completed
- **Priority**: High
- **Depends On**: SPEC-TRADING-001 (Completed)
- **Lifecycle Level**: spec-anchored

---

## Problem Analysis

### Current State

SPEC-TRADING-001에서 TradingService가 구현되었으나, `main.py` CLI 인터페이스에서는 여전히 시뮬레이션 모드로 동작합니다. `main.py` 396-398행에 다음과 같은 TODO가 존재합니다:

```python
# TODO: Implement actual trade execution
print("\n  [실제 거래 실행은 아직 구현 중입니다]")
print("  [Actual trade execution coming soon]")
```

이로 인해 다음과 같은 문제가 발생합니다:

1. **실거래 불가능**: 사용자가 CLI를 통해 실제 거래를 실행할 수 없음
2. **AI 분석 낭비**: GLM 분석 결과에 따른 거래 실행이 불가능
3. **수동 거래 미지원**: CLI에서 수동으로 매수/매도 명령을 내릴 수 없음
4. **승인 워크플로우 미구현**: TradingService의 approval-before-execution 패턴이 CLI에 통합되지 않음

### Root Cause Analysis (Five Whys)

1. **Why?** main.py에 실거래 코드가 구현되지 않음
2. **Why?** SPEC-TRADING-001 범위가 TradingService 구현에 한정됨
3. **Why?** CLI 통합은 별도 사용자 경험 설계가 필요함
4. **Why?** 인터랙티브 승인 워크플로우 설계가 필요함
5. **Root Cause**: CLI에서의 사용자 경험과 승인 워크플로우가 별도 SPEC으로 분리 필요

### Desired State

CLI 사용자가 다음을 수행할 수 있어야 합니다:

1. AI 분석 기반 자동 거래 (승인 포함)
2. 수동 매수/매도 명령 실행
3. 시뮬레이션/실거래 모드 전환
4. 거래 승인을 위한 인터랙티브 프롬프트

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| CLI Framework | argparse | stdlib | 기존 main.py와 일치 |
| Interactive Prompts | rich | 13.7+ | 향상된 TUI 경험 |
| Async Runtime | asyncio | stdlib | TradingService async 지원 |
| Progress Display | rich.progress | 13.7+ | 승인 대기 UI |

### Integration Points

```
main.py CLI
    ↓ parse arguments
run_trading_session()
    ↓ AI analysis
TradingService.request_buy_order/sell_order()
    ↓ returns TradeApproval
Interactive Approval Prompt (rich)
    ↓ user confirms
TradingService.execute_approved_trade()
    ↓ returns TradeResult
Display Result
```

### Constraints

1. **Backward Compatibility**: 기존 `--dry-run` 플래그 유지
2. **Graceful Degradation**: TUI 미지원 터미널에서도 동작
3. **Ctrl-C Handling**: 승인 프롬프트에서 인터럽트 시 안전한 취소
4. **Timeout**: 승인 대기 최대 30초 (TradingService.APPROVAL_TIMEOUT_SECONDS)

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-CLI-001**: 시스템은 CLI에서 TradingService를 통해 실거래를 실행해야 한다 (The system shall execute real trades via TradingService in CLI).

```
The system shall use TradingService for all trade execution in main.py:
- Replace simulation code with TradingService calls
- Support both buy and sell orders
- Handle TradeResult appropriately
```

**REQ-CLI-002**: 시스템은 사용자에게 거래 실행 전 승인을 요청해야 한다 (The system shall request user approval before trade execution).

```
The system shall display trade approval prompt:
- Show estimated price, quantity, and fee
- Require explicit user confirmation (y/n)
- Respect TradingService.APPROVAL_TIMEOUT_SECONDS (30s)
```

### Event-Driven Requirements

**REQ-CLI-003**: WHEN AI 분석이 완료되면 THEN 시스템은 승인 요청을 표시해야 한다.

```
WHEN GLM analysis returns a decision (buy/sell/hold)
THEN if decision is buy or sell:
    - Create TradeApproval via TradingService
    - Display approval details to user
    - Wait for user confirmation
    - Execute if approved, cancel if rejected
```

**REQ-CLI-004**: WHEN 사용자가 --buy 또는 --sell 플래그를 사용하면 THEN 시스템은 수동 거래 모드로 전환해야 한다.

```
WHEN user provides --buy TICKER --amount KRW
THEN skip AI analysis
    AND proceed directly to trade approval
    AND execute buy order after approval

WHEN user provides --sell TICKER --quantity QTY
THEN skip AI analysis
    AND proceed directly to trade approval
    AND execute sell order after approval
```

**REQ-CLI-005**: WHEN 승인 요청이 타임아웃되면 THEN 시스템은 거래를 취소해야 한다.

```
WHEN user does not respond within APPROVAL_TIMEOUT_SECONDS
THEN cancel the pending request
    AND display "승인 시간이 만료되었습니다" message
    AND return to main menu or exit gracefully
```

### State-Driven Requirements

**REQ-CLI-006**: IF --trade-mode=simulation 또는 --dry-run이면 THEN 시스템은 시뮬레이션 모드로 동작해야 한다.

```
IF --trade-mode simulation OR --dry-run
THEN skip TradingService calls
    AND display "[시뮬레이션] 거래가 실행됩니다" message
    AND do NOT execute real trades
```

**REQ-CLI-007**: IF 사용자가 승인을 거부하면 THEN 시스템은 거래를 취소해야 한다.

```
IF user rejects approval (n or Ctrl-C)
THEN call TradingService.cancel_pending_request()
    AND display "거래가 취소되었습니다" message
    AND do NOT execute trade
```

**REQ-CLI-008**: IF TradingService 상태가 IDLE이 아니면 THEN 시스템은 새 거래 요청을 차단해야 한다.

```
IF TradingService.state != TradingState.IDLE
THEN display "이미 진행 중인 거래가 있습니다" warning
    AND wait for current trade to complete
    OR offer to cancel pending request
```

### Optional Requirements

**REQ-CLI-009**: Where possible, 시스템은 배치 거래 기능을 제공해야 한다.

```
Where possible, the system shall support batch operations:
- Read trades from JSON/YAML file
- Execute multiple trades sequentially
- Provide summary report at end
```

**REQ-CLI-010**: Where possible, 시스템은 거래 내역 조회 명령을 제공해야 한다.

```
Where possible, provide --history command:
- Display recent trades
- Support --limit and --ticker filters
- Require SPEC-TRADING-002 for full functionality
```

### Unwanted Behavior Requirements

**REQ-CLI-011**: 시스템은 승인 없이 거래를 실행해서는 안 된다 (The system shall not execute trades without approval).

```
The system shall NOT:
- Execute trades automatically without user confirmation
- Bypass the approval workflow
- Execute trades in simulation mode with real API calls
```

**REQ-CLI-012**: 시스템은 사용자 입력 없이 무한 대기해서는 안 된다 (The system shall not wait indefinitely without user input).

```
The system shall NOT:
- Wait forever for user approval
- Hang without timeout
- Ignore Ctrl-C interrupt
```

---

## Specifications

### CLI Arguments Design

#### New Arguments

```python
# Additions to parse_arguments()

# Trade Mode
parser.add_argument(
    "--trade-mode",
    choices=["simulation", "real"],
    default="simulation",
    help="Trading mode: simulation (dry-run) or real (live trading)",
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Alias for --trade-mode simulation (backward compatibility)",
)

# Manual Trading
parser.add_argument(
    "--buy",
    metavar="TICKER",
    help="Execute manual buy order (e.g., --buy KRW-BTC)",
)
parser.add_argument(
    "--sell",
    metavar="TICKER",
    help="Execute manual sell order (e.g., --sell KRW-BTC)",
)
parser.add_argument(
    "--amount",
    type=float,
    help="Amount in KRW for buy orders",
)
parser.add_argument(
    "--quantity",
    type=float,
    help="Quantity for sell orders",
)

# Batch Operations
parser.add_argument(
    "--batch",
    metavar="FILE",
    help="Execute batch trades from JSON/YAML file",
)

# History (requires SPEC-TRADING-002)
parser.add_argument(
    "--history",
    action="store_true",
    help="Display recent trade history",
)
parser.add_argument(
    "--limit",
    type=int,
    default=20,
    help="Number of history records to display (default: 20)",
)

# Approval Settings
parser.add_argument(
    "--auto-approve",
    action="store_true",
    help="Skip approval prompt (DANGEROUS - use with caution)",
)
parser.add_argument(
    "--approval-timeout",
    type=int,
    default=30,
    help="Seconds to wait for approval (default: 30)",
)
```

### Interactive Approval Workflow

#### Approval Prompt Design

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️  거래 승인 요청 (Trade Approval Request)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  구분 (Side):        매수 (BUY)                             │
│  코인 (Ticker):      KRW-BTC                                │
│  금액 (Amount):      100,000 KRW                            │
│                                                             │
│  예상 체결가:        50,000,000 KRW                         │
│  예상 수량:          0.002 BTC                              │
│  예상 수수료:        50 KRW (0.05%)                         │
│                                                             │
│  ⏱️  승인 만료까지: 30초                                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 이 거래를 승인하시겠습니까? (Approve this trade?)          │
│                                                             │
│   [y] 승인 (Approve)    [n] 거부 (Reject)    [Esc] 취소    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Implementation with Rich

```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, BarColumn, TextColumn

async def interactive_approval(
    approval: TradeApproval,
    timeout: int = 30,
) -> bool:
    """
    Display interactive approval prompt.

    @MX:WARN: This function blocks for user input.
        Ensure it's called in appropriate context.
        @MX:REASON: Interactive prompts require synchronous user interaction.
    """
    console = Console()

    # Display approval details
    panel = Panel(
        f"""
구분 (Side):        {approval.side.upper()}
코인 (Ticker):      {approval.ticker}
금액 (Amount):      {approval.amount:,.0f} KRW

예상 체결가:        {approval.estimated_price:,.0f} KRW
예상 수량:          {approval.estimated_quantity:.6f}
예상 수수료:        {approval.fee_estimate:,.0f} KRW

⏱️  승인 만료까지: {timeout}초
        """,
        title="⚠️  거래 승인 요청 (Trade Approval Request)",
        border_style="yellow",
    )
    console.print(panel)

    # Countdown with progress bar
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.remaining]{task.fields[remaining]}초"),
    ) as progress:
        task = progress.add_task(
            "승인 대기",
            total=timeout,
            remaining=timeout,
        )

        # Wait for user input with timeout
        try:
            for remaining in range(timeout, 0, -1):
                progress.update(task, advance=1, remaining=remaining)

                # Non-blocking input check (simplified)
                # In production, use asyncio with proper input handling
                await asyncio.sleep(1)

            # Timeout reached
            console.print("[red]승인 시간이 만료되었습니다[/red]")
            return False

        except KeyboardInterrupt:
            console.print("\n[yellow]거래가 취소되었습니다[/yellow]")
            return False

    # Prompt for approval
    response = Prompt.ask(
        "이 거래를 승인하시겠습니까?",
        choices=["y", "n"],
        default="n",
    )

    return response == "y"
```

### Main.py Integration

#### Modified run_trading_session()

```python
async def run_trading_session(config: Config) -> None:
    """
    Run a trading session with real trade execution support.

    @MX:NOTE: Supports both AI-driven and manual trading modes.
    """
    # ... existing setup code ...

    # Get TradingService from container
    container = get_container()
    trading_service = container.trading_service()

    try:
        # Mode selection
        if config.buy:
            # Manual buy mode
            await execute_manual_buy(
                trading_service=trading_service,
                ticker=config.buy,
                amount=config.amount,
                auto_approve=config.auto_approve,
            )
        elif config.sell:
            # Manual sell mode
            await execute_manual_sell(
                trading_service=trading_service,
                ticker=config.sell,
                quantity=config.quantity,
                auto_approve=config.auto_approve,
            )
        else:
            # AI-driven mode
            await execute_ai_driven_trade(
                trading_service=trading_service,
                glm_client=glm_client,
                config=config,
            )

    except KeyboardInterrupt:
        logger.info("Trading session interrupted by user")
        if trading_service.state != TradingState.IDLE:
            trading_service.cancel_pending_request()
    finally:
        await upbit_client.close()


async def execute_manual_buy(
    trading_service: TradingService,
    ticker: str,
    amount: float,
    auto_approve: bool,
) -> None:
    """Execute manual buy order with approval workflow."""
    console = Console()

    # Step 1: Request buy order
    console.print(f"\n[cyan]매수 주문 요청: {ticker} {amount:,.0f} KRW[/cyan]")

    approval = await trading_service.request_buy_order(ticker, amount)

    # Step 2: Get approval
    if auto_approve:
        console.print("[yellow]⚠️  자동 승인 모드 - 사용자 확인 없이 실행[/yellow]")
        approved = True
    else:
        approved = await interactive_approval(approval)

    # Step 3: Execute or cancel
    if approved:
        approval.mark_approved()
        result = await trading_service.execute_approved_trade(approval)

        if result.success:
            console.print(f"[green]✅ 주문 완료: {result.order_id}[/green]")
        else:
            console.print(f"[red]❌ 주문 실패: {result.error_message}[/red]")
    else:
        trading_service.cancel_pending_request()
        console.print("[yellow]거래가 취소되었습니다[/yellow]")


async def execute_ai_driven_trade(
    trading_service: TradingService,
    glm_client: GLMClient,
    config: Config,
) -> None:
    """Execute AI-driven trade with approval workflow."""
    console = Console()

    # ... existing AI analysis code ...

    if response.parsed:
        decision = response.parsed

        if decision.decision == "hold":
            console.print("[blue]AI 분석 결과: 보유 (HOLD)[/blue]")
            return

        # Calculate trade amount
        balance = await upbit_client.get_balance("KRW")
        trade_amount = balance * (decision.percentage / 100)

        if decision.decision == "buy":
            approval = await trading_service.request_buy_order(
                ticker=config.coin,
                amount_krw=trade_amount,
            )
        else:  # sell
            base_currency = config.coin.split("-")[1]
            coin_balance = await upbit_client.get_balance(base_currency)
            sell_quantity = coin_balance * (decision.percentage / 100)

            approval = await trading_service.request_sell_order(
                ticker=config.coin,
                quantity=sell_quantity,
            )

        # Get approval
        if config.trade_mode == "real" and not config.dry_run:
            approved = await interactive_approval(approval)

            if approved:
                approval.mark_approved()
                result = await trading_service.execute_approved_trade(approval)
                display_trade_result(result)
            else:
                trading_service.cancel_pending_request()
                console.print("[yellow]거래가 취소되었습니다[/yellow]")
        else:
            console.print("[blue][시뮬레이션] 거래가 실행됩니다[/blue]")
```

---

## MX Tag Targets

### High Fan-In Functions

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `execute_manual_buy()` | 2+ | @MX:ANCHOR | main.py |
| `execute_manual_sell()` | 2+ | @MX:ANCHOR | main.py |
| `interactive_approval()` | 2+ | @MX:ANCHOR | main.py |
| `display_trade_result()` | 2+ | @MX:NOTE | main.py |

### Danger Zones

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `--auto-approve` flag | Financial risk | @MX:WARN | Bypasses approval workflow |
| `execute_approved_trade()` call | Real money | @MX:WARN | Executes actual trades |
| Ctrl-C handling | State corruption | @MX:NOTE | Must cancel pending request |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `tests/unit/test_cli_trading.py` | CLI trading tests | ~300 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `main.py` | Add TradingService integration | +200 |
| `tests/characterization/test_autotrade_v3.py` | Update characterization tests | +50 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Accidental trade execution | Medium | High | Default to simulation mode, require explicit --trade-mode real |
| Approval timeout confusion | Medium | Medium | Clear countdown display, extendable timeout |
| Terminal compatibility | Low | Medium | Fallback to simple text prompts |
| State corruption on interrupt | Low | High | Robust Ctrl-C handler, state reset |

### Safety Measures

1. **Default Safe Mode**: `--trade-mode simulation` is default
2. **Explicit Real Mode**: Must specify `--trade-mode real` for live trading
3. **Approval Required**: Even in real mode, approval is required (unless --auto-approve)
4. **--auto-approve Warning**: Display prominent warning when using auto-approve

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-CLI-001 | run_trading_session() | test_real_trade_execution() |
| REQ-CLI-002 | interactive_approval() | test_approval_prompt_display() |
| REQ-CLI-003 | execute_ai_driven_trade() | test_ai_driven_approval_flow() |
| REQ-CLI-004 | execute_manual_buy/sell() | test_manual_trading_mode() |
| REQ-CLI-005 | interactive_approval() | test_approval_timeout() |
| REQ-CLI-006 | run_trading_session() | test_simulation_mode() |
| REQ-CLI-007 | run_trading_session() | test_user_rejection() |
| REQ-CLI-008 | run_trading_session() | test_concurrent_trade_prevention() |
| REQ-CLI-011 | All execution paths | test_no_unapproved_trades() |
| REQ-CLI-012 | interactive_approval() | test_no_infinite_wait() |

---

## Success Criteria

1. **Functional**: All 12 requirements implemented and passing tests
2. **Safety**: Default simulation mode, explicit real mode required
3. **UX**: Clear approval prompts with countdown
4. **Error Handling**: Graceful Ctrl-C handling, state cleanup
5. **Coverage**: Minimum 85% test coverage for new code

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService foundation (Completed - dependency)
- **SPEC-TRADING-002**: Trading History (can use data from CLI trades)
- **SPEC-TRADING-004**: Security Enhancements (adds 2FA to approval)

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
