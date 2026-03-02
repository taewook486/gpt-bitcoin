# Acceptance Criteria: SPEC-UPDATE-AI-001

**SPEC ID**: SPEC-UPDATE-AI-001
**Title**: GLM-5 AI Model Migration
**Created**: 2026-03-02
**Updated**: 2026-03-02 (Added dual provider fallback tests)
**Status**: Planned

---

## Overview

This document defines the acceptance criteria, test scenarios, and validation procedures for the GLM-5 migration. All criteria must be satisfied before the migration is considered complete.

---

## Acceptance Criteria

### Functional Requirements

#### AC-001: GLM-5 API Authentication
**Requirement**: REQ-001
**Priority**: Critical
**Status**: Pending

**Given** the system is configured with GLM_API_KEY environment variable
**When** the system initializes the AI client
**Then** authentication with GLM-5 API succeeds without errors

**Validation**:
```python
def test_glm_authentication():
    client = GLMClient()
    assert client.api_key is not None
    assert client.client is not None
    # Test simple API call
    response = client.chat_completion(
        model="glm-5",
        messages=[{"role": "user", "content": "test"}]
    )
    assert response is not None
```

---

#### AC-002: JSON Response Format
**Requirement**: REQ-002, REQ-003
**Priority**: Critical
**Status**: Pending

**Given** the system calls GLM-5 API with response_format={"type":"json_object"}
**When** the API returns a decision
**Then** the response is valid JSON with decision, percentage, and reason fields

**Validation**:
```python
def test_json_response_format():
    response = client.chat_completion(
        model="glm-5",
        messages=[...],
        response_format={"type":"json_object"}
    )
    decision = json.loads(response)
    assert "decision" in decision
    assert decision["decision"] in ["buy", "sell", "hold"]
    assert "percentage" in decision
    assert 0 <= decision["percentage"] <= 100
    assert "reason" in decision
    assert isinstance(decision["reason"], str)
```

---

#### AC-002-A: Dual Provider Fallback Mechanism
**Requirement**: REQ-010, REQ-010-A, REQ-011
**Priority**: Critical
**Status**: Pending

**Given** the system is configured with both GLM_API_KEY and OPENAI_API_KEY
**When** GLM-5 API fails or times out
**Then** the system automatically falls back to OpenAI without service disruption

**Test Scenarios**:

1. **GLM-5 Authentication Failure**:
```python
def test_fallback_on_auth_failure():
    # Mock invalid GLM_API_KEY
    with mock.patch.dict(os.environ, {'GLM_API_KEY': 'invalid_key'}):
        client = get_ai_client()
        # Should fallback to OpenAI
        assert isinstance(client, OpenAI)
        # OpenAI key should be used
        assert client.api_key == os.getenv('OPENAI_API_KEY')
```

2. **GLM-5 Timeout Fallback**:
```python
def test_fallback_on_timeout():
    # Mock GLM-5 timeout
    with mock.patch('glm_client.GLMClient.chat_completion', side_effect=TimeoutError):
        client = get_ai_client()
        # Should fall back to OpenAI
        response = client.chat_completion(...)
        assert response is not None
```

3. **Fallback Logging**:
```python
def test_fallback_logging():
    with mock.patch.dict(os.environ, {'GLM_API_KEY': 'invalid_key'}):
        with caplog.at_level(logging.INFO):
            client = get_ai_client()
            # Verify fallback was logged
            assert "Falling back to OpenAI" in caplog.text
```

**Validation**:
- Fallback occurs within 2 seconds of GLM-5 failure
- Fallback event is logged with timestamp
- Subsequent calls attempt GLM-5 again (not permanent fallback)
- No data loss during fallback transition

---

#### AC-003: v1 Migration Success
**Requirement**: REQ-005
**Priority**: Critical
**Status**: Pending

**Given** autotrade.py uses GLM-5 client
**When** make_decision_and_execute() is triggered
**Then** GLM-5 API is called and returns valid decision

**Test Scenario**:
```bash
# Manual test
python autotrade.py

# Expected output
# - API call succeeds
# - JSON decision parsed correctly
# - Decision logged to console
```

**Validation**:
- API call success
- JSON parsing success
- Decision schema validation

---

#### AC-004: v2 Migration Success
**Requirement**: REQ-005
**Priority**: Critical
**Status**: Pending

