# SPEC-TRADING-004: Security Enhancements (보안 강화)

## Metadata

- **SPEC ID**: SPEC-TRADING-004
- **Title**: Security Enhancements (보안 강화 - 2FA, 거래 한도)
- **Created**: 2026-03-04
- **Status**: Completed
- **Priority**: High
- **Depends On**: SPEC-TRADING-001 (Completed), SPEC-TRADING-003 (CLI Integration)
- **Lifecycle Level**: spec-anchored

---

## Problem Analysis

### Current State

SPEC-TRADING-001에서 TradingService가 구현되었고, SPEC-TRADING-003에서 CLI 통합이 완료되었으나, 실제 거래 실행에 대한 보안 장치가 부족합니다. 현재 시스템은 다음과 같은 보안 취약점을 가집니다:

1. **인증 부재**: 누구나 시스템에 접근하면 거래를 실행할 수 있음
2. **무제한 거래**: 일일 거래 횟수나 금액에 제한이 없어 과도한 거래 가능
3. **고액 거래 경고 없음**: 큰 금액의 거래에 대한 추가 확인 절차 부재
4. **감사 기록 부재**: 거래 시도(실패 포함)에 대한 로그가 체계적으로 기록되지 않음

### Root Cause Analysis (Five Whys)

1. **Why?** 거래 실행에 대한 보안 계층이 없음
2. **Why?** 초기 개발에서 핵심 거래 로직에 집중하여 보안 기능 제외
3. **Why?** SPEC-TRADING-001 범위가 실시간 거래 실행에 한정됨
4. **Why?** 개인 프로젝트로 시작하여 다중 사용자 보안 고려 없음
5. **Root Cause**: 실거래 전환에 따른 보안 요구사항이 별도 SPEC으로 분리 필요

### Assumption Analysis

| Assumption | Confidence | Evidence | Risk if Wrong | Validation |
|------------|------------|----------|---------------|------------|
| 4-digit PIN이 충분한 보안 제공 | Medium | 개인 로컬 사용 환경 | Medium | 보안 전문가 리뷰 |
| 사용자가 한도 설정을 원함 | High | 리스크 관리 표준 관행 | Low | 사용자 피드백 |
| SQLite audit log로 충분함 | Medium | 저용량 예상 | Low | 부하 테스트 |
| Settings에 보안 설정 저장 가능 | High | Pydantic 검증 | Low | Config 리뷰 |

### Desired State

모든 거래 실행 전 2FA 인증이 요구되며, 거래 한도 설정이 적용되고, 고액 거래에 대한 추가 확인이 이루어지며, 모든 거래 시도가 감사 로그에 기록됩니다.

---

## Environment

### Technology Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| 2FA Implementation | hashlib (SHA-256) | stdlib | 4-digit PIN 해시 저장 |
| Settings Storage | Pydantic Settings | v2 | 기존 설정 시스템 확장 |
| Audit Log | SQLite | 3.45+ | SPEC-TRADING-002 DB 활용 |
| CLI Integration | Rich | 13.7+ | 인터랙티브 PIN 입력 |

### Integration Points

