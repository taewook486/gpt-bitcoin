# 인수 조건 (Acceptance Criteria)

**SPEC ID**: SPEC-MODERNIZE-001
**형식**: Gherkin (Behavior-Driven Development)
**언어**: Korean

---

## AC-001: 비동기 아키텍처

### Feature: 외부 API 비동기 호출

**Scenario: 병렬 데이터 수집**
```gherkin
Given 시스템이 시작될 때
And 복수의 외부 데이터 소스가 구성되어 있음
When 트레이딩 결정이 필요한 시점이到来
Then 뉴스, 차트, 공포탐욕지수 데이터가 병렬로 수집되어야 한다
And 전체 수집 시간은 개별 수집 시간의 최댓값 이하여야 한다
```

**Scenario: API 타임아웃 handling**
```gherkin
Given 외부 API 호출이 실행 중일 때
And 설정된 타임아웃 시간이 경과함
Then TimeoutException이 발생해야 한다
And 해당 요청은 재시도 큐에 추가되어야 한다
And 시스템은 계속 운영되어야 한다
```

---

## AC-002: 구조화된 로깅

### Feature: JSON 포맷 로그 출력

**Scenario: 거래 실행 로그**
```gherkin
Given 매수/매도 주문이 실행될 때
When 주문 결과가 수신됨
Then 다음 필드를 포함한 JSON 로그가 출력되어야 한다:
  | 필드 | 타입 | 설명 |
  | event | string | "buy_executed" 또는 "sell_executed" |
  | order_id | string | 업비트 주문 UUID |
  | volume | float | 거래 수량 |
  | price | float | 거래 가격 |
  | timestamp | string | ISO 8601 형식 |
And 민감한 정보(API 키 등)는 마스킹되어야 한다
```

**Scenario: Correlation ID 추적**
```gherkin
Given 단일 트레이딩 사이클이 시작될 때
When correlation_id가 생성됨
Then 해당 사이클의 모든 로그에 동일한 correlation_id가 포함되어야 한다
```

---

## AC-003: 테스트 커버리지

### Feature: Characterization Tests

**Scenario: 기존 동작 보존**
```gherkin
Given autotrade_v2.py의 현재 동작이 관찰됨
When characterization test가 작성됨
Then 테스트는 현재 동작의 스냅샷을 저장해야 한다
And 코드 수정 후 테스트 실행 시, 의도적 변경 외에는 실패하면 안 된다
```

### Feature: 최종 커버리지 목표

**Scenario: 85% 커버리지 달성**
```gherkin
Given 모든 기능이 구현됨
When 테스트 스위트가 실행됨
Then 전체 커버리지는 85% 이상이어야 한다
And 모든 핵심 모듈은 90% 이상이어야 한다
```

---

## AC-004: 설정 관리

### Feature: Pydantic Settings

**Scenario: 환경 변수 로딩**
```gherkin
Given .env 파일이 존재함
When 애플리케이션이 시작됨
Then Settings 클래스가 환경 변수를 로드해야 한다
And 타입 변환이 자동으로 수행되어야 한다
And 필수 값이 누락된 경우 ValidationError가 발생해야 한다
```

**Scenario: 개발/운영 환경 분리**
```gherkin
Given dev와 prod 환경이 존재함
When 각 환경에서 애플리케이션이 시작됨
Then 각 환경에 맞는 설정이 로드되어야 한다
And dev에서는 DEBUG 레벨 로그가 활성화되어야 한다
And prod에서는 INFO 레벨 로그가 활성화되어야 한다
```

---

## AC-005: ZhipuAI GLM-5/4.6V 마이그레이션

### Feature: Structured Outputs

**Scenario: TradingDecision 파싱**
```gherkin
Given GLM-5 API가 호출됨
When response_format이 TradingDecision schema로 설정됨
Then 응답은 파이썬 객체로 자동 파싱되어야 한다
And decision 필드는 "buy", "sell", "hold" 중 하나여야 한다
And percentage 필드는 0-100 범위여야 한다
And JSON 파싱 에러가 발생하지 않아야 한다
```

**Scenario: 비용 절감 확인**
```gherkin
Given gpt-4-turbo-preview에서 GLM-5로 마이그레이션됨
When 동일한 입력으로 API 호출됨
Then GLM-5의 token 사용량이 더 적어야 한다
And 응답 품질이 저하되지 않아야 한다
```

