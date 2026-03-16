"""
Mock Upbit API client for testnet simulation.

This client simulates all Upbit API operations without making real HTTP requests.
All operations are performed in-memory with virtual balance.

@MX:NOTE: MockUpbitClient - 실제 API 호출 없이 시뮬레이션만 수행
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from gpt_bitcoin.domain.testnet_config import MockBalance, TestnetConfig


@dataclass
class _OrderbookUnit:
    """Mock orderbook unit for simulation."""

    ask_price: float
    bid_price: float
    ask_size: float
    bid_size: float


@dataclass
class _Orderbook:
    """Mock orderbook for simulation."""

    ticker: str
    orderbook_units: list[_OrderbookUnit]
    timestamp: datetime


@dataclass
class _Order:
    """Mock order for simulation."""

    uuid: str
    ticker: str
    side: str
    order_type: str
    price: float
    volume: float
    executed_volume: float  # 실제 체결된 수량 (시장가는 volume과 동일)
    fee: float
    created_at: datetime


@dataclass
class _Balance:
    """Mock balance for simulation."""

    currency: str
    balance: float
    avg_buy_price: float | None


@dataclass
class MockUpbitClient:
    """
    Upbit API Mock 클라이언트 for Testnet.

    실제 UpbitClient와 동일한 인터페이스를 제공하며,
    모든 작업을 메모리 내에서 시뮬레이션합니다.

    Attributes:
        config: TestnetConfig 설정
        _balance: 가상 잔액 관리

    @MX:ANCHOR: MockUpbitClient.buy_market_order
        fan_in: 2+ (trading service, tests)
        @MX:REASON: Testnet 환경에서의 중앙 거래 실행 메서드

    @MX:ANCHOR: MockUpbitClient.sell_market_order
        fan_in: 2+ (trading service, tests)
        @MX:REASON: Testnet 환경에서의 중앙 거래 실행 메서드
    """

    # Simulated market prices (ticker -> price in KRW)
    _SIMULATED_PRICES: ClassVar[dict[str, float]] = {
        "KRW-BTC": 50_000_000.0,
        "KRW-ETH": 3_000_000.0,
        "KRW-SOL": 150_000.0,
        "KRW-XRP": 500.0,
        "KRW-ADA": 400.0,
        "KRW-DOGE": 70.0,
        "KRW-AVAX": 35_000.0,
        "KRW-DOT": 25.0,
    }

    def __init__(self, config: TestnetConfig | None = None) -> None:
        """
        Initialize MockUpbitClient.

        Args:
            config: TestnetConfig 설정 (기본값 사용)
        """
        self.config = config or TestnetConfig()
        self._balance = MockBalance(
            krw_balance=self.config.initial_krw_balance,
        )

    async def get_orderbook(self, ticker: str = "KRW-BTC") -> _Orderbook:
        """
        Get current orderbook for a ticker.

        시뮬레이션된 호가 books를 반환합니다.

        Args:
            ticker: Market ticker (default: "KRW-BTC")

        Returns:
            Mock Orderbook with simulated prices
        """
        price = self._SIMULATED_PRICES.get(ticker, 50_000_000.0)
        spread = price * 0.001  # 0.1% spread

        return _Orderbook(
            ticker=ticker,
            orderbook_units=[
                _OrderbookUnit(
                    ask_price=price + spread / 2,
                    bid_price=price - spread / 2,
                    ask_size=10.0,
                    bid_size=10.0,
                ),
            ],
            timestamp=datetime.now(),
        )

    async def get_current_price(self, ticker: str = "KRW-BTC") -> float:
        """
        Get current price for a ticker.

        시뮬레이션된 현재가를 반환합니다.

        Args:
            ticker: Market ticker (default: "KRW-BTC")

        Returns:
            Current price in KRW
        """
        return self._SIMULATED_PRICES.get(ticker, 50_000_000.0)

    async def get_balances(self) -> list[_Balance]:
        """
        Get account balances.

        가상 잔액 전체를 반환합니다.

        Returns:
            List of balances (KRW + all coins)
        """
        balances = [
            _Balance(
                currency="KRW",
                balance=self._balance.krw_balance,
                avg_buy_price=None,
            )
        ]

        for coin, quantity in self._balance.coin_balances.items():
            avg_price = self._balance.avg_buy_prices.get(coin)
            balances.append(
                _Balance(
                    currency=coin,
                    balance=quantity,
                    avg_buy_price=avg_price,
                )
            )

        return balances

    async def get_balance(self, currency: str = "KRW") -> float:
        """
        Get balance for a specific currency.

        Args:
            currency: Currency code (default: "KRW")

        Returns:
            Balance amount
        """
        if currency == "KRW":
            return self._balance.krw_balance

        return self._balance.coin_balances.get(currency, 0.0)

    async def buy_market_order(
        self,
        ticker: str,
        amount: float,
    ) -> _Order:
        """
        Execute a market buy order (simulated).

        시뮬레이션된 시장가 매수를 실행합니다.
        가상 잔액을 업데이트하고 수수료를 차감합니다.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            amount: Amount in KRW to spend

        Returns:
            Mock Order with execution details

        Raises:
            ValueError: Insufficient balance
        """
        price = await self.get_current_price(ticker)
        quantity = amount / price
        fee = amount * self.config.simulated_fee_rate

        total_krw_needed = amount + fee

        if self._balance.krw_balance < total_krw_needed:
            raise ValueError(
                f"잔액 부족: 필요 {total_krw_needed:,.0f} KRW, "
                f"보유 {self._balance.krw_balance:,.0f} KRW"
            )

        # Update balance
        self._balance.krw_balance -= total_krw_needed

        # Update coin balance
        coin = ticker.split("-")[1] if "-" in ticker else ticker
        self._balance.coin_balances[coin] = self._balance.coin_balances.get(coin, 0.0) + quantity

        # Update avg buy price
        old_quantity = self._balance.coin_balances.get(coin, 0.0) - quantity
        old_avg_price = self._balance.avg_buy_prices.get(coin, price)

        if old_quantity > 0:
            new_avg_price = (old_avg_price * old_quantity + price * quantity) / (
                old_quantity + quantity
            )
            self._balance.avg_buy_prices[coin] = new_avg_price
        else:
            self._balance.avg_buy_prices[coin] = price

        return _Order(
            uuid=str(uuid.uuid4()),
            ticker=ticker,
            side="bid",
            order_type="market",
            price=price,
            volume=quantity,
            executed_volume=quantity,  # 시장가 주문은 전량 체결
            fee=fee,
            created_at=datetime.now(),
        )

    async def sell_market_order(
        self,
        ticker: str,
        volume: float,
    ) -> _Order:
        """
        Execute a market sell order (simulated).

        시뮬레이션된 시장가 매도를 실행합니다.
        가상 잔액을 업데이트하고 수수료를 차감합니다.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            volume: Volume of coin to sell

        Returns:
            Mock Order with execution details

        Raises:
            ValueError: Insufficient coin balance
        """
        price = await self.get_current_price(ticker)
        amount = price * volume
        fee = amount * self.config.simulated_fee_rate

        coin = ticker.split("-")[1] if "-" in ticker else ticker

        current_balance = self._balance.coin_balances.get(coin, 0.0)

        if current_balance < volume:
            raise ValueError(
                f"잔액 부족: 필요 {volume:.8f} {coin}, 보유 {current_balance:.8f} {coin}"
            )

        # Update coin balance
        self._balance.coin_balances[coin] = current_balance - volume

        # Update KRW balance
        self._balance.krw_balance += amount - fee

        return _Order(
            uuid=str(uuid.uuid4()),
            ticker=ticker,
            side="ask",
            order_type="market",
            price=price,
            volume=volume,
            executed_volume=volume,  # 시장가 주문은 전량 체결
            fee=fee,
            created_at=datetime.now(),
        )

    async def close(self) -> None:
        """Close the mock client (no-op for simulation)."""
        pass

    def get_krw_balance(self) -> float:
        """Get current KRW balance (convenience method)."""
        return self._balance.krw_balance

    def set_krw_balance(self, amount: float) -> None:
        """
        Set KRW balance to specific amount.

        @MX:WARN: 테스트넷 모드에서만 사용해야 하는 메서드
            @MX:REASON: 가상 잔액 조작용 - 테스트 목적 외 사용 금지
        """
        self._balance.krw_balance = amount
