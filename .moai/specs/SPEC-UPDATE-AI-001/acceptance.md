# Acceptance Criteria: SPEC-UPDATE-AI-001

**SPEC ID**: SPEC-UPDATE-AI-001
**Title**: GLM-5 AI Model Migration
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Status**: Planned

---

## Overview

이 문서는 GLM-5 마이그레이션에 대한 인수 조건, 테스트 시나리오, 검증 절차를 정의합니다. 모든 인수 조건은 Gherkin 형식(Given-When-Then)으로 작성되었으며, 마이그레이션 완료로 간주되기 전에 충족되어야 합니다.

---

## Definition of Done

### Must-Have Criteria (완료 필수 조건)

- [ ] 모든 버전(v1, v2, v3)이 GLM-5 API를 성공적으로 호출
- [ ] JSON 의사결정 출력 형식이 올바르게 작동
- [ ] v3 Vision 분석이 작동하거나 우아한 성능 저하 처리
- [ ] 모든 정의된 시나리오에 대한 에러 처리 구현
- [ ] 롤백 절차가 테스트되고 검증됨
- [ ] 마이그레이션 중 트레이딩 실행 실패 0건
- [ ] 듀얼 프로바이더 폴백이 구현되고 테스트됨
- [ ] 모든 단위 테스트 통과 (커버리지 85% 이상)
- [ ] 모든 통합 테스트 통과
- [ ] 보안 감사 통과 (API 키 노출 없음)

### Should-Have Criteria (권장 조건)

- [ ] 포괄적인 로깅 (모든 API 호출 추적)
- [ ] 토큰 사용량 모니터링 구현
- [ ] OpenAI 베이스라인과 성능 매칭 또는 개선
- [ ] 에러 복구 시간 < 30초

### Nice-to-Have Criteria (선택 조건)

- [ ] A/B 테스트 프레임워크 운영
- [ ] GLM-5 특화 프롬프트 최적화 완료
- [ ] 의사결정 품질 메트릭 대시보드
- [ ] 비용 절감 실시간 시각화

---

## Acceptance Criteria (Gherkin Format)

### Feature 1: 듀얼 프로바이더 AI 클라이언트

#### Scenario 1.1: GLM-5 기본 인증 성공
```gherkin
Feature: 듀얼 프로바이더 AI 클라이언트 인증

  Scenario: GLM-5 API 키로 성공적인 인증
    Given 환경 변수 GLM_API_KEY가 유효한 API 키로 설정됨
    And 환경 변수 GLM_API_BASE가 "https://api.z.ai/api/coding/paas/v4/"로 설정됨
    When 시스템이 get_ai_client() 함수를 호출함
    Then GLM-5 클라이언트가 성공적으로 초기화됨
    And 클라이언트의 base_url이 GLM_API_BASE와 일치함
    And 클라이언트의 api_key가 GLM_API_KEY와 일치함
```

#### Scenario 1.2: GLM-5 실패 시 OpenAI 폴백
```gherkin
  Scenario: GLM-5 인증 실패 시 OpenAI 자동 폴백
    Given 환경 변수 GLM_API_KEY가 "invalid_key"로 설정됨
    And 환경 변수 OPENAI_API_KEY가 유효한 키로 설정됨
    When 시스템이 get_ai_client() 함수를 호출함
    Then 경고 로그 "GLM-5 client initialization failed"가 출력됨
    And OpenAI 클라이언트가 반환됨
    And 로그에 "Falling back to OpenAI" 메시지가 포함됨
```

#### Scenario 1.3: API 키 누락 시 명확한 에러
```gherkin
  Scenario: 모든 API 키 누락 시 명확한 에러 메시지
    Given 환경 변수 GLM_API_KEY가 설정되지 않음
    And 환경 변수 OPENAI_API_KEY가 설정되지 않음
    When 시스템이 get_ai_client() 함수를 호출함
    Then ValueError 예외가 발생함
    And 에러 메시지에 "Either GLM_API_KEY or OPENAI_API_KEY must be set"가 포함됨
```

---

### Feature 2: Exponential Backoff 재시도 로직

