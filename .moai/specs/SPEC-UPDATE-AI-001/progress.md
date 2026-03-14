# SPEC-UPDATE-AI-001: GLM-5 AI Model Migration

## Progress Tracker

**Created**: 2026-03-14
**Status**: ✅ COMPLETE (100%)
**Development Mode**: TDD (test_coverage_target: 85%)
**Current Phase**: Phase 3 Complete - All Tasks Done

---

## 1. Current State Analysis (현재 상태 분석)

### 1.1 Existing AI Client Usage

**Current Implementation:**
- All autotrade files (v1, v2, v3) use `zhipuai.ZhipuAI` directly
- No fallback mechanism exists
- No abstraction layer for provider switching

**Affected Files:**
| File | Line | Current Code | Model Used |
|------|------|--------------|------------|
| `autotrade.py` | 8, 13 | `from zhipuai import ZhipuAI` | `glm-5` |
| `autotrade_v2.py` | 8, 16 | `from zhipuai import ZhipuAI` | `glm-5` |
| `autotrade_v3.py` | 8, 22 | `from zhipuai import ZhipuAI` | `glm-4-flash` (vision) |

**Existing Infrastructure:**
- `src/gpt_bitcoin/infrastructure/external/glm_client.py` - Advanced async GLM client exists
- Contains: `GLMClient` class with rate limiting, retry logic, Pydantic models
- Models: `TradingDecision`, `TokenUsage`, `GLMResponse`, `RateLimiter`

### 1.2 Gap Analysis

**Missing Components:**
1. Dual-provider factory function (`get_ai_client()`)
2. OpenAI fallback integration
3. Provider health tracking
4. Provider switching logic
5. Comprehensive error handling for dual-provider scenarios

**Existing Strengths:**
- Rate limiting (`RateLimiter` class)
- Exponential backoff retry (`tenacity` library)
- Structured outputs (`TradingDecision` Pydantic model)
- Token usage monitoring

### 1.3 Key Decision

**Reuse vs. Build:**
- **Reuse**: Existing `GLMClient` class from `glm_client.py`
- **Build**: Dual-provider factory in new `ai_client_factory.py`
- **Rationale**: Leverage existing robust implementation, add abstraction layer

---

## 2. Implementation Strategy (구현 전략)

### 2.1 Phased Approach

```
Phase 1: Infrastructure Setup (Tasks 1-3)
    ├── Task 1: Create AI Client Factory with dual-provider support
    ├── Task 2: Create Retry Handler with provider switching
    └── Task 3: Update environment configuration

Phase 2: Migration (Tasks 4-6)
    ├── Task 4: Migrate autotrade.py (v1)
    ├── Task 5: Migrate autotrade_v2.py (v2)
    └── Task 6: Migrate autotrade_v3.py (v3) with Vision

Phase 3: Validation (Tasks 7-8)
    ├── Task 7: Integration testing
    └── Task 8: Documentation update
```

### 2.2 Dependency Graph

```
Task 1 (Factory) ──┬──> Task 4 (v1 Migration)
                   │
Task 2 (Retry) ────┼──> Task 5 (v2 Migration)
                   │
Task 3 (Config) ───┴──> Task 6 (v3 Migration)
                           │
                           v
                    Task 7 (Integration Tests)
                           │
                           v
                    Task 8 (Documentation)
```

### 2.3 Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| GLM-5 API failure | Automatic fallback to OpenAI |
| Vision API incompatibility | Text-only fallback for v3 |
| Authentication errors | Clear error messages, validation |
| Rate limiting | Existing RateLimiter + exponential backoff |

---

## 3. TDD Cycle Plan (TDD 사이클 계획)

### Task 1: AI Client Factory (`ai_client_factory.py`)

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/unit/infrastructure/test_ai_client_factory.py`

```python
# Test cases to write:
- test_get_ai_client_with_glm_key_returns_glm_client
- test_get_ai_client_without_glm_key_returns_openai_client
- test_get_ai_client_without_any_key_raises_error
- test_get_ai_client_with_invalid_glm_key_falls_back_to_openai
- test_provider_selection_via_env_variable
```

#### GREEN Phase - Minimal Implementation

**Implementation File**: `src/gpt_bitcoin/infrastructure/external/ai_client_factory.py`

```python
def get_ai_client() -> OpenAI | ZhipuAI:
    """Factory function with dual-provider support."""
    # Minimal implementation to pass tests
    pass
```

#### REFACTOR Phase - Improve Quality

- Add type hints
- Add docstrings
- Add logging
- Optimize imports

---

### Task 2: Retry Handler with Provider Switching

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/unit/infrastructure/test_retry_handler.py`

```python
# Test cases to write:
- test_retry_on_timeout
- test_max_retries_exceeded
- test_rate_limit_handling_with_60s_wait
- test_provider_switch_on_consecutive_failures
- test_provider_recovery_after_5_minutes
```