```
CLI / Web UI Trade Request
        ↓
SecurityService.verify_2fa()  ← 새로운 보안 계층
        ↓ verified
SecurityService.check_limits()
        ↓ within limits
TradingService.request_buy_order/sell_order()
        ↓
SecurityService.check_high_value() → 추가 확인 (100,000 KRW 초과)
        ↓ confirmed
TradingService.execute_approved_trade()
        ↓
SecurityService.log_audit() → audit_log 테이블
```

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SecurityService (NEW)                         │
├─────────────────────────────────────────────────────────────────┤
│  2FA Module:                                                    │
│    - verify_pin(pin: str) → bool                               │
│    - setup_pin(new_pin: str) → None                            │
│    - change_pin(old_pin: str, new_pin: str) → bool             │
├─────────────────────────────────────────────────────────────────┤
│  Limits Module:                                                 │
│    - check_daily_volume(current: float) → bool                  │
│    - check_daily_trades(current: int) → bool                    │
│    - check_single_trade(amount: float) → bool                   │
├─────────────────────────────────────────────────────────────────┤
│  Audit Module:                                                  │
│    - log_trade_attempt(...) → int                              │
│    - get_audit_history(...) → list[AuditRecord]                │
└─────────────────────────────────────────────────────────────────┘
```

### Constraints

1. **PIN Storage**: PIN은 평문으로 저장되지 않음 (SHA-256 + salt)
2. **Brute Force Protection**: PIN 5회 실패 시 5분 잠금
3. **Limits Persist**: 한도 설정은 Settings에 저장되어 재시작 후에도 유지
4. **Audit Immutable**: 감사 로그는 수정/삭제 불가

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-SEC-001**: 시스템은 모든 거래 실행 전 2FA 인증을 항상 요구해야 한다 (The system shall always require 2FA authentication before any trade execution).

```
The system shall require 2FA verification before:
- TradingService.execute_approved_trade() 호출
- Manual buy/sell commands in CLI
- Web UI trade execution

Exception: --dry-run 또는 simulation mode
```

**REQ-SEC-002**: 시스템은 모든 거래 시도를 감사 로그에 항상 기록해야 한다 (The system shall always log all trade attempts to audit log).

```
The system shall log to audit_log table:
- timestamp, ticker, side, amount
- user action (approved/rejected/cancelled/timeout)
- 2fa_verified (true/false)
- limit_check_passed (true/false)
- error_message (if any)
```

**REQ-SEC-003**: 시스템은 PIN을 항상 해시하여 저장해야 한다 (The system shall always store PIN as hash).

```
The system shall:
- Use SHA-256 with random salt
- Never store plain-text PIN
- Store in Settings.security.pin_hash (not in .env)
```

### Event-Driven Requirements

**REQ-SEC-010**: WHEN 거래 요청이 발생하면 THEN 시스템은 2FA 인증을 요청해야 한다.

```
WHEN user initiates trade execution
THEN display PIN input prompt (masked input)
    AND verify entered PIN against stored hash
    AND proceed only if verification succeeds
```

**REQ-SEC-011**: WHEN PIN 인증이 5회 연속 실패하면 THEN 시스템은 5분간 잠금해야 한다.

```
WHEN pin_failure_count >= 5
THEN lock_security_module(duration=300 seconds)
    AND display "보안 모듈이 잠겼습니다. 5분 후 다시 시도하세요"
    AND reject all trade requests during lock period
```

**REQ-SEC-012**: WHEN 일일 거래 한도에 도달하면 THEN 시스템은 추가 거래를 차단해야 한다.

```
WHEN daily_volume_traded + current_trade_amount > max_daily_volume
THEN reject trade with "일일 거래 한도 초과" message
    AND log to audit (limit_exceeded=True)

WHEN daily_trade_count >= max_daily_trades
THEN reject trade with "일일 거래 횟수 한도 초과" message
    AND log to audit (limit_exceeded=True)
```

**REQ-SEC-013**: WHEN 고액 거래가 요청되면 THEN 시스템은 추가 확인을 요구해야 한다.

```
WHEN trade_amount > high_value_threshold (default: 100,000 KRW)
THEN display high-value warning:
    "⚠️ 고액 거래 감지: {amount:,.0f} KRW"
    "정말 진행하시겠습니까? (y/n)"
    AND require explicit confirmation
    AND log to audit (high_value=True)
```

**REQ-SEC-014**: WHEN 거래가 실행되면 THEN 시스템은 감사 로그를 기록해야 한다.

```
WHEN trade execution completes (success or failure)
THEN INSERT INTO audit_log (
    timestamp, ticker, side, amount,
    user_action, 2fa_verified, limit_check_passed,
    high_value, error_message
)
```

### State-Driven Requirements

**REQ-SEC-020**: IF PIN이 설정되지 않았으면 THEN 시스템은 거래를 차단하고 PIN 설정을 안내해야 한다.

```
IF settings.security.pin_hash is None OR empty
THEN block all trade executions
    AND display "PIN을 먼저 설정해주세요: moai security setup-pin"
    AND offer guided PIN setup
