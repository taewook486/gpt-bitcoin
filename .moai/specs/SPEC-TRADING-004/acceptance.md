# SPEC-TRADING-004: Acceptance Criteria

## Gherkin Format

### Feature: 2FA PIN Authentication

```gherkin
Feature: 2FA PIN Authentication
  As a trader
  I want to authenticate with a PIN before trading
  So that my trades are protected from unauthorized access

  Background:
    Given SecurityService is initialized
    And PIN is set to "1234"

  Scenario: Successful PIN verification
    When I verify PIN "1234"
    Then verification should succeed
    And failed attempts should reset to 0

  Scenario: Failed PIN verification
    When I verify PIN "0000"
    Then verification should fail
    And failed attempts should increase to 1

  Scenario: Security lock after 3 failed attempts
    When I verify PIN "0000"
    And I verify PIN "0000"
    And I verify PIN "0000"
    Then SecurityService should be locked for 60 seconds
    And subsequent verifications should fail with lock error

  Scenario: PIN not configured
    Given PIN is not set
    When I try to verify PIN "1234"
    Then error should be "PIN이 설정되지 않았습니다"
```

### Feature: Trading Limits

```gherkin
Feature: Trading Limits
  As a trader
  I want trading limits to prevent excessive losses
  So that I don't accidentally trade too much

  Background:
    Given SecurityService is initialized
    And daily volume limit is 1,000,000 KRW
    And daily trade count limit is 10
    And single trade limit is 500,000 KRW

  Scenario: Single trade limit exceeded
    When I request to buy 600,000 KRW of BTC
    Then request should be rejected
    And error should contain "단일 거래 한도 초과"

  Scenario: Daily volume limit exceeded
    Given I have already traded 900,000 KRW today
    When I request to buy 200,000 KRW of BTC
    Then request should be rejected
    And error should contain "일일 거래 한도 초과"

  Scenario: Daily count limit exceeded
    Given I have already made 10 trades today
    When I request to buy 50,000 KRW of BTC
    Then request should be rejected
    And error should contain "일일 거래 횟수 초과"

  Scenario: All limits within range
    When I request to buy 50,000 KRW of BTC
    Then request should be approved
```

### Feature: High-Value Trade Confirmation

```gherkin
Feature: High-Value Trade Confirmation
  As a trader
  I want to confirm high-value trades separately
  So that I don't accidentally execute large trades

  Background:
    Given high-value threshold is 100,000 KRW
    And SecurityService is initialized

  Scenario: Normal trade execution
    When I request to buy 50,000 KRW of BTC
    Then approval should be granted without extra confirmation

  Scenario: High-value trade requires confirmation
    When I request to buy 150,000 KRW of BTC
    Then approval should indicate high-value trade
    And execution should require high_value_confirmed=True

  Scenario: High-value trade executed without confirmation
    Given I have approval for 150,000 KRW BTC trade
    When I execute without high_value_confirmation
    Then execution should fail
    And error should be "고액 거래 확인이 필요합니다"

  Scenario: High-value trade executed with confirmation
    Given I have approval for 150,000 KRW BTC trade
    When I execute with high_value_confirmation=True
    Then execution should succeed
```

### Feature: Audit Logging

```gherkin
Feature: Audit Logging
  As a system administrator
  I want all trade attempts logged
  So that I can review security events

  Background:
    Given SecurityService is initialized
    And audit log is empty

  Scenario: Log successful trade
    When I execute a trade with valid PIN
    Then audit log should contain record with user_action="approved"
    And two_fa_verified should be True
    And limit_check_passed should be True

  Scenario: Log failed PIN verification
    When I verify invalid PIN "0000"
    Then audit log should contain record with user_action="rejected"
    And two_fa_verified should be False

  Scenario: Log limit exceeded
    When I request trade exceeding single trade limit
    Then audit log should contain record with user_action="blocked_limit"
    And limit_check_passed should be False

  Scenario: Query audit history
    Given audit log contains 50 records
    When I query audit history with limit=20
    Then 20 records should be returned
    And records should be ordered by timestamp DESC
```

---

Version: 1.0.0
Last Updated: 2026-03-04
