# Implementation Plan: SPEC-UPDATE-AI-001

**SPEC ID**: SPEC-UPDATE-AI-001
**Title**: GLM-5 AI Model Migration
**Created**: 2026-03-02
**Updated**: 2026-03-02 (Added dual provider strategy)
**Status**: Planned

---

## Implementation Strategy

### Approach: Phased Migration with Fallback

Migration will occur in three phases to minimize risk and enable rapid rollback:

1. **Phase 1: Infrastructure Setup** - Prepare GLM-5 client without removing OpenAI
2. **Phase 2: Gradual Migration** - Migrate versions sequentially (v1 → v2 → v3)
3. **Phase 3: Validation & Cleanup** - Comprehensive testing and OpenAI removal

This approach allows instant fallback to OpenAI if any phase encounters critical issues.

---

## Task Breakdown

### Primary Goal: Core Migration

#### Task 1: GLM-5 Client Implementation
**Priority**: High | **Complexity**: Medium | **Files**: New file `glm_client.py`

**Objective**: Create GLM-5 API client with OpenAI-compatible interface

**Subtasks**:
1. Research GLM-5 API documentation (endpoint, authentication, request format)
2. Install zhipuai package or configure OpenAI-compatible endpoint
3. Create `glm_client.py` with `GLMClient` class
4. Implement authentication using GLM_API_KEY environment variable
5. Add timeout configuration (10-second default)
6. Implement retry logic with exponential backoff (max 5 retries)
7. Add comprehensive error handling for network, auth, and rate limit errors
8. Create factory function `get_ai_client()` for provider selection

**Code Pattern (Dual Provider Mode)**:
```python
# ai_client_factory.py
import os
from typing import Optional
from openai import OpenAI

def get_ai_client():
    """
    AI client factory with dual provider support.

    Priority:
    1. GLM-5 (primary) - if GLM_API_KEY is set
    2. OpenAI (fallback) - if GLM-5 fails or not configured

    Returns:
        OpenAI: Configured client instance
    """
    # Try GLM-5 first (primary provider)
    glm_key = os.getenv("GLM_API_KEY")
    if glm_key:
        try:
            return OpenAI(
                api_key=glm_key,
                base_url=os.getenv("GLM_API_BASE", "https://open.bigmodel.cn/api/paas/v4/"),
                timeout=30
            )
        except Exception as e:
            print(f"GLM-5 client initialization failed: {e}")
            print("Falling back to OpenAI...")

    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("Either GLM_API_KEY or OPENAI_API_KEY must be set")

    return OpenAI(api_key=openai_key)

# Usage in autotrade files
client = get_ai_client()
```

**Validation**:
- Unit test for client initialization
- Mock API call test
- Error handling test for auth failure

---

#### Task 2: Environment Configuration
**Priority**: High | **Complexity**: Low | **Files**: `.env.example`, `.gitignore`

**Objective**: Configure environment variables for GLM-5 API

**Subtasks**:
1. Add `GLM_API_KEY=your_key_here` to `.env.example`
2. Add `AI_PROVIDER=glm` to `.env.example`
3. Document environment variable setup in README.md
4. Verify `.gitignore` includes `.env` entry
5. Create setup guide for obtaining GLM-5 API key

**Configuration File**:
```bash
# .env.example

# AI Provider Configuration (Dual Provider Mode)
# Primary: GLM-5 (Zhipu AI)
GLM_API_KEY=your_glm_api_key_here
GLM_API_BASE=https://open.bigmodel.cn/api/paas/v4/

# Fallback: OpenAI (retained for backup)
OPENAI_API_KEY=sk-proj-xxxxx

# Exchange API Keys
UPBIT_ACCESS_KEY=your_upbit_access_key
UPBIT_SECRET_KEY=your_upbit_secret_key

# External Data Sources
SERPAPI_API_KEY=your_serpapi_key
```

**Provider Selection Logic**:
1. System attempts GLM-5 first if `GLM_API_KEY` is set
2. Automatic fallback to OpenAI if GLM-5 fails
3. Environment variable `AI_PROVIDER` can force specific provider (optional)
4. Both providers support identical interface for seamless switching

**Validation**:
- Manual test: Load environment variables with python-dotenv
- Security audit: Verify .env is not in git tracking

---