#### Scenario 2.1: 네트워크 타임아웃 재시도
```gherkin
Feature: Exponential Backoff 재시도 로직

  Scenario: 네트워크 타임아웃 발생 시 점진적 재시도
    Given AI 클라이언트가 초기화됨
    And GLM-5 API가 처음 2회 호출에서 TimeoutError를 반환하도록 모킹됨
    And 3번째 호출에서 성공 응답을 반환하도록 모킹됨
    When call_with_retry() 함수가 호출됨
    Then 시스템이 총 3회 API를 호출함
    And 첫 번째 재시도 전 1초 대기함
    And 두 번째 재시도 전 2초 대기함
    And 최종적으로 성공 응답을 반환함
    And 로그에 각 재시도 시도가 기록됨
```

#### Scenario 2.2: 최대 재시도 초과
```gherkin
  Scenario: 최대 재시도 횟수 초과 시 에러 발생
    Given AI 클라이언트가 초기화됨
    And GLM-5 API가 모든 호출에서 TimeoutError를 반환하도록 모킹됨
    When call_with_retry() 함수가 max_retries=5로 호출됨
    Then 시스템이 정확히 5회 API를 호출함
    And MaxRetriesExceededError 예외가 발생함
    And 에러 메시지에 총 시도 횟수가 포함됨
    And 로그에 "Max retries (5) exceeded" 메시지가 기록됨
```

#### Scenario 2.3: Rate Limit 처리
```gherkin
  Scenario: Rate Limit (429) 응답 시 60초 대기 후 재시도
    Given AI 클라이언트가 초기화됨
    And 첫 번째 API 호출이 HTTP 429를 반환하도록 모킹됨
    And 두 번째 호출이 성공하도록 모킹됨
    When call_with_retry() 함수가 호출됨
    Then 시스템이 60초 동안 대기함
    And 대기 후 재시도가 수행됨
    And 최종적으로 성공 응답을 반환함
    And 로그에 "Rate limit hit, waiting 60s" 메시지가 기록됨
```

---

### Feature 3: GLM-5 API 호출 및 응답

#### Scenario 3.1: 성공적인 JSON 응답 파싱
```gherkin
Feature: GLM-5 API 호출 및 응답 처리

  Scenario: 유효한 JSON 의사결정 응답 파싱
    Given AI 클라이언트가 GLM-5로 초기화됨
    And 기술적 지표 데이터가 준비됨
    When analyze_data_with_glm5() 함수가 호출됨
    Then API 호출이 model="glm-5"로 수행됨
    And 응답이 JSON으로 성공적으로 파싱됨
    And 파싱된 JSON에 "decision" 필드가 포함됨
    And decision 값이 "buy", "sell", 또는 "hold" 중 하나임
    And 파싱된 JSON에 "percentage" 필드가 포함됨
    And percentage 값이 0에서 100 사이임
    And 파싱된 JSON에 "reason" 필드가 포함됨
    And reason이 비어 있지 않은 문자열임
```

#### Scenario 3.2: GLM-5 응답 시간 모니터링
```gherkin
  Scenario: API 응답 시간이 허용 범위 내에 있음
    Given AI 클라이언트가 GLM-5로 초기화됨
    When 100회의 API 호출이 수행됨
    Then P95 응답 시간이 10초를 초과하지 않음
    And 평균 응답 시간이 5초 미만임
    And 모든 응답 시간이 로그에 기록됨
```

#### Scenario 3.3: 잘못된 JSON 응답 처리
```gherkin
  Scenario: JSON 파싱 실패 시 안전한 처리
    Given AI 클라이언트가 초기화됨
    And GLM-5 API가 "invalid json {"를 반환하도록 모킹됨
    When analyze_data_with_glm5() 함수가 호출됨
    Then JSONDecodeError 예외가 발생함
    And 트레이딩이 실행되지 않음
    And 로그에 "JSON parsing failed" 에러가 기록됨
    And 기본 "hold" 의사결정이 적용됨
```

---

### Feature 4: Vision API (v3)

#### Scenario 4.1: Chart 스크린샷 Base64 인코딩
```gherkin
Feature: Vision API 차트 분석 (v3)

  Scenario: Chart 스크린샷 캡처 및 Base64 인코딩
    Given autotrade_v3.py가 실행 중임
    And ChromeDriver가 사용 가능함
    When get_current_base64_image() 함수가 호출됨
    Then screenshot.png 파일이 생성됨
    And 파일 크기가 0바이트보다 큼
    And Base64 인코딩된 문자열이 반환됨
    And 인코딩된 문자열 길이가 1000자 이상임
    And 로그에 "Screenshot captured" 메시지가 기록됨
```

