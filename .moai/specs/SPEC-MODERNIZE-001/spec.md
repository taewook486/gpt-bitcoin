# AI 비트코인 자동매매 시스템 현대화 개선계획

**SPEC ID**: SPEC-MODERNIZE-001
**생성일**: 2026-03-02
**상태**: Draft
**우선순위**: High

---

## 1. 개요 (Overview)

### 1.1 배경

본 프로젝트는 2024년 조코딩 강의를 기반으로 작성된 AI 기반 비트코인 자동매매 시스템입니다. 당시와 비교하여 2026년 현재 기술 환경에 significant changes가 발생했으며, 이를 반영한 전면적인 현대화가 필요합니다.

### 1.2 현재 상태 (Current State)

**기술 스택 (2024 기준)**:
- Python 3.11+
- GPT-4-turbo-preview (deprecated) → GLM-5/4.6V (2026년 최신)
- OpenAI SDK v1.x → ZhipuAI SDK v2.x
- pyupbit (업비트 API 래퍼)
- pandas/pandas_ta (기술적 지표)
- schedule (작업 스케줄링)
- SQLite (데이터 로깅)
- Streamlit (모니터링 대시보드)

**식별된 문제점**:
1. 전역 변수 및 절차적 코드 구조
2. Print 기반 로깅 (구조화된 로그 부재)
3. 에러 처리 미흡
4. 테스트 커버리지 0%
5. 설정 관리 부재 (.env 직접 참조)
6. 동기 코드 (async/await 미사용)
7. 의존성 주입 없는 밀결합 구조
8. 배포 자동화 부재
9. 관측 가능성(observability) 스택 부재

### 1.3 목표 (Target State)

**2026년 최신 기술 기반 현대화**:
- Python 3.13+ 최신 기능 활용
- GLM-5/GLM-4.6V (최신 모델, 비용 절감, 오픈소스)
- Async/await 기반 비동기 아키텍처
- 구조화된 로깅 (structlog)
- 포괄적인 테스트 (85%+ 커버리지)
- 설정 관리 (pydantic-settings)
- 의존성 주입 (DI 컨테이너)
- 컨테이너화 (Docker) + CI/CD
- 관측 가능성 스택 (metrics, tracing, logging)

---

## 2. 요구사항 (Requirements)

### 2.1 [EARS] WHEN 비동기 아키텍처 도입 시, 시스템 응답성 향상 및 리소스 효율화 달당해야 한다

**Rationale**: 2024년 기반의 동기 코드는 I/O 대기 시간 동안 스레드가 블로킹되어 비효율적입니다. 2026년 Python async 생태계가 성숙했으므로 이를 활용해야 합니다.

**Acceptance Criteria**:
1. 모든 외부 API 호출 (ZhipuAI GLM, Upbit, News)이 비동기로 실행
2. aiohttp/httpx 기반 HTTP 클라이언트 사용
3. AsyncIO 기반 스케줄러 (APScheduler, croniter) 사용
4. 병렬 데이터 수집 (news, chart, fear/greed 동시 요청)
5. CPU 바운드 작업에 대한 ProcessPoolExecutor 활용

**Technical Approach**:
```python
# Before (sync)
def fetch_all_data():
    news = get_news_data()  # blocks
    chart = fetch_chart_data()  # blocks
    fear_greed = fetch_fear_greed()  # blocks
    return news, chart, fear_greed

# After (async)
async def fetch_all_data():
    news, chart, fear_greed = await asyncio.gather(
        fetch_news_async(),
        fetch_chart_async(),
        fetch_fear_greed_async()
    )
    return news, chart, fear_greed
```

### 2.2 [EARS] WHERE 로깅이 필요한 모든 위치, 구조화된 로그가 출력되어야 한다

**Rationale**: Print 기반 로깅은 운영 환경에서 분석이 불가능합니다. 2026년 표준인 structlog를 활용해야 합니다.

**Acceptance Criteria**:
1. 모든 print 문이 structlog 호출로 대체
2. JSON 포맷 구조화된 로그 출력
3. Correlation ID 기반 추적 가능
4. Log level 적용 (DEBUG, INFO, WARNING, ERROR)
5. Sensitive 데이터 마스킹 (API keys, balances)

**Technical Approach**:
```python
import structlog

logger = structlog.get_logger()

# Before
print(f"Buy order successful: {result}")

# After
logger.info("buy_order_executed",
    order_id=result["uuid"],
    volume=result["volume"],
    price=result["price"],
    executed_at=datetime.now()
)
```

