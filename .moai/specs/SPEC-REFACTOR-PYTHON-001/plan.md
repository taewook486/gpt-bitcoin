---
spec_id: SPEC-REFACTOR-PYTHON-001
title: Implementation Plan - Legacy Python Code Modernization
created: 2026-03-02
status: Planned
priority: High
---

# Implementation Plan: Legacy Python Code Modernization

## Overview

본 문서는 gpt-bitcoin 자동거래 시스템의 현대화를 위한 단계별 구현 계획을 정의합니다.

---

## Phase 1: Foundation & Dependency Updates

### Primary Goals

- 의존성 버전 고정 및 보안 업데이트
- 프로젝트 구조 재조직
- 개발 환경 표준화

### Tasks

#### 1.1 의존성 관리 현대화

**현재 상태:**
```
python-dotenv
openai
pyupbit
pyjwt
pandas
pandas_ta
schedule
streamlit
selenium
```

**목표 상태 (pyproject.toml):**
```toml
[project]
name = "gpt-bitcoin"
version = "2.0.0"
requires-python = ">=3.12"
dependencies = [
    "python-dotenv>=1.0.0",
    "openai>=1.54.0",
    "pyupbit>=0.2.33",
    "pandas>=2.2.0",
    "pandas-ta>=0.3.14b",
    "structlog>=24.1.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.2.0",
    "httpx>=0.27.0",
    "tenacity>=8.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "ruff>=0.3.0",
    "pre-commit>=3.6.0",
]
dashboard = [
    "streamlit>=1.32.0",
]
news = [
    "beautifulsoup4>=4.12.0",
    "feedparser>=6.0.0",
]
vision = [
    "selenium>=4.18.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
```

**검증:**
- `pip install -e ".[dev]"` 성공
- 모든 의존성 버전 확인

#### 1.2 프로젝트 구조 재조직

**현재 구조:**
```
gpt-bitcoin/
├── autotrade.py
├── autotrade_v2.py
├── autotrade_v3.py
├── streamlit_app.py
├── requirements.txt
├── instructions.md
└── trading_decisions.sqlite
```

**목표 구조:**
```
gpt-bitcoin/
├── src/
│   └── gpt_bitcoin/
│       ├── __init__.py
│       ├── main.py              # 진입점
│       ├── config.py            # 설정 관리
│       ├── models/              # 데이터 모델
│       │   ├── __init__.py
│       │   ├── trading.py       # 거래 관련 모델
│       │   └── market.py        # 시장 데이터 모델
│       ├── services/            # 비즈니스 로직
│       │   ├── __init__.py
│       │   ├── trader.py        # 거래 실행
│       │   ├── analyzer.py      # AI 분석
│       │   └── scheduler.py     # 스케줄링
│       ├── exchanges/           # 거래소 연동
│       │   ├── __init__.py
│       │   ├── base.py          # 추상 베이스
│       │   └── upbit.py         # Upbit 구현
│       ├── ai/                  # AI 제공자
│       │   ├── __init__.py
│       │   ├── base.py          # 추상 베이스
│       │   └── openai.py        # OpenAI 구현
│       └── utils/               # 유틸리티
│           ├── __init__.py
│           ├── logging.py       # 로깅 설정
│           └── retry.py         # 재시도 로직
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest fixtures
│   ├── unit/
│   │   ├── test_trader.py
│   │   ├── test_analyzer.py
│   │   └── test_models.py
│   └── integration/
│       ├── test_upbit.py
│       └── test_openai.py
├── pyproject.toml
├── README.md
├── .env.example
└── .gitignore
```

#### 1.3 개발 도구 설정

**pre-commit 설정 (.pre-commit-config.yaml):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.9.0
          - types-requests

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

---

## Phase 2: Architecture Refactoring

### Primary Goals

- 의존성 주입 패턴 적용
- 서비스 레이어 분리
- 비동기 아키텍처 구현

### Tasks

#### 2.1 데이터 모델 정의 (Pydantic v2)

**src/gpt_bitcoin/models/trading.py:**
```python
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class DecisionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class OrderResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    order_id: str | None = None
    error: str | None = None


class TradingDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: DecisionType
    percentage: int = Field(ge=0, le=100)
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)


class Balance(BaseModel):
    model_config = ConfigDict(frozen=True)

    btc: Decimal = Decimal("0")
    krw: Decimal = Decimal("0")
    btc_avg_buy_price: Decimal = Decimal("0")

    @property
    def total_btc_value(self) -> Decimal:
        return self.btc


class MarketData(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
```

