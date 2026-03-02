# SPEC-UPDATE-AI-001: GLM-5 Migration

**SPEC ID**: SPEC-UPDATE-AI-001
**Title**: GLM-5 AI Model Migration for Auto-Trading System
**Created**: 2026-03-02
**Updated**: 2026-03-02 (Added dual provider strategy)
**Status**: Planned
**Priority**: High
**Assigned**: expert-backend

---

## Problem Analysis

### Current State

The gpt-bitcoin auto-trading system currently uses OpenAI GPT models across three versions:

- **autotrade.py (v1)**: Uses `gpt-4-turbo-preview` (lines 13, 102)
- **autotrade_v2.py (v2)**: Uses `gpt-4-turbo-preview` (lines 16, 231)
- **autotrade_v3.py (v3)**: Uses `gpt-4o` with vision capabilities (lines 22, 292)

### Root Cause Analysis (Five Whys)

**Surface Problem**: System depends on OpenAI API with associated costs and availability constraints.

**First Why**: Why use OpenAI? → Initial development chose GPT-4 for advanced reasoning capabilities.

**Second Why**: Why change now? → GLM-5 offers comparable performance with better cost efficiency and regional availability.

**Third Why**: Why GLM-5 specifically? → Supports Korean language natively, competitive pricing, and offers vision capabilities matching v3 requirements.

**Fourth Why**: Why migrate all versions? → Ensures consistency across the codebase and simplifies maintenance.

**Root Cause**: Strategic decision to optimize operational costs while maintaining decision quality through regional AI service adoption.

### Assumptions

| Assumption | Confidence | Evidence | Risk if Wrong | Validation |
|------------|------------|----------|---------------|------------|
| GLM-5 API is compatible with OpenAI SDK | Medium | Both follow similar chat completion patterns | Need custom client implementation | API documentation review |
| GLM-5 supports JSON response format | High | Common feature in modern LLMs | Response parsing changes required | Test API call with response_format |
| GLM-5 vision matches GPT-4o quality | Medium | Claimed in documentation | v3 chart analysis quality may degrade | A/B testing required |
| Token limits are sufficient | High | GLM-5 has 128K context window | None expected | Monitor token usage |
| API rate limits accommodate schedule | High | 3 calls per day schedule | May need retry logic | Test during peak hours |

---

## Environment

### Technology Stack (Current)

- **Language**: Python 3.x
- **AI Client**: `openai` package
- **API Provider**: OpenAI
- **Models**: gpt-4-turbo-preview, gpt-4o
- **Environment Variables**: OPENAI_API_KEY

### Technology Stack (Target)

- **Language**: Python 3.x (unchanged)
- **AI Client**: OpenAI-compatible client with provider abstraction
- **API Provider**: Dual provider mode
  - Primary: Zhipu AI (GLM-5)
  - Fallback: OpenAI (GPT-4o)
- **Models**: glm-5 (text), glm-5-vision (for v3)
- **Environment Variables**:
  - GLM_API_KEY (primary)
  - GLM_API_BASE (endpoint configuration)
  - OPENAI_API_KEY (fallback, retained)

### Infrastructure

- **Runtime**: Local execution with schedule-based triggers
- **Data Storage**: SQLite (trading_decisions.sqlite)
- **External APIs**: Upbit exchange, SERPAPI, Fear & Greed Index
- **Dependencies**: requirements.txt

---

## Dual Provider Architecture

### Overview

The system implements a dual provider strategy to ensure high availability and seamless migration:

```
┌─────────────────────────────────────────────────────────┐
│                   AI Client Factory                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Primary: GLM-5 (Zhipu AI)                     │    │
│  │  - GLM_API_KEY                                 │    │
│  │  - GLM_API_BASE                                │    │
│  │  - Cost efficient                              │    │
│  │  - Korean language optimized                   │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                              │
│                         ▼                              │
│                   [Try First]                          │
│                         │                              │
│                   [Fail?] ──────┐                       │
│                         │        │                     │
│                         │        ▼                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Fallback: OpenAI (GPT-4o)                     │    │
│  │  - OPENAI_API_KEY                              │    │
│  │  - Proven reliability                          │    │
│  │  - Vision capabilities                         │    │
│  │  - Backup assurance                            │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Benefits

1. **High Availability**: Automatic fallback prevents service disruption
2. **Zero Downtime Migration**: Gradual transition without stopping scheduled trades
3. **A/B Testing**: Compare GLM-5 vs OpenAI decision quality
4. **Cost Optimization**: Use GLM-5 primary (lower cost), OpenAI fallback only when needed
5. **Risk Mitigation**: Quick rollback if GLM-5 underperforms
6. **Provider Independence**: Easy to add more providers in the future

### Provider Selection Logic

```python
def get_ai_client():
    # Priority 1: GLM-5 (if configured)
    if GLM_API_KEY exists:
        try GLM-5 client
        return on success

    # Priority 2: OpenAI (fallback)
    if OPENAI_API_KEY exists:
        return OpenAI client

    # Error: No provider available
    raise ConfigurationError