#### Task 3: Migrate autotrade.py (v1)
**Priority**: High | **Complexity**: Low | **Files**: `autotrade.py`

**Objective**: Update v1 to use GLM-5 client

**Changes**:
1. **Line 8**: Update import statement
   ```python
   # Before
   from openai import OpenAI

   # After
   from glm_client import get_ai_client
   ```

2. **Line 13**: Replace client initialization
   ```python
   # Before
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

   # After
   client = get_ai_client()  # Factory function selects provider
   ```

3. **Line 102**: Update model parameter
   ```python
   # Before
   model="gpt-4-turbo-preview",

   # After
   model="glm-5",
   ```

**Testing**:
- Run `python autotrade.py` in test mode
- Verify API call succeeds
- Verify JSON response parsing works
- Compare decision output with previous GPT-4 results

---

#### Task 4: Migrate autotrade_v2.py (v2)
**Priority**: High | **Complexity**: Low | **Files**: `autotrade_v2.py`

**Objective**: Update v2 to use GLM-5 client

**Changes**:
1. **Line 8**: Update import statement (same as v1)
2. **Line 16**: Replace client initialization (same as v1)
3. **Line 231**: Update model parameter to `"glm-5"`

**Testing**:
- Same validation as v1
- Additional test: Verify SQLite database logging still works
- Verify news data integration with GLM-5

---

#### Task 5: Migrate autotrade_v3.py (v3) with Vision
**Priority**: High | **Complexity**: Medium | **Files**: `autotrade_v3.py`

**Objective**: Update v3 to use GLM-5 vision model

**Changes**:
1. **Line 8**: Update import statement
2. **Line 22**: Replace client initialization
3. **Line 292**: Update model parameter
   ```python
   # Before
   model="gpt-4o",

   # After
   model="glm-5-vision",  # or "glm-5" if vision not available
   ```

4. **Vision API Compatibility Check**:
   - Verify GLM-5 vision accepts base64-encoded images
   - Test image message format compatibility
   - If incompatible, implement adapter in `glm_client.py`

**Vision Message Format** (may need adaptation):
```python
# Current GPT-4o format
{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}

# GLM-5 vision format (verify documentation)
# May differ - implement adapter if needed
```

**Testing**:
- Test chart screenshot capture still works
- Verify base64 encoding produces valid image
- Validate GLM-5 vision API accepts image input
- Compare chart analysis quality with GPT-4o results

---

#### Task 6: Update Dependencies
**Priority**: Medium | **Complexity**: Low | **Files**: `requirements.txt`

**Objective**: Update package dependencies

**Changes**:
```txt
# Current
python-dotenv
openai
pyupbit
pyjwt
pandas
pandas_ta
schedule
streamlit
selenium

# After (Option A: zhipuai package)
python-dotenv
zhipuai
openai  # Keep for fallback or compatible mode
pyupbit
pyjwt
pandas
pandas_ta
schedule
streamlit
selenium

# After (Option B: OpenAI-compatible mode)
# No changes if using OpenAI SDK with custom base_url
```

**Decision Criteria**:
- If GLM-5 provides official Python SDK → Use zhipuai package
- If GLM-5 offers OpenAI-compatible endpoint → Keep openai package with base_url override

**Validation**:
- Run `pip install -r requirements.txt`
- Verify all imports work
- Check for dependency conflicts

---

### Secondary Goal: Reliability Enhancements

#### Task 7: Dual-Provider Support
**Priority**: Medium | **Complexity**: Medium | **Files**: `glm_client.py`

**Objective**: Implement fallback to OpenAI if GLM-5 fails

**Implementation**:
```python
# glm_client.py
def get_ai_client(provider: str = None):
    provider = provider or os.getenv("AI_PROVIDER", "glm")

    if provider == "glm":
        try:
            return GLMClient()
        except Exception as e:
            print(f"GLM-5 initialization failed: {e}")
            if os.getenv("OPENAI_API_KEY"):
                print("Falling back to OpenAI")
                return OpenAIClient()
            raise
    else:
        return OpenAIClient()
```

**Benefits**:
- Zero-downtime migration
- Automatic failover on GLM-5 outage
- Gradual rollout capability

**Validation**:
- Test GLM-5 failure triggers OpenAI fallback
- Verify fallback logs warning message
- Ensure decision quality remains acceptable

---

