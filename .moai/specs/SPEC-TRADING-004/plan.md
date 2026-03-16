# SPEC-TRADING-004: Implementation Plan

## Metadata

- **SPEC ID**: SPEC-TRADING-004
- **Title**: Security Enhancements Implementation Plan
- **Created**: 2026-03-04
- **Development Mode**: DDD (Characterization Tests First)

---

## Implementation Strategy

### Approach: Wrapper Pattern

SecurityService는 TradingService를 감싸는 Wrapper로 구현됩니다. 기존 TradingService는 수정 없이 그대로 사용되며, 모든 보안 로직은 SecurityService에서 처리됩니다.

```
Before (SPEC-TRADING-003):
CLI → TradingService → UpbitClient

After (SPEC-TRADING-004):
CLI → SecurityService → TradingService → UpbitClient
              ↓
         AuditRepository → SQLite
```

### Priority Milestones

1. **Primary Goal**: 2FA PIN 시스템 구현
2. **Primary Goal**: 거래 한도 검증 시스템
3. **Secondary Goal**: 고액 거래 추가 확인
4. **Secondary Goal**: 감사 로그 시스템
5. **Optional Goal**: TOTP/Password/IP 제한 (향후 확장)

---

## Phase 1: Foundation (Security Domain Models)

### Tasks

1. **Create SecuritySettings Model**
   - Location: `src/gpt_bitcoin/config/settings.py`
   - Add security-related fields to Settings class
   - Include validation for limit values

2. **Create AuditRecord Model**
   - Location: `src/gpt_bitcoin/domain/audit.py`
   - Define dataclass for audit log entries
   - Add Literal types for user_action field

3. **Add audit_log Table Schema**
   - Location: `src/gpt_bitcoin/infrastructure/persistence/database.py`
   - CREATE TABLE statement for audit_log
   - Indexes for efficient querying

### Files to Create/Modify

- `src/gpt_bitcoin/domain/audit.py` (NEW)
- `src/gpt_bitcoin/config/settings.py` (MODIFY)
- `src/gpt_bitcoin/infrastructure/persistence/database.py` (MODIFY)

### Acceptance Criteria

- [ ] SecuritySettings fields defined with validation
- [ ] AuditRecord dataclass with all required fields
- [ ] audit_log table schema with indexes
- [ ] Unit tests for model validation

---

## Phase 2: 2FA PIN System

### Tasks

1. **Implement PIN Hashing**
   - Use SHA-256 with random salt
   - Block weak PINs (1234, 1111, etc.)
   - Store in Settings.security

2. **Implement verify_pin()**
   - Check lock status first
   - Compare hash with stored value
   - Increment failure count on mismatch
   - Lock module after 5 failures

3. **Implement setup_pin()**
   - Validate PIN format (4 digits)
   - Check against blocked PIN list
   - Generate salt and hash
   - Store in Settings

4. **Implement change_pin()**
   - Verify old PIN first
   - Validate new PIN
   - Update stored hash

### Files to Create/Modify

- `src/gpt_bitcoin/domain/security.py` (NEW)
- `tests/unit/domain/test_security.py` (NEW)

### Acceptance Criteria

- [ ] PIN stored as SHA-256 hash only
- [ ] Weak PINs rejected with clear error message
- [ ] 5 failed attempts triggers 5-minute lockout
- [ ] Lock status persisted across restarts
- [ ] Unit tests cover all PIN operations

---

## Phase 3: Trading Limits System

### Tasks

1. **Implement check_daily_limits()**
   - Query audit_log for today's volume
   - Compare against max_daily_volume_krw
   - Compare trade count against max_daily_trades

2. **Implement check_session_limits()**
   - Track session volume in memory
   - Compare against max_session_volume_krw
   - Compare against max_session_trades

3. **Implement check_single_trade_limit()**
   - Simple comparison against max_single_trade_krw

4. **Implement is_high_value_trade()**
   - Compare against high_value_threshold_krw

### Files to Modify

- `src/gpt_bitcoin/domain/security.py` (MODIFY)
- `tests/unit/domain/test_security.py` (MODIFY)

### Acceptance Criteria

- [ ] Daily volume limit enforced
- [ ] Daily trade count limit enforced
- [ ] Session limits tracked correctly
- [ ] Single trade limit enforced
- [ ] High-value threshold detection works
- [ ] Unit tests for all limit scenarios