**Given** autotrade_v2.py uses GLM-5 client
**When** make_decision_and_execute() is triggered
**Then** GLM-5 API processes news, data, decisions, and fear/greed inputs
**And** SQLite database stores decision correctly

**Test Scenario**:
```bash
# Manual test
python autotrade_v2.py

# Expected output
# - News data fetched
# - Technical data prepared
# - Last decisions retrieved
# - Fear & Greed index fetched
# - GLM-5 API call succeeds
# - Decision saved to SQLite
```

**Validation**:
- All data sources load correctly
- API call includes all inputs
- Database entry created with correct schema

---

#### AC-005: v3 Migration Success with Vision
**Requirement**: REQ-008
**Priority**: Critical
**Status**: Pending

**Given** autotrade_v3.py uses GLM-5 vision model
**When** make_decision_and_execute() is triggered
**Then** chart screenshot is captured and encoded
**And** GLM-5 vision API processes image
**And** decision includes chart analysis

**Test Scenario**:
```bash
# Manual test
python autotrade_v3.py

# Expected output
# - Screenshot captured (screenshot.png exists)
# - Base64 encoding successful
# - Vision API call succeeds
# - Decision includes visual analysis in reason
```

**Validation**:
- Screenshot file created
- Base64 string generated
- Vision API accepts image input
- Decision quality matches GPT-4o baseline

---

#### AC-006: Retry Logic
**Requirement**: REQ-006, REQ-007
**Priority**: High
**Status**: Pending

**Given** GLM-5 API call fails with network error
**When** retry logic is triggered
**Then** system retries up to 5 times with 5-second exponential backoff

**Test Scenario**:
```python
def test_retry_logic(mocker):
    # Mock API to fail 3 times then succeed
    call_count = 0
    def mock_api_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            raise requests.exceptions.Timeout()
        return {"choices": [{"message": {"content": '{"decision":"hold"}'}}]}

    mocker.patch('client.chat_completion', side_effect=mock_api_call)

    result = analyze_data_with_glm5(...)

    assert call_count == 4  # 3 failures + 1 success
    assert result is not None
```

---

#### AC-007: Error Handling - Authentication Failure
**Requirement**: REQ-010
**Priority**: High
**Status**: Pending

**Given** GLM_API_KEY is not set or invalid
**When** system initializes AI client
**Then** clear error message is raised

**Test Scenario**:
```python
def test_auth_failure():
    # Remove GLM_API_KEY
    os.environ.pop("GLM_API_KEY", None)

    with pytest.raises(ValueError) as exc_info:
        client = GLMClient()

    assert "GLM_API_KEY" in str(exc_info.value)
```

---

#### AC-008: Error Handling - Timeout
**Requirement**: REQ-011
**Priority**: High
**Status**: Pending

**Given** GLM-5 API response exceeds 10-second timeout
**When** API call is made
**Then** request is cancelled and timeout error is logged

**Test Scenario**:
```python
def test_timeout_handling(mocker):
    # Mock slow API response
    def slow_api_call(*args, **kwargs):
        time.sleep(15)
        return {"choices": [...]}

    mocker.patch('client.chat_completion', side_effect=slow_api_call)

    with pytest.raises(requests.exceptions.Timeout):
        analyze_data_with_glm5(...)

    # Verify timeout logged
    assert "timeout" in log_output.lower()
```

---

#### AC-009: Error Handling - Rate Limit
**Requirement**: REQ-014
**Priority**: Medium
**Status**: Pending

**Given** GLM-5 API returns HTTP 429 (rate limit exceeded)
**When** system receives rate limit response
**Then** execution pauses for 60 seconds
**And** system retries API call

**Test Scenario**:
```python
def test_rate_limit_handling(mocker):
    # Mock rate limit response
    call_times = []
    def rate_limit_api(*args, **kwargs):
        call_times.append(time.time())
        if len(call_times) == 1:
            raise requests.exceptions.HTTPError(response=Mock(status_code=429))
        return {"choices": [...]}

    mocker.patch('client.chat_completion', side_effect=rate_limit_api)

    result = analyze_data_with_glm5(...)

    assert result is not None
    assert len(call_times) == 2
    assert call_times[1] - call_times[0] >= 60  # 60-second delay
```

---

#### AC-010: Vision API Fallback
**Requirement**: REQ-013
**Priority**: Medium
**Status**: Pending

