"""
Trade repository for SQLite persistence (SPEC-TRADING-002).

이 모듈은 TradeRecord를 SQLite 데이터베이스에 저장하고 조회하는 기능을 제공합니다.

@MX:NOTE: SQLite를 사용하여 가볍고 휴대 가능한 저장소를 구현합니다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings

from gpt_bitcoin.domain.trade_history import TradeRecord, TradeType


class TradeRepository:
    """
    거래 내역 저장소 (SQLite).

    TradeRecord를 SQLite 데이터베이스에 저장하고 조회합니다.

    Example:
        ```python
        repo = TradeRepository(settings)
        repo.add_trade(trade_record)
        trades = repo.get_trades(ticker="KRW-BTC")
        ```

    @MX:ANCHOR: TradeRepository는 데이터베이스 접근의 중앙 진입점입니다.
        fan_in: 2 (TradeHistoryService, main)
        @MX:REASON: 데이터베이스 연결 관리와 쿼리 실행을 캡슐화합니다.
    """

    def __init__(self, settings: Settings) -> None:
        """
        TradeRepository 초기화.

        Args:
            settings: 애플리케이션 설정

        @MX:NOTE: 데이터베이스 파일은 settings.db_path에서 지정한 위치에 생성됩니다.
        """
        self._settings = settings
        self._db_path = Path(settings.db_path)
        self._conn: sqlite3.Connection | None = None

        # 데이터베이스 초기화
        self._initialize_database()

    def _initialize_database(self) -> None:
        """
        데이터베이스 테이블 초기화.

        @MX:NOTE: 테이블이 존재하지 않으면 생성합니다.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                fee REAL NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticker ON trades(ticker)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)
        """)

        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """
        데이터베이스 연결 가져오기.

        Returns:
            SQLite 연결 객체

        @MX:NOTE: 연결은 지연 초기화됩니다.
        """
        if self._conn is None:
            # 디렉토리 생성
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

            # 연결 생성
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
            )
            self._conn.row_factory = sqlite3.Row

        return self._conn

    def add_trade(self, trade: TradeRecord) -> None:
        """
        거래 내역 추가.

        Args:
            trade: 저장할 거래 기록

        @MX:ANCHOR: add_trade
        @MX:REASON: 거래 내역 저장의 유일한 진입점
        fan_in: 3 (TradingService, main, test)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO trades (ticker, trade_type, price, quantity, fee, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                trade.ticker,
                trade.trade_type.value,
                trade.price,
                trade.quantity,
                trade.fee,
                trade.timestamp.isoformat(),
            ),
        )

        conn.commit()

    def get_trades(
        self,
        ticker: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TradeRecord]:
        """
        거래 내역 조회.

        Args:
            ticker: 마켓 티커 필터 (선택 사항)
            start_date: 시작 날짜 필터 (선택 사항)
            end_date: 종료 날짜 필터 (선택 사항)

        Returns:
            거래 기록 리스트

        @MX:ANCHOR: get_trades
        @MX:REASON: 거래 내역 조회의 유일한 진입점
        fan_in: 3 (TradeHistoryService, main, test)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params: list[str | float] = []

        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY timestamp ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            TradeRecord(
                ticker=row["ticker"],
                trade_type=TradeType(row["trade_type"]),
                price=row["price"],
                quantity=row["quantity"],
                fee=row["fee"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]

    def close(self) -> None:
        """
        데이터베이스 연결 종료.

        @MX:NOTE: 애플리케이션 종료 시 호출해야 합니다.
        """
        if self._conn is not None:
            self._conn.close()
            self._conn = None


__all__ = ["TradeRepository"]
