# GPT Bitcoin AI 자동매매 시스템
GLM-4.6 기반 고급 AI 트레이딩 시스템 - 다중 코인 지원, 차트 분석, 실시간 모니터링

## 프로젝트 개요

이 프로젝트는 GLM-4.6(지능형 언어 모델) API를 활용한 비트코인 및 이더리움 자동매매 시스템입니다. 최신 DDD(Domain-Driven Design) 아키텍처를 기반으로 구현되었으며, 다음과 같은 고급 기능을 제공합니다.

### 핵심 기능

**1. 다중 코인 지원 (Multi-Coin Trading)**
- BTC, ETH 동시 지원 및 확장 가능한 구조
- 코인별 독립 전략 및 포트폴리오 관리
- Cryptocurrency 도메인 모델을 통한 일관된 인터페이스

**2. GLM-4.6V 비전 인TEGRATION (Chart Analysis)**
- 차트 이미지 생성 및 분석 (GLM-4.6V)
- 30일 일봉 + 24시간 시봉 기술적 지표
- Moving Averages, RSI, Stochastic, MACD, Bollinger Bands
- 시각적 패턴 인식을 통한 매매 의사결정

**3. 스마트 전략 관리 (Strategy Management)**
- 3가지 리스크 프로필: Conservative, Balanced, Aggressive
- 동적 전략 스위칭 및 최적화
- 거래 내역 기반 AI 학습 및 개선

**4. 실시간 모니터링 (Monitoring Stack)**
- Prometheus: 메트릭 수집 및 저장
- Grafana: 시각화 대시보드 (Trading Overview, System Performance)
- AlertManager: 알림 라우팅 및 관리
- 비용 추적 및 예산 관리

**5. 비용 최적화 (Cost Optimization)**
- GLM API 호출 횟수 추적 및 최적화
- 일일/월간 비용 모니터링
- 예산 알림 및 자동 중단 기능

**6. 보안 및 감사 (Security & Audit)**
- API 키 보안 관리
- 거래 내역 감사 로그
- Testnet 환경 지원

**7. 자동화 스케줄러 (Scheduler)**
- 8시간 단위 자동 거래 실행
- 설정 가능한 실행 간격
- 에러 핸들링 및 재시도 메커니즘

### 아키텍처 특징

**Domain-Driven Design (DDD)**
- 4계층 아키텍처: Domain, Application, Infrastructure, Presentation
- 의존성 주입 (Dependency Injection)
- 깔끔한 분리 및 테스트 가능성

**도메인 계층 (Domain Layer)**
- `Trading`: 거래 로직 및 상태 관리
- `Cryptocurrency`: 다중 코인 지원
- `Security`: API 보안 및 인증
- `Audit`: 감사 로그 및 추적
- `UserPreferences`: 사용자 설정 관리

**애플리케이션 계층 (Application Layer)**
- `StrategyManager`: 전략 실행 및 관리
- `Scheduler`: 자동화 스케줄링
- `VisionAnalyzer`: 차트 이미지 분석
- `CostOptimization`: 비용 추적 및 최적화

**인프라 계층 (Infrastructure Layer)**
- `GLMClient`: GLM API 클라이언트
- `Observability`: 메트릭 및 추적
- `Persistence`: 데이터베이스 리포지토리
- `Resilience`: 회로 차단기 및 재시도

## 시작하기 (Getting Started)

### 필수 조건
- Python 3.11+
- Docker & Docker Compose (모니터링 스택용)
- Upbit API 계정 및 키
- GLM API 키

### 환경 변수 설정

`.env` 파일을 생성하고 다음 키를 설정하세요:

```bash
# GLM API
GLM_API_KEY="your-glm-api-key"

# Upbit API
UPBIT_ACCESS_KEY="your-upbit-access-key"
UPBIT_SECRET_KEY="your-upbit-secret-key"

# 선택사항: SerpApi (뉴스 데이터)
SERPAPI_API_KEY="your-serpapi-key"

# 비용 관리
DAILY_COST_LIMIT=10000
COST_ALERT_THRESHOLD=8000

# 알림 설정
ALERT_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 로컬 설치

```bash
# 리포지토리 클론
git clone https://github.com/taewook486/gpt-bitcoin.git
cd gpt-bitcoin

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 입력