---

## Phase 4: Audit Logging System

### Tasks

1. **Create AuditRepository**
   - Location: `src/gpt_bitcoin/infrastructure/persistence/audit_repository.py`
   - Implement insert() for audit records
   - Implement find_with_filters() for querying

2. **Implement log_audit()**
   - Insert record after every trade attempt
   - Include all required fields
   - Handle database errors gracefully

3. **Implement get_audit_history()**
   - Support date range filtering
   - Support action type filtering
   - Return newest first with pagination

### Files to Create/Modify

- `src/gpt_bitcoin/infrastructure/persistence/audit_repository.py` (NEW)
- `src/gpt_bitcoin/domain/security.py` (MODIFY - add log_audit)
- `tests/unit/infrastructure/test_audit_repository.py` (NEW)

### Acceptance Criteria

- [ ] All trade attempts logged to audit_log
- [ ] Audit records immutable (no UPDATE/DELETE)
- [ ] Query by date range works
- [ ] Query by action type works
- [ ] Unit tests for repository operations

---

## Phase 5: SecurityService Integration

### Tasks

1. **Implement secure_request_buy()**
   - Call verify_pin()
   - Call check_single_trade_limit()
   - Call check_daily_limits()
   - Call check_session_limits()
   - Call TradingService.request_buy_order()
   - Log audit on failure

2. **Implement secure_request_sell()**
   - Same flow as secure_request_buy()

3. **Implement secure_execute_trade()**
   - Check high_value_trade confirmation
   - Call TradingService.execute_approved_trade()
   - Log audit (success or failure)
   - Update session counters

4. **Register in DI Container**
   - Add SecurityService to container.py
   - Wire dependencies correctly

### Files to Create/Modify

- `src/gpt_bitcoin/domain/security.py` (MODIFY)
- `src/gpt_bitcoin/dependencies/container.py` (MODIFY)
- `tests/unit/domain/test_security.py` (MODIFY)

### Acceptance Criteria

- [ ] All security checks execute in correct order
- [ ] TradingService called only after all checks pass
- [ ] Audit log records all outcomes
- [ ] Session counters updated correctly
- [ ] Integration tests pass

---

## Phase 6: CLI Integration

### Tasks

1. **Add Security CLI Commands**
   - --setup-pin: Interactive PIN setup
   - --change-pin: PIN change workflow
   - --security-status: Display current status

2. **Add Limits CLI Commands**
   - --set-daily-limit: Configure daily volume limit
   - --set-trade-limit: Configure daily trade count

3. **Modify Trade Flow in main.py**
   - Replace TradingService calls with SecurityService
   - Add PIN prompt before trade execution
   - Add high-value confirmation prompt

4. **Implement PIN Input Prompt**
   - Use getpass for masked input
   - Validate 4-digit format
   - Handle lockout gracefully

### Files to Modify

- `main.py` (MODIFY)
- `tests/characterization/test_autotrade_v3.py` (MODIFY - if needed)

### Acceptance Criteria

- [ ] PIN prompt appears before trade execution
- [ ] Masked input for PIN entry
- [ ] Lockout message displays remaining time
- [ ] High-value confirmation works
- [ ] All CLI security commands work
- [ ] Backward compatible with --dry-run

---

## Phase 7: Web UI Integration

### Tasks

1. **Add Security Status Section**
   - Display PIN status (set/not set)
   - Display current limits
   - Display today's trading volume

2. **Add PIN Input Modal**
   - Streamlit text_input with type="password"
   - Trigger on trade button click
   - Validate before executing

3. **Add High-Value Confirmation Dialog**
   - Display warning for trades > threshold
   - Require explicit checkbox or button

4. **Update Trade Execution Flow**
   - Replace TradingService with SecurityService
   - Pass PIN from input modal

### Files to Modify

- `web_ui.py` (MODIFY)

### Acceptance Criteria

- [ ] PIN input modal appears on trade
- [ ] Security status visible in sidebar
- [ ] High-value warning displays correctly
- [ ] Audit records created from UI trades

---

## Technical Approach

### PIN Hashing Implementation