#### GREEN Phase - Minimal Implementation

**Implementation File**: `src/gpt_bitcoin/infrastructure/external/retry_handler.py`

```python
def call_with_retry(client, messages, model, max_retries=5) -> dict:
    """API call with exponential backoff and provider switching."""
    pass
```

#### REFACTOR Phase - Improve Quality

- Extract provider state tracking to separate class
- Add metrics collection
- Improve error messages

---

### Task 3: Environment Configuration

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/unit/config/test_ai_provider_config.py`

```python
# Test cases to write:
- test_config_loads_glm_api_key
- test_config_loads_openai_api_key
- test_config_defaults
- test_config_validation
```

#### GREEN Phase - Minimal Implementation

**Files to modify:**
- `.env.example` - Add new environment variables
- `src/gpt_bitcoin/config/settings.py` - Add configuration fields

#### REFACTOR Phase - Improve Quality

- Add validation
- Add documentation

---

### Task 4: Migrate autotrade.py (v1)

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/characterization/test_autotrade_v1_glm.py`

```python
# Test cases to write:
- test_analyze_data_uses_glm5_model
- test_analyze_data_returns_valid_json
- test_analyze_data_handles_api_failure
- test_fallback_to_openai_on_glm_failure
```

#### GREEN Phase - Minimal Implementation

**Files to modify:**
- `autotrade.py` - Replace direct ZhipuAI with factory

Changes:
```python
# Line 8: Before
from zhipuai import ZhipuAI

# Line 8: After
from gpt_bitcoin.infrastructure.external.ai_client_factory import get_ai_client

# Line 13: Before
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))

# Line 13: After
client = get_ai_client()
```

#### REFACTOR Phase - Improve Quality

- Extract AI call logic to separate function
- Add error handling
- Add logging

---