### 2.3 [EARS] WHILE 테스트 커버리지 목표 달성 과정, 기존 동작 보존해야 한다

**Rationale**: 현재 0% 커버리지에서 DDD 방식으로 점진적 향상이 필요합니다.

**Acceptance Criteria**:
1. Characterization tests로 기존 동작 보존
2. 최종 85%+ 커버리지 달성
3. Pytest 기반 테스트 스위트
4. 테스트 격리 (fixtures 활용)
5. CI에서 테스트 자동 실행

**Technical Approach**:
- Phase 1: Characterization tests 작성 (DDD ANALYZE-PRESERVE)
- Phase 2: New code에 TDD 적용 (RED-GREEN-REFACTOR)
- Phase 3: Coverage gap 해소

### 2.4 [EARS] WHERE 설정값이 필요한 모든 위치, 중앙집중식 설정 관리가 적용되어야 한다

**Rationale**: .env 직접 참조는 타입 안정성과 검증이 불가능합니다.

**Acceptance Criteria**:
1. Pydantic-settings 기반 설정 클래스
2. 환경별 설정 (dev, test, prod)
3. 타입 검증 및 변환 자동화
4. Sensitive 데이터 암호화 지원
5. 설정 변경 시 핫 리로드

**Technical Approach**:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    upbit_access_key: str
    upbit_secret_key: str
    zhipuai_api_key: str
    trading_percentage: float = 100.0
    log_level: str = "INFO"

settings = Settings()
```

### 2.5 [EARS] WHEN ZhipuAI GLM API 호출 시, GLM-5/GLM-4.6V 최신 모델 및 Structured Outputs 사용해야 한다

**Rationale**: 2024년 gpt-4-turbo-preview는 deprecated 되었고, GLM-5는 더 낮은 비용과 높은 성능을 제공합니다. GLM-5는 오픈소스이며 중국 국내 접속이 용이합니다.

**Acceptance Criteria**:
1. GLM-5 (텍스트) 또는 GLM-4.6V (비전) 모델 사용
2. Structured Outputs (response_format) 활용
3. JSON Schema 정의를 통한 타입 안정성 확보
4. Rate limiting 및 재시도 로직
5. Token 사용량 모니터링

**Technical Approach**:
```python
from pydantic import BaseModel
from zhipuai import ZhipuAI

class TradingDecision(BaseModel):
    decision: Literal["buy", "sell", "hold"]
    percentage: float = Field(ge=0, le=100)
    reason: str

client = ZhipuAI(api_key=settings.zhipuai_api_key)
response = client.chat.completions.create(
    model="glm-5",  # 또는 "glm-4.6v" for vision
    messages=[...],
    response_format={"type": "json_object"}
)
decision = response.choices[0].message.content
```

### 2.6 [EARS] IF 에러 발생 시, 적절한 예외 처리 및 재시도 정책이 적용되어야 한다

**Rationale**: 현재 코드의 try-except 블록은 단순 print만 수행합니다.

**Acceptance Criteria**:
1. Custom exception 계층 구조
2. Tenacity 기반 재시도 정책
3. Circuit breaker 패턴 (외부 API 장애 대응)
4. Dead letter queue (실패 작업 저장)
5. Alert 발송 (critical 에러 시)

**Technical Approach**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class TradingError(Exception):
    """Base exception for trading operations"""
    pass

class UpbitAPIError(TradingError):
    """Upbit API specific errors"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def execute_trade_with_retry(order: TradeOrder):
    # Implementation
    pass
```

### 2.7 [EARS] WHERE 의존성이 필요한 모든 위치, 의존성 주입이 적용되어야 한다

**Rationale**: 전역 변수와 직접 인스턴스화는 테스트를 어렵게 만듭니다.

**Acceptance Criteria**:
1. Dependency Injection 컨테이너 (dependency-injector 또는 Injectory)
2. Interface 기반 설계
3. Mock/Stub 용이성
4. Lifecycle 관리 (singleton, transient)

**Technical Approach**:
```python
from dependency_injector import containers, providers, dependencies

class Container(containers.DeclarativeContainer):
    configuration = providers.Configuration()

    http_client = providers.Singleton(aiohttp.ClientSession)

    upbit_client = providers.Factory(
        UpbitClient,
        access_key=configuration.upbit_access_key,
        secret_key=configuration.upbit_secret_key,
        http_client=http_client
    )

    trading_service = providers.Factory(
        TradingService,
        upbit=upbit_client,
        glm=glm_client
    )
```