```python
import hashlib
import secrets

BLOCKED_PINS = {"1234", "4321", "1111", "2222", "3333", "4444", "5555",
                "6666", "7777", "8888", "9999", "0000"}

def hash_pin(pin: str, salt: str) -> str:
    """Hash PIN with salt using SHA-256."""
    return hashlib.sha256(f"{pin}{salt}".encode()).hexdigest()

def is_weak_pin(pin: str) -> bool:
    """Check if PIN is in blocked list."""
    return pin in BLOCKED_PINS

def generate_salt() -> str:
    """Generate random salt for PIN hashing."""
    return secrets.token_hex(16)
```

### Lockout Implementation

```python
from datetime import datetime, timedelta

class SecurityService:
    MAX_PIN_FAILURES = 5
    LOCK_DURATION_SECONDS = 300

    def _check_lock_status(self) -> None:
        """Check and clear expired locks."""
        if self._settings.security.locked_until:
            if datetime.now() > self._settings.security.locked_until:
                # Lock expired, reset
                self._settings.security.locked_until = None
                self._settings.security.pin_failure_count = 0

    def _increment_failure(self) -> None:
        """Increment failure count and lock if threshold reached."""
        self._settings.security.pin_failure_count += 1

        if self._settings.security.pin_failure_count >= self.MAX_PIN_FAILURES:
            self._settings.security.locked_until = (
                datetime.now() + timedelta(seconds=self.LOCK_DURATION_SECONDS)
            )
```

### Session Tracking

```python
@dataclass
class SessionTracker:
    """Track trading activity within a session."""

    session_id: str
    start_time: datetime
    volume_krw: float = 0.0
    trade_count: int = 0

    def add_trade(self, amount_krw: float) -> None:
        """Record a trade in this session."""
        self.volume_krw += amount_krw
        self.trade_count += 1
```

---

## Dependencies Graph

```
security.py
    ├── settings.py (SecuritySettings)
    ├── audit.py (AuditRecord)
    ├── trading.py (TradingService - existing)
    └── persistence/audit_repository.py

audit_repository.py
    ├── database.py (SQLite connection)
    └── audit.py (AuditRecord)

main.py
    ├── security.py (SecurityService - NEW)
    ├── trading.py (TradingService - via SecurityService)
    └── dependencies/container.py

web_ui.py
    ├── security.py (SecurityService - NEW)
    └── trading.py (TradingService - via SecurityService)
```

---

## Testing Strategy

### Unit Tests

1. **test_security.py**
   - PIN hashing verification
   - Weak PIN detection
   - Lockout behavior
   - Limit checking logic
   - Audit logging

2. **test_audit_repository.py**
   - CRUD operations
   - Query filtering
   - Immutability verification

### Integration Tests

1. **test_security_trading_flow.py**
   - Full flow: PIN → Limits → Trade → Audit
   - Error scenarios
   - Lockout during trade

### Characterization Tests

Update existing tests to use SecurityService instead of TradingService directly.

---

## Rollback Plan

If issues arise:

1. **Phase 1-2 Issues**: Feature flag to disable 2FA
   ```python
   if settings.security.enable_2fa:
       verified = await security_service.verify_pin(pin)
   ```

2. **Phase 3 Issues**: Feature flag to disable limits
   ```python
   if settings.security.enable_limits:
       passed, error = await security_service.check_daily_limits(...)
   ```

3. **Complete Rollback**: Revert CLI to call TradingService directly
   - Keep SecurityService code for future use
   - Remove from container wiring temporarily

---

## Performance Considerations

1. **PIN Verification**: O(1) - single hash comparison
2. **Daily Limits Query**: O(n) with date index - ~100 records max
3. **Session Tracking**: O(1) - in-memory counters
4. **Audit Insert**: O(1) - single INSERT

Expected overhead per trade: < 50ms for security checks

---

## Configuration Example

```yaml
# .moai/config/sections/security.yaml (future)
security:
  enable_2fa: true
  enable_limits: true
  enable_audit: true

  pin:
    min_length: 4
    max_length: 4
    lockout_attempts: 5
    lockout_duration_seconds: 300

  limits:
    max_daily_volume_krw: 10000000
    max_daily_trades: 20
    max_single_trade_krw: 5000000
    max_session_volume_krw: 5000000
    max_session_trades: 10
    high_value_threshold_krw: 100000
```

---

Version: 1.0.0
Last Updated: 2026-03-04