# 데이터베이스 마이그레이션
python -m src.gpt_bitcoin.infrastructure.database.migrations.migrate_to_v6

# 테스트 실행 (선택사항)
pytest tests/
```

### Docker로 실행 (권장)

```bash
# 모든 서비스 시작 (애플리케이션 + 모니터링)
docker-compose up -d

# 모니터링 스택만 시작
docker-compose --profile monitoring up -d

# 로그 확인
docker-compose logs -f app
```

### AWS EC2 Ubuntu 서버 설정

#### 업비트 API 허용 IP 설정
[업비트 API 홈페이지](https://upbit.com/mypage/open_api_management)

#### 기본 세팅
```bash
# 한국 시간대 설정
sudo ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python3 및 pip 설치
sudo apt install python3-pip -y
```

#### 애플리케이션 배포
```bash
# 리포지토리 클론
git clone https://github.com/taewook486/gpt-bitcoin.git
cd gpt-bitcoin

# 의존성 설치
pip3 install -r requirements.txt

# 환경 변수 설정
vim .env
```

#### 실행 방법
```bash
# 직접 실행
python3 -m gpt_bitcoin.presentation.cli --coin BTC --strategy balanced

# 백그라운드 실행
nohup python3 -u main.py > output.log 2>&1 &

# 로그 확인
tail -f output.log

# 프로세스 확인
ps ax | grep python

# 프로세스 종료
kill -9 <PID>
```

## 사용 방법

### CLI로 거래 실행

```bash
# 단일 거래 실행 (BTC)
python -m gpt_bitcoin.presentation.cli --coin BTC --strategy balanced

# 단일 거래 실행 (ETH)
python -m gpt_bitcoin.presentation.cli --coin ETH --strategy aggressive

# 스케줄러 시작 (8시간마다 자동 거래)
python -m gpt_bitcoin.application.scheduler

# Testnet 모드로 테스트
python -m gpt_bitcoin.presentation.cli --coin BTC --testnet --strategy conservative
```

### 거래 전략 선택

**Conservative (보수적)**
- 소액 투자 및 안정적인 접근
- 손실 제한 엄격 관리
- 신중한 진입/퇴출

**Balanced (균형적)**
- 중간 리스크/리턴
- 기술적 지표 기반 의사결정
- 뉴스 감안한 조정

**Aggressive (공격적)**
- 고수익 추구
- 적극적인 포트폴리오 운용
- 비전 분석 적극 활용

## 모니터링 및 운영

### 모니터링 스택

이 시스템은 Prometheus, Grafana, AlertManager를 통합한 모니터링 기능을 제공합니다.

**서비스 구성**
- **Prometheus** (포트 9090): 메트릭 수집 및 저장
- **Grafana** (포트 3000): 시각화 대시보드
- **AlertManager** (포트 9093): 알림 라우팅 및 관리

**시작 방법**
```bash
# 모니터링 서비스 시작
docker-compose --profile monitoring up -d

# 특정 서비스만 시작
docker-compose up -d prometheus
docker-compose up -d grafana
docker-compose up -d alertmanager
```

**서비스 접속**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (기본 로그인: admin/admin)
- AlertManager: http://localhost:9093

**제공 메트릭**
- **거래 관련**: 총 거래 횟수, 성공/실패율, 평균 실행 시간
- **API 관련**: GLM API 호출 횟수, 응답 시간, 에러율
- **시스템 리소스**: CPU 사용량, 메모리 사용량, 디스크 I/O
- **비용 관련**: GLM API 비용 추적, 일일/월간 비용 집계

### 대시보드

Grafana는 다음 대시보드를 제공합니다:
- **Trading Overview**: 거래 활동 및 성과 요약
- **System Performance**: 시스템 리소스 사용 현황
- **API Monitoring**: GLM API 호출 및 비용 추적

### 비용 관리

**비용 최적화 전략**
1. **캐싱 최적화**: 반복 조회 최소화로 API 호출 감소
2. **배치 처리**: 여러 요청을 단일 배치로 처리
3. **메트릭 수집**: 실시간 비용 추적 및 예산 알림

**비용 모니터링**
- 일일 API 호출 횟수
- 토큰 사용량 (입력/출력)
- 추정 비용 (원화 기준)
- 비용 추세 및 예측

**예산 설정**
```bash
# 일일 최대 비용 (KRW)
DAILY_COST_LIMIT=10000