**src/gpt_bitcoin/models/market.py:**
```python
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class TechnicalIndicators(BaseModel):
    model_config = ConfigDict(frozen=True)

    sma_10: Decimal
    ema_10: Decimal
    rsi_14: Decimal
    macd: Decimal
    signal_line: Decimal
    macd_histogram: Decimal
    upper_band: Decimal
    middle_band: Decimal
    lower_band: Decimal


class OHLCV(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
```

#### 2.2 추상 베이스 클래스 정의

**src/gpt_bitcoin/exchanges/base.py:**
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from ..models.trading import Balance, OrderResult

if TYPE_CHECKING:
    from ..models.trading import DecisionType


class ExchangeBase(ABC):
    """거래소 추상 베이스 클래스"""

    @abstractmethod
    async def get_balance(self) -> Balance:
        """현재 잔고 조회"""
        ...

    @abstractmethod
    async def get_market_data(self, ticker: str, interval: str, count: int) -> list[dict[str, Any]]:
        """시장 데이터 조회"""
        ...

    @abstractmethod
    async def execute_order(
        self,
        ticker: str,
        decision: DecisionType,
        amount: Decimal
    ) -> OrderResult:
        """주문 실행"""
        ...

    @abstractmethod
    async def get_current_price(self, ticker: str) -> Decimal:
        """현재 가격 조회"""
        ...
```

**src/gpt_bitcoin/ai/base.py:**
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models.trading import TradingDecision


class AIAnalyzerBase(ABC):
    """AI 분석기 추상 베이스 클래스"""

    @abstractmethod
    async def analyze(
        self,
        market_data: dict[str, Any],
        current_status: dict[str, Any],
        instructions: str
    ) -> TradingDecision:
        """시장 데이터 분석 및 거래 결정 생성"""
        ...
```

#### 2.3 서비스 레이어 구현

**src/gpt_bitcoin/services/trader.py:**
```python
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING

import structlog

from ..models.trading import Balance, DecisionType, OrderResult, TradingDecision
from ..utils.retry import with_retry

if TYPE_CHECKING:
    from ..ai.base import AIAnalyzerBase
    from ..exchanges.base import ExchangeBase

logger = structlog.get_logger()

MIN_ORDER_AMOUNT = Decimal("5000")
TRADING_FEE_RATE = Decimal("0.9995")


class TradingService:
    """거래 실행 서비스"""

    def __init__(
        self,
        exchange: ExchangeBase,
        analyzer: AIAnalyzerBase,
        instructions: str
    ) -> None:
        self._exchange = exchange
        self._analyzer = analyzer
        self._instructions = instructions

    async def make_decision(self) -> TradingDecision:
        """AI 분석을 통한 거래 결정"""
        market_data = await self._fetch_market_data()
        current_status = await self._get_current_status()

        decision = await self._analyzer.analyze(
            market_data=market_data,
            current_status=current_status,
            instructions=self._instructions
        )

        logger.info(
            "trading_decision_made",
            decision=decision.decision.value,
            percentage=decision.percentage,
            reason=decision.reason
        )

        return decision

    async def execute_decision(self, decision: TradingDecision) -> OrderResult:
        """거래 결정 실행"""
        if decision.decision == DecisionType.HOLD:
            logger.info("holding_position", reason=decision.reason)
            return OrderResult(success=True)

        balance = await self._exchange.get_balance()

        if decision.decision == DecisionType.BUY:
            return await self._execute_buy(balance, decision.percentage)
        else:
            return await self._execute_sell(balance, decision.percentage)

    @with_retry(max_retries=3)
    async def _execute_buy(self, balance: Balance, percentage: int) -> OrderResult:
        amount = balance.krw * (Decimal(percentage) / 100) * TRADING_FEE_RATE

        if amount < MIN_ORDER_AMOUNT:
            logger.warning("insufficient_balance", amount=amount, required=MIN_ORDER_AMOUNT)
            return OrderResult(success=False, error="Insufficient balance")

        result = await self._exchange.execute_order(
            ticker="KRW-BTC",
            decision=DecisionType.BUY,
            amount=amount
        )

        logger.info("buy_order_executed", amount=amount, success=result.success)
        return result

    @with_retry(max_retries=3)
    async def _execute_sell(self, balance: Balance, percentage: int) -> OrderResult:
        btc_to_sell = balance.btc * (Decimal(percentage) / 100)
        current_price = await self._exchange.get_current_price("KRW-BTC")
        estimated_value = btc_to_sell * current_price

        if estimated_value < MIN_ORDER_AMOUNT:
            logger.warning("insufficient_btc", value=estimated_value, required=MIN_ORDER_AMOUNT)
            return OrderResult(success=False, error="Insufficient BTC")

        result = await self._exchange.execute_order(
            ticker="KRW-BTC",
            decision=DecisionType.SELL,
            amount=btc_to_sell
        )

        logger.info("sell_order_executed", btc_amount=btc_to_sell, success=result.success)
        return result

    async def _fetch_market_data(self) -> dict[str, Any]:
        """시장 데이터 수집"""
        daily = await self._exchange.get_market_data("KRW-BTC", "day", 30)
        hourly = await self._exchange.get_market_data("KRW-BTC", "minute60", 24)
        return {"daily": daily, "hourly": hourly}

    async def _get_current_status(self) -> dict[str, Any]:
        """현재 상태 조회"""
        balance = await self._exchange.get_balance()
        current_price = await self._exchange.get_current_price("KRW-BTC")

        return {
            "btc_balance": float(balance.btc),
            "krw_balance": float(balance.krw),
            "btc_avg_buy_price": float(balance.btc_avg_buy_price),
            "current_price": float(current_price)
        }
```