#### Scenario 4.2: GLM-5 Vision API 호출
```gherkin
  Scenario: GLM-5 Vision API 성공적 호출
    Given AI 클라이언트가 GLM-5로 초기화됨
    And Base64 인코딩된 차트 이미지가 준비됨
    When prepare_vision_message()가 호출됨
    Then Vision 메시지가 GLM-5 호환 형식으로 생성됨
    And 메시지에 텍스트 프롬프트가 포함됨
    And 메시지에 Base64 이미지가 포함됨
    And API 호출이 model="glm-5-vision"으로 수행됨
    And 응답에 차트 분석 내용이 포함됨
```

#### Scenario 4.3: Vision API 실패 시 텍스트 전용 폴백
```gherkin
  Scenario: Vision API 실패 시 텍스트 전용 분석으로 폴백
    Given AI 클라이언트가 초기화됨
    And GLM-5 Vision API가 HTTP 503을 반환하도록 모킹됨
    And GLM-5 텍스트 API가 정상 작동하도록 모킹됨
    When autotrade_v3가 의사결정을 수행함
    Then "Vision model unavailable" 경고가 로그에 기록됨
    And "Falling back to text-only analysis" 메시지가 출력됨
    And 텍스트 전용 API 호출이 수행됨
    And 의사결정이 성공적으로 반환됨
    And reason 필드에 "Text-only analysis" 접두사가 포함됨
```

---

### Feature 5: 프로바이더 상태 추적

#### Scenario 5.1: 연속 실패 시 프로바이더 전환
```gherkin
Feature: 프로바이더 상태 추적 및 전환

  Scenario: GLM-5 연속 3회 실패 시 OpenAI로 전환
    Given 듀얼 프로바이더가 활성화됨
    And GLM-5 API가 연속 3회 실패하도록 모킹됨
    And OpenAI API가 정상 작동하도록 모킹됨
    When 4번째 API 호출이 수행됨
    Then 시스템이 자동으로 OpenAI를 사용함
    And "Provider switched to OpenAI" 로그가 기록됨
    And 향후 5분간 OpenAI가 기본 프로바이더로 유지됨
```

#### Scenario 5.2: 프로바이더 복구
```gherkin
  Scenario: 5분 후 GLM-5 프로바이더 복구 시도
    Given GLM-5가 비활성화됨 (연속 실패로 인해)
    And 5분이 경과함
    When 다음 API 호출이 수행됨
    Then 시스템이 GLM-5를 다시 시도함
    And GLM-5가 성공하면 기본 프로바이더로 복원됨
    And "Provider restored to GLM-5" 로그가 기록됨
```

---

### Feature 6: 보안 및 감사

#### Scenario 6.1: API 키 로그 필터링
```gherkin
Feature: 보안 및 감사 로깅

  Scenario: API 키가 로그에 노출되지 않음
    Given AI 클라이언트가 GLM-5로 초기화됨
    And GLM_API_KEY="sk-secret-key-12345"로 설정됨
    When API 호출이 수행되고 로그가 기록됨
    Then 로그 파일에 "sk-secret-key-12345"가 나타나지 않음
    And 로그 파일에 "GLM_API_KEY" 문자열이 나타나지 않음
    And API 키 값이 마스킹됨 (예: "sk-***...***45")
```

#### Scenario 6.2: 민감 정보 소스 코드 제외
```gherkin
  Scenario: API 키가 소스 코드에 하드코딩되지 않음
    Given 소스 코드 리포지토리가 준비됨
    When 모든 Python 파일이 스캔됨
    Then "api_key.*=.*['\"]" 패턴과 일치하는 하드코딩된 키가 없음
    And ".env" 파일이 .gitignore에 포함됨
    And ".env.example"에만 플레이스홀더 키가 존재함
```

#### Scenario 6.3: 구조화된 감사 로그
```gherkin
  Scenario: 모든 API 호출이 구조화된 JSON 로그로 기록됨
    Given AI 클라이언트가 초기화됨
    When API 호출이 수행됨
    Then 로그가 JSON 형식으로 기록됨
    And 로그에 "timestamp" 필드가 포함됨
    And 로그에 "provider" 필드가 포함됨 ("glm" 또는 "openai")
    And 로그에 "model" 필드가 포함됨
    And 로그에 "response_time_ms" 필드가 포함됨
    And 로그에 "tokens_used" 필드가 포함됨
    And 로그에 "fallback_triggered" 부울 필드가 포함됨
```