#### Task 8: Error Handling Improvements
**Priority**: Medium | **Complexity**: Low | **Files**: All autotrade versions

**Objective**: Enhance error handling for GLM-5 specific errors

**Changes**:
1. Add specific exception handling for GLM-5 error codes
2. Implement rate limit detection (HTTP 429)
3. Add timeout handling with clear error messages
4. Improve retry logic with exponential backoff

**Error Handling Pattern**:
```python
try:
    advice = analyze_data_with_glm5(...)
except requests.exceptions.Timeout:
    print("GLM-5 API timeout after 10 seconds")
    # Retry logic
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        print("Rate limit exceeded, waiting 60 seconds")
        time.sleep(60)
        # Retry
    elif e.response.status_code == 401:
        raise ValueError("GLM_API_KEY is invalid")
except json.JSONDecodeError as e:
    print(f"JSON parsing failed: {e}")
    # Retry with explicit JSON instruction
```

**Validation**:
- Test timeout scenario (mock slow response)
- Test rate limit handling
- Test authentication failure

---

#### Task 9: Logging and Monitoring
**Priority**: Medium | **Complexity**: Low | **Files**: All autotrade versions

**Objective**: Add comprehensive logging for API calls

**Implementation**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='autotrade.log'
)

logger = logging.getLogger(__name__)

def analyze_data_with_glm5(...):
    logger.info(f"Calling GLM-5 API with model: {model}")
    start_time = time.time()

    try:
        response = client.chat.completions.create(...)
        elapsed = time.time() - start_time
        logger.info(f"GLM-5 API call succeeded in {elapsed:.2f}s")
        logger.info(f"Tokens used: {response.usage.total_tokens}")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"GLM-5 API call failed: {e}")
        raise