---

## Phase 3: Testing Infrastructure

### Primary Goals

- pytest 기반 테스트 프레임워크 구축
- 85%+ 코드 커버리지 달성
- 단위 테스트 및 통합 테스트 작성

### Tasks

#### 3.1 테스트 설정

**tests/conftest.py:**
```python
from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gpt_bitcoin.models.trading import Balance, DecisionType, OrderResult, TradingDecision
from gpt_bitcoin.ai.base import AIAnalyzerBase
from gpt_bitcoin.exchanges.base import ExchangeBase


@pytest.fixture
def mock_exchange() -> ExchangeBase:
    """Mock 거래소"""
    exchange = MagicMock(spec=ExchangeBase)
    exchange.get_balance = AsyncMock(return_value=Balance(
        btc=Decimal("0.01"),
        krw=Decimal("100000"),
        btc_avg_buy_price=Decimal("50000000")
    ))
    exchange.get_current_price = AsyncMock(return_value=Decimal("55000000"))
    exchange.execute_order = AsyncMock(return_value=OrderResult(success=True, order_id="test-order"))
    return exchange


@pytest.fixture
def mock_analyzer() -> AIAnalyzerBase:
    """Mock AI 분석기"""
    analyzer = MagicMock(spec=AIAnalyzerBase)
    analyzer.analyze = AsyncMock(return_value=TradingDecision(
        decision=DecisionType.BUY,
        percentage=50,
        reason="Test decision",
        confidence=0.8
    ))
    return analyzer


@pytest.fixture
def sample_market_data() -> dict[str, Any]:
    """샘플 시장 데이터"""
    return {
        "daily": [{"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}],
        "hourly": [{"open": 104, "high": 106, "low": 103, "close": 105, "volume": 100}]
    }
```

#### 3.2 단위 테스트

**tests/unit/test_trader.py:**
```python
from __future__ import annotations

from decimal import Decimal

import pytest

from gpt_bitcoin.models.trading import Balance, DecisionType, OrderResult, TradingDecision
from gpt_bitcoin.services.trader import TradingService


class TestTradingService:
    """TradingService 단위 테스트"""

    @pytest.mark.asyncio
    async def test_make_decision_returns_valid_decision(self, mock_exchange, mock_analyzer):
        """AI 분석이 유효한 결정을 반환하는지 테스트"""
        service = TradingService(
            exchange=mock_exchange,
            analyzer=mock_analyzer,
            instructions="Test instructions"
        )

        decision = await service.make_decision()

        assert decision.decision == DecisionType.BUY
        assert 0 <= decision.percentage <= 100
        assert len(decision.reason) > 0

    @pytest.mark.asyncio
    async def test_execute_buy_with_sufficient_balance(self, mock_exchange, mock_analyzer):
        """충분한 잔고로 매수 실행 테스트"""
        service = TradingService(
            exchange=mock_exchange,
            analyzer=mock_analyzer,
            instructions="Test instructions"
        )

        decision = TradingDecision(
            decision=DecisionType.BUY,
            percentage=50,
            reason="Test buy",
            confidence=0.8
        )

        result = await service.execute_decision(decision)

        assert result.success is True
        assert result.order_id is not None

    @pytest.mark.asyncio
    async def test_execute_buy_with_insufficient_balance(self, mock_exchange, mock_analyzer):
        """잔고 부족 시 매수 실패 테스트"""
        mock_exchange.get_balance = AsyncMock(return_value=Balance(
            btc=Decimal("0"),
            krw=Decimal("1000"),  # 최소 주문 금액 미달
            btc_avg_buy_price=Decimal("0")
        ))

        service = TradingService(
            exchange=mock_exchange,
            analyzer=mock_analyzer,
            instructions="Test instructions"
        )

        decision = TradingDecision(
            decision=DecisionType.BUY,
            percentage=100,
            reason="Test buy",
            confidence=0.8
        )

        result = await service.execute_decision(decision)

        assert result.success is False
        assert "Insufficient balance" in result.error

    @pytest.mark.asyncio
    async def test_hold_decision_does_not_execute_order(self, mock_exchange, mock_analyzer):
        """HOLD 결정 시 주문 미실행 테스트"""
        service = TradingService(
            exchange=mock_exchange,
            analyzer=mock_analyzer,
            instructions="Test instructions"
        )

        decision = TradingDecision(
            decision=DecisionType.HOLD,
            percentage=0,
            reason="Market uncertain",
            confidence=0.6
        )

        result = await service.execute_decision(decision)

        assert result.success is True
        mock_exchange.execute_order.assert_not_called()
```

