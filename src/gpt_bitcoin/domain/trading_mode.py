"""
Trading mode enumeration for production and testnet environments.

@MX:NOTE: 거래 모드 열거형 - PRODUCTION(실거래) / TESTNET(시뮬레이션)
"""

from __future__ import annotations

from enum import StrEnum


class TradingMode(StrEnum):
    """
    거래 모드 열거형 (Trading Mode Enumeration).

    Attributes:
        PRODUCTION: 실제 Upbit API를 사용하는 프로덕션 모드
        TESTNET: Mock API를 사용하는 테스트넷 모드

    @MX:ANCHOR: TradingMode는 시스템 전체에서 거래 모드 결정에 사용됨
        fan_in: 3+ (container, settings, web_ui)
        @MX:REASON: Single source of truth for trading mode selection
    """

    PRODUCTION = "production"
    TESTNET = "testnet"
