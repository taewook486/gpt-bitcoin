---
spec_id: SPEC-REFACTOR-PYTHON-001
title: Acceptance Criteria - Legacy Python Code Modernization
created: 2026-03-02
status: Planned
priority: High
---

# Acceptance Criteria: Legacy Python Code Modernization

## Overview

본 문서는 gpt-bitcoin 자동거래 시스템 현대화 작업의 완료 기준을 정의합니다. 모든 기준은 Given-When-Then (Gherkin) 형식으로 작성되었습니다.

---

## Phase 1: Foundation & Dependency Updates

### AC-1.1: 의존성 관리

```gherkin
Feature: 의존성 관리 현대화

  Scenario: pyproject.toml을 사용한 의존성 설치
    Given 프로젝트 루트에 pyproject.toml 파일이 존재함
    And pyproject.toml에 모든 의존성이 버전과 함께 정의됨
    When 개발자가 "pip install -e .[dev]" 명령을 실행함
    Then 모든 의존성이 성공적으로 설치됨
    And 의존성 버전이 고정되어 재현 가능한 빌드가 보장됨

  Scenario: 의존성 보안 취약점 검사
    Given 모든 의존성이 설치됨
    When "pip-audit" 명령을 실행함
    Then 알려진 보안 취약점이 0개임
    Or 취약점이 있는 경우 적절한 대안 버전으로 업데이트됨
```

### AC-1.2: 프로젝트 구조

```gherkin
Feature: 프로젝트 구조 재조직

  Scenario: 모듈화된 프로젝트 구조
    Given 프로젝트가 src/ 디렉토리 기반으로 재조직됨
    When 프로젝트 구조를 검사함
    Then src/gpt_bitcoin/ 디렉토리가 존재함
    And models/, services/, exchanges/, ai/, utils/ 서브디렉토리가 존재함
    And 각 서브디렉토리에 __init__.py 파일이 존재함
    And 레거시 파일이 legacy/ 디렉토리로 이동됨

  Scenario: 패키지 임포트 가능
    Given 프로젝트가 설치됨
    When Python에서 "from gpt_bitcoin.models.trading import TradingDecision"을 실행함
    Then ImportError 없이 임포트가 성공함
```

### AC-1.3: 개발 도구

```gherkin
Feature: 개발 도구 설정

  Scenario: Ruff 린팅 통과
    Given 모든 Python 파일에 타입 힌트가 적용됨
    When "ruff check src/" 명령을 실행함
    Then 린트 에러가 0개임
    And 경고가 10개 이하임

  Scenario: MyPy 타입 체크 통과
    Given 모든 Python 파일에 타입 힌트가 적용됨
    When "mypy src/" 명령을 실행함
    Then 타입 에러가 0개임
    And "Success: no issues found" 메시지가 출력됨

  Scenario: Pre-commit 훅 동작
    Given .pre-commit-config.yaml이 설정됨
    When "pre-commit run --all-files" 명령을 실행함
    Then 모든 훅이 통과함
    And 자동 수정이 가능한 문제는 자동으로 수정됨
```

---

## Phase 2: Architecture Refactoring

### AC-2.1: 타입 힌트

```gherkin
Feature: 타입 힌트 적용

  Scenario: 모든 함수에 타입 힌트
    Given src/gpt_bitcoin/의 모든 Python 파일
    When AST를 분석하여 함수 정의를 검사함
    Then 모든 public 함수에 반환 타입 힌트가 존재함
    And 모든 함수 매개변수에 타입 힌트가 존재함
    And mypy strict 모드에서 에러가 0개임

  Scenario: Pydantic 모델 검증
    Given 모든 데이터 모델이 Pydantic BaseModel을 상속함
    When 잘못된 데이터로 모델을 생성하려 함
    Then ValidationError가 발생함
    And 에러 메시지에 필드명과 검증 실패 이유가 포함됨

  Scenario: 타입 힌트 커버리지
    Given 전체 코드베이스
    When "mypy --disallow-untyped-defs src/" 명령을 실행함
    Then 에러가 0개임
    And 모든 함수가 타입 힌트를 가짐이 보장됨
```

### AC-2.2: 비동기 아키텍처

```gherkin
Feature: 비동기 아키텍처 구현

  Scenario: 모든 I/O 작업이 비동기
    Given 모든 외부 API 호출 함수
    When 함수 정의를 검사함
    Then 모든 함수가 async def로 정의됨
    And await 키워드가 적절히 사용됨
    And 동기식 HTTP 클라이언트가 사용되지 않음

  Scenario: 비동기 컨텍스트 관리
    Given 리소스를 사용하는 모든 클래스
    When __aenter__와 __aexit__ 메서드를 검사함
    Then 모든 리소스가 async with 구문으로 관리됨
    And 리소스 누수가 발생하지 않음

  Scenario: 동시성 안전성
    Given 여러 비동기 작업이 동시에 실행됨
    When asyncio.gather()로 여러 작업을 실행함
    Then 경쟁 조건이 발생하지 않음
    And 데드락이 발생하지 않음
```

