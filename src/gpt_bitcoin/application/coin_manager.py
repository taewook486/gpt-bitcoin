"""
Coin manager for multi-coin data collection and portfolio management.

This module provides:
- Parallel market data fetching for multiple coins
- Portfolio aggregation and status tracking
- Coin-specific error handling with graceful degradation
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency

logger = structlog.get_logger(__name__)


@dataclass
class MarketData:
    """
    Market data for a single cryptocurrency.

    Attributes:
        coin: Cryptocurrency enum value
        ticker: Upbit ticker symbol
        current_price: Current price in KRW
        price_change_24h: 24-hour price change percentage
        volume_24h: 24-hour trading volume in KRW
        high_24h: 24-hour high price
        low_24h: 24-hour low price
        timestamp: Data fetch timestamp
    """

    coin: Cryptocurrency
    ticker: str
    current_price: float
    price_change_24h: float = 0.0
    volume_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CoinPosition:
    """
    Position for a single cryptocurrency in portfolio.

    Attributes:
        coin: Cryptocurrency enum value
        balance: Balance in coin units
        avg_buy_price: Average buy price in KRW
        current_price: Current price in KRW
        value_krw: Current value in KRW
        profit_loss_krw: Profit/Loss in KRW
        profit_loss_percentage: Profit/Loss percentage
    """

    coin: Cryptocurrency
    balance: float = 0.0
    avg_buy_price: float = 0.0
    current_price: float = 0.0
    value_krw: float = 0.0
    profit_loss_krw: float = 0.0
    profit_loss_percentage: float = 0.0

    def update_with_price(self, current_price: float) -> None:
        """Update position with current price."""
        self.current_price = current_price
        self.value_krw = self.balance * current_price
        if self.avg_buy_price > 0:
            self.profit_loss_krw = self.value_krw - (self.balance * self.avg_buy_price)
            self.profit_loss_percentage = (
                (self.profit_loss_krw / (self.balance * self.avg_buy_price)) * 100
                if self.avg_buy_price > 0
                else 0.0
            )


@dataclass
class PortfolioStatus:
    """
    Aggregated portfolio status across all coins.

    Attributes:
        total_value_krw: Total portfolio value in KRW
        total_profit_loss_krw: Total profit/loss in KRW
        total_profit_loss_percentage: Total profit/loss percentage
        positions: Dictionary of coin to position
        allocation_percentages: Dictionary of coin to allocation percentage
        updated_at: Last update timestamp
    """

    total_value_krw: float = 0.0
    total_profit_loss_krw: float = 0.0
    total_profit_loss_percentage: float = 0.0
    positions: dict[Cryptocurrency, CoinPosition] = field(default_factory=dict)
    allocation_percentages: dict[Cryptocurrency, float] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_position(self, coin: Cryptocurrency) -> CoinPosition | None:
        """Get position for a specific coin."""
        return self.positions.get(coin)


class CoinManager:
    """
    Manages multi-coin data collection and portfolio tracking.

    @MX:NOTE This class provides the central point for multi-coin operations.
        Uses parallel async fetching for efficiency.
        Gracefully handles individual coin failures.

    Attributes:
        upbit_client: Upbit API client for market data
        request_timeout: Timeout for individual requests (seconds)
        max_concurrent_requests: Maximum concurrent API requests
    """

    def __init__(
        self,
        upbit_client: Any,
        request_timeout: float = 10.0,
        max_concurrent_requests: int = 5,
    ):
        """
        Initialize coin manager.

        Args:
            upbit_client: Upbit API client instance
            request_timeout: Timeout for individual requests (seconds)
            max_concurrent_requests: Maximum concurrent API requests
        """
        self.upbit_client = upbit_client
        self.request_timeout = request_timeout
        self.max_concurrent_requests = max_concurrent_requests
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

        logger.info(
            "Coin manager initialized",
            request_timeout=request_timeout,
            max_concurrent_requests=max_concurrent_requests,
        )

    async def fetch_market_data(
        self,
        coins: list[Cryptocurrency],
    ) -> dict[Cryptocurrency, MarketData]:
        """
        Fetch market data for multiple coins in parallel.

        Args:
            coins: List of Cryptocurrency enum values to fetch

        Returns:
            Dictionary mapping coin to its market data.
            Failed coins are excluded from the result.

        @MX:NOTE Parallel fetching uses semaphore to limit concurrent requests.
            Failed coins are logged but don't affect others.
        """
        results: dict[Cryptocurrency, MarketData] = {}
        tasks = [self._fetch_single_coin_data(coin) for coin in coins]

        # Execute all tasks in parallel
        fetch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for coin, result in zip(coins, fetch_results):
            if isinstance(result, Exception):
                logger.warning(
                    "Failed to fetch market data for coin",
                    coin=coin.value,
                    error=str(result),
                )
                continue
            if result is not None:
                results[coin] = result

        logger.info(
            "Market data fetch complete",
            requested=len(coins),
            successful=len(results),
            failed=len(coins) - len(results),
        )

        return results

    async def _fetch_single_coin_data(
        self,
        coin: Cryptocurrency,
    ) -> MarketData | None:
        """
        Fetch market data for a single coin.

        Args:
            coin: Cryptocurrency to fetch

        Returns:
            MarketData if successful, None if failed
        """
        async with self._semaphore:
            try:
                ticker = coin.upbit_ticker

                # Fetch ticker data from Upbit
                # Using sync client in async context with executor
                loop = asyncio.get_event_loop()
                ticker_data = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.upbit_client.get_ticker(ticker),
                    ),
                    timeout=self.request_timeout,
                )

                if not ticker_data:
                    logger.warning("No ticker data returned", coin=coin.value)
                    return None

                # Parse ticker data
                # Upbit returns: {'market': 'KRW-BTC', 'trade_price': 50000000, ...}
                current_price = float(ticker_data.get("trade_price", 0))
                price_change = float(ticker_data.get("signed_change_rate", 0) * 100)
                volume = float(ticker_data.get("acc_trade_price_24h", 0))
                high = float(ticker_data.get("high_price", 0))
                low = float(ticker_data.get("low_price", 0))

                return MarketData(
                    coin=coin,
                    ticker=ticker,
                    current_price=current_price,
                    price_change_24h=price_change,
                    volume_24h=volume,
                    high_24h=high,
                    low_24h=low,
                    timestamp=datetime.now(),
                )

            except TimeoutError:
                logger.warning(
                    "Timeout fetching coin data",
                    coin=coin.value,
                    timeout=self.request_timeout,
                )
                return None
            except Exception as e:
                logger.error(
                    "Error fetching coin data",
                    coin=coin.value,
                    error=str(e),
                )
                return None

    async def get_portfolio_status(
        self,
        positions: dict[Cryptocurrency, CoinPosition],
    ) -> PortfolioStatus:
        """
        Get aggregated portfolio status across all coins.

        Args:
            positions: Dictionary of current positions per coin

        Returns:
            PortfolioStatus with aggregated values and allocation percentages
        """
        # Fetch current prices for all positions
        coins_with_positions = [coin for coin, pos in positions.items() if pos.balance > 0]

        if coins_with_positions:
            market_data = await self.fetch_market_data(coins_with_positions)

            # Update positions with current prices
            for coin, data in market_data.items():
                if coin in positions:
                    positions[coin].update_with_price(data.current_price)

        # Calculate totals
        total_value = sum(pos.value_krw for pos in positions.values())
        total_pl = sum(pos.profit_loss_krw for pos in positions.values())

        # Calculate cost basis for percentage
        total_cost = sum(
            pos.balance * pos.avg_buy_price for pos in positions.values() if pos.avg_buy_price > 0
        )

        total_pl_percentage = (total_pl / total_cost * 100) if total_cost > 0 else 0.0

        # Calculate allocation percentages
        allocations: dict[Cryptocurrency, float] = {}
        if total_value > 0:
            for coin, pos in positions.items():
                allocations[coin] = (pos.value_krw / total_value) * 100

        status = PortfolioStatus(
            total_value_krw=total_value,
            total_profit_loss_krw=total_pl,
            total_profit_loss_percentage=total_pl_percentage,
            positions=positions,
            allocation_percentages=allocations,
            updated_at=datetime.now(),
        )

        logger.info(
            "Portfolio status calculated",
            total_value_krw=total_value,
            total_pl_krw=total_pl,
            total_pl_percentage=round(total_pl_percentage, 2),
            coins=len(positions),
        )

        return status

    async def get_coin_balances(
        self,
        coins: list[Cryptocurrency],
    ) -> dict[Cryptocurrency, float]:
        """
        Get balances for multiple coins from Upbit.

        Args:
            coins: List of coins to check balances for

        Returns:
            Dictionary mapping coin to balance in coin units
        """
        balances: dict[Cryptocurrency, float] = {}

        try:
            # Fetch all accounts from Upbit
            loop = asyncio.get_event_loop()
            accounts = await loop.run_in_executor(
                None,
                lambda: self.upbit_client.get_accounts(),
            )

            # Map accounts to coins
            for account in accounts:
                currency = account.get("currency", "")
                balance = float(account.get("balance", 0))

                try:
                    coin = Cryptocurrency(currency)
                    if coin in coins:
                        balances[coin] = balance
                except ValueError:
                    # Not a supported cryptocurrency
                    pass

            logger.info(
                "Balances fetched",
                requested=len(coins),
                found=len(balances),
            )

        except Exception as e:
            logger.error(
                "Failed to fetch balances",
                error=str(e),
            )

        # Initialize missing coins with zero balance
        for coin in coins:
            if coin not in balances:
                balances[coin] = 0.0

        return balances


__all__ = [
    "CoinManager",
    "CoinPosition",
    "MarketData",
    "PortfolioStatus",
]