---

## AC-006: 에러 Handling

### Feature: Custom Exception 계층

**Scenario: Upbit API 에러**
```gherkin
Given Upbit API 호출이 실행됨
When 429 Too Many Requests 응답 수신
Then UpbitRateLimitError가 발생해야 한다
And 에러 메시지에 retry_after 정보가 포함되어야 한다
```

**Scenario: 재시도 정책**
```gherkin
Given 일시적인 네트워크 에러가 발생함
When Tenacity 재시도 정책이 적용됨
Then 요청이 최대 3회 재시도되어야 한다
And 재시도 간격은 지수 백오프로 증가해야 한다
```

### Feature: Circuit Breaker

**Scenario: 연속 실패 시 서킷 오픈**
```gherkin
Given 외상 API가 5회 연속 실패함
When Circuit Breaker가 적용됨
Then 서킷이 OPEN 상태로 전환되어야 한다
And 이후 요청은 즉시 거부되어야 한다
And 60초 후 HALF_OPEN 상태로 전환되어야 한다
```

---

## AC-007: 의존성 주입

### Feature: DI 컨테이너

**Scenario: Mock 주입 용이성**
```gherkin
Given 테스트 환경에서 UpbitClient가 필요함
When DI 컨테이너에서 MockUpbitClient로 대체됨
Then 애플리케이션은 Mock을 사용해야 한다
And 실제 API 호출이 발생하지 않아야 한다
```

**Scenario: Singleton Lifecycle**
```gherkin
Given HttpClient가 Singleton으로 설정됨
When 여러 서비스에서 HttpClient가 주입됨
Then 모든 주입은 동일한 인스턴스를 참조해야 한다
```

---

## AC-008: 컨테이너화 및 배포

### Feature: Docker Multi-stage Build

**Scenario: 최적화된 이미지 크기**
```gherkin
Given Dockerfile이 multi-stage로 작성됨
When docker build가 실행됨
Then 최종 이미지 크기는 200MB 이하여야 한다
And 런타임 이미지에는 Python만 포함되어야 한다
```

**Scenario: CI/CD 파이프라인**
```gherkin
Given GitHub Actions workflow가 구성됨
When Pull Request가 생성됨
Then 다음 작업이 자동 실행되어야 한다:
  - Linting (ruff)
  - Type checking (mypy)
  - Unit tests
  - Integration tests
And 모든 작업 통과 시 merge가 허용되어야 한다
```

---

## AC-009: Observability

### Feature: Metrics

**Scenario: Prometheus Metrics**
```gherkin
Given /metrics 엔드포인트가 노출됨
When Prometheus가 scraping을 실행함
Then 다음 지표가 포함되어야 한다:
  | 지표 | 타입 | 설명 |
  | trading_decisions_total | Counter | 총 트레이딩 결정 수 |
  | api_requests_duration_seconds | Histogram | API 요청 소요 시간 |
  | glm_tokens_used_total | Counter | 사용된 총 토큰 수 |
  | errors_total | Counter | 총 에러 발생 수 |
```

### Feature: Distributed Tracing

**Scenario: OpenTelemetry Tracing**
```gherkin
Given 트레이딩 사이클이 실행됨
When distributed tracing이 활성화됨
Then 다음 span이 생성되어야 한다:
  - fetch_news_data
  - fetch_chart_data
  - analyze_with_glm
  - execute_trade
And 각 span에는 태그와 로그가 포함되어야 한다
```

---

## AC-010: 보안

### Feature: Secrets Management

**Scenario: API 키 암호화**
```gherkin
Given API 키가 저장소에 저장됨
When 키가 저장됨
Then rest는 평문이 아닌 암호화 형태여야 한다
And 실행 시에만 복호화되어야 한다
```

**Scenario: 민감 정보 마스킹**
```gherkin
Given 로그에 API 키 포함 필요 상황
When 로그가 기록됨
Then API 키는 "****" 형태로 마스킹되어야 한다
And 원본 키는 로그에 포함되지 않아야 한다
```

---

## AC-011: 성능

### Feature: Response Time

**Scenario: API 응답 시간**
```gherkin
Given 트레이딩 결정 API가 호출됨
When 모든 데이터 수집이 완료됨
Then 전체 응답 시간(p95)은 2초 이하여야 한다
```

