"""
Chart rendering utilities with Plotly (SPEC-TRADING-008).

이 모듈은 다음 기능을 제공합니다:
- create_portfolio_value_chart: 포트폴리오 가치 차트 생성
- create_performance_chart: 성과 비교 차트 생성
- create_distribution_heatmap: 거래 분포 히트맵 생성

REQ-ANALYTICS-007: 인터랙티브 차트 (확대/축소, 패닝)

@MX:NOTE: Plotly 5.18+ 사용하여 인터랙티브 차트 생성
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from gpt_bitcoin.domain.analytics import (
        PortfolioValueHistory,
        TradeDistribution,
    )


def create_portfolio_value_chart(
    history: PortfolioValueHistory,
    period: Literal["7d", "30d", "90d", "1y"] = "30d",
) -> dict:
    """
    포트폴리오 가치 시계열 차트 생성.

    REQ-ANALYTICS-001: 실시간 포트폴리오 총 가치 계산

    Args:
        history: 포트폴리오 가치 시계열 데이터
        period: 표시 기간

    Returns:
        Plotly Figure JSON (dict)

    @MX:NOTE: Line chart with markers for trade events
    """
    # TODO: Implement Plotly line chart
    # This is a placeholder for the TDD implementation
    return {
        "data": [],
        "layout": {
            "title": "Portfolio Value Over Time",
            "xaxis": {"title": "Time"},
            "yaxis": {"title": "Value (KRW)"},
        },
    }


def create_performance_chart(
    cumulative_pl: list[float],
    benchmark: list[float] | None = None,
) -> dict:
    """
    성과 비교 차트 생성 (Cumulative P/L).

    REQ-ANALYTICS-002: ROI, 승률, P/L 지표

    Args:
        cumulative_pl: 누적 손익 데이터
        benchmark: 벤치마크 데이터 (선택 사항)

    Returns:
        Plotly Figure JSON (dict)

    @MX:NOTE: Compare portfolio performance vs BTC buy-and-hold
    """
    # TODO: Implement Plotly comparison chart
    # This is a placeholder for the TDD implementation
    return {
        "data": [],
        "layout": {
            "title": "Cumulative P/L",
            "xaxis": {"title": "Time"},
            "yaxis": {"title": "P/L (KRW)"},
        },
    }


def create_distribution_heatmap(
    distribution: TradeDistribution,
) -> dict:
    """
    거래 시간대 분포 히트맵 생성.

    REQ-ANALYTICS-008: 요일 vs 시간대 히트맵

    Args:
        distribution: 거래 분포 데이터

    Returns:
        Plotly Figure JSON (dict)

    @MX:NOTE: Heatmap with day of week vs hour of day
    """
    # TODO: Implement Plotly heatmap
    # This is a placeholder for the TDD implementation
    return {
        "data": [],
        "layout": {
            "title": "Trade Distribution",
            "xaxis": {"title": "Hour of Day"},
            "yaxis": {"title": "Day of Week"},
        },
    }


def format_number(value: float) -> str:
    """
    숫자를 한국어 형식으로 포맷팅.

    Args:
        value: 포맷팅할 숫자

    Returns:
        포맷팅된 문자열 (예: "1,234,567.89")

    @MX:ANCHOR: format_number
        fan_in: 3+ (Overview cards, Holdings table, Tooltips)
        @MX:REASON: 숫자 포맷팅의 중앙 진입점
    """
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.2f}"


def format_percentage(value: float) -> str:
    """
    퍼센트를 포맷팅.

    Args:
        value: 퍼센트 값

    Returns:
        포맷팅된 문자열 (예: "+15.5%")

    @MX:NOTE: 양수는 + 접두사, 음수는 - 접두사
    """
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


__all__ = [
    "create_distribution_heatmap",
    "create_performance_chart",
    "create_portfolio_value_chart",
    "format_number",
    "format_percentage",
]