### AC-2.3: 의존성 주입

```gherkin
Feature: 의존성 주입 패턴

  Scenario: 글로벌 변수 제거
    Given 리팩토링된 코드베이스
    When 소스 코드를 검사함
    Then 모듈 레벨에서 mutable 글로벌 변수가 존재하지 않음
    And 모든 의존성이 생성자를 통해 주입됨

  Scenario: 인터페이스 기반 의존성
    Given ExchangeBase와 AIAnalyzerBase 추상 클래스
    When 구체적인 구현체를 사용함
    Then 구현체가 추상 클래스를 상속함
    And 추상 메서드가 모두 구현됨

  Scenario: 테스트에서 Mock 주입
    Given TradingService 클래스
    When 단위 테스트에서 Mock Exchange와 Analyzer를 주입함
    Then 실제 API 호출 없이 테스트가 실행됨
    And 테스트가 결정적으로 실행됨
```

### AC-2.4: 에러 처리

```gherkin
Feature: 구조화된 에러 처리

  Scenario: 커스텀 예외 계층
    Given TradingError 기본 예외 클래스
    When 특정 에러 상황이 발생함
    Then 적절한 서브클래스 예외가 발생함
    And 예외 메시지에 컨텍스트 정보가 포함됨

  Scenario: 베어 익셉션 미사용
    Given 전체 코드베이스
    When try-except 구문을 검사함
    Then "except:" 또는 "except Exception:" 구문이 존재하지 않음
    And 구체적인 예외 타입만 catch됨

  Scenario: 에러 로깅
    Given 예외가 발생함
    When 예외가 catch됨
    Then structlog를 통해 에러가 로깅됨
    And 에러 메시지, 스택 트레이스, 컨텍스트가 포함됨
```

---

## Phase 3: Testing Infrastructure

### AC-3.1: 테스트 커버리지

```gherkin
Feature: 테스트 커버리지 달성

  Scenario: 최소 커버리지 기준
    Given 모든 소스 코드
    When "pytest --cov=src --cov-report=term-missing" 명령을 실행함
    Then 전체 커버리지가 85% 이상임
    And 각 모듈별 커버리지가 80% 이상임
    And 커버리지 리포트에 미달 부분이 표시됨

  Scenario: 브랜치 커버리지
    Given 모든 조건문
    When 브랜치 커버리지를 측정함
    Then 브랜치 커버리지가 80% 이상임
    And 모든 예외 처리 경로가 테스트됨
```

### AC-3.2: 단위 테스트

```gherkin
Feature: 단위 테스트 품질

  Scenario: 모든 public 함수 테스트
    Given src/gpt_bitcoin/의 모든 public 함수
    When tests/unit/ 디렉토리를 검사함
    Then 각 public 함수에 대한 테스트가 존재함
    And 정상 케이스, 에러 케이스, 엣지 케이스가 모두 테스트됨

  Scenario: 테스트 독립성
    Given pytest 테스트 스위트
    When 테스트를 임의의 순서로 실행함
    Then 모든 테스트가 독립적으로 통과함
    And 테스트 간 상태 공유가 없음

  Scenario: Mock 사용
    Given 외부 의존성이 있는 테스트
    When 테스트를 실행함
    Then 모든 외부 의존성이 Mock됨
    And 실제 네트워크 호출이 발생하지 않음
```

### AC-3.3: 통합 테스트

```gherkin
Feature: 통합 테스트

  Scenario: Upbit API 통합
    Given 유효한 Upbit API 키
    When tests/integration/test_upbit.py를 실행함
    Then 실제 API 호출이 성공함
    And 응답 데이터가 Pydantic 모델로 파싱됨

  Scenario: OpenAI API 통합
    Given 유효한 OpenAI API 키
    When tests/integration/test_openai.py를 실행함
    Then 실제 API 호출이 성공함
    And TradingDecision이 올바르게 생성됨

  Scenario: 통합 테스트 격리
    Given 통합 테스트가 실행됨
    When 테스트가 완료됨
    Then 테스트 데이터가 정리됨
    And 실제 거래가 실행되지 않음 (페이퍼 트레이딩)
```

### AC-3.4: 테스트 실행