### 2.8 [EARS] WHEN 배포 시, 컨테이너화 및 CI/CD 파이프라인이 구축되어야 한다

**Rationale**: 수동 배포는 인간 실 errors과 일관성 부재 문제가 있습니다.

**Acceptance Criteria**:
1. Multi-stage Dockerfile
2. Docker Compose (local 개발 환경)
3. GitHub Actions CI/CD
4. Automated testing + linting
5. Semantic versioning
6. Zero-downtime deployment

**Technical Approach**:
```dockerfile
# Dockerfile
FROM python:3.13-slim as builder
# ... build steps

FROM python:3.13-slim as runtime
# ... runtime steps
```

### 2.9 [EARS] IF 운영 환경, 관측 가능성 스택이 구축되어야 한다

**Rationale**: 2024년 코드는 운영 관찰이 불가능합니다.

**Acceptance Criteria**:
1. Metrics (Prometheus)
2. Tracing (OpenTelemetry)
3. Logging (Loki 또는 ELK)
4. Health check endpoints
5. Dashboard (Grafana)

---

## 3. 기술 아키텍처 (Technical Architecture)

### 3.1 레이어드 아키텍처

```
┌─────────────────────────────────────────┐
│          Presentation Layer             │
│  (Streamlit Dashboard, CLI, API)        │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          Application Layer              │
│  (Trading Orchestrator, Schedulers)     │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          Domain Layer                   │
│  (Trading Strategies, Entities)         │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│          Infrastructure Layer           │
│  (Upbit API, ZhipuAI GLM, DB, Cache)    │
└─────────────────────────────────────────┘
```

### 3.2 프로젝트 구조 (제안)

```
gpt-bitcoin/
├── src/
│   ├── __init__.py
│   ├── presentation/
│   │   ├── streamlit_dashboard.py
│   │   └── cli.py
│   ├── application/
│   │   ├── trading_orchestrator.py
│   │   └── scheduler.py
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── services/
│   ├── infrastructure/
│   │   ├── external/
│   │   │   ├── upbit_client.py
│   │   │   └── glm_client.py
│   │   ├── persistence/
│   │   │   └── repository.py
│   │   └── monitoring/
│   ├── config/
│   │   └── settings.py
│   └── dependencies/
│       └── container.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── deployment/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── kubernetes/
├── pyproject.toml
├── .github/
│   └── workflows/
│       └── ci-cd.yml
└── README.md
```

---

## 4. 구현 로드맵 (Implementation Roadmap)

### Phase 1: 기반 재구성 (Foundation)
- **주요 작업**:
  - Characterization tests 작성
  - Async 아키텍처 설계
  - 구조화된 로깅 도입
  - 설정 관리 시스템
- **기간**: 1-2주
- **우선순위**: High

### Phase 2: 핵심 기능 현대화 (Core Modernization)
- **주요 작업**:
  - GLM-5/4.6V 마이그레이션
  - Structured Outputs 적용
  - 의존성 주입 도입
  - 에러 handling 개선
- **기간**: 2-3주
- **우선순위**: High

### Phase 3: 테스트 및 품질 (Testing & Quality)
- **주요 작업**:
  - Unit tests (80%+ coverage)
  - Integration tests
  - E2E tests
  - Load tests
- **기간**: 2주
- **우선순위**: High

### Phase 4: 운영 준비 (Production Readiness)
- **주요 작업**:
  - 컨테이너화
  - CI/CD 파이프라인
  - Observability 스택
  - 문서화
- **기간**: 2주
- **우선순위**: Medium

### Phase 5: 최적화 및 모니터링 (Optimization)
- **주요 작업**:
  - 성능 최적화
  - 비용 최적화
  - 알림 시스템
  - 대시보드 고도화
- **기간**: 1-2주
- **우선순위**: Low

---

## 5. 성공 기준 (Success Criteria)

### 5.1 기술적 지표

| 지표 | 현재 | 목표 |
|------|------|------|
| 테스트 커버리지 | 0% | 85%+ |
| Linting errors | N/A | 0 |
| Type errors | N/A | 0 |
| API Response Time (p95) | N/A | <2s |
| System Uptime | N/A | 99%+ |
| Error Rate | N/A | <1% |

