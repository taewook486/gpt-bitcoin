# SPEC-TRADING-005: Implementation Plan

## Phases

### Phase 1: Domain Models & Config (Est. 2 hours)

**Tasks**:
1. Create `TradingMode` enum in `domain/trading_mode.py`
2. Create `TestnetConfig` and `MockBalance` in `domain/testnet_config.py`
3. Add testnet settings to `config/settings.py`

**Acceptance Criteria**:
- [ ] TradingMode enum created with PRODUCTION and TESTNET values
- [ ] TestnetConfig model with default balance of 10,000,000 KRW
- [ ] Settings.testnet_mode flag added

---

### Phase 2: MockUpbitClient Implementation (Est. 4 hours)

**Tasks**:
1. Create `MockUpbitClient` class in `infrastructure/external/mock_upbit_client.py`
2. Implement virtual balance management
3. Implement simulated order execution
4. Add orderbook and price simulation

**Acceptance Criteria**:
- [ ] MockUpbitClient implements same interface as UpbitClient
- [ ] Virtual KRW balance initialized and updated correctly
- [ ] Coin balances tracked properly
- [ ] Simulated fees calculated (0.05%)
- [ ] No real HTTP requests made

---

### Phase 3: DI Container Integration (Est. 2 hours)

**Tasks**:
1. Modify `Container` class in `dependencies/container.py`
2. Add trading_mode provider
3. Add mock_upbit_client provider
4. Implement get_upbit_client() mode selector

**Acceptance Criteria**:
- [ ] Container switches between UpbitClient and MockUpbitClient based on mode
- [ ] Mode can be changed at runtime
- [ ] All existing code works without changes

---

### Phase 4: Web UI Integration (Est. 3 hours)

**Tasks**:
1. Add testnet banner to web_ui.py
2. Add mode switcher in Settings tab
3. Add virtual balance management UI
4. Update trade confirmation dialogs to show mode

**Acceptance Criteria**:
- [ ] Red/yellow "TESTNET MODE" banner displayed
- [ ] Mode switcher functional
- [ ] Virtual balance can be reset/added
- [ ] All trade dialogs show current mode

---

### Phase 5: CLI Integration (Est. 1 hour)

**Tasks**:
1. Add --testnet flag to main.py
2. Set trading_mode based on flag

**Acceptance Criteria**:
- [ ] `python main.py --testnet` enables testnet mode
- [ ] CLI shows testnet mode indicator

---

### Phase 6: Testing (Est. 3 hours)

**Tasks**:
1. Write unit tests for MockUpbitClient
2. Write integration tests for mode switching
3. Write UI tests for testnet banner and switcher

**Acceptance Criteria**:
- [ ] All tests passing
- [ ] Coverage >= 85%

---

## Risk Management

| Risk | Mitigation |
|------|------------|
| Mode confusion | Prominent UI banner, different colors |
| DB mixing | Separate file paths enforced |
| Mock inaccuracy | Document limitations clearly |

---

## Success Criteria

1. All phases completed
2. All tests passing
3. No real API calls in testnet mode
4. Clear visual distinction between modes

---

Version: 1.0.0
Last Updated: 2026-03-04