```

**REQ-SEC-021**: IF 보안 모듈이 잠금 상태이면 THEN 시스템은 모든 거래 요청을 거부해야 한다.

```
IF security_module.locked_until > now()
THEN reject trade request
    AND display remaining lock time
    AND log to audit (action=blocked_locked)
```

**REQ-SEC-022**: IF 단일 거래 금액이 max_single_trade를 초과하면 THEN 시스템은 거래를 차단해야 한다.

```
IF trade_amount > settings.security.max_single_trade
THEN reject trade with "단일 거래 한도 초과 ({max_single_trade:,} KRW)"
    AND suggest splitting into smaller trades
```

### Optional Requirements

**REQ-SEC-030**: Where possible, 시스템은 OTP (Google Authenticator)를 지원해야 한다.

```
Where possible, support TOTP-based 2FA:
- Generate QR code for Google Authenticator
- Verify 6-digit OTP codes
- Fallback to PIN if OTP fails
```

**REQ-SEC-031**: Where possible, 시스템은 비밀번호 확인을 지원해야 한다.

```
Where possible, support password confirmation:
- Require password for high-value trades (> 1,000,000 KRW)
- Use secure password prompt
- Rate limit password attempts
```

**REQ-SEC-032**: Where possible, 시스템은 IP 기반 접근 제한을 지원해야 한다.

```
Where possible, restrict by IP:
- Allow configuration of allowed IP ranges
- Block trades from unknown IPs
- Log IP address in audit records
```

### Unwanted Behavior Requirements

**REQ-SEC-040**: 시스템은 PIN을 평문으로 저장해서는 안 된다 (The system shall not store PIN in plain text).

```
The system shall NOT:
- Store PIN in .env file
- Log PIN in any output
- Display PIN in error messages
- Transmit PIN over network (local only)
```

**REQ-SEC-041**: 시스템은 2FA 없이 거래를 실행해서는 안 된다 (The system shall not execute trades without 2FA).

```
The system shall NOT:
- Bypass 2FA verification
- Allow --skip-2fa flag in production
- Execute trades with expired verification
```

**REQ-SEC-042**: 시스템은 감사 로그를 수정하거나 삭제해서는 안 된다 (The system shall not modify or delete audit log records).

```
The system shall NOT:
- Allow UPDATE on audit_log table
- Allow DELETE on audit_log table
- Expose audit_log modification API
```

---

## Specifications

### Data Models

#### SecuritySettings

```python
@dataclass
class SecuritySettings:
    """Security configuration stored in Settings."""

    # 2FA Settings
    pin_hash: str | None = None  # SHA-256 hash of PIN + salt
    pin_salt: str | None = None  # Random salt for PIN hashing
    pin_failure_count: int = 0   # Consecutive failed attempts
    locked_until: datetime | None = None  # Lock expiration time

    # Trading Limits
    max_daily_volume_krw: float = 10_000_000.0  # 10M KRW per day
    max_daily_trades: int = 20  # Max trades per day
    max_single_trade_krw: float = 5_000_000.0  # 5M KRW per trade
    high_value_threshold_krw: float = 100_000.0  # Extra confirmation above 100K

    # Session Limits
    max_session_volume_krw: float = 5_000_000.0  # 5M KRW per session
    max_session_trades: int = 10  # Max trades per session
```

#### AuditRecord

```python
@dataclass
class AuditRecord:
    """Audit log entry for trade attempts."""

    id: int  # Auto-increment
    timestamp: datetime
    ticker: str
    side: Literal["buy", "sell"]
    amount: float

    # User action outcome
    user_action: Literal["approved", "rejected", "cancelled", "timeout", "blocked_locked", "blocked_limit"]

    # Security checks
    two_fa_verified: bool
    limit_check_passed: bool
    high_value_trade: bool

    # Error info
    error_message: str | None

    # Session info
    session_id: str  # UUID for tracking
