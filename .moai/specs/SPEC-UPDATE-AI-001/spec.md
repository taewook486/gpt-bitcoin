# SPEC: GLM-5 AI Model Migration

**SPEC ID**: SPEC-UPDATE-AI-001
**Title**: GLM-5 AI Model Migration
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Status**: Planned
**Priority**: High
**Lifecycle Level**: spec-anchored

---

## Environment

### System Context

이 시스템은 GPT-Bitcoin 자동매매 플랫폼의 AI 의사결정 엔진 마이그레이션을 다룹니다. 현재 시스템은 다음과 같은 환경에서 운영됩니다:

- **플랫폼**: Python 3.13+ 기반 자동매매 시스템
- **대상 파일**: autotrade.py, autotrade_v2.py, autotrade_v3.py
- **외부 API**: Upbit 거래소 API, GLM-5 (Zhipu AI), OpenAI API
- **데이터 저장**: SQLite (v2), 로그 파일
- **스케줄링**: schedule 라이브러리를 통한 정기 실행

### Current State

현재 시스템은 GLM-5 (ZhipuAI)를 사용 중이며, OpenAI API는 폴백 용도로 유지됩니다:

```python
from zhipuai import ZhipuAI
client = ZhipuAI(api_key=os.getenv("ZHIPUAI_API_KEY"))
```

### Target State

듀얼 프로바이더 아키텍처로 마이그레이션하여 안정성과 비용 효율성을 모두 확보:

1. **Primary Provider**: GLM-5 (Zhipu AI) - 60-70% 비용 절감
2. **Fallback Provider**: OpenAI API - 안정성 보장
3. **자동 장애 조치**: GLM-5 실패 시 OpenAI로 자동 전환

---

## Assumptions

### Technical Assumptions

1. **API 호환성**: GLM-5 API는 OpenAI SDK와 호환되는 엔드포인트를 제공함
   - Confidence: High
   - Evidence: GLM-5 공식 문서에서 OpenAI 호환 모드 지원 확인
   - Risk if wrong: 커스텀 어댑터 구현 필요 (2-3일 추가 개발)

2. **Vision API 지원**: GLM-5 Vision 모델이 base64 인코딩된 이미지를 처리 가능
   - Confidence: Medium
   - Evidence: GLM-4V 모델 문서 존재, v3 호환성 미확인
   - Risk if wrong: v3에서 Vision 기능 비활성화 또는 OpenAI 전용 처리 필요

3. **응답 품질**: GLM-5의 트레이딩 의사결정 품질이 GPT-4와 동등함
   - Confidence: Medium
   - Evidence: GLM-5 벤치마크 결과, 실제 트레이딩 도메인 테스트 필요
   - Risk if wrong: 프롬프트 최적화 또는 OpenAI 유지 필요

### Business Assumptions

1. **비용 절감**: GLM-5 사용 시 60-70% 비용 절감 달성
   - Confidence: High
   - Evidence: GLM-5 가격 정책 (GPT-4 대비 30-40% 가격)
   - Risk if wrong: 예상보다 낮은 절감 효과

2. **서비스 안정성**: Zhipu AI 서비스의 가용성이 99% 이상임
   - Confidence: Medium
   - Evidence: SLA 문서 미확인, 커뮤니티 피드백 필요
   - Risk if wrong: 빈번한 폴백으로 인한 OpenAI 의존도 증가

### Integration Assumptions

1. **타임아웃 호환성**: GLM-5 응답 시간이 10초 이내
   - Confidence: High
   - Evidence: GLM-5 공식 문서의 평균 응답 시간
   - Risk if wrong: 타임아웃 설정 조정 필요

2. **Rate Limit**: GLM-5의 Rate Limit이 현재 트레이딩 빈도를 수용 가능
   - Confidence: Medium
   - Evidence: 분당 60회 호출 제한, 실제 사용 패턴 분석 필요
   - Risk if wrong: Rate Limit 조정 또는 스케줄링 변경 필요

---

## Requirements

### Ubiquitous Requirements (Always Active)

**REQ-001: 환경 변수 기반 인증**
시스템은 **항상** 환경 변수에서 API 키를 로드하여 인증을 수행해야 한다.

**REQ-002: JSON 응답 파싱**
시스템은 **항상** AI 모델의 응답을 JSON 형식으로 파싱하여 트레이딩 의사결정을 추출해야 한다.

**REQ-003: 에러 로깅**
시스템은 **항상** 모든 API 호출 실패를 표준 로그 형식으로 기록해야 한다.