#### 3.3 통합 테스트

**tests/integration/test_upbit.py:**
```python
from __future__ import annotations

import os
from decimal import Decimal

import pytest

from gpt_bitcoin.exchanges.upbit import UpbitExchange


@pytest.mark.integration
class TestUpbitExchange:
    """UpbitExchange 통합 테스트 (실제 API 호출)"""

    @pytest.fixture
    def upbit_exchange(self):
        """실제 Upbit 거래소 인스턴스"""
        access_key = os.getenv("UPBIT_ACCESS_KEY")
        secret_key = os.getenv("UPBIT_SECRET_KEY")

        if not access_key or not secret_key:
            pytest.skip("Upbit API keys not configured")

        return UpbitExchange(access_key, secret_key)

    @pytest.mark.asyncio
    async def test_get_balance_returns_valid_data(self, upbit_exchange):
        """잔고 조회가 유효한 데이터를 반환하는지 테스트"""
        balance = await upbit_exchange.get_balance()

        assert balance.btc >= Decimal("0")
        assert balance.krw >= Decimal("0")

    @pytest.mark.asyncio
    async def test_get_current_price_returns_positive_value(self, upbit_exchange):
        """현재 가격 조회가 양수 값을 반환하는지 테스트"""
        price = await upbit_exchange.get_current_price("KRW-BTC")

        assert price > Decimal("0")
```

---

## Phase 4: Observability & Monitoring

### Primary Goals

- 구조화된 로깅 구현
- 헬스체크 엔드포인트 구현
- 에러 추적 시스템 연동

### Tasks

#### 4.1 구조화된 로깅

**src/gpt_bitcoin/utils/logging.py:**
```python
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """앱 컨텍스트 추가"""
    event_dict["app"] = "gpt-bitcoin"
    event_dict["version"] = "2.0.0"
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """로깅 설정"""
    # structlog 프로세서 체인
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_app_context,
    ]

    # JSON 포맷 (프로덕션) 또는 콘솔 포맷 (개발)
    if log_level == "DEBUG":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 표준 logging 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
```

#### 4.2 헬스체크 엔드포인트

**src/gpt_bitcoin/api/health.py:**
```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    timestamp: str
    version: str
    checks: dict[str, Any]


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """헬스체크 엔드포인트"""
    checks = {
        "database": await _check_database(),
        "exchange_api": await _check_exchange_api(),
        "ai_api": await _check_ai_api(),
    }

    all_healthy = all(check["status"] == "ok" for check in checks.values())

    return HealthStatus(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version="2.0.0",
        checks=checks
    )


async def _check_database() -> dict[str, Any]:
    """데이터베이스 연결 확인"""
    # TODO: 실제 DB 연결 확인 로직
    return {"status": "ok", "latency_ms": 5}


async def _check_exchange_api() -> dict[str, Any]:
    """거래소 API 연결 확인"""
    # TODO: 실제 API 연결 확인 로직
    return {"status": "ok", "latency_ms": 120}


async def _check_ai_api() -> dict[str, Any]:
    """AI API 연결 확인"""
    # TODO: 실제 API 연결 확인 로직
    return {"status": "ok", "latency_ms": 50}
```

---

## Phase 5: Documentation & Cleanup

### Primary Goals

- API 문서 생성
- README 업데이트
- 레거시 코드 정리

### Tasks

#### 5.1 README 업데이트