---

### Feature 7: 버전별 마이그레이션

#### Scenario 7.1: v1 마이그레이션 검증
```gherkin
Feature: 버전별 마이그레이션 검증

  Scenario: autotrade.py (v1) GLM-5 마이그레이션 성공
    Given autotrade.py가 GLM-5 클라이언트를 사용하도록 업데이트됨
    And 환경 변수가 올바르게 설정됨
    When python autotrade.py가 실행됨
    Then "Calling GLM-5 API" 메시지가 출력됨
    And API 호출이 성공함
    And JSON 의사결정이 파싱됨
    And 의사결정이 콘솔에 로깅됨
    And OpenAI API가 호출되지 않음 (폴백 미발생)
```

#### Scenario 7.2: v2 마이그레이션 검증
```gherkin
  Scenario: autotrade_v2.py (v2) GLM-5 마이그레이션 성공
    Given autotrade_v2.py가 GLM-5 클라이언트를 사용하도록 업데이트됨
    And SQLite 데이터베이스가 존재함
    When python autotrade_v2.py가 실행됨
    Then 뉴스 데이터가 페치됨
    And 기술적 데이터가 준비됨
    And 마지막 의사결정이 조회됨
    And Fear & Greed 인덱스가 페치됨
    And GLM-5 API 호출이 모든 입력과 함께 수행됨
    And 의사결정이 SQLite에 올바른 스키마로 저장됨
    And 데이터베이스 항목에 "glm-5" 모델이 기록됨
```

#### Scenario 7.3: v3 마이그레이션 검증
```gherkin
  Scenario: autotrade_v3.py (v3) Vision 마이그레이션 성공
    Given autotrade_v3.py가 GLM-5 Vision을 사용하도록 업데이트됨
    And ChromeDriver가 사용 가능함
    When python autotrade_v3.py가 실행됨
    Then 차트 스크린샷이 캡처됨
    And Base64 인코딩이 완료됨
    And GLM-5 Vision API 호출이 수행됨
    And 응답에 차트 시각적 분석이 포함됨
    And 의사결정 품질이 GPT-4o 베이스라인과 매칭됨
    And SQLite 데이터베이스에 저장됨
```

---

### Feature 8: 성능 및 비용

#### Scenario 8.1: 비용 절감 검증
```gherkin
Feature: 성능 및 비용 최적화

  Scenario: GLM-5 사용 시 비용 절감 달성
    Given 시스템이 30일 동안 GLM-5를 사용함
    And 동일 기간 OpenAI 사용 시 비용이 $100임
    When 월간 비용이 계산됨
    Then 총 GLM-5 비용이 $50 미만임
    And 비용 절감률이 50% 이상임
    And 토큰당 비용이 로그에 기록됨
```

#### Scenario 8.2: 의사결정 품질 유지
```gherkin
  Scenario: GLM-5 의사결정 품질이 GPT-4와 동등함
    Given 30일치 과거 데이터가 준비됨
    When 백테스팅이 GLM-5와 GPT-4 모두에 대해 수행됨
    Then GLM-5 수익률이 GPT-4 수익률의 95% 이상임
    And GLM-5 샤프 비율이 GPT-4 샤프 비율의 90% 이상임
    And GLM-5 최대 낙폭이 GPT-4 최대 낙폭의 110% 이내임
    And 의사결정 품질 메트릭이 대시보드에 표시됨
```

---

## Test Execution Plan

### Phase 1: Unit Tests (단위 테스트)

**Priority**: Critical
**Estimated Time**: 2 days

| Test Suite | Test Cases | Coverage Target |
|------------|-----------|-----------------|
| test_ai_client_factory.py | 15 | 100% (factory functions) |
| test_retry_handler.py | 12 | 100% (retry logic) |
| test_vision_adapter.py | 10 | 100% (vision functions) |
| test_glm_client.py | 20 | 90% (integration) |
| test_security.py | 8 | 100% (security functions) |

**Execution Command**:
```bash
pytest tests/unit -v --cov=ai_client_factory --cov=retry_handler --cov=vision_adapter --cov-report=term-missing
```

### Phase 2: Integration Tests (통합 테스트)

**Priority**: Critical
**Estimated Time**: 3 days

