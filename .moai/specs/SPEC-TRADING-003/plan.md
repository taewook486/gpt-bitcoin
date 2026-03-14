# Implementation Plan: SPEC-TRADING-003 (CLI Integration)

## Overview

이 문서는 SPEC-TRADING-003 CLI 실거래 연동 기능의 구현 계획을 정의합니다.

---

## Milestones (Priority-Based)

### Phase 1: Core Integration (Primary Goal)

**Objective**: main.py에서 TradingService를 통한 실거래 실행

#### Tasks

1. **Import TradingService**
   - Priority: Critical
   - Add TradingService import to main.py
   - Get service from DI container
   - Handle initialization errors

2. **Implement Approval Workflow**
   - Priority: Critical
   - Create `interactive_approval()` function
   - Display approval details with rich formatting
   - Handle user input (y/n/Esc)
   - Implement timeout countdown

3. **Modify run_trading_session()**
   - Priority: Critical
   - Replace TODO with actual TradingService calls
   - Add simulation/real mode branching
   - Handle TradeResult display

4. **Error Handling**
   - Priority: High
   - Implement Ctrl-C handler
   - Add state cleanup on interrupt
   - Handle TradingService exceptions

5. **Unit Tests - Core**
   - Priority: High
   - Test approval prompt display
   - Test timeout behavior
   - Test mode switching

**Deliverables**:
- Working real trade execution via CLI
- Interactive approval workflow
- Robust error handling

---

### Phase 2: Manual Trading Commands (Secondary Goal)

**Objective**: 수동 매수/매도 명령 지원

#### Tasks

1. **Add CLI Arguments**
   - Priority: High
   - Implement --buy, --sell arguments
   - Implement --amount, --quantity arguments
   - Add --trade-mode flag

2. **Implement Manual Trade Functions**
   - Priority: High
   - Create `execute_manual_buy()`
   - Create `execute_manual_sell()`
   - Integrate with approval workflow

3. **Integration Tests**
   - Priority: Medium
   - Test manual buy flow
   - Test manual sell flow
   - Test argument validation

**Deliverables**:
- Manual trading commands working
- Proper argument validation
- Integration with approval workflow

---

### Phase 3: Enhanced Features (Final Goal)

**Objective**: 배치 거래 및 향상된 UX

#### Tasks

1. **Batch Operations** (Optional)
   - Priority: Low
   - Implement --batch file reading
   - Sequential trade execution
   - Summary report generation

2. **History Command** (Optional)
   - Priority: Low
   - Implement --history flag
   - Display recent trades
   - Requires SPEC-TRADING-002

3. **Rich UX Enhancements**
   - Priority: Medium
   - Add color-coded output
   - Progress indicators
   - Better error messages

**Deliverables**:
- Optional batch operations
- Enhanced CLI UX
- History display (if SPEC-002 ready)

---

## Technical Approach

### CLI Argument Additions

```python
# main.py parse_arguments() additions

# Trade Mode
parser.add_argument(
    "--trade-mode",
    choices=["simulation", "real"],
    default="simulation",
    help="Trading mode: simulation (dry-run) or real (live trading)",
)

# Manual Trading
parser.add_argument("--buy", metavar="TICKER", help="Execute manual buy order")
parser.add_argument("--sell", metavar="TICKER", help="Execute manual sell order")
parser.add_argument("--amount", type=float, help="Amount in KRW for buy orders")
parser.add_argument("--quantity", type=float, help="Quantity for sell orders")

# Approval Settings
parser.add_argument("--auto-approve", action="store_true",
    help="Skip approval prompt (DANGEROUS)")
```

### Approval Prompt Design

```python
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

async def interactive_approval(approval: TradeApproval, timeout: int = 30) -> bool:
    """Interactive approval prompt with timeout."""
    console = Console()

    # Display approval details
    side_kr = "매수" if approval.side == "buy" else "매도"
    panel = Panel(
        f"[bold]구분:[/bold] {side_kr}\n"
        f"[bold]코인:[/bold] {approval.ticker}\n"
        f"[bold]금액:[/bold] {approval.amount:,.0f} KRW\n"
        f"[bold]예상 수수료:[/bold] {approval.fee_estimate:,.0f} KRW",
        title="거래 승인 요청",
        border_style="yellow",
    )
    console.print(panel)

    try:
        response = Prompt.ask("승인하시겠습니까?", choices=["y", "n"], default="n")
        return response == "y"
    except KeyboardInterrupt:
        return False
```

### Main Integration Pattern

```python
async def run_trading_session(config: Config) -> None:
    """Run trading session with real trade support."""
    container = get_container()
    trading_service = container.trading_service()

    try:
        if config.buy:
            await _execute_manual_buy(trading_service, config)
        elif config.sell:
            await _execute_manual_sell(trading_service, config)
        else:
            await _execute_ai_driven_trade(trading_service, config)
    except KeyboardInterrupt:
        if trading_service.state != TradingState.IDLE:
            trading_service.cancel_pending_request()
```

---

## Files to Modify

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `main.py` | Add TradingService integration, approval workflow, manual trading | +200 |
| `tests/unit/test_cli_trading.py` | New test file | +300 |

---

## Dependencies

### New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| rich | >=13.7.0 | Enhanced CLI UX |

---

## Testing Strategy

### Test Categories

1. **Unit Tests**: Test approval prompt logic, mode detection
2. **Integration Tests**: End-to-end manual buy/sell flows

### Key Test Cases

- test_user_approves_trade()
- test_user_rejects_trade()
- test_ctrl_c_cancels_trade()
- test_expired_approval_auto_rejects()
- test_manual_buy_success()
- test_manual_sell_success()
- test_simulation_mode_no_real_api_calls()

---

## Success Criteria

1. All 12 requirements implemented and passing tests
2. Default simulation mode, explicit real mode required
3. Clear approval prompts with countdown
4. Graceful Ctrl-C handling, state cleanup
5. Minimum 85% test coverage for new code

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