**REQ-004: 안전한 키 관리**
시스템은 **항상** API 키를 소스 코드에서 분리하여 관리해야 한다 (.env 파일 사용).

**REQ-005: 타임아웃 설정**
시스템은 **항상** API 호출에 대해 최소 10초, 최대 30초의 타임아웃을 적용해야 한다.

### Event-Driven Requirements

**REQ-010: 듀얼 프로바이더 초기화**
**WHEN** 시스템이 시작될 때 **THEN** 시스템은 GLM-5를 1차 프로바이더로, OpenAI를 폴백 프로바이더로 초기화해야 한다.

**REQ-011: 자동 폴백 트리거**
**WHEN** GLM-5 API 호출이 실패할 때 **THEN** 시스템은 자동으로 OpenAI API로 재시도해야 한다.

**REQ-012: 성공적 응답 처리**
**WHEN** AI 모델이 유효한 JSON 응답을 반환할 때 **THEN** 시스템은 트레이딩 의사결정을 실행해야 한다.

**REQ-013: Rate Limit 감지**
**WHEN** API가 429 상태 코드를 반환할 때 **THEN** 시스템은 exponential backoff로 재시도해야 한다.

**REQ-014: 인증 실패 처리**
**WHEN** API 키가 유효하지 않을 때 **THEN** 시스템은 즉시 실행을 중단하고 명확한 에러 메시지를 출력해야 한다.

**REQ-015: 네트워크 오류 복구**
**WHEN** 네트워크 연결이 실패할 때 **THEN** 시스템은 최대 5회 재시도 후 폴백 프로바이더로 전환해야 한다.

**REQ-016: Vision API 호출 (v3)**
**WHEN** autotrade_v3가 차트 스크린샷을 분석할 때 **THEN** 시스템은 base64 인코딩된 이미지를 Vision 모델에 전송해야 한다.

### State-Driven Requirements

**REQ-020: 프로바이더 상태 추적**
**IF** GLM-5 프로바이더가 연속 3회 실패 상태 **THEN** 시스템은 다음 5분간 OpenAI를 기본 프로바이더로 사용해야 한다.

**REQ-021: 폴백 상태 로깅**
**IF** 폴백 프로바이더가 활성화된 상태 **THEN** 시스템은 모든 호출을 "FALLBACK" 접두사와 함께 로깅해야 한다.

**REQ-022: Vision 모델 호환성 (v3)**
**IF** GLM-5 Vision 모델이 호환되지 않는 상태 **THEN** 시스템은 텍스트 전용 분석으로 자동 전환하거나 OpenAI Vision을 사용해야 한다.

**REQ-023: 토큰 사용량 모니터링**
**IF** 일일 토큰 사용량이 예산의 80%를 초과하는 상태 **THEN** 시스템은 경고 로그를 출력해야 한다.

### Unwanted Behavior Requirements

**REQ-030: 무한 재시도 방지**
시스템은 **반드시** 동일한 요청에 대해 5회 이상의 재시도를 수행해서는 안 된다.

**REQ-031: 민감 정보 노출 방지**
시스템은 **반드시** API 키를 로그 파일이나 에러 메시지에 노출해서는 안 된다.

**REQ-032: 블로킹 호출 방지**
시스템은 **반드시** 메인 스레드에서 무기한 대기하는 블로킹 API 호출을 수행해서는 안 된다.

**REQ-033: 무효 트레이딩 방지**
시스템은 **반드시** API 실패 시 자동으로 트레이딩을 실행해서는 안 된다 (명시적인 hold 상태 유지).

**REQ-034: 중복 주문 방지**
시스템은 **반드시** 타임아웃 발생 시 중복 주문이 발생하지 않도록 보장해야 한다.

### Optional Requirements

**REQ-040: A/B 테스트 프레임워크**
**가능하면** GLM-5와 OpenAI의 의사결정 품질을 비교하는 A/B 테스트 기능을 제공한다.

**REQ-041: 프롬프트 최적화**
**가능하면** GLM-5에 특화된 프롬프트 최적화를 수행한다.

**REQ-042: 비용 대시보드**
**가능하면** 실시간 비용 절감 현황을 시각화하는 대시보드를 제공한다.

**REQ-043: 품질 메트릭**
**가능하면** 의사결정 품질을 추적하는 메트릭 수집 시스템을 구현한다.

---

## Specifications

### Functional Specifications