**README.md:**
```markdown
# GPT Bitcoin Auto-Trading System

Modern Python 3.12+ 기반 비트코인 자동거래 시스템

## Features

- AI 기반 거래 결정 (OpenAI GPT-4)
- 기술적 지표 분석 (RSI, MACD, Bollinger Bands)
- 비동기 아키텍처
- 구조화된 로깅
- 포괄적인 테스트 커버리지 (85%+)

## Requirements

- Python 3.12+
- Upbit 계정 및 API 키
- OpenAI API 키

## Installation

\`\`\`bash
# 저장소 클론
git clone https://github.com/your-repo/gpt-bitcoin.git
cd gpt-bitcoin

# 가상 환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# 의존성 설치
pip install -e ".[dev]"

# pre-commit 훅 설치
pre-commit install
\`\`\`

## Configuration

\`\`\`bash
# .env 파일 생성
cp .env.example .env

# API 키 설정
OPENAI_API_KEY=your-openai-api-key
UPBIT_ACCESS_KEY=your-upbit-access-key
UPBIT_SECRET_KEY=your-upbit-secret-key
\`\`\`

## Usage

\`\`\`bash
# 거래 봇 실행
python -m gpt_bitcoin.main

# 테스트 실행
pytest

# 타입 체크
mypy src

# 린트
ruff check src
\`\`\`

## Architecture

\`\`\`
src/gpt_bitcoin/
├── models/       # Pydantic 데이터 모델
├── services/     # 비즈니스 로직
├── exchanges/    # 거래소 연동
├── ai/           # AI 분석기
└── utils/        # 유틸리티
\`\`\`

## License

MIT
```

#### 5.2 레거시 코드 정리

**작업:**
- `autotrade.py`, `autotrade_v2.py`, `autotrade_v3.py`를 `legacy/` 디렉토리로 이동
- `requirements.txt` 삭제 (pyproject.toml로 대체)
- `.env.example` 파일 생성

---

## Risk Assessment

### High Risk

1. **API 호환성 문제**
   - 완화: 모든 API 호출에 대한 통합 테스트 작성
   - 완화: Mock을 사용한 단위 테스트로 회귀 방지

2. **거래 로직 변경으로 인한 손실**
   - 완화: 페이퍼 트레이딩 모드로 먼저 검증
   - 완화: 소액으로 실제 거래 테스트

### Medium Risk

1. **의존성 버전 충돌**
   - 완화: poetry.lock 또는 uv.lock으로 의존성 고정
   - 완화: 가상 환경 격리

2. **성능 저하**
   - 완화: 비동기 처리로 I/O 병목 해소
   - 완화: 벤치마크 테스트 작성

### Low Risk

1. **개발 환경 설정 오류**
   - 완화: 상세한 설치 문서 제공
   - 완화: Docker 컨테이너 옵션 제공

---

## Success Metrics

### Phase 1 완료 기준
- [ ] pyproject.toml 생성 완료
- [ ] 모든 의존성 버전 고정
- [ ] pre-commit 훅 동작 확인
- [ ] ruff, mypy 설정 완료

### Phase 2 완료 기준
- [ ] 모든 모델에 타입 힌트 적용
- [ ] 서비스 레이어 분리 완료
- [ ] 추상 베이스 클래스 구현
- [ ] 순환 의존성 없음

### Phase 3 완료 기준
- [ ] 테스트 커버리지 85% 이상
- [ ] 모든 단위 테스트 통과
- [ ] 통합 테스트 통과 (API 키 있음)
- [ ] pytest-cov 리포트 생성

### Phase 4 완료 기준
- [ ] 구조화된 로깅 동작
- [ ] 헬스체크 엔드포인트 응답
- [ ] 에러 추적 연동 (선택)

### Phase 5 완료 기준
- [ ] README 업데이트 완료
- [ ] API 문서 생성
- [ ] 레거시 코드 정리 완료
- [ ] CHANGELOG 작성

---

## Dependencies Between Phases

```
Phase 1 (Foundation)
    ↓
Phase 2 (Architecture) ← Phase 2는 Phase 1 완료 후 시작
    ↓
Phase 3 (Testing) ← Phase 3는 Phase 2 완료 후 시작
    ↓
Phase 4 (Observability) ← Phase 4는 Phase 2, 3 완료 후 시작
    ↓
Phase 5 (Documentation) ← Phase 5는 모든 Phase 완료 후 시작
```

---

## Notes

- 각 Phase는 독립적으로 검증 가능해야 함
- Phase 간 의존성을 고려하여 순차적 실행
- Phase 3 (Testing)은 Phase 2와 병행 가능
- Phase 4 (Observability)는 Phase 2 이후 언제든 시작 가능