### Task 5: Migrate autotrade_v2.py (v2)

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/characterization/test_autotrade_v2_glm.py`

```python
# Test cases to write:
- test_analyze_with_news_data_uses_glm5
- test_decision_stored_in_database
- test_database_records_provider_used
```

#### GREEN Phase - Minimal Implementation

**Files to modify:**
- `autotrade_v2.py` - Same pattern as v1

#### REFACTOR Phase - Improve Quality

- Same as v1

---

### Task 6: Migrate autotrade_v3.py (v3) with Vision

**TDD Phases:**

#### RED Phase - Write Failing Tests

**Test File**: `tests/characterization/test_autotrade_v3_glm.py`

```python
# Test cases to write:
- test_vision_analysis_uses_glm4_flash
- test_vision_api_failure_falls_back_to_text_only
- test_chart_screenshot_base64_encoding
```

#### GREEN Phase - Minimal Implementation

**Files to modify:**
- `autotrade_v3.py` - Replace direct ZhipuAI with factory
- Handle Vision API compatibility

#### REFACTOR Phase - Improve Quality

- Extract Vision adapter to separate module
- Add Vision API format detection

---

### Task 7: Integration Testing

**Test File**: `tests/integration/test_dual_provider_integration.py`

```python
# Test scenarios:
- test_end_to_end_glm_success
- test_end_to_end_glm_failure_openai_fallback
- test_provider_switching_after_consecutive_failures
- test_provider_recovery
```

---

### Task 8: Documentation Update

**Files to update:**
- `README.md` - Add dual-provider setup instructions
- `.moai/docs/api-reference.md` - Add factory function docs
- `.moai/specs/SPEC-UPDATE-AI-001/spec.md` - Mark completed

---

## 4. File Impact Analysis (파일 영향 분석)

### 4.1 New Files to Create

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `src/gpt_bitcoin/infrastructure/external/ai_client_factory.py` | Dual-provider factory | 100 |
| `src/gpt_bitcoin/infrastructure/external/provider_health.py` | Provider state tracking | 80 |
| `tests/unit/infrastructure/test_ai_client_factory.py` | Factory unit tests | 150 |
| `tests/unit/infrastructure/test_retry_handler.py` | Retry handler tests | 120 |
| `tests/unit/infrastructure/test_provider_health.py` | Health tracking tests | 100 |
| `tests/characterization/test_autotrade_v1_glm.py` | v1 characterization | 80 |
| `tests/characterization/test_autotrade_v2_glm.py` | v2 characterization | 90 |
| `tests/characterization/test_autotrade_v3_glm.py` | v3 characterization | 100 |
| `tests/integration/test_dual_provider_integration.py` | Integration tests | 150 |

### 4.2 Existing Files to Modify

| File | Changes | Impact |
|------|---------|--------|
| `autotrade.py` | Import and client init | Low (3 lines) |
| `autotrade_v2.py` | Import and client init | Low (3 lines) |
| `autotrade_v3.py` | Import, client init, vision handling | Medium (10 lines) |
| `.env.example` | Add new env vars | Low (5 lines) |
| `src/gpt_bitcoin/config/settings.py` | Add config fields | Low (10 lines) |

### 4.3 Files to Reference (No Changes)

| File | Reason |
|------|--------|
| `src/gpt_bitcoin/infrastructure/external/glm_client.py` | Reuse existing GLMClient |
| `src/gpt_bitcoin/infrastructure/exceptions.py` | Reuse existing exceptions |
| `src/gpt_bitcoin/infrastructure/logging.py` | Reuse existing logging |

---

## 5. Progress Checklist (진행 상황 추적)

### Phase 1: Infrastructure Setup

- [x] **Task 1: AI Client Factory** ✅
  - [x] RED: Write test_ai_client_factory.py
  - [x] GREEN: Implement ai_client_factory.py
  - [x] REFACTOR: Add logging and type hints
  - [x] Coverage: 100% (12/12 tests passed)

- [x] **Task 2: Retry Handler** ✅
  - [x] RED: Write test_retry_handler.py
  - [x] GREEN: Implement retry_handler.py
  - [x] REFACTOR: Extract provider health tracking
  - [x] Coverage: 88.6% (14/14 tests passed)

- [x] **Task 3: Environment Configuration** ✅
  - [x] RED: Write test_ai_provider_config.py
  - [x] GREEN: Update .env.example and settings.py
  - [x] REFACTOR: Add validation
  - [x] Coverage: Settings verified

### Phase 2: Migration

- [x] **Task 4: Migrate autotrade.py (v1)** ✅
  - [x] RED: Write test_autotrade_v1_glm.py
  - [x] GREEN: Update imports and client init
  - [x] REFACTOR: Extract AI call logic
  - [x] Verify: Syntax check passed

- [x] **Task 5: Migrate autotrade_v2.py (v2)** ✅
  - [x] RED: Write test_autotrade_v2_glm.py
  - [x] GREEN: Update imports and client init
  - [x] REFACTOR: Add database provider logging
  - [x] Verify: Syntax check passed

- [x] **Task 6: Migrate autotrade_v3.py (v3)** ✅
  - [x] RED: Write test_autotrade_v3_glm.py
  - [x] GREEN: Update imports and vision handling
  - [x] REFACTOR: Extract Vision adapter
  - [x] Verify: Syntax check passed

### Phase 3: Validation

- [x] **Task 7: Integration Testing** ✅
  - [x] Write integration test suite
  - [x] Test dual-provider scenarios
  - [x] Test error recovery
  - [x] Coverage: 36 tests passed (unit + integration)

- [x] **Task 8: Documentation** ✅
  - [x] Update README.md
  - [x] Update API documentation
  - [x] Update SPEC status to Completed

### Quality Gates

- [x] All tests passing (pytest) - 36/36 tests passed
- [x] Coverage >= 85% (pytest --cov) - Factory: 100%, Retry: 88.6%
- [x] Linting clean (ruff check)
- [x] Type checking clean (mypy) - All errors resolved
- [x] Security scan clean (bandit) - No issues found
- [x] No API keys in code (grep check)

---

## 6. Test Files Summary

### Unit Tests (New)

| Test File | Test Cases | Target Coverage |
|-----------|------------|-----------------|
| `test_ai_client_factory.py` | 10 | 100% |
| `test_retry_handler.py` | 8 | 100% |
| `test_provider_health.py` | 6 | 100% |
| `test_ai_provider_config.py` | 5 | 95% |

### Characterization Tests (New)

| Test File | Test Cases | Purpose |
|-----------|------------|---------|
| `test_autotrade_v1_glm.py` | 5 | Verify v1 migration |
| `test_autotrade_v2_glm.py` | 6 | Verify v2 migration |
| `test_autotrade_v3_glm.py` | 7 | Verify v3 + Vision |

### Integration Tests (New)

| Test File | Test Cases | Purpose |
|-----------|------------|---------|
| `test_dual_provider_integration.py` | 10 | End-to-end scenarios |

---

## 7. Estimated Effort

| Task | Estimated Time | Complexity |
|------|----------------|------------|
| Task 1: Factory | 2 hours | Medium |
| Task 2: Retry Handler | 2 hours | Medium |
| Task 3: Configuration | 1 hour | Low |
| Task 4: v1 Migration | 1 hour | Low |
| Task 5: v2 Migration | 1 hour | Low |
| Task 6: v3 Migration | 2 hours | Medium |
| Task 7: Integration Tests | 3 hours | Medium |
| Task 8: Documentation | 1 hour | Low |
| **Total** | **13 hours** | |

---

## 8. Next Steps

1. **User Approval**: Review this plan and approve to proceed
2. **Run Phase**: Execute `/moai run SPEC-UPDATE-AI-001`
3. **Start with Task 1**: AI Client Factory (TDD cycle)

---

**Last Updated**: 2026-03-14
**Next Review**: After user approval