| Test Suite | Test Cases | Focus Area |
|------------|-----------|------------|
| test_autotrade_v1.py | 8 | v1 end-to-end flow |
| test_autotrade_v2.py | 10 | v2 with database |
| test_autotrade_v3.py | 12 | v3 with vision |
| test_dual_provider.py | 15 | Provider switching |
| test_error_recovery.py | 10 | Error scenarios |

**Execution Command**:
```bash
pytest tests/integration -v --cov=autotrade --cov=autotrade_v2 --cov=autotrade_v3 --cov-report=term-missing
```

### Phase 3: Regression Tests (회귀 테스트)

**Priority**: High
**Estimated Time**: 2 days

**Focus Areas**:
- 트레이딩 실행 로직 변경 없음
- 데이터베이스 스키마 호환성
- JSON 응답 형식 호환성
- 스케줄링 동작 유지

**Execution Command**:
```bash
pytest tests/regression -v --cov-report=term-missing
```

### Phase 4: Performance Tests (성능 테스트)

**Priority**: Medium
**Estimated Time**: 1 day

**Metrics to Validate**:
- API 응답 시간 (P95 < 10s)
- 메모리 사용량 (< 50MB 증가)
- CPU 사용률 (유휴 시 < 5%)
- 동시 요청 처리 능력

**Execution Command**:
```bash
pytest tests/performance -v --benchmark-only
```

---

## Validation Checklist

### Pre-Migration Validation (마이그레이션 전 검증)

**Date**: _______________
**Validator**: _______________

- [ ] GLM-5 API 키 획득 및 테스트 완료
- [ ] GLM-5 API 문서 검토 완료
- [ ] 환경 변수 설정 가이드 작성
- [ ] .env.example 업데이트
- [ ] .gitignore에 .env 포함 확인
- [ ] 현재 코드베이스 백업 (git tag: pre-glm-migration)
- [ ] 롤백 절차 문서화
- [ ] 테스트 환경 구축 완료

**Sign-Off**: _______________

### During Migration Validation (마이그레이션 중 검증)

**Hourly Checks** (First 24 Hours):

| Hour | Success Rate | P95 Latency | Auth Errors | Rate Limits | Quality | Initials |
|------|--------------|-------------|-------------|-------------|---------|----------|
| 1    |              |             |             |             |         |          |
| 2    |              |             |             |             |         |          |
| 4    |              |             |             |             |         |          |
| 8    |              |             |             |             |         |          |
| 12   |              |             |             |             |         |          |
| 24   |              |             |             |             |         |          |

**Thresholds**:
- Success Rate > 99%
- P95 Latency < 8s
- Auth Errors = 0
- Rate Limit Errors < 3
- Decision Quality: Acceptable

### Post-Migration Validation (마이그레이션 후 검증)

**24-Hour Validation** (Date: _______________):

- [ ] 모든 예약 실행이 성공적으로 완료됨
- [ ] 트레이딩 실행 실패 0건
- [ ] SQLite 데이터베이스 항목 정확함
- [ ] 로그 파일에 에러 없음
- [ ] 비용 절감 달성 (예상: ____________)
- [ ] Vision API 작동 (v3)
- [ ] 폴백 메커니즘 테스트 완료

**1-Week Validation** (Date: _______________):

- [ ] 백테스팅을 통한 의사결정 품질 검증 완료
- [ ] 프로덕션 환경에서 치명적 에러 없음
- [ ] 성능 메트릭 목표 달성
- [ ] 비용 절감 목표 달성 (__________% 절감)
- [ ] 문서 업데이트 완료
- [ ] 팀 교육 완료

**Sign-Off**: _______________

---

## Rollback Criteria (롤백 기준)

### Immediate Rollback Triggers (즉시 롤백 트리거)

- API 호출 성공률이 24시간 동안 95% 미만
- 치명적 프로덕션 에러로 트레이딩 실행 영향
- 인증 실패로 인한 완전 중단
- 데이터 손실 발생

### Investigate-Then-Decide Triggers (조사 후 결정 트리거)

- 의사결정 품질 저하 (백테스팅 기반)
- 예상보다 낮은 비용 절감
- 빈번한 폴백 발생
- 응답 시간 증가

### Rollback Procedure (롤백 절차)