**SPEC-F001: AI Client Factory**

듀얼 프로바이더를 지원하는 클라이언트 팩토리 함수 구현:

```python
# ai_client_factory.py
def get_ai_client() -> OpenAI:
    """
    듀얼 프로바이더 AI 클라이언트 팩토리

    Priority:
    1. GLM-5 (primary) - GLM_API_KEY 설정 시
    2. OpenAI (fallback) - GLM-5 실패 또는 미설정 시

    Returns:
        OpenAI: 설정된 클라이언트 인스턴스
    """
    pass
```

**SPEC-F002: Retry Logic with Exponential Backoff**

```python
def call_with_retry(
    client: OpenAI,
    messages: list,
    model: str,
    max_retries: int = 5,
    initial_delay: float = 1.0
) -> dict:
    """
    Exponential backoff를 적용한 API 호출

    Args:
        client: AI 클라이언트
        messages: 메시지 리스트
        model: 모델명
        max_retries: 최대 재시도 횟수
        initial_delay: 초기 지연 시간 (초)

    Returns:
        dict: API 응답
    """
    pass
```

**SPEC-F003: Vision API Adapter (v3)**

```python
def prepare_vision_message(
    text_prompt: str,
    base64_image: str,
    provider: str
) -> list:
    """
    Vision API 메시지 형식을 프로바이더에 맞게 변환

    Args:
        text_prompt: 텍스트 프롬프트
        base64_image: base64 인코딩된 이미지
        provider: "glm" 또는 "openai"

    Returns:
        list: 프로바이더 호환 메시지 리스트
    """
    pass
```

**SPEC-F004: Provider Health Check**

```python
def check_provider_health(client: OpenAI) -> bool:
    """
    프로바이더 상태 확인

    Args:
        client: AI 클라이언트

    Returns:
        bool: 프로바이더 사용 가능 여부
    """
    pass
```

### Non-Functional Specifications

**SPEC-NF001: Performance Requirements**

- **응답 시간**: P95 지연 시간 10초 이내
- **처리량**: 분당 최소 10회 API 호출 지원
- **메모리**: 추가 메모리 사용량 50MB 이내
- **CPU**: 유휴 상태에서 CPU 사용률 5% 이내

**SPEC-NF002: Reliability Requirements**

- **가용성**: 99.5% 이상 (듀얼 프로바이더 활용)
- **폴백 전환 시간**: 5초 이내
- **데이터 무결성**: 트레이딩 의사결정 0% 손실
- **에러 복구 시간**: 평균 30초 이내

**SPEC-NF003: Security Requirements**

- **API 키 보호**: 환경 변수 암호화 (선택적)
- **전송 보안**: HTTPS 필수 사용
- **감사 로그**: 모든 API 호출에 대한 추적 로그
- **접근 제어**: API 키별 권한 관리

**SPEC-NF004: Maintainability Requirements**

- **코드 커버리지**: 85% 이상
- **문서화**: 모든 공개 함수에 대한 docstring
- **로깅 표준**: 구조화된 JSON 로그 형식
- **설정 외부화**: 모든 설정 값 환경 변수화

### Interface Specifications

**SPEC-I001: Environment Variables**

```bash
# Primary Provider (GLM-5)
GLM_API_KEY=your_glm_api_key_here
GLM_API_BASE=https://open.bigmodel.cn/api/paas/v4/
GLM_MODEL=glm-5  # or glm-5-vision for v3

# Fallback Provider (OpenAI)
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL=gpt-4-turbo  # or gpt-4o for v3

# Provider Selection (optional override)
AI_PROVIDER=glm  # "glm" or "openai" or "auto" (default)

# Retry Configuration
AI_MAX_RETRIES=5
AI_INITIAL_DELAY=1.0
AI_TIMEOUT=30

# Health Check
AI_HEALTH_CHECK_INTERVAL=300  # seconds
AI_FAILURE_THRESHOLD=3  # consecutive failures
```

**SPEC-I002: Configuration Schema**

```python
@dataclass
class AIProviderConfig:
    """AI 프로바이더 설정"""
    glm_api_key: str | None = None
    glm_api_base: str = "https://open.bigmodel.cn/api/paas/v4/"
    glm_model: str = "glm-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4-turbo"
    provider: str = "auto"  # "glm", "openai", "auto"
    max_retries: int = 5
    initial_delay: float = 1.0
    timeout: int = 30
```

**SPEC-I003: Error Response Format**