```

### SQLite Schema (audit_log)

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
    amount REAL NOT NULL,

    user_action TEXT NOT NULL CHECK(user_action IN (
        'approved', 'rejected', 'cancelled', 'timeout',
        'blocked_locked', 'blocked_limit'
    )),

    two_fa_verified INTEGER NOT NULL DEFAULT 0,
    limit_check_passed INTEGER NOT NULL DEFAULT 1,
    high_value_trade INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,

    session_id TEXT NOT NULL
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_session ON audit_log(session_id);
CREATE INDEX idx_audit_action ON audit_log(user_action);
```

### Service Interface

#### SecurityService

```python
class SecurityService:
    """
    Domain service for security enforcement.

    This service wraps TradingService with security layers:
    1. 2FA verification
    2. Trading limits check
    3. High-value confirmation
    4. Audit logging

    @MX:NOTE: SecurityService is the secure entry point for all trades.
        TradingService should not be called directly after this is implemented.
    """

    MAX_PIN_FAILURES: int = 5
    LOCK_DURATION_SECONDS: int = 300  # 5 minutes

    def __init__(
        self,
        trading_service: TradingService,
        settings: Settings,
        audit_repository: AuditRepository,
        logger: Logger | None = None,
    ):
        """Initialize with dependencies."""
        pass

    # === 2FA Methods ===

    async def verify_pin(self, pin: str) -> bool:
        """
        Verify 4-digit PIN against stored hash.

        Returns:
            bool: True if PIN is correct

        Raises:
            SecurityLockedError: If module is locked due to too many failures
            PinNotSetError: If PIN has not been configured

        @MX:WARN: Increments failure count on incorrect PIN.
            Locks module after 5 consecutive failures.
            @MX:REASON: Brute force protection for PIN-based authentication.
        """
        pass

    async def setup_pin(self, new_pin: str) -> None:
        """
        Set up PIN for the first time.

        Requirements:
        - Must be exactly 4 digits
        - Cannot be sequential (1234, 4321)
        - Cannot be repetitive (1111, 2222)

        Raises:
            ValueError: If PIN does not meet requirements
            PinAlreadySetError: If PIN is already configured
        """
        pass

    async def change_pin(self, old_pin: str, new_pin: str) -> bool:
        """
        Change existing PIN after verifying old PIN.

        Returns:
            bool: True if PIN changed successfully
        """
        pass

    def is_locked(self) -> bool:
        """Check if security module is currently locked."""
        pass

    def get_lock_remaining_seconds(self) -> int:
        """Get remaining lock time in seconds (0 if not locked)."""
        pass

    # === Limits Methods ===

    async def check_daily_limits(
        self,
        ticker: str,
        side: str,
        amount_krw: float,
    ) -> tuple[bool, str]:
        """
        Check if trade would exceed daily limits.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        pass

    async def check_session_limits(
        self,
        ticker: str,
        side: str,
        amount_krw: float,
    ) -> tuple[bool, str]:
        """
        Check if trade would exceed session limits.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        pass

    def check_single_trade_limit(self, amount_krw: float) -> tuple[bool, str]:
        """
        Check if single trade exceeds limit.

        Returns:
            tuple[bool, str]: (passed, error_message_if_failed)
        """
        pass

    def is_high_value_trade(self, amount_krw: float) -> bool:
        """Check if trade requires extra confirmation."""
        pass

    # === Secure Trade Execution ===

    async def secure_request_buy(
        self,
        ticker: str,
        amount_krw: float,
        pin: str,
        session_id: str,
    ) -> TradeApproval:
        """
        Request buy order with security checks.

        Flow:
        1. Verify PIN
        2. Check single trade limit
        3. Check daily/session limits
        4. Request via TradingService

        Returns:
            TradeApproval: Approval request from TradingService

        Raises:
            SecurityLockedError: Module locked
            PinNotSetError: PIN not configured
            LimitExceededError: Trading limit exceeded
        """
        pass

    async def secure_request_sell(
        self,
        ticker: str,
        quantity: float,
        pin: str,
        session_id: str,
    ) -> TradeApproval:
        """Request sell order with security checks (same flow as buy)."""
        pass

    async def secure_execute_trade(
        self,
        approval: TradeApproval,
        high_value_confirmed: bool,
        session_id: str,
    ) -> TradeResult:
        """
        Execute trade with security validation.

        Flow:
        1. Check high-value confirmation if needed
        2. Execute via TradingService
        3. Log to audit (success or failure)
        4. Update session/daily counters

        @MX:WARN: Executes REAL trades with REAL money.
            All security checks must pass before execution.
            @MX:REASON: Direct API call to Upbit exchange.
        """
        pass

    # === Audit Methods ===

    async def log_audit(
        self,
        ticker: str,
        side: str,
        amount: float,
        user_action: str,
        two_fa_verified: bool,
        limit_check_passed: bool,
        high_value_trade: bool,
        error_message: str | None,
        session_id: str,
    ) -> int:
        """Log trade attempt to audit table."""
        pass

    async def get_audit_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        user_action: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """Query audit log history."""
        pass
```