```

### Monitoring Requirements

- Log provider selection for each API call
- Track fallback frequency (alert if > 10%)
- Compare response times between providers
- Monitor cost per decision by provider

---

## Assumptions

### Technical Assumptions

1. **API Compatibility**: GLM-5 provides OpenAI-compatible chat completion endpoint
2. **JSON Output**: GLM-5 supports structured JSON output via response_format parameter
3. **Vision Support**: GLM-5 vision model accepts base64-encoded images like GPT-4o
4. **Token Limits**: Current prompts fit within GLM-5 context window
5. **Rate Limits**: GLM-5 API accommodates 3 daily calls without throttling

### Business Assumptions

1. **Cost Reduction**: GLM-5 provides at least 50% cost reduction vs OpenAI
2. **Performance Parity**: Decision quality maintains or improves post-migration
3. **Availability**: GLM-5 API reliability meets 99% uptime requirement
4. **Compliance**: Data handling meets regional regulatory requirements

### Migration Assumptions

1. **Backward Compatibility**: Fallback to OpenAI possible if migration fails
2. **Testing Window**: 1-week testing period sufficient for validation
3. **Zero Downtime**: Migration can occur without stopping scheduled trades
4. **Rollback Plan**: Git version control enables instant rollback

---

## Requirements (EARS Format)

### Ubiquitous Requirements (System-Wide)

**REQ-001**: The system **shall** authenticate with GLM-5 API using GLM_API_KEY environment variable for all AI model invocations.

**REQ-002**: The system **shall** use JSON response format for structured decision output across all versions (v1, v2, v3).

**REQ-003**: The system **shall** maintain consistent decision schema with fields: decision, percentage, reason.

**REQ-004**: The system **shall** log all API calls with timestamp, model version, token usage, and response status.

### Event-Driven Requirements (Trigger-Response)

**REQ-005**: **WHEN** `make_decision_and_execute()` is triggered by schedule, **THEN** the system **shall** invoke GLM-5 chat completion API within 5 seconds.

**REQ-006**: **WHEN** API call fails with network error, **THEN** the system **shall** retry up to 5 times with 5-second exponential backoff.

**REQ-007**: **WHEN** API call returns non-200 status code, **THEN** the system **shall** log error details and proceed to retry logic.

**REQ-008**: **WHEN** v3 captures chart screenshot, **THEN** the system **shall** encode image as base64 and include in GLM-5 vision API request.

**REQ-009**: **WHEN** JSON parsing fails after successful API call, **THEN** the system **shall** retry API call with explicit JSON format instruction.

### State-Driven Requirements (Conditional)

**REQ-010**: **IF** environment variable GLM_API_KEY is set, **THEN** the system **shall** use GLM-5 as primary AI provider. **IF** GLM_API_KEY is not set or GLM-5 fails, **THEN** the system **shall** automatically fall back to OpenAI using OPENAI_API_KEY.

**REQ-010-A**: **WHEN** falling back from GLM-5 to OpenAI, **THEN** the system **shall** log the fallback event with timestamp and reason for transparency.

**REQ-011**: **IF** GLM-5 API response exceeds 10-second timeout, **THEN** the system **shall** cancel request and fall back to OpenAI for that invocation.

**REQ-012**: **IF** token usage exceeds 100,000 tokens per call, **THEN** the system **shall** log warning for cost monitoring.

**REQ-013**: **IF** vision model is unavailable for v3, **THEN** the system **shall** fall back to text-only analysis with degraded functionality warning.

**REQ-014**: **IF** API rate limit is reached, **THEN** the system **shall** pause execution and resume after 60-second cooldown.

### Unwanted Behavior Requirements (Prohibited Actions)

**REQ-015**: The system **shall not** store GLM_API_KEY in source code or version control.

**REQ-016**: The system **shall not** expose API keys in logs or error messages.

**REQ-017**: The system **shall not** proceed with trade execution if AI decision parsing fails.

**REQ-018**: The system **shall not** cache API responses for longer than current session to ensure fresh analysis.

**REQ-019**: The system **shall not** use deprecated GLM-4 models after migration completion.

### Optional Requirements (Enhancement Features)

**REQ-020**: **Where possible**, the system should support dual-provider mode (GLM-5 primary, OpenAI fallback) for reliability.

**REQ-021**: **Where possible**, the system should implement A/B testing framework to compare GLM-5 vs GPT-4 decision quality.

**REQ-022**: **Where possible**, the system should expose model selection via environment variable for runtime switching.

**REQ-023**: **Where possible**, the system should collect decision quality metrics for continuous evaluation.

---

## Specifications

### API Client Changes

#### Current Implementation (autotrade_v3.py lines 22, 291-303)

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type":"json_object"}
)
```

#### Target Implementation

```python
# Option A: Direct GLM-5 Client
from zhipuai import ZhipuAI

client = ZhipuAI(api_key=os.getenv("GLM_API_KEY"))

response = client.chat.completions.create(
    model="glm-5",  # or "glm-5-vision" for v3
    messages=[...],
    response_format={"type":"json_object"}
)

# Option B: OpenAI-Compatible Endpoint (if available)
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GLM_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

response = client.chat.completions.create(
    model="glm-5",
    messages=[...],
    response_format={"type":"json_object"}
)
```