```bash
# Step 1: 환경 변수 업데이트
echo "AI_PROVIDER=openai" >> .env

# Step 2: 프로세스 재시작
pkill -f autotrade
python autotrade.py &
python autotrade_v2.py &
python autotrade_v3.py &

# Step 3: 롤백 검증
tail -f autotrade.log | grep "OpenAI API"

# Step 4: 인시던트 문서화
# - 근본 원인
# - 타임라인
# - 해결 방안
# - 재마이그레이션 일정
```

**Rollback Time Target**: < 5 minutes

---

## Quality Gates

### Code Quality Gates

```bash
# Linting
ruff check . --line-length=100

# Type Checking
mypy . --ignore-missing-imports

# Security Scan
bandit -r . -f json -o security-report.json

# Test Coverage
pytest --cov=. --cov-report=html --cov-fail-under=85
```

**Pass Criteria**:
- Ruff Errors: 0
- Mypy Errors: 0
- Bandit Issues: 0 (High/Critical)
- Test Coverage: >= 85%

### Functional Quality Gates

- [ ] 모든 인수 조건 통과
- [ ] 모든 테스트 시나리오 통과
- [ ] 트레이딩 로직 회귀 없음
- [ ] Vision 분석 품질이 베이스라인과 매칭

### Operational Quality Gates

- [ ] 로깅이 포괄적이고 유용함
- [ ] 에러 메시지가 명확하고 실행 가능함
- [ ] 모니터링 알림이 구성됨
- [ ] Runbook이 문서화됨

---

## Sign-Off Section

### Development Sign-Off

**Developer**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] 모든 코드 변경 구현 완료
- [ ] 모든 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] 문서 업데이트 완료

### QA Sign-Off

**QA Engineer**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] 모든 인수 조건 검증 완료
- [ ] 모든 테스트 시나리오 실행 완료
- [ ] 남은 치명적 결함 없음
- [ ] 회귀 테스트 통과

### Product Owner Sign-Off

**Product Owner**: _______________
**Date**: _______________
**Signature**: _______________

**Confirmation**:
- [ ] 비즈니스 요구사항 충족
- [ ] 비용 절감 검증 완료
- [ ] 의사결정 품질 수용 가능
- [ ] 프로덕션 배포 준비 완료

---

## Appendices

### Appendix A: 테스트 데이터 샘플

**API 요청 예시**:
```json
{
  "model": "glm-5",
  "messages": [
    {"role": "system", "content": "당신은 암호화폐 트레이딩 어드바이저입니다..."},
    {"role": "user", "content": "뉴스: 비트코인 ETF 승인..."},
    {"role": "user", "content": "기술적: RSI=45, MACD=매수신호..."},
    {"role": "user", "content": "이전 의사결정: $50,000에 50% 매수..."}
  ],
  "response_format": {"type": "json_object"},
  "temperature": 0.7
}
```

**API 응답 예시**:
```json
{
  "decision": "buy",
  "percentage": 30,
  "reason": "긍정적인 뉴스 심리, RSI 중립권에 MACD 매수 교차, 이전 매수 의사결정은 누적 전략 제안"
}
```

### Appendix B: 모니터링 대시보드 메트릭

**핵심 메트릭**:
- API 호출 수 (시간별, 일별)
- 성공률 (%)
- 평균 지연 시간 (초)
- P95 지연 시간 (초)
- 토큰 사용량 (총합, 호출별)
- 비용 (일별, 월별)
- 의사결정 분포 (buy/sell/hold)
- 프로바이더 사용 분포 (GLM/OpenAI)

**알림 임계값**:
- 성공률 < 95%: 경고
- 성공률 < 90%: 치명적
- P95 지연 시간 > 10s: 경고
- P95 지연 시간 > 15s: 치명적
- 비용 > 베이스라인의 150%: 경고
- 연속 폴백 > 5회: 경고

### Appendix C: 에러 코드 참조

| Error Code | Description | Action |
|------------|-------------|--------|
| E001 | GLM_API_KEY not set | Configure environment variable |
| E002 | GLM-5 auth failed | Check API key validity |
| E003 | Network timeout | Retry with exponential backoff |
| E004 | Rate limit exceeded | Wait 60s, then retry |
| E005 | JSON parse failed | Check API response format |
| E006 | Vision API unavailable | Fallback to text-only |
| E007 | Max retries exceeded | Escalate to manual intervention |
| E008 | All providers failed | System halt, manual review |

---

**Last Updated**: 2026-03-14
**Review Schedule**: 각 테스트 단계 완료 후
**Next Review**: _______________