```gherkin
Feature: 테스트 실행 자동화

  Scenario: 전체 테스트 스위트 실행
    Given 모든 테스트가 작성됨
    When "pytest" 명령을 실행함
    Then 모든 테스트가 60초 이내에 완료됨
    And 테스트 결과가 명확하게 출력됨

  Scenario: CI/CD 통합
    Given GitHub Actions 워크플로우
    When PR이 생성됨
    Then 자동으로 테스트가 실행됨
    And 테스트 실패 시 PR 머지가 차단됨
```

---

## Phase 4: Observability & Monitoring

### AC-4.1: 구조화된 로깅

```gherkin
Feature: 구조화된 로깅 시스템

  Scenario: JSON 형식 로그 출력
    Given 로그 레벨이 INFO 이상으로 설정됨
    When 거래 결정이 실행됨
    Then 로그가 JSON 형식으로 출력됨
    And 로그에 timestamp, level, message, context 필드가 포함됨

  Scenario: 로그 컨텍스트
    Given 거래 실행 중
    When 로그가 출력됨
    Then ticker, decision, amount, success 필드가 포함됨
    And 추적 가능한 order_id가 포함됨

  Scenario: 민감 정보 마스킹
    Given API 키가 로깅됨
    When 로그를 출력함
    Then API 키가 마스킹됨
    And "sk-***" 형식으로 표시됨
```

### AC-4.2: 헬스체크

```gherkin
Feature: 헬스체크 엔드포인트

  Scenario: 기본 헬스체크
    Given FastAPI 서버가 실행 중임
    When GET /health 요청을 보냄
    Then 200 OK 응답이 반환됨
    And 응답에 status, timestamp, version 필드가 포함됨

  Scenario: 종속성 상태 확인
    Given 거래소 API와 AI API가 연결됨
    When GET /health 요청을 보냄
    Then checks 필드에 각 종속성 상태가 포함됨
    And latency_ms가 각 종속성별로 측정됨

  Scenario: 장애 감지
    Given 거래소 API가 응답하지 않음
    When GET /health 요청을 보냄
    Then status가 "degraded"로 반환됨
    And checks.exchange_api.status가 "error"임
```

### AC-4.3: 에러 추적

```gherkin
Feature: 에러 추적 시스템

  Scenario: 예외 자동 캡처
    Given Sentry가 설정됨 (선택)
    When 미처리 예외가 발생함
    Then Sentry로 예외가 자동 전송됨
    And 컨텍스트 정보가 함께 전송됨

  Scenario: 에러 알림
    Given 중요한 에러가 발생함
    When 에러가 로깅됨
    Then 구성된 알림 채널로 알림이 전송됨
    And 알림에 에러 메시지와 발생 시간이 포함됨
```

---

## Phase 5: Documentation & Cleanup

### AC-5.1: 코드 문서화

```gherkin
Feature: 코드 문서화

  Scenario: 모든 public 모듈에 docstring
    Given src/gpt_bitcoin/의 모든 Python 파일
    When 모듈, 클래스, 함수를 검사함
    Then 모든 public 요소에 docstring이 존재함
    And docstring이 Google 스타일을 따름

  Scenario: 타입 힌트와 docstring 일치
    Given 함수에 타입 힌트와 docstring이 존재함
    When docstring을 검사함
    Then Args 섹션의 매개변수가 타입 힌트와 일치함
    And Returns 섹션의 반환 타입이 타입 힌트와 일치함
```

### AC-5.2: 사용자 문서

```gherkin
Feature: 사용자 문서

  Scenario: README 완결성
    Given README.md 파일
    When README를 검사함
    Then Installation 섹션이 존재함
    And Configuration 섹션이 존재함
    And Usage 섹션이 존재함
    And Architecture 섹션이 존재함

  Scenario: .env.example 제공
    Given .env.example 파일
    When 파일을 열람함
    Then 필요한 모든 환경 변수가 나열됨
    And 각 변수에 대한 설명이 주석으로 포함됨
```

### AC-5.3: 레거시 정리

```gherkin
Feature: 레거시 코드 정리

  Scenario: 레거시 파일 격리
    Given autotrade.py, autotrade_v2.py, autotrade_v3.py
    When 리팩토링이 완료됨
    Then 파일들이 legacy/ 디렉토리로 이동됨
    And README에 레거시 파일 참조가 제거됨

  Scenario: 미사용 의존성 제거
    Given requirements.txt
    When 의존성을 분석함
    Then 사용되지 않는 의존성이 제거됨
    And pyjwt가 제거됨 (미사용 확인됨)
```

---

## Quality Gates Summary

### 필수 기준 (MUST)