### CLI Integration

#### New CLI Commands

```python
# main.py additions

# Security setup
parser.add_argument(
    "--setup-pin",
    action="store_true",
    help="Set up 4-digit PIN for trade authentication",
)

parser.add_argument(
    "--change-pin",
    action="store_true",
    help="Change existing PIN",
)

# Security status
parser.add_argument(
    "--security-status",
    action="store_true",
    help="Display security configuration status",
)

# Limits configuration
parser.add_argument(
    "--set-daily-limit",
    type=float,
    metavar="KRW",
    help="Set daily trading volume limit in KRW",
)

parser.add_argument(
    "--set-trade-limit",
    type=int,
    metavar="COUNT",
    help="Set daily trade count limit",
)
```

#### Interactive PIN Input

```python
async def prompt_pin(console: Console) -> str:
    """
    Securely prompt for 4-digit PIN.

    Uses masked input for security.
    """
    console.print("[yellow]PIN 입력 (4자리):[/yellow] ", end="")

    # Use getpass for masked input
    import getpass
    pin = getpass.getpass("")

    if not pin.isdigit() or len(pin) != 4:
        console.print("[red]PIN은 4자리 숫자여야 합니다[/red]")
        raise ValueError("Invalid PIN format")

    return pin
```

---

## MX Tag Targets

### High Fan-In Functions (>= 3 callers)

| Function | Expected Fan-In | MX Tag Type | Location |
|----------|-----------------|-------------|----------|
| `SecurityService.verify_pin()` | 3+ | @MX:ANCHOR | domain/security.py |
| `SecurityService.secure_execute_trade()` | 2+ | @MX:ANCHOR | domain/security.py |
| `SecurityService.log_audit()` | 2+ | @MX:ANCHOR | domain/security.py |

### Danger Zones (Critical Operations)

| Function | Risk | MX Tag Type | Reason |
|----------|------|-------------|--------|
| `verify_pin()` | Brute force vulnerability | @MX:WARN | Must implement lockout |
| `setup_pin()` | Weak PIN acceptance | @MX:WARN | Must validate PIN strength |
| `secure_execute_trade()` | Financial loss | @MX:WARN | Executes real trades |
| PIN storage in Settings | Data exposure | @MX:NOTE | Never store plain-text PIN |

---

## Files to Modify

### New Files

| File Path | Purpose | Lines (Est.) |
|-----------|---------|--------------|
| `src/gpt_bitcoin/domain/security.py` | SecurityService, SecuritySettings | ~400 |
| `src/gpt_bitcoin/domain/audit.py` | AuditRecord, AuditRepository | ~150 |
| `src/gpt_bitcoin/infrastructure/persistence/audit_repository.py` | SQLite audit storage | ~120 |
| `tests/unit/domain/test_security.py` | SecurityService unit tests | ~500 |
| `tests/unit/infrastructure/test_audit_repository.py` | Audit repository tests | ~200 |