**Scenario: Throughput**
```gherkin
Given 시스템이 정상 운영 중임
When 동시에 10개의 트레이딩 결정 요청이 도착함
Then 모든 요청이 5초 내에 처리되어야 한다
```

---

## AC-012: 데이터베이스

### Feature: Database Abstraction

**Scenario: Repository Pattern**
```gherkin
Given TradingDecision 데이터를 저장해야 함
When Repository.save()가 호출됨
Then 저장소 종류(SQLite, PostgreSQL)와 무관하게 저장되어야 한다
And 동일한 인터페이스로 조회가 가능해야 한다
```

**Scenario: Migration**
```gherkin
Given 데이터베이스 스키마 변경 필요함
When migration 스크립트가 실행됨
Then 기존 데이터는 보존되어야 한다
And rollback이 가능해야 한다
```

---

## AC-013: 멀티 코인 지원

### Feature: 암호화폐 선택

**Scenario: 코인 전환**
```gherkin
Given 사용자가 설정 페이지에 있음
When ETH 코인을 선택함
Then 시스템은 KRW-ETH 티커로 데이터 수집을 전환해야 한다
And 기존 BTC 포트폴리오 데이터는 보존되어야 한다
And 새로운 ETH 차트가 표시되어야 한다
```

**Scenario: 지원 코인 목록**
```gherkin
Given 시스템이 시작됨
When 사용자가 코인 선택 드롭다운을 클릭함
Then 다음 코인이 표시되어야 한다:
  | 코인 | 티커 |
  | Bitcoin | KRW-BTC |
  | Ethereum | KRW-ETH |
  | Solana | KRW-SOL |
  | Ripple | KRW-XRP |
  | Cardano | KRW-ADA |
```

**Scenario: 코인별 데이터 수집**
```gherkin
Given ETH가 선택됨
When 데이터 수집이 실행됨
Then 업비트 API에서 ETH OHLCV 데이터가 수집되어야 한다
And ETH 기술적 지표가 계산되어야 한다
And ETH 오더북 데이터가 수집되어야 한다
```

---

## AC-014: 거래전략 선택

### Feature: 전략 관리

**Scenario: 전략 전환**
```gherkin
Given 사용자가 Conservative 전략을 사용 중임
When Aggressive 전략으로 전환함
Then 시스템은 instructions_v3.md를 로드해야 한다
And RSI 임계값이 35/70으로 변경되어야 한다
And 최대 매수 비율이 50%로 변경되어야 한다
```

**Scenario: 전략별 제한**
```gherkin
Given Conservative 전략이 적용됨
When GPT가 40% 매수를 권장함
Then 시스템은 이를 20%로 제한해야 한다
And 사용자에게 전략 제한 알림을 표시해야 한다
```

**Scenario: 전략 설정 영속성**
```gherkin
Given 사용자가 Balanced 전략을 선택함
When 애플리케이션이 재시작됨
Then 이전에 선택한 Balanced 전략이 로드되어야 한다
And 해당 Instruction 파일이 사용되어야 한다
```

---

## AC-015: Instruction 파일 시스템

### Feature: Instruction 버전 관리

**Scenario: Instruction 파일 로딩**
```gherkin
Given 시스템이 시작됨
When 전략이 선택됨
Then 해당 전략의 Instruction 파일이 로드되어야 한다
And GPT 시스템 프롬프트에 적용되어야 한다
```

**Scenario: Instruction 파일 구조**
```gherkin
Given instructions/ 디렉토리가 존재함
When 파일 구조를 확인함
Then 다음 파일들이 존재해야 한다:
  - instructions/strategies/conservative.md
  - instructions/strategies/balanced.md
  - instructions/strategies/aggressive.md
  - instructions/modules/technical_analysis.md
  - instructions/modules/sentiment_analysis.md
```

**Scenario: 동적 Instruction 조합**
```gherkin
Given 사용자가 BTC + Aggressive를 선택함
When Instruction을 로드함
Then base.md + aggressive.md + btc.md가 결합되어야 한다
And 기술적 분석 모듈이 포함되어야 한다
And 공포탐욕지수 모듈이 포함되어야 한다
```

---

## AC-016: GLM-4.6V Vision 차트 분석

### Feature: 차트 이미지 분석