| Category | Metric | Target | Verification |
|----------|--------|--------|--------------|
| 타입 힌트 | MyPy strict mode | 0 errors | `mypy --strict src/` |
| 코드 품질 | Ruff linting | 0 errors | `ruff check src/` |
| 테스트 | Coverage | >= 85% | `pytest --cov` |
| 테스트 | All tests pass | 100% | `pytest` |
| 보안 | No secrets in code | 0 findings | Manual + pre-commit |
| 문서화 | README complete | Yes | Manual review |

### 권장 기준 (SHOULD)

| Category | Metric | Target | Verification |
|----------|--------|--------|--------------|
| 로깅 | Structured logging | Yes | Code review |
| 모니터링 | Health check | Yes | `GET /health` |
| 에러 추적 | Sentry integration | Optional | Manual |
| 문서화 | API docs | Yes | `pydoc` |

---

## Verification Checklist

### Phase 1 완료 확인
- [ ] `pip install -e ".[dev]"` 성공
- [ ] `ruff check src/` 에러 0개
- [ ] `mypy src/` 에러 0개
- [ ] `pre-commit run --all-files` 통과

### Phase 2 완료 확인
- [ ] `mypy --disallow-untyped-defs src/` 에러 0개
- [ ] 글로벌 변수 0개 (리뷰)
- [ ] 모든 I/O 함수가 async (리뷰)
- [ ] 베어 익셉션 0개 (리뷰)

### Phase 3 완료 확인
- [ ] `pytest --cov=src` 커버리지 >= 85%
- [ ] `pytest` 모든 테스트 통과
- [ ] 통합 테스트 통과 (API 키 있음)

### Phase 4 완료 확인
- [ ] 로그가 JSON 형식으로 출력됨
- [ ] `GET /health` 200 OK 응답
- [ ] 에러 발생 시 적절한 로깅

### Phase 5 완료 확인
- [ ] README.md 완결성 확인
- [ ] .env.example 존재
- [ ] 레거시 파일이 legacy/로 이동됨

---

## Test Scenarios Summary

### 정상 시나리오 (Happy Path)
1. 사용자가 봇을 시작함 → 정상적으로 거래 결정이 실행됨
2. AI가 BUY 결정 → KRW 잔고 확인 → 매수 주문 실행 → 로깅
3. AI가 SELL 결정 → BTC 잔고 확인 → 매도 주문 실행 → 로깅
4. AI가 HOLD 결정 → 아무 작업 없음 → 로깅

### 에러 시나리오 (Error Cases)
1. KRW 잔고 부족 → 매수 실패 → 에러 로깅 → 사용자 알림
2. BTC 잔고 부족 → 매도 실패 → 에러 로깅 → 사용자 알림
3. Upbit API 장애 → 재시도 → 실패 시 에러 로깅 → 알림
4. OpenAI API 장애 → 재시도 → 실패 시 에러 로깅 → 알림

### 엣지 케이스 (Edge Cases)
1. 잔고가 정확히 5,000원 → 최소 주문 금액 경계값 테스트
2. 매수/매도 퍼센티지가 0% → 아무 작업 없음
3. 매수/매도 퍼센티지가 100% → 전체 잔고 사용
4. 네트워크 지연 → 타임아웃 처리 → 재시도

---

## Final Acceptance

### 전체 시스템 검증

```gherkin
Feature: 전체 시스템 검증

  Scenario: 엔드 투 엔드 거래 플로우
    Given 모든 Phase가 완료됨
    And 유효한 API 키가 설정됨
    When 봇을 실행함
    Then 시장 데이터를 수집함
    And AI 분석을 수행함
    And 거래 결정을 내림
    And 결정을 실행함
    And 모든 작업이 로깅됨
    And 0개의 에러가 발생함

  Scenario: 페이퍼 트레이딩 모드
    Given PAPER_TRADING=true 환경 변수
    When 봇을 실행함
    Then 모든 거래 결정이 시뮬레이션됨
    And 실제 주문이 실행되지 않음
    And 로깅은 실제 모드와 동일함

  Scenario: 시스템 복구
    Given 봇이 실행 중임
    When 예기치 않은 종료가 발생함
    And 봇을 재시작함
    Then 이전 상태가 복구됨
    And 거래가 중단된 지점부터 재개됨
```

---

## Sign-Off Criteria

### 개발자 승인
- [ ] 모든 코드 리뷰 완료
- [ ] 모든 테스트 통과
- [ ] 문서화 완료

### 사용자 승인
- [ ] 페이퍼 트레이딩 모드 검증 완료
- [ ] 실제 소액 거래 검증 완료
- [ ] 사용자 매뉴얼 검토 완료

### 운영 승인
- [ ] 모니터링 대시보드 확인
- [ ] 알림 시스템 동작 확인
- [ ] 장애 복구 절차 검증

---

**마지막 업데이트:** 2026-03-02
**버전:** 1.0.0
**작성자:** manager-spec agent