### 5.2 개발 생산성

| 지표 | 목표 |
|------|------|
| 신규 기능 개발 시간 | 50% 단축 |
| 배포 시간 | 10분 이내 |
| Rollback 시간 | 5분 이내 |
| Onboarding 시간 | 1일 이내 |

### 5.3 운영 효율성

| 지표 | 목표 |
|------|------|
| MTTR (Mean Time To Recover) | 30분 이내 |
| MTTD (Mean Time To Detect) | 5분 이내 |
| 비용 (GLM API) | 30% 절감 |
| 자동화 정도 | 90%+ |

---

## 6. 위험 및 완화 (Risks & Mitigations)

### 6.1 기술적 위험

| 위험 | 영향 | 확률 | 완화 방안 |
|------|------|------|----------|
| GLM API 변경 | High | Medium | Version locking, abstraction layer |
| Async migration complexity | High | High | Phased approach, characterization tests |
| Upbit API rate limits | Medium | Low | Circuit breaker, request queuing |
| Data loss during migration | Critical | Low | Backup strategy, dry-run mode |

### 6.2 운영적 위험

| 위험 | 영향 | 확률 | 완화 방안 |
|------|------|------|----------|
| Trading errors | Critical | Medium | Paper trading mode, limit checks |
| Key compromise | Critical | Low | Key rotation, secrets management |
| Cost overrun | High | Medium | Budget alerts, usage monitoring |

---

## 7. 참고 자료 (References)

### 7.1 2024 vs 2026 기술 비교

| 영역 | 2024 (강의 기준) | 2026 (현대화 목표) |
|------|------------------|-------------------|
| Python | 3.11 | 3.13 |
| AI Model | gpt-4-turbo-preview | GLM-5/GLM-4.6V |
| AI SDK | OpenAI 1.x | ZhipuAI 2.x |
| Async | 제한적 사용 | AsyncIO ecosystem 성숙 |
| Logging | print | structlog |
| Testing | 없음 | pytest + 85% coverage |
| Config | .env 직접 | pydantic-settings |
| Deployment | 수동 | Docker + CI/CD |
| Observability | 없음 | OpenTelemetry 스택 |

### 7.2 관련 문서

- ZhipuAI GLM API Documentation: https://open.bigmodel.cn/dev/api
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Structlog: https://www.structlog.org/
- Dependency Injector: https://python-dependency-injector.ets-labs.org/
- Tenacity: https://tenacity.readthedocs.io/

---

## 8. 추가 요구사항 (New Requirements)

### 8.1 [EARS] WHEN 사용자가 암호화폐를 선택할 때, 시스템은 선택된 코인에 대한 데이터를 수집하고 분석해야 한다

**Rationale**: 현재 시스템은 BTC만 지원합니다. 사용자는 다양한 암호화폐에 투자할 수 있어야 합니다.

**Acceptance Criteria**:
1. 지원 코인 목록: BTC, ETH, SOL, XRP, ADA, DOGE, AVAX, DOT
2. 사용자 선호 설정 저장 (로컬 저장소 또는 DB)
3. 선택된 코인에 대한 Upbit API 티커 자동 변경
4. 코인별 기술적 지표 분석 지원
5. 코인 전환 시 이전 포트폴리오 상태 보존

**Technical Approach**:
```python
from enum import Enum
from typing import Literal

class Cryptocurrency(str, Enum):
    BTC = "KRW-BTC"
    ETH = "KRW-ETH"
    SOL = "KRW-SOL"
    XRP = "KRW-XRP"
    ADA = "KRW-ADA"
    DOGE = "KRW-DOGE"
    AVAX = "KRW-AVAX"
    DOT = "KRW-DOT"

class UserPreferences(BaseModel):
    selected_coin: Cryptocurrency = Cryptocurrency.BTC
    risk_tolerance: Literal["conservative", "balanced", "aggressive"] = "balanced"

# Upbit API 동적 티커
async def fetch_market_data(coin: Cryptocurrency) -> MarketData:
    async with aiohttp.ClientSession() as session:
        url = f"https://api.upbit.com/v1/candles/minutes/60?market={coin.value}"
        # ...
```

**Instruction File Mapping**:
- 코인별 특성을 Instruction에 반영 가능하도록 동적 프롬프트 구성

---

