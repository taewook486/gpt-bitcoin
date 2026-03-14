# SPEC-TRADING-005: Acceptance Criteria

## Gherkin Format

### Feature: Testnet Mode

```gherkin
Feature: Testnet Mode
  As a trader
  I want to practice trading in a simulation environment
  So that I can test strategies without risking real money

  Scenario: Switch to testnet mode
    Given I am in production mode
    When I switch to testnet mode
    Then MockUpbitClient should be active
    And virtual balance should be initialized to 10,000,000 KRW
    And TESTNET MODE banner should be displayed

  Scenario: Switch back to production mode
    Given I am in testnet mode
    When I switch to production mode
    Then real UpbitClient should be active
    And TESTNET MODE banner should be hidden

  Scenario: Execute simulated buy order
    Given I am in testnet mode
    And I have 10,000,000 KRW virtual balance
    When I buy 1,000,000 KRW of BTC
    Then virtual KRW balance should be 9,000,000 KRW
    And BTC balance should be increased
    And no real API call should be made
    And trade should be recorded in testnet_trades.db
```

### Feature: Virtual Balance Management

```gherkin
Feature: Virtual Balance Management
  As a testnet user
  I want to manage my virtual balance
  So that I can test different scenarios

  Scenario: Add virtual KRW
    Given I am in testnet mode
    And I have 10,000,000 KRW virtual balance
    When I add 1,000,000 KRW
    Then virtual KRW balance should be 11,000,000 KRW

  Scenario: Reset to default balance
    Given I am in testnet mode
    And I have 5,000,000 KRW virtual balance
    When I reset balance to default
    Then virtual KRW balance should be 10,000,000 KRW
    And all coin balances should be zero

  Scenario: Insufficient virtual balance
    Given I am in testnet mode
    And I have 1,000 KRW virtual balance
    When I try to buy 100,000 KRW of BTC
    Then error should be "잔액 부족"
    And I should be offered option to add virtual KRW
```

### Feature: UI Mode Indicator

```gherkin
Feature: UI Mode Indicator
  As a trader
  I want to clearly see which mode I'm in
  So that I don't accidentally trade with real money

  Scenario: Production mode UI
    Given I am in production mode
    Then TESTNET MODE banner should NOT be displayed
    And theme should be normal

  Scenario: Testnet mode UI
    Given I am in testnet mode
    Then TESTNET MODE banner should be displayed
    And banner should be red/yellow color
    And banner should say "시뮬레이션 환경입니다"
    And theme should use warning colors
```

### Feature: Database Separation

```gherkin
Feature: Database Separation
  As a system
  I want to keep testnet and production data separate
  So that simulation data doesn't mix with real trades

  Scenario: Testnet uses separate database
    Given I am in testnet mode
    When I execute a trade
    Then trade should be saved to testnet_trades.db
    And trade should NOT be in trades.db

  Scenario: Production uses main database
    Given I am in production mode
    When I execute a trade
    Then trade should be saved to trades.db
    And trade should NOT be in testnet_trades.db

  Scenario: Testnet data not visible in production
    Given I executed 10 trades in testnet mode
    When I switch to production mode
    And I query trade history
    Then those 10 testnet trades should NOT appear
```

---

Version: 1.0.0
Last Updated: 2026-03-04
