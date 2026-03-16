# SPEC-TRADING-004: Research Findings

## Codebase Analysis

### Existing Security Measures

**JWT Authentication** (src/gpt_bitcoin/infrastructure/external/upbit_client.py:194-236):
- Already implements HS256 JWT for Upbit API
- API keys stored in Settings
- Tokens generated per request

**Current Gaps**:
1. No user-facing 2FA before trade execution
2. No trading limits enforced
3. No audit trail for trade attempts
4. No protection against accidental high-value trades

### Reference Implementations

**PIN Hashing Pattern** (from industry best practices):
```python
import hashlib

def hash_pin(pin: str, salt: str) -> str:
    """Hash PIN with salt for storage."""
    return hashlib.sha256(f"{salt}{pin}".encode()).hexdigest()

# Use bcrypt for production (more secure)
import bcrypt
def hash_pin_bcrypt(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
```

**Rate Limiting Pattern** (existing in UpbitClient):
- Already has RateLimiter class at infrastructure/resilience/circuit_breaker.py
- Can reuse for failed attempt tracking

### Integration Points

**TradingService** (src/gpt_bitcoin/domain/trading.py):
- `request_buy_order()` returns TradeApproval
- `execute_approved_trade()` returns TradeResult
- SecurityService wraps these with pre/post checks

**Settings Extension**:
```python
# Add to src/gpt_bitcoin/config/settings.py
class SecuritySettings(BaseSettings):
    pin_hash: str | None = None
    pin_salt: str = Field(default_factory(lambda: os.urandom(16).hex())
    max_daily_volume_krw: float = 1_000_000.0
    max_daily_trades: int = 10
    max_single_trade_krw: float = 500_000.0
    high_value_threshold_krw: float = 100_000.0
```

### Database Schema

**Audit Table** (add to SQLite):
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    amount REAL NOT NULL,
    user_action TEXT NOT NULL,
    two_fa_verified BOOLEAN NOT NULL,
    limit_check_passed BOOLEAN NOT NULL,
    high_value_trade BOOLEAN NOT NULL,
    error_message TEXT,
    session_id TEXT NOT NULL
);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_action ON audit_log(user_action);
```

### Security Considerations

1. **PIN Storage**: Never store plain PIN - use bcrypt hashing
2. **Session Management**: Track session IDs for audit trail
3. **Lockout**: Progressive delay (60s -> 300s -> 3600s) for repeated failures
4. **High-Value Warning**: Confirm trades > 100,000 KRW separately

---

Version: 1.0.0
Last Updated: 2026-03-04