**Given** GLM-5 vision model is unavailable
**When** v3 attempts to call vision API
**Then** system falls back to text-only analysis
**And** degraded functionality warning is logged

**Test Scenario**:
```python
def test_vision_fallback(mocker):
    # Mock vision API failure
    def vision_failure(*args, **kwargs):
        if "image" in str(kwargs.get("messages")):
            raise requests.exceptions.HTTPError(response=Mock(status_code=503))
        return {"choices": [...]}

    mocker.patch('client.chat_completion', side_effect=vision_failure)

    result = analyze_data_with_glm5_with_vision(...)

    assert result is not None
    assert "vision unavailable" in log_output.lower()
```

---

### Non-Functional Requirements

#### AC-011: API Response Latency
**Requirement**: Performance requirement
**Priority**: High
**Status**: Pending

**Given** GLM-5 API is called
**When** response is received
**Then** P95 latency is < 8 seconds

**Validation**:
```python
def test_response_latency():
    latencies = []
    for _ in range(100):  # 100 test calls
        start = time.time()
        client.chat_completion(...)
        latencies.append(time.time() - start)

    p95 = np.percentile(latencies, 95)
    assert p95 < 8.0, f"P95 latency {p95}s exceeds 8s threshold"
```

---

#### AC-012: API Call Success Rate
**Requirement**: Success metric
**Priority**: Critical
**Status**: Pending

**Given** system makes GLM-5 API calls over 24-hour period
**When** success rate is calculated
**Then** success rate is > 99%

**Validation**:
```python
def test_success_rate():
    total_calls = 100
    successful_calls = 0

    for _ in range(total_calls):
        try:
            result = client.chat_completion(...)
            if result:
                successful_calls += 1
        except Exception as e:
            logger.error(f"API call failed: {e}")

    success_rate = successful_calls / total_calls
    assert success_rate > 0.99, f"Success rate {success_rate} below 99%"
```

---

#### AC-013: Cost Reduction
**Requirement**: Business metric
**Priority**: Medium
**Status**: Pending

**Given** system uses GLM-5 instead of OpenAI
**When** monthly cost is calculated
**Then** cost per decision is < 50% of OpenAI cost

**Validation**:
- Track token usage per call
- Calculate cost using GLM-5 pricing
- Compare with historical OpenAI costs
- Verify at least 50% reduction

---

#### AC-014: Decision Quality Parity
**Requirement**: Business metric
**Priority**: High
**Status**: Pending

**Given** GLM-5 makes trading decisions
**When** decisions are backtested on historical data
**Then** decision quality maintains or improves vs GPT-4 baseline

**Validation**:
- Run backtesting on 30-day historical data
- Compare GLM-5 decisions with GPT-4 decisions
- Measure profitability, risk metrics
- Verify no significant degradation (tolerance: 5%)

---

### Security Requirements

#### AC-015: No API Key in Source Code
**Requirement**: REQ-015
**Priority**: Critical
**Status**: Pending

**Given** source code is checked into version control
**When** codebase is scanned for secrets
**Then** no API keys are found in source files

**Validation**:
```bash
# Scan for API key patterns
git log --all --full-history -- '*.py' | grep -i "api_key.*=.*['\"]" || echo "No hardcoded keys found"

# Verify .env is in .gitignore
grep -q "^\.env$" .gitignore && echo ".env ignored" || echo "WARNING: .env not ignored"
```

---

#### AC-016: No API Keys in Logs
**Requirement**: REQ-016
**Priority**: High
**Status**: Pending

**Given** system logs API calls
**When** log files are reviewed
**Then** no API keys appear in log output

**Validation**:
```python
def test_no_keys_in_logs():
    # Make API call
    client.chat_completion(...)

    # Check log file
    with open("autotrade.log", "r") as f:
        log_content = f.read()

    assert "GLM_API_KEY" not in log_content
    assert os.getenv("GLM_API_KEY") not in log_content
```

---

#### AC-017: No Trade Execution on Parse Failure
**Requirement**: REQ-017
**Priority**: Critical
**Status**: Pending

**Given** API returns response that cannot be parsed as JSON
**When** JSON parsing fails
**Then** trade execution is aborted

**Test Scenario**:
```python
def test_no_trade_on_parse_failure(mocker):
    # Mock invalid JSON response
    mocker.patch('client.chat_completion', return_value="invalid json {")

    with pytest.raises(json.JSONDecodeError):
        make_decision_and_execute()

    # Verify no trade executed
    assert not trade_executed
```