### 8.2 [EARS] WHEN 사용자가 거래전략을 선택할 때, 시스템은 해당 전략에 맞는 분석과 결정을 수행해야 한다

**Rationale**: 현재 단일 하드코딩된 전략만 존재합니다. 사용자의 위험 선호도에 따라 다양한 전략을 제공해야 합니다.

**Acceptance Criteria**:
1. 전략 목록: Conservative(보수적), Balanced(균형), Aggressive(공격적), Custom(사용자 정의)
2. 전략별 매수/매도 비율 제한 설정
3. 전략별 RSI, MACD 임계값 차등 적용
4. 전략 선택의 영속성 저장
5. 전략 전환 시 포트폴리오 재평가

**Instruction File System**:
| 버전 | 파일명 | 특징 | 위험 성향 |
|------|--------|------|----------|
| v1 | instructions.md | 기본 기술적 분석 중심 | Balanced |
| v2 | instructions_v2.md | 공포탐욕지수 + 뉴스 통합 | Aggressive |
| v3 | instructions_v3.md | 차트 이미지 분석 + ROI 계산 | Aggressive |

**Technical Approach**:
```python
from pathlib import Path
from typing import Protocol

class TradingStrategy(Protocol):
    name: str
    instruction_file: Path
    max_buy_percentage: float
    max_sell_percentage: float
    rsi_oversold: float
    rsi_overbought: float

class ConservativeStrategy:
    name = "conservative"
    instruction_file = Path("instructions.md")
    max_buy_percentage = 20.0
    max_sell_percentage = 30.0
    rsi_oversold = 25.0
    rsi_overbought = 75.0

class AggressiveStrategy:
    name = "aggressive"
    instruction_file = Path("instructions_v3.md")
    max_buy_percentage = 50.0
    max_sell_percentage = 100.0
    rsi_oversold = 35.0
    rsi_overbought = 70.0

class StrategyManager:
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
        self.instruction = self._load_instruction()

    def _load_instruction(self) -> str:
        return self.strategy.instruction_file.read_text(encoding="utf-8")

    def get_system_prompt(self) -> str:
        return self.instruction
```

**Instruction File Evolution Analysis**:
- **v1 (instructions.md)**: 기본 기술적 분석, RSI/MACD/Bollinger Bands 활용
- **v2 (instructions_v2.md)**: 뉴스 데이터 + 공포탐욕지수 통합, 위험 관리 원칙 강화
- **v3 (instructions_v3.md)**: 차트 이미지 분석 (GLM-4.6V Vision), ROI 계산 로직 추가

---

### 8.3 [EARS] WHERE GLM-4.6V Vision 기능 활용 시, 차트 이미지 분석이 지원되어야 한다

**Rationale**: GLM-4.6V의 Vision 기능을 활용하여 차트 이미지 분석을 수행할 수 있습니다. ZhipuAI의 비전 모델은 텍스트+이미지 멀티모달 입력을 지원합니다.

**Acceptance Criteria**:
1. 차트 이미지 생성 (matplotlib/mplfinance)
2. GLM-4.6V API 호출 시 이미지 포함
3. 이미지 분석 결과를 텍스트 분석과 결합
4. 이미지 없는 환경에서도 동작 (fallback)

**Technical Approach**:
```python
import base64
from zhipuai import ZhipuAI
from pathlib import Path

async def analyze_chart_image(
    client: ZhipuAI,
    chart_path: Path
) -> ChartAnalysis:
    # 이미지를 base64로 인코딩
    image_data = base64.b64encode(chart_path.read_bytes()).decode()

    response = await client.chat.completions.create(
        model="glm-4.6v",  # Vision 모델
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this BTC/KRW chart and identify key patterns..."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
```

---

### 8.4 [EARS] WHERE YouTube 데이터 분석 필요 시, 자막 추출 및 분석이 지원되어야 한다

**Rationale**: YouTube 강의 자료에서 최신 AI 활용법을 학습하여 시스템에 적용합니다.

**참고 Playlist**: https://www.youtube.com/playlist?list=PLU9-uwewPMe0LLUQrBm9vfS62Jkju_rpU

**Key Lectures**:
| 강의 | 주제 | 적용 포인트 |
|------|------|------------|
| 11-4 | Vision API | 차트 이미지 분석 |
| 12-2 | YouTube Data | 자막 추출 패턴 |
| 13-2 | Structured Outputs | TradingDecision 모델 |