### File Modification Matrix

| File | Lines | Current | Target | Changes Required |
|------|-------|---------|--------|------------------|
| autotrade.py | 8, 13, 102 | OpenAI client, gpt-4-turbo-preview | GLM-5 client, glm-5 | Import, client init, model name |
| autotrade_v2.py | 8, 16, 231 | OpenAI client, gpt-4-turbo-preview | GLM-5 client, glm-5 | Import, client init, model name |
| autotrade_v3.py | 8, 22, 292 | OpenAI client, gpt-4o | GLM-5 client, glm-5-vision | Import, client init, model name, vision API |
| requirements.txt | 2 | openai | zhipuai (or keep openai for compatible mode) | Dependency update |
| .env | N/A | OPENAI_API_KEY | GLM_API_KEY | Environment variable |
| instructions_v3.md | N/A | GPT-4o prompt format | GLM-5 prompt optimization | Prompt refinement (optional) |

### Environment Variable Configuration

```bash
# Current
OPENAI_API_KEY=sk-proj-xxxxx

# Target (additive)
GLM_API_KEY=your_glm_api_key_here

# Optional fallback
OPENAI_API_KEY=sk-proj-xxxxx  # Keep for fallback if dual-provider enabled
AI_PROVIDER=glm  # Options: glm, openai
```

### Model Selection Strategy

| Version | Current Model | Target Model | Reason |
|---------|--------------|--------------|--------|
| v1 | gpt-4-turbo-preview | glm-5 | Standard text analysis |
| v2 | gpt-4-turbo-preview | glm-5 | Standard text analysis |
| v3 | gpt-4o | glm-5-vision | Vision-enabled chart analysis |

### JSON Response Schema

```json
{
  "decision": "buy|sell|hold",
  "percentage": 0-100,
  "reason": "string explanation"
}
```

### Error Handling Strategy

| Error Type | Current Behavior | Target Behavior |
|------------|------------------|-----------------|
| Network timeout | Retry 5 times, 5s delay | Same, add timeout config |
| Authentication failure | Print error, return None | Raise exception with clear message |
| Rate limit exceeded | No handling | Pause 60s, retry with backoff |
| JSON parse failure | Retry 5 times | Same, add schema validation |
| Vision API failure | N/A | Fall back to text-only mode |

---

## Constraints

### Technical Constraints

1. **Python Version**: Must maintain compatibility with Python 3.8+
2. **Dependency Size**: Minimize new dependencies to reduce deployment complexity
3. **API Latency**: GLM-5 response time must be < 10 seconds for scheduled execution
4. **Memory Footprint**: No significant increase in memory usage
5. **Code Structure**: Maintain existing function signatures for backward compatibility

### Business Constraints

1. **Budget**: Migration cost < 2 hours development time
2. **Risk Tolerance**: Zero tolerance for trading execution failures
3. **Testing Period**: 1-week validation window before production deployment
4. **Rollback Time**: < 5 minutes to revert to OpenAI if critical issues arise

### Regulatory Constraints

1. **Data Privacy**: API calls must comply with regional data protection regulations
2. **Audit Trail**: All AI decisions must remain traceable in SQLite database
3. **Financial Compliance**: No changes to trade execution logic

---

## Success Metrics

### Technical Metrics

- **API Call Success Rate**: > 99% (matching current OpenAI performance)
- **Response Latency P95**: < 8 seconds
- **Error Recovery Time**: < 30 seconds (automatic retry)
- **Code Coverage**: > 85% for modified modules

### Business Metrics

- **Cost per Decision**: < 50% of OpenAI cost
- **Decision Quality**: Maintain or improve based on backtesting
- **System Availability**: 99.5% uptime during trading hours
- **Migration Duration**: Complete within 1 week

### Quality Metrics

- **Linter Errors**: 0 (ruff validation)
- **Type Errors**: 0 (mypy validation)
- **Security Vulnerabilities**: 0 (OWASP compliance)
- **Documentation Coverage**: 100% for modified functions

---

## Related SPECs

- None (initial migration)

---

## Traceability

| Requirement | Implementation | Test | Documentation |
|-------------|----------------|------|---------------|
| REQ-001 | client initialization | test_auth.py | API setup guide |
| REQ-005 | analyze_data_with_gpt4() | test_api_call.py | Function docstring |
| REQ-006 | retry logic | test_retry.py | Error handling guide |
| REQ-008 | get_current_base64_image() | test_vision.py | Vision API docs |
| REQ-015 | .env configuration | test_security.py | Security guidelines |

---

## Lifecycle Level

**Level 2: spec-anchored**

This SPEC will be maintained alongside implementation for ongoing evolution. Quarterly review scheduled to assess GLM-5 performance and potential updates.

---

**Last Updated**: 2026-03-02
**Next Review**: 2026-04-02