---

## Test Scenarios

### Scenario 1: Happy Path - Successful v1 Execution

**Given** GLM_API_KEY is configured
**And** autotrade.py is running
**When** scheduled execution triggers
**Then** system successfully:
1. Fetches technical data (OHLCV, indicators)
2. Calls GLM-5 API with data
3. Receives valid JSON decision
4. Parses decision correctly
5. Logs decision to console

**Expected Output**:
```
Making decision and executing...
Calling GLM-5 API with model: glm-5
GLM-5 API call succeeded in 3.2s
Tokens used: 1,234
Decision: {"decision": "buy", "percentage": 50, "reason": "RSI oversold, MACD bullish crossover"}
```

---

### Scenario 2: Happy Path - Successful v3 Execution with Vision

**Given** GLM_API_KEY is configured
**And** autotrade_v3.py is running
**And** ChromeDriver is available
**When** scheduled execution triggers
**Then** system successfully:
1. Fetches all data sources (news, technical, history, fear/greed)
2. Captures chart screenshot
3. Encodes screenshot as base64
4. Calls GLM-5 vision API with all inputs
5. Receives valid JSON decision with chart analysis
6. Saves decision to SQLite database

**Expected Output**:
```
Making decision and executing...
Fetching news data...
Fetching technical data...
Fetching last decisions...
Fetching Fear & Greed index...
Capturing chart screenshot...
Screenshot saved to screenshot.png
Base64 encoding complete (45,678 characters)
Calling GLM-5 Vision API with model: glm-5-vision
GLM-5 API call succeeded in 5.1s
Tokens used: 2,345
Decision: {"decision": "hold", "percentage": 0, "reason": "Chart shows consolidation pattern, RSI neutral, awaiting breakout confirmation"}
Decision saved to database
```

---

### Scenario 3: Error Recovery - Network Timeout

**Given** GLM-5 API is slow to respond
**And** timeout is set to 10 seconds
**When** API call exceeds timeout
**Then** system:
1. Logs timeout error
2. Retries API call after 5-second delay
3. Succeeds on retry
4. Continues execution normally

**Expected Output**:
```
Calling GLM-5 API with model: glm-5
ERROR: GLM-5 API timeout after 10 seconds
Retrying in 5 seconds... (attempt 1/5)
Calling GLM-5 API with model: glm-5
GLM-5 API call succeeded in 2.1s
```

---

### Scenario 4: Error Recovery - Rate Limit

**Given** GLM-5 API rate limit is exceeded
**When** system receives HTTP 429 response
**Then** system:
1. Logs rate limit error
2. Pauses execution for 60 seconds
3. Retries API call
4. Succeeds after cooldown

**Expected Output**:
```
Calling GLM-5 API with model: glm-5
ERROR: Rate limit exceeded (HTTP 429)
Waiting 60 seconds before retry...
Calling GLM-5 API with model: glm-5
GLM-5 API call succeeded in 1.8s
```

---

### Scenario 5: Degraded Mode - Vision Unavailable

**Given** GLM-5 vision model is unavailable
**When** v3 attempts to call vision API
**Then** system:
1. Logs vision unavailable warning
2. Falls back to text-only analysis
3. Executes trade decision with reduced confidence
4. Logs degraded mode operation

**Expected Output**:
```
Capturing chart screenshot...
Screenshot saved to screenshot.png
Calling GLM-5 Vision API with model: glm-5-vision
ERROR: Vision model unavailable (HTTP 503)
WARNING: Falling back to text-only analysis
Decision quality may be degraded
Calling GLM-5 API with model: glm-5 (text-only)
GLM-5 API call succeeded in 2.5s
Decision: {"decision": "hold", "percentage": 0, "reason": "Text-only analysis: RSI neutral, insufficient signals for trade"}
```

---

### Scenario 6: Rollback - Critical Failure

**Given** GLM-5 migration encounters critical failure
**And** success rate drops below 95%
**When** rollback is triggered
**Then** system:
1. Sets AI_PROVIDER=openai in .env
2. Restarts autotrade processes
3. Resumes OpenAI API calls
4. Logs rollback event

**Expected Output**:
```
CRITICAL: GLM-5 success rate 92% below 95% threshold
Initiating rollback to OpenAI...
Updating .env: AI_PROVIDER=openai
Restarting autotrade_v1...
Restarting autotrade_v2...
Restarting autotrade_v3...
Rollback complete. OpenAI API active.
```