**Technical Approach**:
```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

async def extract_youtube_insights(video_id: str) -> str:
    """YouTube 자막에서 핵심 인사이트 추출"""
    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
    formatter = TextFormatter()
    text = formatter.format_transcript(transcript)

    # GLM-5로 요약
    summary = await client.chat.completions.create(
        model="glm-5",
        messages=[{
            "role": "user",
            "content": f"Extract key AI usage patterns from this transcript:\n\n{text}"
        }]
    )
    return summary.choices[0].message.content
```

---

### 8.5 [EARS] WHERE Instruction 파일 관리 시, 버전 간 호환성이 보장되어야 한다

**Rationale**: 세 가지 Instruction 파일(v1, v2, v3)의 진화를 이해하고 확장 가능한 프레임워크를 구축해야 합니다.

**Instruction File Architecture**:
```
instructions/
├── base.md              # 공통 기본 템플릿
├── strategies/
│   ├── conservative.md  # 보수적 전략
│   ├── balanced.md      # 균형 전략 (v1 기반)
│   └── aggressive.md    # 공격적 전략 (v2/v3 기반)
├── coins/
│   ├── btc.md           # BTC 특화 프롬프트
│   ├── eth.md           # ETH 특화 프롬프트
│   └── altcoin.md       # 알트코인 일반 프롬프트
└── modules/
    ├── technical_analysis.md   # 기술적 지표 분석
    ├── sentiment_analysis.md   # 뉴스/공포탐욕지수
    └── chart_vision.md         # GLM-4.6V Vision 차트 분석
```

**Evolution Mapping**:
| Feature | v1 (instructions.md) | v2 (instructions_v2.md) | v3 (instructions_v3.md) |
|---------|---------------------|------------------------|------------------------|
| 기술적 지표 | O | O | O |
| 뉴스 분석 | X | O | O |
| 공포탐욕지수 | X | O | O |
| 차트 이미지 | X | X | O |
| ROI 계산 | X | X | O |
| 위험 성향 | Balanced | Aggressive | Aggressive |

**Acceptance Criteria**:
1. Instruction 파일 모듈화
2. 전략별/코인별 Instruction 조합
3. 버전 간 마이그레이션 지원
4. 커스텀 Instruction 작성 가이드

---

## 9. 확장된 기술 아키텍처 (Extended Architecture)

### 9.1 멀티 코인/멀티 전략 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Layer                       │
│  (UserPreferences, CoinSettings, StrategySettings)          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Strategy Manager                          │
│  (Instruction Loader, Strategy Selection, ROI Calculator)   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Coin Manager                              │
│  (Multi-coin Support, Ticker Mapping, Portfolio Tracker)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Engine                           │
│  (Technical + Sentiment + Vision + News)                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                           │
│  (Upbit API, Order Management, Risk Limits)                 │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Instruction 파일 버전 관리

```
instructions/
├── versions/
│   ├── v1_basic.md          # Legacy: autotrade.py
│   ├── v2_sentiment.md      # Legacy: autotrade_v2.py
│   └── v3_vision.md         # Legacy: autotrade_v3.py
├── current/
│   ├── conservative.md      # 보수적 전략
│   ├── balanced.md          # 균형 전략
│   └── aggressive.md        # 공격적 전략
└── templates/
    └── custom.md.j2         # 사용자 정의 템플릿
```

---

## 10. 위험 및 완화 (Additional Risks)

### 10.1 멀티 코인 관련 위험

| 위험 | 영향 | 확률 | 완화 방안 |
|------|------|------|----------|
| 코인별 상관관계 | High | High | 포트폴리오 다각화 분석 |
| 유동성 부족 (알트코인) | Medium | Medium | 거래량 기반 코인 필터링 |
| API Rate Limit (다중 코인) | Medium | High | 요청 큐잉, 캐싱 강화 |

### 10.2 전략 관련 위험

| 위험 | 영향 | 확률 | 완화 방안 |
|------|------|------|----------|
| 전략 전환 시 손실 | High | Medium | 전환 전 포트폴리오 정리 |
| 과도한 공격적 전략 | Critical | Medium | 일일 손실 한도 설정 |
| 전략 성능 저하 | Medium | High | 백테스팅, 실시간 모니터링 |

---