```

**Log Format**:
- Timestamp
- API provider (GLM-5)
- Model version
- Token usage
- Response time
- Error details (if failed)

**Validation**:
- Verify log file creation
- Check log entries for API calls
- Test log rotation for long-running sessions

---

### Optional Goal: Quality Assurance

#### Task 10: A/B Testing Framework
**Priority**: Low | **Complexity**: High | **Files**: New file `ab_testing.py`

**Objective**: Compare GLM-5 vs GPT-4 decision quality

**Implementation**:
- Run both models in parallel for testing period
- Store decisions from both models in separate database columns
- Implement statistical comparison of decision quality
- Generate comparison report

**Validation Criteria**:
- Decision consistency (do models agree?)
- Backtesting performance (which model generates more profitable decisions?)
- Response time comparison

**Note**: This task is optional and can be deferred to post-migration phase.

---

#### Task 11: Prompt Optimization for GLM-5
**Priority**: Low | **Complexity**: Medium | **Files**: `instructions.md`, `instructions_v2.md`, `instructions_v3.md`

**Objective**: Refine system prompts for GLM-5 characteristics

**Considerations**:
- GLM-5 may respond differently to prompt structure
- Korean language support may enable native Korean prompts
- Vision model may need different image analysis instructions

**Approach**:
1. Test current prompts with GLM-5
2. Compare output quality with GPT-4 results
3. Refine prompts if quality degradation detected
4. Document prompt version in SPEC

**Validation**:
- Manual review of decision quality
- Backtesting comparison
- User acceptance testing

**Note**: Only execute if initial GLM-5 results show quality degradation.

---

## Risk Assessment

### High-Risk Areas

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GLM-5 API incompatible with OpenAI SDK | Medium | High | Research API docs before implementation; prepare custom client |
| Vision model quality degradation | Medium | High | A/B testing; keep OpenAI fallback for v3 |
| Rate limiting during testing | Low | Medium | Test during off-peak hours; implement backoff |
| Authentication failure in production | Low | Critical | Thorough testing; environment variable validation |
| Unexpected cost increase | Low | Medium | Monitor token usage; set budget alerts |

### Rollback Plan

**Trigger Conditions**:
- API call success rate < 95% over 24-hour period
- Decision quality degradation detected via backtesting
- Critical production error affecting trade execution

**Rollback Procedure**:
1. Set `AI_PROVIDER=openai` in `.env`
2. Restart autotrade processes
3. Verify OpenAI API calls resume successfully
4. Review error logs for root cause
5. Schedule fix and re-migration

**Rollback Time**: < 5 minutes (environment variable change + process restart)

---

## Dependencies

### External Dependencies

1. **GLM-5 API Documentation**: Required before Task 1
2. **GLM-5 API Key**: Required before Task 2
3. **Testing Environment**: Required before Task 3

### Internal Dependencies

- Task 1 (GLM Client) → Task 3, 4, 5 (Migrations)
- Task 2 (Environment Config) → All migration tasks
- Task 3 (v1) → Task 4 (v2) → Task 5 (v3) (Sequential migration)

---

## Testing Strategy

### Unit Testing

**Coverage Target**: > 85%

**Test Files**:
- `test_glm_client.py`: Client initialization, API calls, error handling
- `test_autotrade_v1.py`: v1 migration validation
- `test_autotrade_v2.py`: v2 migration validation
- `test_autotrade_v3.py`: v3 migration with vision

**Test Cases**:
1. Successful API call with valid response
2. Authentication failure handling
3. Network timeout handling
4. Rate limit handling
5. JSON parsing success and failure
6. Vision API with base64 image
7. Fallback to OpenAI (if dual-provider enabled)

### Integration Testing

**Scenarios**:
1. End-to-end decision flow: Data fetch → API call → Decision → Database storage
2. Scheduled execution: Verify cron job triggers API call
3. Error recovery: Simulate API failure, verify retry and recovery
4. Vision flow: Screenshot capture → Base64 encoding → API call → Decision

### Regression Testing

**Validation**:
- Compare GLM-5 decisions with historical GPT-4 decisions
- Backtest GLM-5 decisions on historical data
- Verify no changes to trade execution logic

### Performance Testing

**Metrics**:
- API response time: < 10 seconds (P95)
- Memory usage: No significant increase
- CPU usage: No significant increase

---

## Timeline

### Week 1: Infrastructure & Core Migration

**Days 1-2**: Task 1 (GLM Client), Task 2 (Environment Config)
**Days 3-4**: Task 3 (v1 Migration), Task 4 (v2 Migration)
**Days 5-7**: Task 5 (v3 Migration), Task 6 (Dependencies)

### Week 2: Testing & Validation

**Days 1-3**: Unit testing, integration testing
**Days 4-5**: Regression testing, performance testing
**Days 6-7**: Production deployment, monitoring setup

### Optional: Week 3: Enhancements

**Days 1-3**: Task 7 (Dual-Provider), Task 8 (Error Handling)
**Days 4-5**: Task 9 (Logging)
**Days 6-7**: Task 10 (A/B Testing), Task 11 (Prompt Optimization)

---

## Resource Requirements

### Development Resources

- **Developer**: 1 backend engineer (Python expertise)
- **Time**: 40 hours (Week 1-2 full-time, Week 3 optional)

### Infrastructure Resources

- **GLM-5 API Key**: Obtain from Zhipu AI
- **Testing Environment**: Local machine with Python 3.8+
- **Production Environment**: Existing server (no changes required)

### Budget

- **GLM-5 API Costs**: ~50% of current OpenAI costs (estimated)
- **Development Time**: 40 hours × hourly rate
- **Testing Time**: 20 hours × hourly rate

---

## Acceptance Criteria

### Must-Have Criteria

- [ ] All three versions (v1, v2, v3) successfully call GLM-5 API
- [ ] JSON decision output format works correctly
- [ ] Vision analysis works in v3 (or graceful degradation)
- [ ] Error handling covers all defined scenarios
- [ ] Rollback procedure tested and validated
- [ ] Zero trading execution failures during migration

### Should-Have Criteria

- [ ] Dual-provider fallback implemented and tested
- [ ] Comprehensive logging for all API calls
- [ ] Token usage monitoring in place
- [ ] Performance matches or exceeds OpenAI baseline

### Nice-to-Have Criteria

- [ ] A/B testing framework operational
- [ ] Prompt optimization for GLM-5 completed
- [ ] Decision quality metrics dashboard

---

## Next Steps

1. **Immediate**: Obtain GLM-5 API key and documentation
2. **Day 1**: Begin Task 1 (GLM Client Implementation)
3. **Day 2**: Complete Task 2 (Environment Configuration)
4. **Day 3**: Start migration with v1 (lowest risk)

---

**Last Updated**: 2026-03-02
**Review Schedule**: Daily during migration week
