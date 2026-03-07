"""
Testnet configuration and mock balance management.

@MX:NOTE: 테스트넷 환경 설정 및 가상 잔액 관리
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, field_validator


@dataclass
class MockBalance:
    """
    Testnet용 가상 잔액 관리 (Virtual Balance Manager for Testnet).

    Attributes:
        krw_balance: KRW 잔액 (기본 1000만 원)
        coin_balances: 코인별 보유 수량
        avg_buy_prices: 코인별 평균 매수 단가

    @MX:NOTE: MockUpbitClient에서 사용되는 가상 잔액 데이터클래스
    """

    krw_balance: float = 10_000_000.0
    coin_balances: dict[str, float] = field(default_factory=dict)
    avg_buy_prices: dict[str, float] = field(default_factory=dict)


class TestnetConfig(BaseModel):
    """
    테스트넷 환경 설정 (Testnet Environment Configuration).

    Attributes:
        initial_krw_balance: 초기 KRW 잔액 (기본 1000만 원)
        simulated_fee_rate: 시뮬레이션 수수료율 (기본 0.05%)
        db_path: 테스트넷 전용 DB 경로 (기본 testnet_trades.db)

    @MX:NOTE: 테스트넷 환경의 전역 설정값
    """

    initial_krw_balance: float = Field(
        default=10_000_000.0,
        ge=0,
        description="Initial KRW balance for testnet mode",
    )
    simulated_fee_rate: float = Field(
        default=0.0005,
        ge=0,
        description="Simulated fee rate (0.05% by default)",
    )
    db_path: str = Field(
        default="testnet_trades.db",
        description="Path to testnet-specific database",
    )

    @field_validator("initial_krw_balance", "simulated_fee_rate")
    @classmethod
    def validate_non_negative(cls, v: float) -> float:
        """Validate that balance and fee rate are non-negative."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v
