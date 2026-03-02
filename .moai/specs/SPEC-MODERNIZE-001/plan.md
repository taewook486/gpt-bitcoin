# 실행 계획 (Execution Plan)

**SPEC ID**: SPEC-MODERNIZE-001
**생성일**: 2026-03-02
**예상 기간**: 8-12주

---

## Phase별 상세 일정

### Phase 1: 기반 재구성 (주 1-2)

**주요 목표**: Characterization tests + Async 기반 확립

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| Characterization tests 작성 | autotrade_v2.py 동작 캡처 | 2일 | High |
| Async 아키텍처 설계 | Layered architecture 정의 | 1일 | High |
| 프로젝트 구조 재구성 | src/ 디렉토리 구조 생성 | 1일 | High |
| Structlog 도입 | print → logger 변환 | 2일 | High |
| Pydantic-settings 구현 | Settings 클래스 작성 | 1일 | High |

**완료 기준**:
- [x] Characterization tests 통과
- [x] JSON 로그 출력 확인
- [x] 설정 파일 로딩 성공

---

### Phase 2: 핵심 기능 현대화 (주 3-5)

**주요 목표**: GLM-5/4.6V 마이그레이션 + DI 도입

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| ZhipuAI GLM 클라이언트 리팩토링 | GLM-5/4.6V + Structured Outputs | 2일 | High |
| Upbit 클라이언트 비동기화 | aiohttp 기반 재작성 | 2일 | High |
| DI 컨테이너 구현 | dependency-injector 도입 | 2일 | High |
| Custom exception 계층 | TradingError 기반 클래스 | 1일 | High |
| Tenacity 재시도 로직 | @retry 데코레이터 적용 | 1일 | Medium |
| Circuit breaker 구현 | external API 장애 대응 | 2일 | Medium |

**완료 기준**:
- [x] GLM-5/4.6V API 호출 성공
- [x] TradingDecision 객체 파싱
- [x] DI로 모든 의존성 주입

---

### Phase 3: 테스트 및 품질 (주 6-7)

**주요 목표**: 85% 커버리지 달성

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| Unit tests 작성 | domain, application layer | 3일 | High |
| Integration tests | external API mocking | 2일 | High |
| Test fixtures 개선 | conftest.py 확장 | 1일 | Medium |
| Coverage gap 해소 | 미달 커버리지 영역 테스트 | 2일 | High |
| Load tests | locust 기반 성능 테스트 | 1일 | Medium |

**완료 기준**:
- [x] 85%+ 커버리지
- [x] 모든 테스트 통과
- [x] CI에서 자동 실행

---

### Phase 4: 운영 준비 (주 8-9)

**주요 목표**: 컨테이너화 + CI/CD

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| Dockerfile 작성 | multi-stage build | 1일 | High |
| docker-compose.yml | local dev 환경 | 1일 | High |
| GitHub Actions workflow | CI/CD 파이프라인 | 2일 | High |
| OpenTelemetry integration | tracing, metrics | 2일 | Medium |
| Health check endpoint | /health 엔드포인트 | 1일 | Medium |

**완료 기준**:
- [x] Docker 이미지 빌드 성공
- [x] CI/CD 파이프라인 동작
- [x] Metrics 수집 확인

---

### Phase 5: 최적화 및 모니터링 (주 10-12)

**주요 목표**: 성능 최적화 + 대시보드

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| Prometheus 설정 | metrics export | 1일 | Medium |
| Grafana dashboard | monitoring UI | 2일 | Low |
| 알림 시스템 | critical error alert | 1일 | Medium |
| 비용 최적화 | token usage monitoring | 1일 | Low |
| 문서화 | README, API docs | 2일 | Low |

**완료 기준**:
- [x] Grafana 대시보드 구축
- [x] 알림 수신 확인
- [x] 문서 완료

---

## 의존성 그래프

```
Phase 1 (Foundation)
    ↓
Phase 2 (Core Modernization)
    ↓
Phase 3 (Testing & Quality)
    ↓
Phase 4 (Production Readiness)
    ↓
Phase 5 (Optimization)
```

**병렬 실행 가능**:
- Phase 4의 CI/CD와 Phase 3의 일부 테스트는 병렬 가능
- Phase 5의 문서화는 Phase 4부터 시작 가능

---

## 리스크 완화 계획

| 위험 | 영향 | 완화 조치 |
|------|------|----------|
| Async migration 복잡도 | High | Phased approach, rollback plan |
| GLM API 호환성 | Medium | 버전 locking, abstraction layer |
| 일정 지연 | Medium | Buffer week 포함, MVP 우선 |
| 테스트 커버리지 부족 | Low | Coverage gap 분석, focus on critical paths |

---

## 성공 모니터링

### 주간 체크리스트

- [ ] Characterization tests 통과?
- [ ] JSON 로그 출력 확인?
- [ ] API 호출 성공?
- [ ] 테스트 커버리지 증가?
- [ ] Code review 완료?

### 마일스톤

| 주차 | 마일스톤 | 확인 방법 |
|------|----------|----------|
| 2 | 기반 완료 | Characterization tests pass |
| 5 | 현대화 완료 | GLM-5/4.6V + DI 동작 |
| 7 | 품질 달성 | 85%+ coverage |
| 9 | 배포 준비 | Docker + CI/CD |
| 12 | 최적화 완료 | Production ready |

---

### Phase 6: 멀티 코인/전략 확장 (주 13-15)

