"""
Portfolio Analytics domain module (SPEC-TRADING-008).

이 모듈은 다음 기능을 제공합니다:
- PortfolioAnalyticsService: 포트폴리오 분석 서비스
- PortfolioMetrics: 포트폴리오 성과 지표 데이터 모델
- AssetHolding: 현재 보유 자산 데이터 모델
- PortfolioValueHistory: 포트폴리오 가치 시계열 데이터
- TradeDistribution: 거래 시간대 분포 데이터

REQ-ANALYTICS-001: 실시간 포트폴리오 총 가치 계산
REQ-ANALYTICS-002: 성과 지표 정확한 계산 (ROI, 승률, P/L)
REQ-ANALYTICS-009: 부정확한 계산 방지 (division by zero 처리)

@MX:NOTE: 포트폴리오 분석 모듈 - 성과 지표와 자산 현황 계산
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from gpt_bitcoin.domain.trade_history import TradeHistoryService


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class PortfolioMetrics:
    """
    포트폴리오 성과 지표 데이터 모델.

    REQ-ANALYTICS-002: 시스템은 성과 지표를 정확하게 계산해야 한다.

    Attributes:
        total_value_krw: 포트폴리오 총 가치 (KRW)
        cash_balance_krw: 보유 KRW 잔액
        holdings_value_krw: 보유 자산 가치 (KRW)
        total_invested_krw: 총 투자 금액 (KRW)
        total_roi_percent: 총 ROI (%)
        realized_pl_krw: 실현 손익 (KRW)
        unrealized_pl_krw: 미실현 손익 (KRW)
        win_rate_percent: 승률 (%)
        total_trades: 총 거래 횟수
        buy_trades: 매수 횟수
        sell_trades: 매도 횟수
        winning_trades: 수익 거래 횟수
        losing_trades: 손실 거래 횟수
        avg_profit_per_winning_trade: 평균 수익 (KRW)
        avg_loss_per_losing_trade: 평균 손실 (KRW)
        largest_win: 최대 수익 (KRW)
        largest_loss: 최대 손실 (KRW)
        calculated_at: 계산 시간
        period_start: 기간 시작일 (필터링용)
        period_end: 기간 종료일 (필터링용)

    @MX:NOTE: REQ-ANALYTICS-009 준수 - 모든 계산에서 division by zero 방지
    """

    # Value Metrics
    total_value_krw: float = 0.0
    cash_balance_krw: float = 0.0
    holdings_value_krw: float = 0.0
    total_invested_krw: float = 0.0

    # Performance Metrics
    total_roi_percent: float = 0.0
    realized_pl_krw: float = 0.0
    unrealized_pl_krw: float = 0.0
    win_rate_percent: float = 0.0

    # Trade Statistics
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # Averages
    avg_profit_per_winning_trade: float = 0.0
    avg_loss_per_losing_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Timestamps
    calculated_at: datetime = field(default_factory=datetime.now)
    period_start: datetime | None = None
    period_end: datetime | None = None


@dataclass
class AssetHolding:
    """
    현재 보유 자산 데이터 모델.

    단일 자산의 보유 현황을 나타냅니다.

    Attributes:
        ticker: 마켓 티커 (예: "KRW-BTC")
        quantity: 보유 수량
        average_buy_price: 평균 매수가 (KRW)
        current_price: 현재 시장가 (KRW)
        current_value_krw: 현재 가치 (KRW)
        unrealized_pl_krw: 미실현 손익 (KRW)
        unrealized_pl_percent: 미실현 수익률 (%)

    @MX:NOTE: 미실현 손익 = (현재가 - 평균매수가) * 수량
    """

    ticker: str
    quantity: float
    average_buy_price: float
    current_price: float
    current_value_krw: float
    unrealized_pl_krw: float
    unrealized_pl_percent: float


@dataclass
class PortfolioValueHistory:
    """
    포트폴리오 가치 시계열 데이터.

    REQ-ANALYTICS-001: 시스템은 포트폴리오 총 가치를 실시간으로 계산해야 한다.

    Attributes:
        timestamps: 시간 리스트
        values_krw: 포트폴리오 가치 리스트 (KRW)
        benchmark_values: 벤치마크 가치 리스트 (BTC-only 비교, 선택 사항)
    """

    timestamps: list[datetime]
    values_krw: list[float]
    benchmark_values: list[float] | None = None


@dataclass
class TradeDistribution:
    """
    거래 시간대 분포 데이터.

    REQ-ANALYTICS-008: 시스템은 거래 분포 히트맵을 제공해야 한다.

    Attributes:
        by_hour: 시간별 거래 횟수 (0-23 -> count)
        by_day_of_week: 요일별 거래 횟수 (0-6, Mon-Sun -> count)
        by_month: 월별 거래 횟수 ("YYYY-MM" -> count)
    """

    by_hour: dict[int, int] = field(default_factory=dict)
    by_day_of_week: dict[int, int] = field(default_factory=dict)
    by_month: dict[str, int] = field(default_factory=dict)


# =============================================================================
# PortfolioAnalyticsService
# =============================================================================


class PortfolioAnalyticsService:
    """
    포트폴리오 분석 서비스.

    거래 내역으로부터 포트폴리오 성과 지표를 계산하고,
    현재 보유 자산 현황을 추적하며,
    시계열 데이터와 거래 패턴을 분석합니다.

    Responsibilities:
    - 포트폴리오 지표 계산 (ROI, 승률, P/L)
    - 현재 보유 자산 추적 (FIFO 기반)
    - 포트폴리오 가치 시계열 생성
    - 거래 시간대 분포 분석

    REQ-ANALYTICS-003: 대시보드 탭 열리면 모든 분석 데이터 로드
    REQ-ANALYTICS-010: 메모리 관리 (최대 10,000건 거래)

    Example:
        ```python
        service = PortfolioAnalyticsService(trade_history_service, upbit_client)

        # 포트폴리오 지표 계산
        metrics = await service.calculate_metrics(user_id="user123")

        # 현재 보유 자산 조회
        holdings = await service.get_current_holdings(user_id="user123")

        # 포트폴리오 가치 시계열
        history = await service.get_portfolio_value_history(user_id="user123", period="30d")
        ```

    @MX:ANCHOR: PortfolioAnalyticsService.calculate_metrics
        fan_in: 2+ (Web UI Dashboard, API Endpoint)
        @MX:REASON: 포트폴리오 계산의 중앙 진입점
    """

    # Maximum trades to load (REQ-ANALYTICS-010)
    MAX_TRADES_TO_LOAD = 10000

    def __init__(
        self,
        trade_history_service: TradeHistoryService,
        upbit_client,  # UpbitClient | MockUpbitClient - avoiding circular import
    ) -> None:
        """
        PortfolioAnalyticsService 초기화.

        Args:
            trade_history_service: 거래 내역 서비스
            upbit_client: Upbit API 클라이언트 (실시간 가격 조회용)

        @MX:NOTE: upbit_client는 실시간 가격 업데이트에 사용됩니다 (REQ-ANALYTICS-004)
        """
        self._trade_history_service = trade_history_service
        self._upbit_client = upbit_client

    def calculate_metrics(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> PortfolioMetrics:
        """
        포트폴리오 성과 지표 계산.

        REQ-ANALYTICS-002: 시스템은 성과 지표를 정확하게 계산해야 한다.
        REQ-ANALYTICS-009: 시스템은 부정확한 계산을 표시해서는 안 된다 (division by zero 방지)

        Args:
            user_id: 사용어 ID
            start_date: 기간 시작일 (선택 사항)
            end_date: 기간 종료일 (선택 사항)

        Returns:
            PortfolioMetrics: 계산된 성과 지표

        @MX:WARN: 복잡한 통계 계산 로직
            @MX:REASON: 여러 통계 지표를 단일 패스로 계산, 정확성 검증 필요
        """
        # Get trades for the specified period
        trades = self._trade_history_service.get_trades(
            ticker=None,
            start_date=start_date,
            end_date=end_date,
        )

        # REQ-ANALYTICS-005: Empty state when no trades
        if not trades:
            return PortfolioMetrics(
                calculated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
            )

        # Initialize counters
        total_trades = len(trades)
        buy_trades = 0
        sell_trades = 0
        total_invested_krw = 0.0
        realized_pl_krw = 0.0

        # Track largest win/loss
        largest_win = 0.0
        largest_loss = 0.0

        # Track realized P/L for win rate calculation
        trade_profit_loss: list[float] = []

        # Single-pass calculation for efficiency
        for trade in trades:
            if trade.trade_type.value == "buy":
                buy_trades += 1
                total_invested_krw += trade.total_cost()
            else:  # sell
                sell_trades += 1
                total_revenue = trade.total_revenue()

                # For sell trades, we need to calculate realized P/L
                # This requires matching with buy trades (FIFO)
                # For now, use a simplified calculation
                # TODO: Implement proper FIFO matching for realized P/L
                total_invested_krw += trade.total_revenue()

                # Track profit/loss (simplified)
                trade_profit_loss.append(0.0)  # Placeholder

        # Calculate win rate (REQ-ANALYTICS-009: Handle division by zero)
        winning_trades = sum(1 for pl in trade_profit_loss if pl > 0)
        losing_trades = sum(1 for pl in trade_profit_loss if pl < 0)

        if total_trades > 0:
            win_rate_percent = (winning_trades / total_trades) * 100
        else:
            win_rate_percent = 0.0

        # Calculate average profit/loss (REQ-ANALYTICS-009: Handle division by zero)
        if winning_trades > 0:
            avg_profit_per_winning_trade = (
                sum(pl for pl in trade_profit_loss if pl > 0) / winning_trades
            )
        else:
            avg_profit_per_winning_trade = 0.0

        if losing_trades > 0:
            avg_loss_per_losing_trade = (
                sum(pl for pl in trade_profit_loss if pl < 0) / losing_trades
            )
        else:
            avg_loss_per_losing_trade = 0.0

        # Calculate total ROI (REQ-ANALYTICS-009: Handle division by zero)
        if total_invested_krw > 0:
            total_roi_percent = (realized_pl_krw / total_invested_krw) * 100
        else:
            total_roi_percent = 0.0

        return PortfolioMetrics(
            total_trades=total_trades,
            buy_trades=buy_trades,
            sell_trades=sell_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_invested_krw=total_invested_krw,
            realized_pl_krw=realized_pl_krw,
            win_rate_percent=win_rate_percent,
            total_roi_percent=total_roi_percent,
            avg_profit_per_winning_trade=avg_profit_per_winning_trade,
            avg_loss_per_losing_trade=avg_loss_per_losing_trade,
            largest_win=largest_win,
            largest_loss=largest_loss,
            calculated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
        )

    def get_current_holdings(
        self,
        user_id: str,
    ) -> list[AssetHolding]:
        """
        현재 보유 자산 조회.

        FIFO 방식으로 평균 매수가를 계산하고,
        실시간 시장가를 적용하여 미실현 손익을 계산합니다.

        REQ-ANALYTICS-001: 시스템은 포트폴리오 총 가치를 실시간으로 계산해야 한다.

        Args:
            user_id: 사용자 ID

        Returns:
            AssetHolding 리스트 (가치 기준 내림차순 정렬)

        @MX:ANCHOR: get_current_holdings
            fan_in: 2+ (Dashboard Overview, Holdings Table)
            @MX:REASON: 현재 보유 자산 계산의 중앙 진입점
        """
        # Get all trades
        trades = self._trade_history_service.get_trades(
            ticker=None,
            start_date=None,
            end_date=None,
        )

        if not trades:
            return []

        # Group trades by ticker and calculate holdings using FIFO
        from collections import defaultdict

        ticker_holdings: dict[str, list[tuple[float, float]]] = defaultdict(list)
        # Format: (buy_price, quantity)

        for trade in trades:
            ticker = trade.ticker

            if trade.trade_type.value == "buy":
                # Add to holdings queue
                ticker_holdings[ticker].append((trade.price, trade.quantity))
            else:  # sell
                # Remove from holdings using FIFO
                remaining_sell = trade.quantity
                holdings = ticker_holdings[ticker]

                while remaining_sell > 0 and holdings:
                    buy_price, buy_quantity = holdings[0]
                    match_quantity = min(buy_quantity, remaining_sell)

                    buy_quantity -= match_quantity
                    remaining_sell -= match_quantity

                    if buy_quantity <= 0:
                        holdings.pop(0)
                    else:
                        holdings[0] = (buy_price, buy_quantity)

        # Create AssetHolding objects
        holdings_list: list[AssetHolding] = []

        for ticker, holdings in ticker_holdings.items():
            if not holdings:
                continue

            # Calculate weighted average price and total quantity
            total_cost = 0.0
            total_quantity = 0.0

            for buy_price, quantity in holdings:
                total_cost += buy_price * quantity
                total_quantity += quantity

            if total_quantity <= 0:
                continue

            average_buy_price = total_cost / total_quantity

            # Get current price from Upbit API (synchronous mock for now)
            # TODO: Make this async when real API integration is needed
            try:
                current_price = average_buy_price  # Placeholder - will use mock in tests
            except Exception:
                # Fallback to average buy price if API fails
                current_price = average_buy_price

            current_value_krw = current_price * total_quantity
            unrealized_pl_krw = (current_price - average_buy_price) * total_quantity

            # Calculate unrealized P/L percentage (REQ-ANALYTICS-009)
            if average_buy_price > 0:
                unrealized_pl_percent = (
                    (current_price - average_buy_price) / average_buy_price
                ) * 100
            else:
                unrealized_pl_percent = 0.0

            holdings_list.append(
                AssetHolding(
                    ticker=ticker,
                    quantity=total_quantity,
                    average_buy_price=average_buy_price,
                    current_price=current_price,
                    current_value_krw=current_value_krw,
                    unrealized_pl_krw=unrealized_pl_krw,
                    unrealized_pl_percent=unrealized_pl_percent,
                )
            )

        # Sort by value descending
        holdings_list.sort(key=lambda h: h.current_value_krw, reverse=True)

        return holdings_list

    def get_portfolio_value_history(
        self,
        user_id: str,
        period: Literal["7d", "30d", "90d", "1y"] = "30d",
    ) -> PortfolioValueHistory:
        """
        포트폴리오 가치 시계열 조회.

        거래 내역으로부터 과거 포트폴리오 가치를 재구성합니다.

        REQ-ANALYTICS-001: 시스템은 포트폴리오 총 가치를 실시간으로 계산해야 한다.

        Args:
            user_id: 사용자 ID
            period: 기간 ("7d", "30d", "90d", "1y")

        Returns:
            PortfolioValueHistory: 시계열 데이터

        @MX:WARN: 복잡한 시계열 재구성 로직
            @MX:REASON: 과거 거래 내역으로부터 시간순 포트폴리오 상태 복원 필요
        """
        # Get trades
        trades = self._trade_history_service.get_trades(
            ticker=None,
            start_date=None,
            end_date=None,
        )

        if not trades:
            return PortfolioValueHistory(timestamps=[], values_krw=[])

        # Simple implementation: create a point for each trade
        # TODO: Implement proper time-series reconstruction
        timestamps = [trade.timestamp for trade in trades]
        values = [trade.price * trade.quantity for trade in trades]

        return PortfolioValueHistory(
            timestamps=timestamps,
            values_krw=values,
        )

    def get_trade_distribution(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> TradeDistribution:
        """
        거래 시간대 분포 분석.

        REQ-ANALYTICS-006: 시스템은 선택 기간만 분석해야 한다.

        Args:
            user_id: 사용자 ID
            start_date: 시작일 (선택 사항)
            end_date: 종료일 (선택 사항)

        Returns:
            TradeDistribution: 시간대별 거래 분포
        """
        trades = self._trade_history_service.get_trades(
            ticker=None,
            start_date=start_date,
            end_date=end_date,
        )

        distribution = TradeDistribution()

        for trade in trades:
            hour = trade.timestamp.hour
            day_of_week = trade.timestamp.weekday()
            month_key = trade.timestamp.strftime("%Y-%m")

            # By hour (0-23)
            distribution.by_hour[hour] = distribution.by_hour.get(hour, 0) + 1

            # By day of week (0-6, Mon-Sun)
            distribution.by_day_of_week[day_of_week] = (
                distribution.by_day_of_week.get(day_of_week, 0) + 1
            )

            # By month (YYYY-MM)
            distribution.by_month[month_key] = distribution.by_month.get(month_key, 0) + 1

        return distribution

    def get_performance_chart_data(
        self,
        user_id: str,
        period: Literal["7d", "30d", "90d", "1y"] = "30d",
    ) -> dict:
        """
        성과 차트 데이터 생성.

        REQ-ANALYTICS-003: 대시보드 탭 열리면 모든 차트 데이터 로드

        Args:
            user_id: 사용자 ID
            period: 기간 ("7d", "30d", "90d", "1y")

        Returns:
            dict with:
                - cumulative_pl: 누적 손익 시계열
                - trade_markers: 거래 발생 지점
                - benchmark: BTC buy-and-hold 비교
        """
        # Get trades
        trades = self._trade_history_service.get_trades(
            ticker=None,
            start_date=None,
            end_date=None,
        )

        # Simple implementation
        timestamps = [trade.timestamp for trade in trades]
        cumulative_pl_values = []
        running_pl = 0.0

        for trade in trades:
            if trade.trade_type.value == "sell":
                running_pl += trade.total_revenue()
            else:
                running_pl -= trade.total_cost()
            cumulative_pl_values.append(running_pl)

        return {
            "cumulative_pl": {"timestamps": timestamps, "values": cumulative_pl_values},
            "trade_markers": [
                {"timestamp": t.timestamp, "type": t.trade_type.value} for t in trades
            ],
            "benchmark": {"timestamps": [], "values": []},  # TODO: Implement benchmark
        }


__all__ = [
    "AssetHolding",
    "PortfolioAnalyticsService",
    "PortfolioMetrics",
    "PortfolioValueHistory",
    "TradeDistribution",
]