```python
@dataclass
class AICallError:
    """API 호출 에러 정보"""
    provider: str  # "glm" or "openai"
    error_type: str  # "auth", "network", "rate_limit", "timeout"
    message: str
    retry_count: int
    timestamp: datetime
    fallback_used: bool
```

**SPEC-I004: Log Format**

```json
{
  "timestamp": "2026-03-14T10:30:00Z",
  "level": "INFO",
  "provider": "glm",
  "model": "glm-5",
  "response_time_ms": 1234,
  "tokens_used": 500,
  "fallback_triggered": false,
  "error": null
}
```

### Constraint Specifications

**SPEC-C001: GLM-5 API Limits**

- **Rate Limit**: 분당 60회 호출
- **최대 토큰**: 요청당 8,000 토큰
- **타임아웃**: 30초 권장, 60초 최대
- **동시 연결**: 최대 10개

**SPEC-C002: OpenAI API Limits (Fallback)**

- **Rate Limit**: 계정별 상이 (기본 3,000 RPM)
- **최대 토큰**: 모델별 상이 (GPT-4: 8,192)
- **타임아웃**: 30초 권장
- **동시 연결**: 제한 없음

**SPEC-C003: Vision API Constraints (v3)**

- **이미지 크기**: 최대 20MB
- **지원 형식**: JPEG, PNG, WebP
- **해상도**: 최대 4K (4096x4096)
- **처리 시간**: 텍스트 전용 대비 2-3배 증가 예상

**SPEC-C004: Budget Constraints**

- **일일 예산**: $50 (GLM-5) + $20 (OpenAI 폴백)
- **월간 목표 절감**: 60-70%
- **알림 임계값**: 80% 사용 시 경고

---

## Traceability

### Requirement to Implementation Mapping

| Requirement | Implementation | Test File |
|-------------|----------------|-----------|
| REQ-001 | ai_client_factory.py:get_ai_client() | test_glm_client.py:test_env_auth() |
| REQ-010 | ai_client_factory.py:get_ai_client() | test_glm_client.py:test_dual_provider_init() |
| REQ-011 | retry_handler.py:call_with_retry() | test_glm_client.py:test_auto_fallback() |
| REQ-013 | retry_handler.py:exponential_backoff() | test_glm_client.py:test_rate_limit() |
| REQ-016 | vision_adapter.py:prepare_vision_message() | test_autotrade_v3.py:test_vision_api() |
| REQ-020 | provider_health.py:track_failures() | test_glm_client.py:test_provider_switching() |
| REQ-030 | retry_handler.py:max_retries_check | test_glm_client.py:test_max_retries() |
| SPEC-F001 | ai_client_factory.py | test_ai_factory.py |
| SPEC-F002 | retry_handler.py | test_retry_handler.py |
| SPEC-F003 | vision_adapter.py | test_vision_adapter.py |

### Tag References

이 SPEC은 다음 @MX 태그와 연관됨:
- `@MX:ANCHOR`: get_ai_client() - 듀얼 프로바이더 진입점
- `@MX:NOTE`: call_with_retry() - 재시도 로직 설명
- `@MX:WARN`: API 키 관련 코드 - 민감 정보 처리 주의

---

## Quality Gates

### Pre-Implementation Checklist

- [ ] GLM-5 API 키 획득 완료
- [ ] GLM-5 API 문서 검토 완료
- [ ] 테스트 환경 구축 완료
- [ ] .env.example 업데이트 완료

### Implementation Checklist

- [ ] ai_client_factory.py 구현 완료
- [ ] retry_handler.py 구현 완료
- [ ] vision_adapter.py 구현 완료 (v3)
- [ ] autotrade.py 마이그레이션 완료
- [ ] autotrade_v2.py 마이그레이션 완료
- [ ] autotrade_v3.py 마이그레이션 완료

### Post-Implementation Checklist

- [ ] 단위 테스트 커버리지 85% 달성
- [ ] 통합 테스트 통과
- [ ] 회귀 테스트 통과
- [ ] 성능 테스트 통과
- [ ] 보안 감사 통과

---

## Related Documents

- **Implementation Plan**: plan.md
- **Acceptance Criteria**: acceptance.md
- **Migration Guide**: .moai/docs/glm-migration-guide.md (to be created)
- **API Documentation**: .moai/docs/api-reference.md (to be updated)

---

**Last Updated**: 2026-03-14
**Review Schedule**: Weekly during implementation
**Next Review**: 2026-03-21