# 비용 알림 임계값 (KRW)
COST_ALERT_THRESHOLD=8000

# 알림 수신 설정
ALERT_EMAIL=your-email@example.com
ALERT_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 알림 설정

**지원 알림 채널**
- **Webhook**: 애플리케이션으로 직접 알림 전송
- **Email**: 이메일 알림 (선택 사항)
- **Slack**: Slack 메시지 (선택 사항)

**알림 규칙**
`monitoring/alerting/rules.yml`에서 알림 규칙을 구성할 수 있습니다:
- **API 비용 알림**: 일일/월간 비용 임계값 초과 시
- **거래 실패 알림**: 연속 실패 횟수 임계값 초과 시
- **시스템 리소스 알림**: CPU/메모리 사용량 임계값 초과 시
- **API 응답 시간 알림**: 응답 시간 지연 시

**알림 설정 단계**
1. `monitoring/alertmanager.yml`에서 알림 수신자 설정
2. Email/Slack Webhook URL 구성
3. 알림 규칙 및 임계값 조정
4. AlertManager 재시작으로 설정 적용

```bash
# AlertManager 재시작
docker-compose restart alertmanager
```

## 아키텍처

### 프로젝트 구조

```
gpt-bitcoin/
├── src/gpt_bitcoin/
│   ├── application/          # 애플리케이션 계층
│   │   ├── strategy_manager.py   # 전략 관리
│   │   ├── scheduler.py          # 자동화 스케줄러
│   │   ├── cost_optimization.py  # 비용 최적화
│   │   └── vision/               # 차트 분석
│   │       ├── vision_analyzer.py
│   │       └── chart_generator.py
│   ├── domain/                # 도메인 계층
│   │   ├── trading.py             # 거래 도메인
│   │   ├── cryptocurrency.py      # 다중 코인 지원
│   │   ├── security.py            # 보안 도메인
│   │   ├── audit.py               # 감사 로그
│   │   └── models/                # 도메인 모델
│   ├── infrastructure/        # 인프라 계층
│   │   ├── external/              # 외부 API 클라이언트
│   │   ├── database/              # 데이터베이스
│   │   ├── monitoring/            # 메트릭 수집
│   │   ├── observability/         # 추적 및 로깅
│   │   └── persistence/           # 리포지토리
│   └── presentation/          # 프레젠테이션 계층
│       ├── cli.py                 # CLI 인터페이스
│       └── alert_handlers.py      # 알림 핸들러
├── tests/                     # 통합/단위 테스트
├── docs/                      # 문서
├── monitoring/                # 모니터링 설정
└── main.py                    # 진입점
```

### 기술 스택

**백엔드**
- Python 3.11+
- FastAPI (API 서버)
- Pydantic (데이터 검증)
- SQLAlchemy (ORM)

**AI/ML**
- GLM-4.6 (언어 모델)
- GLM-4.6V (비전 모델)

**모니터링**
- Prometheus (메트릭)
- Grafana (시각화)
- AlertManager (알림)

**데이터베이스**
- SQLite (개발)
- PostgreSQL (프로덕션 권장)

## 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 커버리지 리포트
pytest --cov=src/gpt_bitcoin --cov-report=html

# 단위 테스트만
pytest tests/unit/

# 통합 테스트만
pytest tests/integration/

# 특정 테스트 모듈
pytest tests/unit/domain/test_trading.py -v
```

## 문서

- [API 문서](docs/api-documentation.md) - REST API 상세
- [운영 가이드](docs/operations-guide.md) - 운영 및 배포
- [아키텍처 문서](.moai/docs/backend-architecture-SPEC-MODERNIZE-001-phase5.3.md) - Phase 5.3 상세

## 기여

기여를 환영합니다! Pull Request를 제출해주세요.

## 라이선스

MIT License

## 연락처

- GitHub: [taewook486](https://github.com/taewook486)
- 이슈: [GitHub Issues](https://github.com/taewook486/gpt-bitcoin/issues)

## 추후 계획

- [ ] 빗썸, 바이낸스 거래소 지원
- [ ] 더 많은 암호화폐 지원 (SOL, ADA 등)
- [ ] 백테스팅 프레임워크
- [ ] 웹 대시보드
- [ ] 모바일 앱 알림