**Scenario: 차트 이미지 생성**
```gherkin
Given 트레이딩 사이클이 시작됨
When 차트 데이터가 준비됨
Then matplotlib/mplfinance로 차트 이미지가 생성되어야 한다
And 이미지는 /tmp/charts/ 디렉토리에 저장되어야 한다
And 이미지 크기는 1MB 이하여야 한다
```

**Scenario: Vision API 호출**
```gherkin
Given 차트 이미지가 생성됨
When GLM-4.6V Vision API가 호출됨
Then 이미지가 base64로 인코딩되어야 한다
And chat.completions.create에 image_url 타입으로 전달되어야 한다
And 응답은 ChartAnalysis 모델로 파싱되어야 한다
```

**Scenario: Vision Fallback**
```gherkin
Given 차트 이미지 생성에 실패함
When GLM-5 API가 호출됨 (텍스트만)
Then 텍스트 기반 분석만 수행되어야 한다
And 로그에 Vision 미사용 이유가 기록되어야 한다
```

---

## AC-017: YouTube 인사이트 통합

### Feature: 학습 자료 참조

**Scenario: YouTube 자막 추출**
```gherkin
Given YouTube 동영상 URL이 제공됨
When 자막 추출이 요청됨
Then youtube-transcript-api가 호출되어야 한다
And 한국어/영어 자막이 추출되어야 한다
And 텍스트 포맷으로 반환되어야 한다
```

**Scenario: 핵심 패턴 추출**
```gherkin
Given YouTube 자막 텍스트가 있음
When GLM-5로 요약을 요청함
Then AI 활용 패턴이 추출되어야 한다
And 코드 예시가 포함될 수 있음
And 한국어로 요약되어야 한다
```

---

## AC-018: 포트폴리오 다각화

### Feature: 멀티 코인 포트폴리오

**Scenario: 코인별 잔고 추적**
```gherkin
Given 사용자가 BTC와 ETH를 보유 중임
When 포트폴리오 조회를 요청함
Then 각 코인별 잔고가 표시되어야 한다:
  | 코인 | 수량 | 평균매수가 | 현재가 | 수익률 |
  | BTC | 0.05 | 95,000,000 | 96,000,000 | +1.05% |
  | ETH | 1.2 | 3,500,000 | 3,600,000 | +2.86% |
```

**Scenario: 전체 포트폴리오 가치**
```gherkin
Given 멀티 코인 포트폴리오가 있음
When 전체 가치를 계산함
Then KRW 총 가치가 계산되어야 한다
And 코인별 비중이 백분율로 표시되어야 한다
```

---

## AC-019: 백테스팅

### Feature: 전략 성능 검증

**Scenario: 과거 데이터 백테스팅**
```gherkin
Given 1년치 과거 OHLCV 데이터가 있음
When Conservative 전략으로 백테스팅을 실행함
Then 다음 지표가 계산되어야 한다:
  - 총 수익률
  - 최대 낙폭 (MDD)
  - 승률
  - 샤프 비율
```

**Scenario: 전략 비교**
```gherkin
Given Conservative와 Aggressive 전략이 있음
When 동일 기간 백테스팅을 실행함
Then 두 전략의 성능이 비교 표로 표시되어야 한다
And 더 나은 전략이 추천되어야 한다
```

---

## AC-020: 위험 관리 고도화

### Feature: 일일 손실 한도

**Scenario: 손실 한도 도달**
```gherkin
Given 일일 손실 한도가 -5%로 설정됨
When 당일 손실이 -5%에 도달함
Then 모든 매도 포지션이 정지되어야 한다
And 사용자에게 알림이 발송되어야 한다
And 다음 날까지 자동 거래가 중단되어야 한다
```

**Scenario: 코인별 손실 한도**
```gherkin
Given ETH 일일 손실 한도가 -3%임
When ETH 손실이 -3%에 도달함
Then ETH 거래만 정지되어야 한다
And BTC 거래는 계속되어야 한다
```

---

**문서 이력**:
- 2026-03-02: 초안 작성 (MoAI Orchestrator)
- 2026-03-02: AC-013~020 추가 (멀티 코인, 전략, Vision, 백테스팅)
- 2026-03-02: GPT → GLM 모델 마이그레이션 반영 (ZhipuAI GLM-5/4.6V)