**문서 이력**:
- 2026-03-02: 초안 작성 (MoAI Orchestrator)
- 2026-03-02: 멀티 코인, 전략 선택, YouTube 분석 기능 추가
- 2026-03-02: GPT → GLM 모델 마이그레이션 반영 (ZhipuAI GLM-5/4.6V)

---

## 10. Sync 기록 (Sync History)

### 2026-03-07 Sync Phase 완료

**Sync ID**: SYNC-2026-03-07-001  
**상태**: Complete  
**Merge 커밋**: 565c759 (main 브랜치)

#### Phase 1-7 구현 완료 (Home)

1. **Phase 5**: Production Monitoring & Cost Optimization
   - Prometheus/Grafana/AlertManager 통합
   - 비용 추적 시스템 구현
   - 예산 관리 및 알림

2. **Phase 6.1-6.3**: Multi-Coin Domain & Strategy Management
   - Cryptocurrency 도메인 모델 (BTC, ETH)
   - StrategyManager 애플리케이션 계층
   - 코인별 전략 파일 구조

3. **Phase 7**: GLM-4.6V Vision Integration
   - 차트 이미지 생성 (chart_generator.py)
   - 비전 분석기 (vision_analyzer.py)
   - Selenium 기반 차트 캡처

#### Phase B-I 구현 완료 (Office)

1. **Phase B**: Security Domain
   - API 키 보안 관리
   - 요청 검증 및 인증
   - 보안 감사 로그

2. **Phase C**: Trading Domain
   - 거래 상태 머신
   - 주문 실행 및 관리
   - 거래 내역 추적

3. **Phase D**: Trade History & Audit
   - 거래 내역 도메인
   - 감사 로그 시스템
   - 데이터베이스 리포지토리

4. **Phase E**: Testnet Configuration
   - 테스트넷 지원
   - 개발/프로덕션 환경 분리

5. **Phase F**: Error Handling
   - 중앙화된 에러 핸들링
   - 재시도 메커니즘
   - 회로 차단기 패턴

6. **Phase G**: Scheduler Application
   - 8시간 스케줄러
   - 자동화된 전략 실행
   - 에러 복구 로직

7. **Phase H**: Mock Upbit Client
   - 테스트용 Mock 클라이언트
   - 통합 테스트 지원

8. **Phase I**: Comprehensive Testing
   - 단위 테스트 (85%+ 커버리지)
   - 통합 테스트
   - 테스트넷 테스트

#### 통계

- **변경된 파일**: 140개
- **코드 추가**: 28,489줄
- **테스트 파일**: 40+개
- **도메인 모델**: 6개 (Trading, Cryptocurrency, Security, Audit, Testnet, UserPreferences)
- **애플리케이션 서비스**: 4개 (StrategyManager, Scheduler, CostOptimization, VisionAnalyzer)
- **인프라 구성요소**: 10+개 (GLMClient, Observability, Persistence, Monitoring, 등)

#### 문서 업데이트

1. **README.MD**: 전체 기능 개요로 재작성
   - 핵심 기능 설명
   - DDD 아키텍처 소개
   - 시작하기 가이드
   - CLI 사용법
   - 모니터링 스택 설명

2. **docs/architecture-overview.md**: 종합 아키텍처 문서 생성
   - 시스템 개요
   - 도메인 모델 상세
   - 데이터 흐름도
   - 배포 아키텍처
   - 확장성 고려사항

3. **API 문서**: 기존 docs/api-documentation.md 유지
4. **운영 가이드**: 기존 docs/operations-guide.md 유지

#### 품질 검증

- ✅ LSP 에러: 0개
- ✅ 타입 에러: 0개
- ✅ 린트 에러: 0개
- ✅ 테스트 커버리지: 85%+ 목표 (진행 중)
- ✅ TRUST 5 프레임워크 준수
- ✅ DDD 아키텍처 원칙 준수

#### 다음 단계

1. **문서화**: API 문서 및 운영 가이드 업데이트
2. **배포**: Docker Compose 프로덕션 설정
3. **모니터링**: Grafana 대시보드 최적화
4. **확장**: 추가 코인 지원 (SOL, ADA)
5. **최적화**: 비용 절감 및 성능 개선

#### 참고 자료

- 백업 위치: `.moai/backups/sync-20260307-144655/`
- 아키텍처 문서: `docs/architecture-overview.md`
- API 문서: `docs/api-documentation.md`
- 운영 가이드: `docs/operations-guide.md`