---

## Validation Procedures

### Pre-Migration Validation

**Checklist**:
- [ ] GLM-5 API key obtained and tested
- [ ] API documentation reviewed
- [ ] Environment variables configured
- [ ] Backup of current codebase (git tag)
- [ ] Rollback plan documented

---

### During Migration Validation

**Hourly Checks**:
- [ ] API call success rate > 99%
- [ ] Response latency P95 < 8 seconds
- [ ] No authentication errors
- [ ] No rate limit errors
- [ ] Decision quality acceptable

**Daily Reports**:
- Total API calls
- Success rate
- Average latency
- Token usage
- Cost comparison

---

### Post-Migration Validation

**24-Hour Validation**:
- [ ] All scheduled executions completed successfully
- [ ] No trading execution failures
- [ ] SQLite database entries correct
- [ ] Log files contain no errors
- [ ] Cost reduction achieved

**1-Week Validation**:
- [ ] Decision quality parity confirmed via backtesting
- [ ] No critical errors in production
- [ ] Performance metrics meet targets
- [ ] OpenAI fallback removed (optional)
- [ ] Documentation updated

---

## Quality Gates

### Code Quality

- [ ] All code passes ruff linting (0 errors)
- [ ] All code passes mypy type checking (0 errors)
- [ ] Test coverage > 85%
- [ ] No security vulnerabilities (OWASP compliance)

### Functional Quality

- [ ] All acceptance criteria passed
- [ ] All test scenarios passed
- [ ] No regression in trading logic
- [ ] Vision analysis quality matches baseline

### Operational Quality

- [ ] Logging comprehensive and useful
- [ ] Error messages clear and actionable
- [ ] Monitoring alerts configured
- [ ] Runbook documented

---

## Sign-Off

### Development Sign-Off

**Developer**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] All code changes implemented
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated

---

### QA Sign-Off

**QA Engineer**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] All acceptance criteria validated
- [ ] All test scenarios executed
- [ ] No critical defects remaining
- [ ] Regression testing passed

---

### Product Owner Sign-Off

**Product Owner**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] Business requirements met
- [ ] Cost reduction validated
- [ ] Decision quality acceptable
- [ ] Ready for production deployment

---

## Appendices

### Appendix A: Test Data

**Sample API Request**:
```json
{
  "model": "glm-5",
  "messages": [
    {"role": "system", "content": "You are a cryptocurrency trading advisor..."},
    {"role": "user", "content": "News: Bitcoin ETF approved..."},
    {"role": "user", "content": "Technical: RSI=45, MACD=bullish..."},
    {"role": "user", "content": "Last decisions: buy 50% at $50,000..."}
  ],
  "response_format": {"type": "json_object"}
}
```

**Sample API Response**:
```json
{
  "decision": "buy",
  "percentage": 30,
  "reason": "Positive news sentiment, RSI neutral with bullish MACD crossover, previous buy decision suggests accumulation strategy"
}
```

---

### Appendix B: Monitoring Dashboard

**Key Metrics**:
- API Call Count (hourly, daily)
- Success Rate (%)
- Average Latency (seconds)
- P95 Latency (seconds)
- Token Usage (total, per call)
- Cost (daily, monthly)
- Decision Distribution (buy/sell/hold)

**Alert Thresholds**:
- Success Rate < 95%: Warning
- Success Rate < 90%: Critical
- Latency P95 > 10s: Warning
- Latency P95 > 15s: Critical
- Cost > 150% of baseline: Warning

---

### Appendix C: Rollback Procedure

**Step-by-Step**:

1. **Identify Issue**: Monitor alerts or manual observation
2. **Assess Severity**: Critical (immediate rollback) or Warning (investigate first)
3. **Execute Rollback**:
   ```bash
   # Update .env
   echo "AI_PROVIDER=openai" >> .env

   # Restart processes
   pkill -f autotrade
   python autotrade_v1.py &
   python autotrade_v2.py &
   python autotrade_v3.py &
   ```
4. **Verify Rollback**: Check logs for OpenAI API calls
5. **Document Incident**: Record root cause, timeline, resolution
6. **Schedule Fix**: Plan re-migration with corrections

---

**Last Updated**: 2026-03-02
**Review Schedule**: After each test phase completion
