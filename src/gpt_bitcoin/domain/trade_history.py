"""
Trading history domain models and service (SPEC-TRADING-002).

이 모듈은 다음 기능을 제공합니다:
- TradeRecord: 거래 기록 도메인 모델
- TradeType: 거래 유형 enum (매수/매도)
- TradeHistoryService: FIFO 기반 손익 계산 서비스
- CSV 내보내기 기능

@MX:NOTE: FIFO(선입선출) 방식으로 실현 손익을 계산합니다.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from gpt_bitcoin.infrastructure.persistence.trade_repository import TradeRepository


# =============================================================================
# Domain Models
# =============================================================================


class TradeType(str, Enum):
    """
    거래 유형 enum.

    @MX:NOTE: 매수(BUY)와 매도(SELL) 두 가지 유형만 지원합니다.
    """

    BUY = "buy"
    SELL = "sell"


@dataclass
class TradeRecord:
    """
    거래 기록 도메인 모델.

    단일 거래에 대한 모든 정보를 저장합니다.

    Attributes:
        ticker: 마켓 티커 (예: "KRW-BTC")
        trade_type: 거래 유형 (매수/매도)
        price: 체결 가격 (KRW)
        quantity: 거래 수량
        fee: 거래 수수료 (KRW)
        timestamp: 거래 시간

    @MX:NOTE: TradeRecord는 불변 객체입니다.
    """

    ticker: str
    trade_type: TradeType
    price: float
    quantity: float
    fee: float
    timestamp: datetime = field(default_factory=datetime.now)

    def total_cost(self) -> float:
        """
        매수 거래의 총 비용 계산.

        Returns:
            총 비용 (가격 * 수량 + 수수료)

        @MX:ANCHOR: total_cost
        @MX:REASON: 매수 비용 계산의 중앙 진입점
        fan_in: 3 (손익 계산, 요약, CSV 내보내기)
        """
        return self.price * self.quantity + self.fee

    def total_revenue(self) -> float:
        """
        매도 거래의 총 수익 계산.

        Returns:
            총 수익 (가격 * 수량 - 수수료)

        @MX:ANCHOR: total_revenue
        @MX:REASON: 매도 수익 계산의 중앙 진입점
        fan_in: 3 (손익 계산, 요약, CSV 내보내기)
        """
        return self.price * self.quantity - self.fee

    def to_dict(self) -> dict[str, str | float]:
        """
        딕셔너리로 변환 (직렬화).

        Returns:
            거래 정보를 담은 딕셔너리
        """
        return {
            "ticker": self.ticker,
            "trade_type": self.trade_type.value,
            "price": self.price,
            "quantity": self.quantity,
            "fee": self.fee,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | float]) -> "TradeRecord":
        """
        딕셔너리로부터 인스턴스 생성 (역직렬화).

        Args:
            data: 거래 정보를 담은 딕셔너리

        Returns:
            TradeRecord 인스턴스
        """
        return cls(
            ticker=str(data["ticker"]),
            trade_type=TradeType(data["trade_type"]),
            price=float(data["price"]),
            quantity=float(data["quantity"]),
            fee=float(data["fee"]),
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
        )


class TradeHistoryError(Exception):
    """
    거래 내역 관련 오류.

    @MX:NOTE: 거래 내역 조회나 계산 중 발생하는 오류를 나타냅니다.
    """

    pass


# =============================================================================
# Trade History Service
# =============================================================================


class TradeHistoryService:
    """
    거래 내역 관리 서비스.

    FIFO(선입선출) 방식으로 실현 손익을 계산하고,
    거래 내역을 CSV로 내보내는 기능을 제공합니다.

    Example:
        ```python
        service = TradeHistoryService(trade_repository)

        # FIFO 손익 계산
        profit = service.calculate_fifo_profit("KRW-BTC")

        # 거래 요약
        summary = service.get_trade_summary("KRW-BTC")

        # CSV 내보내기
        service.export_to_csv(file, "KRW-BTC")
        ```

    @MX:ANCHOR: TradeHistoryService는 거래 내역 분석의 중앙 진입점입니다.
        fan_in: 2 (web_ui, main)
        @MX:REASON: FIFO 계산 로직을 한 곳에서 관리합니다.
    """

    def __init__(self, repository: TradeRepository) -> None:
        """
        TradeHistoryService 초기화.

        Args:
            repository: 거래 내역 저장소
        """
        self._repository = repository

    def _get_sorted_trades(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TradeRecord]:
        """
        정렬된 거래 내역을 반환하는 헬퍼 메서드.

        Args:
            ticker: 마켓 티커
            start_date: 시작 날짜 (선택 사항)
            end_date: 종료 날짜 (선택 사항)

        Returns:
            시간 순으로 정렬된 거래 목록

        @MX:NOTE: 중복 정렬을 방지하기 위한 헬퍼 메서드입니다.
        """
        trades = self._repository.get_trades(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )
        return sorted(trades, key=lambda t: t.timestamp)

    def _calculate_fifo_profit_from_trades(
        self,
        trades: list[TradeRecord],
    ) -> float:
        """
        이미 정렬된 거래 목록에서 FIFO 손익 계산.

        Args:
            trades: 시간 순으로 정렬된 거래 목록

        Returns:
            실현 손익 (KRW)

        @MX:NOTE: get_trade_summary에서 중복 쿼리를 피하기 위해 사용합니다.
        """
        # FIFO 큐: 매수 내역을 저장 (남은 수량 포함)
        buy_queue: list[tuple[TradeRecord, float]] = []  # (거래, 남은 수량)

        realized_profit = 0.0

        for trade in trades:
            if trade.trade_type == TradeType.BUY:
                # 매수: 큐에 추가
                buy_queue.append((trade, trade.quantity))

            elif trade.trade_type == TradeType.SELL:
                # 매도: FIFO로 매수와 매칭
                remaining_sell = trade.quantity

                while remaining_sell > 0 and buy_queue:
                    buy_trade, buy_remaining = buy_queue[0]

                    # 매칭 수량 계산
                    match_quantity = min(buy_remaining, remaining_sell)

                    # 매칭 비용 계산
                    buy_cost = (
                        buy_trade.price * match_quantity
                        + buy_trade.fee * (match_quantity / buy_trade.quantity)
                    )
                    sell_revenue = (
                        trade.price * match_quantity
                        - trade.fee * (match_quantity / trade.quantity)
                    )

                    # 손익 누적
                    realized_profit += sell_revenue - buy_cost

                    # 수량 업데이트
                    remaining_sell -= match_quantity
                    buy_remaining -= match_quantity

                    # 큐 업데이트
                    if buy_remaining > 0:
                        buy_queue[0] = (buy_trade, buy_remaining)
                    else:
                        buy_queue.pop(0)

        return realized_profit

    def calculate_fifo_profit(
        self,
        ticker: str,
    ) -> float:
        """
        FIFO 방식으로 실현 손익 계산.

        선입선출(FIFO) 방식으로 매수와 매도를 매칭하여
        실현된 손익을 계산합니다.

        Args:
            ticker: 마켓 티커 (예: "KRW-BTC")

        Returns:
            실현 손익 (KRW)

        @MX:WARN: 복잡한 FIFO 계산 로직
            @MX:REASON: 잔량 추적과 부분 매도 처리가 필요합니다.

        @MX:ANCHOR: calculate_fifo_profit
        @MX:REASON: FIFO 손익 계산의 핵심 로직
        fan_in: 3 (요약, API, CSV)
        """
        # 정렬된 거래 내역 조회 및 계산
        trades = self._get_sorted_trades(ticker)
        return self._calculate_fifo_profit_from_trades(trades)

    def get_trade_summary(
        self,
        ticker: str,
    ) -> dict[str, float | int]:
        """
        거래 내역 요약 통계.

        Args:
            ticker: 마켓 티커 (예: "KRW-BTC")

        Returns:
            요약 통계 딕셔너리

        @MX:NOTE: 요약에는 총 거래 횟수, 수량, 실현 손익이 포함됩니다.
        """
        # 거래 내역 조회 (calculate_fifo_profit에서도 사용)
        trades = self._get_sorted_trades(ticker)

        total_buy_quantity = sum(
            t.quantity for t in trades if t.trade_type == TradeType.BUY
        )
        total_sell_quantity = sum(
            t.quantity for t in trades if t.trade_type == TradeType.SELL
        )

        # FIFO 손익 계산 (이미 정렬된 trades 사용)
        realized_profit = self._calculate_fifo_profit_from_trades(trades)

        return {
            "total_trades": len(trades),
            "total_buy_quantity": total_buy_quantity,
            "total_sell_quantity": total_sell_quantity,
            "realized_profit": realized_profit,
        }

    def export_to_csv(
        self,
        output: StringIO,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        """
        거래 내역을 CSV로 내보내기.

        Args:
            output: CSV 출력을 위한 StringIO 객체
            ticker: 마켓 티커 (예: "KRW-BTC")
            start_date: 시작 날짜 (선택 사항)
            end_date: 종료 날짜 (선택 사항)

        @MX:NOTE: CSV는 표준 형식으로 내보내집니다.
        """
        # 정렬된 거래 내역 조회
        trades = self._get_sorted_trades(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        # CSV 작성
        writer = csv.DictWriter(
            output,
            fieldnames=["ticker", "trade_type", "price", "quantity", "fee", "timestamp"],
        )
        writer.writeheader()

        for trade in trades:
            writer.writerow({
                "ticker": trade.ticker,
                "trade_type": trade.trade_type.value,
                "price": trade.price,
                "quantity": trade.quantity,
                "fee": trade.fee,
                "timestamp": trade.timestamp.isoformat(),
            })


__all__ = [
    "TradeType",
    "TradeRecord",
    "TradeHistoryService",
    "TradeHistoryError",
]