### Modified Files

| File Path | Changes | Lines Changed (Est.) |
|-----------|---------|---------------------|
| `main.py` | Security CLI commands, PIN prompts | +150 |
| `src/gpt_bitcoin/config/settings.py` | Add SecuritySettings | +50 |
| `src/gpt_bitcoin/dependencies/container.py` | Register SecurityService | +15 |
| `src/gpt_bitcoin/infrastructure/persistence/database.py` | Add audit_log table | +30 |
| `web_ui.py` | PIN input modal, security status | +100 |

---

## Risks and Mitigations

### Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PIN brute force attack | Medium | High | 5-attempt lockout, 5-minute cooldown |
| Weak PIN selection | High | Medium | Block sequential/repetitive PINs |
| Settings file exposure | Low | High | Encrypt PIN hash with app-level key |
| Audit log tampering | Low | Medium | SQLite permissions, log rotation |
| Session hijacking | Low | High | Session ID in audit, IP logging (optional) |

### Security Considerations

1. **PIN Strength**: Block 1234, 4321, 1111, 2222, 0000, 9999
2. **Salt Generation**: Use secrets.token_hex(16) for salt
3. **Hash Algorithm**: SHA-256 (sufficient for 4-digit PIN)
4. **Lockout Implementation**: Store in Settings with expiration timestamp
5. **Future Enhancement**: TOTP (Google Authenticator) for stronger 2FA

---

## Traceability Matrix

| Requirement | Component | Test Case |
|-------------|-----------|-----------|
| REQ-SEC-001 | SecurityService.verify_pin() | test_2fa_required_before_trade() |
| REQ-SEC-002 | SecurityService.log_audit() | test_all_trades_logged() |
| REQ-SEC-003 | setup_pin() | test_pin_hashed_storage() |
| REQ-SEC-010 | secure_request_buy/sell() | test_pin_prompt_on_trade() |
| REQ-SEC-011 | verify_pin() | test_lockout_after_5_failures() |
| REQ-SEC-012 | check_daily_limits() | test_daily_limit_enforcement() |
| REQ-SEC-013 | is_high_value_trade() | test_high_value_confirmation() |
| REQ-SEC-014 | log_audit() | test_audit_on_trade_completion() |
| REQ-SEC-020 | secure_request_*() | test_pin_setup_required() |
| REQ-SEC-021 | is_locked() | test_locked_module_rejection() |
| REQ-SEC-022 | check_single_trade_limit() | test_single_trade_limit() |
| REQ-SEC-040 | setup_pin() | test_no_plaintext_pin_storage() |
| REQ-SEC-041 | secure_execute_trade() | test_no_2fa_bypass() |
| REQ-SEC-042 | AuditRepository | test_audit_log_immutable() |

---

## Success Criteria

1. **Functional**: All 14 core requirements implemented and passing tests
2. **Security**: PIN stored as hash only, no plaintext anywhere
3. **UX**: Clear PIN prompts with masked input
4. **Limits**: Daily/session limits enforced correctly
5. **Audit**: All trade attempts logged to audit_log table
6. **Coverage**: Minimum 85% test coverage for security module
7. **Integration**: CLI and Web UI both use SecurityService

---

## Related SPECs

- **SPEC-TRADING-001**: TradingService foundation (Completed - wrapped by SecurityService)
- **SPEC-TRADING-002**: Trading History (audit_log extends trades table)
- **SPEC-TRADING-003**: CLI Integration (CLI calls SecurityService)

---

## Future Enhancements (Out of Scope)

1. **TOTP Support**: Google Authenticator integration (REQ-SEC-030)
2. **Password Confirmation**: For very high-value trades (REQ-SEC-031)
3. **IP Restrictions**: Geographic/network-based access control (REQ-SEC-032)
4. **Biometric Auth**: Fingerprint/Face ID for supported devices
5. **Multi-Signature**: Require multiple approvals for large trades

---

Version: 1.0.0
Last Updated: 2026-03-04
Author: MoAI SPEC Builder