**주요 목표**: 다중 코인 및 전략 선택 시스템 구축

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| Cryptocurrency Enum 설계 | 지원 코인 목록 정의 | 1일 | High |
| UserPreferences 모델 | 설정 저장/로드 시스템 | 1일 | High |
| StrategyManager 구현 | 전략 선택 및 Instruction 로딩 | 2일 | High |
| Instruction 파일 모듈화 | 전략별/코인별 파일 분리 | 2일 | High |
| CoinManager 구현 | 멀티 코인 데이터 관리 | 2일 | High |
| 설정 UI (Streamlit) | 코인/전략 선택 인터페이스 | 2일 | Medium |
| 포트폴리오 추적기 | 코인별 잔고 관리 | 1일 | Medium |

**완료 기준**:
- [ ] BTC, ETH, SOL, XRP, ADA 데이터 수집 성공
- [ ] 전략 전환 시 Instruction 파일 자동 로드
- [ ] 사용자 설정 영속성 저장 확인

---

### Phase 7: GLM-4.6V Vision 통합 (주 16-17)

**주요 목표**: 차트 이미지 분석 기능 구현

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| 차트 이미지 생성 | mplfinance 캔들스틱 차트 | 1일 | High |
| GLM-4.6V Vision API 통합 | 이미지 분석 요청 | 1일 | High |
| ChartAnalysis 모델 | Structured Output 스키마 | 1일 | High |
| Vision + Text 결합 | 분석 결과 통합 로직 | 2일 | High |
| Fallback 처리 | 이미지 없는 환경 대응 | 1일 | Medium |
| YouTube 학습 적용 | Vision 패턴 적용 | 1일 | Medium |

**완료 기준**:
- [ ] 차트 이미지 분석 결과 수신
- [ ] Vision 분석이 텍스트 분석 보완
- [ ] 이미지 없이도 정상 동작

---

### Phase 8: 백테스팅 및 검증 (주 18-19)

**주요 목표**: 전략 성능 검증 시스템

| 작업 | 상세 | 예상 시간 | 우선순위 |
|------|------|----------|----------|
| 백테스팅 엔진 | 과거 데이터 기반 시뮬레이션 | 3일 | High |
| 성능 메트릭 | Sharpe Ratio, MDD, Win Rate | 1일 | High |
| 전략 비교 리포트 | 전략별 성과 비교 | 2일 | Medium |
| Paper Trading | 실시간 모의 거래 | 2일 | High |
| 위험 한도 시스템 | 일일 손실 제한 | 1일 | High |

**완료 기준**:
- [ ] 1년 과거 데이터 백테스팅
- [ ] 전략별 성과 비교 가능
- [ ] Paper Trading 모드 정상 동작

---

## 확장된 의존성 그래프

```
Phase 1 (Foundation)
    ↓
Phase 2 (Core Modernization)
    ↓
Phase 3 (Testing & Quality)
    ↓
Phase 4 (Production Readiness)
    ↓
Phase 5 (Optimization)
    ↓
Phase 6 (Multi-coin/Strategy)  ← NEW
    ↓
Phase 7 (GLM-4.6V Vision)      ← NEW
    ↓
Phase 8 (Backtesting)          ← NEW
```

**병렬 실행 가능 (NEW)**:
- Phase 6의 UI 작업과 Phase 7의 Vision 작업은 병렬 가능
- Phase 7의 YouTube 학습은 Phase 6부터 시작 가능
- Phase 8의 백테스팅 엔진은 Phase 5부터 병렬 개발 가능

---

## Instruction 파일 마이그레이션 계획

### 기존 파일 → 모듈화 구조

| 기존 파일 | 새 구조 | 비고 |
|----------|---------|------|
| instructions.md | instructions/current/balanced.md | 기존 v1 유지 |
| instructions_v2.md | instructions/current/aggressive.md | 공포탐욕지수 포함 |
| instructions_v3.md | instructions/current/vision_aggressive.md | Vision + ROI 포함 |

### 새 파일 생성

```
instructions/
├── base.md                    # 공통 기본 템플릿
├── current/
│   ├── conservative.md        # 신규: 보수적 전략
│   ├── balanced.md           # v1 기반
│   └── aggressive.md         # v2 기반
├── coins/
│   ├── btc.md                # BTC 특화
│   ├── eth.md                # ETH 특화
│   └── altcoin.md            # 알트코인 일반
└── modules/
    ├── technical_analysis.md
    ├── sentiment_analysis.md
    └── chart_vision.md
```

---

## 성공 모니터링 (확장)

### 주간 체크리스트 (NEW)

- [ ] 멀티 코인 데이터 수집 성공?
- [ ] 전략 전환 정상 동작?
- [ ] Vision API 호출 성공?
- [ ] 백테스팅 결과 신뢰성?
- [ ] Paper Trading 손익 확인?

### 마일스톤 (확장)

| 주차 | 마일스톤 | 확인 방법 |
|------|----------|----------|
| 15 | 멀티 코인/전략 완료 | 5개 코인 + 3개 전략 동작 |
| 17 | Vision 통합 완료 | 차트 분석 결과 확인 |
| 19 | 백테스팅 완료 | 1년치 시뮬레이션 결과 |

---

**문서 이력**:
- 2026-03-02: 초안 작성 (MoAI Orchestrator)
- 2026-03-02: Phase 6-8 추가 (멀티 코인, Vision, 백테스팅)
- 2026-03-02: GPT → GLM 모델 마이그레이션 반영 (ZhipuAI GLM-5/4.6V)
