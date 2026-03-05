"""
Tests for TradeRepository (SQLite persistence) - SPEC-TRADING-002.

This test module covers:
- SQLite database initialization
- Trade record storage and retrieval
- Date-based filtering
- Ticker-based filtering

@MX:NOTE: Test-first approach - RED phase before implementation.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import os

import pytest

from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository
from gpt_bitcoin.domain.trade_history import TradeRecord, TradeType


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_db_path():
    """
    임시 데이터베이스 파일 경로 생성.

    Yields:
        임시 데이터베이스 파일 경로
    """
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    yield path
    # 테스트 후 정리
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def mock_settings(temp_db_path):
    """
    Mock settings for testing.

    Args:
        temp_db_path: 임시 데이터베이스 파일 경로

    Yields:
        Mock settings 객체
    """
    from gpt_bitcoin.config.settings import Settings

    # 환경 변수 설정
    os.environ["UPBIT_ACCESS_KEY"] = "test_access_key"
    os.environ["UPBIT_SECRET_KEY"] = "test_secret_key"
    os.environ["ZHIPUAI_API_KEY"] = "test_zhipu_key"

    settings = Settings(
        upbit_access_key="test_access_key",
        upbit_secret_key="test_secret_key",
        zhipuai_api_key="test_zhipu_key",
        db_path=temp_db_path,
    )
    yield settings

    # 환경 변수 정리
    del os.environ["UPBIT_ACCESS_KEY"]
    del os.environ["UPBIT_SECRET_KEY"]
    del os.environ["ZHIPUAI_API_KEY"]


@pytest.fixture
def repository(mock_settings):
    """
    TradeRepository fixture.

    Args:
        mock_settings: Mock settings

    Yields:
        TradeRepository 인스턴스
    """
    repo = TradeRepository(mock_settings)
    yield repo
    repo.close()


# =============================================================================
# TradeRepository Tests
# =============================================================================


class TestTradeRepository:
    """Test cases for TradeRepository."""

    def test_database_initialization(self, repository) -> None:
        """Test database table initialization."""
        # 데이터베이스 파일이 생성되었는지 확인
        assert Path(repository._settings.db_path).exists()

    def test_add_trade_buy(self, repository) -> None:
        """Test adding a buy trade record."""
        trade = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.BUY,
            price=50000000.0,
            quantity=0.001,
            fee=25.0,
            timestamp=datetime(2026, 3, 5, 10, 0, 0),
        )

        repository.add_trade(trade)

        # 저장된 거래 내역 조회
        trades = repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 1
        assert trades[0].ticker == "KRW-BTC"
        assert trades[0].trade_type == TradeType.BUY
        assert trades[0].price == 50000000.0

    def test_add_trade_sell(self, repository) -> None:
        """Test adding a sell trade record."""
        trade = TradeRecord(
            ticker="KRW-BTC",
            trade_type=TradeType.SELL,
            price=55000000.0,
            quantity=0.001,
            fee=27.5,
            timestamp=datetime(2026, 3, 5, 11, 0, 0),
        )

        repository.add_trade(trade)

        trades = repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 1
        assert trades[0].trade_type == TradeType.SELL

    def test_get_trades_by_ticker(self, repository) -> None:
        """Test filtering trades by ticker."""
        # BTC 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        # ETH 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-ETH",
                trade_type=TradeType.BUY,
                price=3000000.0,
                quantity=0.01,
                fee=15.0,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        # BTC만 조회
        btc_trades = repository.get_trades(ticker="KRW-BTC")
        assert len(btc_trades) == 1
        assert btc_trades[0].ticker == "KRW-BTC"

        # ETH만 조회
        eth_trades = repository.get_trades(ticker="KRW-ETH")
        assert len(eth_trades) == 1
        assert eth_trades[0].ticker == "KRW-ETH"

    def test_get_trades_by_date_range(self, repository) -> None:
        """Test filtering trades by date range."""
        # 다른 날짜의 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 1, 10, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=51000000.0,
                quantity=0.001,
                fee=25.5,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=52000000.0,
                quantity=0.001,
                fee=26.0,
                timestamp=datetime(2026, 3, 10, 10, 0, 0),
            )
        )

        # 날짜 범위로 조회
        trades = repository.get_trades(
            ticker="KRW-BTC",
            start_date=datetime(2026, 3, 2),
            end_date=datetime(2026, 3, 8),
        )

        assert len(trades) == 1
        assert trades[0].price == 51000000.0

    def test_get_trades_ordering(self, repository) -> None:
        """Test that trades are returned in chronological order."""
        # 랜덤 순서로 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=52000000.0,
                quantity=0.001,
                fee=26.0,
                timestamp=datetime(2026, 3, 5, 12, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=51000000.0,
                quantity=0.001,
                fee=25.5,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        # 시간 순서대로 정렬되어야 함
        trades = repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 3
        assert trades[0].price == 50000000.0
        assert trades[1].price == 51000000.0
        assert trades[2].price == 52000000.0

    def test_get_trades_empty(self, repository) -> None:
        """Test getting trades when none exist."""
        trades = repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 0

    def test_multiple_adds(self, repository) -> None:
        """Test adding multiple trades."""
        for i in range(5):
            repository.add_trade(
                TradeRecord(
                    ticker="KRW-BTC",
                    trade_type=TradeType.BUY,
                    price=50000000.0 + i * 1000000.0,
                    quantity=0.001,
                    fee=25.0 + i * 0.5,
                    timestamp=datetime(2026, 3, 5, 10 + i, 0, 0),
                )
            )

        trades = repository.get_trades(ticker="KRW-BTC")
        assert len(trades) == 5

    def test_close_connection(self, repository) -> None:
        """Test closing database connection."""
        # 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
            )
        )

        # 연결 종료
        repository.close()
        assert repository._conn is None

    def test_persistence_across_instances(self, mock_settings) -> None:
        """Test that trades persist across repository instances."""
        # 첫 번째 인스턴스로 거래 추가
        repo1 = TradeRepository(mock_settings)
        repo1.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
            )
        )
        repo1.close()

        # 두 번째 인스턴스로 거래 조회
        repo2 = TradeRepository(mock_settings)
        trades = repo2.get_trades(ticker="KRW-BTC")
        assert len(trades) == 1
        assert trades[0].price == 50000000.0
        repo2.close()

    def test_combined_filters(self, repository) -> None:
        """Test using both ticker and date filters together."""
        # 다른 티커와 날짜의 거래 추가
        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=50000000.0,
                quantity=0.001,
                fee=25.0,
                timestamp=datetime(2026, 3, 1, 10, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-BTC",
                trade_type=TradeType.BUY,
                price=51000000.0,
                quantity=0.001,
                fee=25.5,
                timestamp=datetime(2026, 3, 5, 10, 0, 0),
            )
        )

        repository.add_trade(
            TradeRecord(
                ticker="KRW-ETH",
                trade_type=TradeType.BUY,
                price=3000000.0,
                quantity=0.01,
                fee=15.0,
                timestamp=datetime(2026, 3, 5, 11, 0, 0),
            )
        )

        # 티커와 날짜 필터 조합
        trades = repository.get_trades(
            ticker="KRW-BTC",
            start_date=datetime(2026, 3, 3),
        )

        assert len(trades) == 1
        assert trades[0].ticker == "KRW-BTC"
        assert trades[0].price == 51000000.0
