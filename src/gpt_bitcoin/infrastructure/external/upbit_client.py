"""
Async Upbit exchange API client.

This module provides an async client for interacting with Upbit exchange API,
replacing the synchronous pyupbit library with aiohttp-based implementation.

Features:
- Full async/await support
- JWT authentication
- Rate limiting compliance
- Automatic retry logic
- Type-safe responses with Pydantic
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from typing import Any, Literal

import aiohttp
from pydantic import BaseModel, Field
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.infrastructure.exceptions import (
    InsufficientBalanceError,
    UpbitAPIError,
)
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class Balance(BaseModel):
    """Account balance for a single currency."""

    currency: str = Field(..., description="Currency code (e.g., KRW, BTC)")
    balance: float = Field(default=0.0, description="Available balance")
    locked: float = Field(default=0.0, description="Locked balance in orders")
    avg_buy_price: float = Field(default=0.0, description="Average buy price")
    avg_buy_price_modified: bool = Field(default=False)
    unit_currency: str = Field(default="KRW")


class OrderbookUnit(BaseModel):
    """Single orderbook unit (bid or ask)."""

    ask_price: float = Field(..., description="Ask price")
    bid_price: float = Field(..., description="Bid price")
    ask_size: float = Field(..., description="Ask size")
    bid_size: float = Field(..., description="Bid size")


class Orderbook(BaseModel):
    """Orderbook data for a ticker."""

    market: str = Field(..., description="Market code (e.g., KRW-BTC)")
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    total_ask_size: float = Field(..., description="Total ask size")
    total_bid_size: float = Field(..., description="Total bid size")
    orderbook_units: list[OrderbookUnit] = Field(
        default_factory=list,
        description="Orderbook price levels",
    )


class OHLCV(BaseModel):
    """OHLCV candlestick data."""

    market: str = Field(..., description="Market code")
    timestamp: int = Field(..., description="Unix timestamp")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: float = Field(..., description="Trading volume")


class Order(BaseModel):
    """Order information."""

    uuid: str = Field(..., description="Order UUID")
    side: Literal["bid", "ask"] = Field(..., description="Order side")
    ord_type: Literal["limit", "price", "market"] = Field(..., description="Order type")
    price: float | None = Field(default=None, description="Order price")
    state: Literal["wait", "watch", "done", "cancel"] = Field(
        default="wait",
        description="Order state",
    )
    market: str = Field(..., description="Market code")
    created_at: str = Field(..., description="Creation timestamp")
    volume: float | None = Field(default=None, description="Order volume")
    remaining_volume: float | None = Field(default=None, description="Remaining volume")
    reserved_fee: float | None = Field(default=None)
    remaining_fee: float | None = Field(default=None)
    paid_fee: float | None = Field(default=None)
    locked: float | None = Field(default=None)
    executed_volume: float | None = Field(default=None)
    trades_count: int | None = Field(default=None)


# =============================================================================
# Upbit Client
# =============================================================================


class UpbitClient:
    """
    Async client for Upbit exchange API.

    Provides async interface for trading operations with:
    - JWT authentication
    - Rate limiting
    - Automatic retry
    - Type-safe responses

    Example:
        ```python
        async with UpbitClient(settings) as client:
            balances = await client.get_balances()
            orderbook = await client.get_orderbook("KRW-BTC")
            order = await client.buy_market_order("KRW-BTC", 10000)
        ```
    """

    BASE_URL = "https://api.upbit.com/v1"

    # Rate limits (Upbit allows 10 requests/second for private endpoints)
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 1.0  # seconds

    def __init__(
        self,
        settings: Settings | None = None,
        max_retries: int = 3,
    ):
        """
        Initialize Upbit client.

        Args:
            settings: Application settings (uses global if not provided)
            max_retries: Maximum retry attempts for failed calls
        """
        self._settings = settings or get_settings()
        self._access_key = self._settings.upbit_access_key
        self._secret_key = self._settings.upbit_secret_key
        self._max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None
        self._request_times: list[float] = []
        self._lock = asyncio.Lock()

        logger.info("Upbit client initialized")

    async def __aenter__(self) -> UpbitClient:
        """Enter async context manager."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context manager."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _generate_jwt(self, query_params: dict[str, Any] | None = None) -> str:
        """
        Generate JWT token for authentication.

        Args:
            query_params: Query parameters to include in the token

        Returns:
            JWT token string
        """
        payload = {
            "access_key": self._access_key,
            "nonce": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
        }

        if query_params:
            query_string = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
            query_hash = hashlib.sha512(query_string.encode()).hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        # Create JWT token
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

        # Sign with secret key
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self._secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode()

        return f"{message}.{signature_b64}"

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting."""
        async with self._lock:
            now = time.time()
            window_start = now - self.RATE_LIMIT_WINDOW

            # Clean old entries
            self._request_times = [t for t in self._request_times if t > window_start]

            # Check if we need to wait
            if len(self._request_times) >= self.RATE_LIMIT_REQUESTS:
                wait_time = self._request_times[0] + self.RATE_LIMIT_WINDOW - now
                if wait_time > 0:
                    logger.debug("Rate limit hit, waiting", wait_time=wait_time)
                    await asyncio.sleep(wait_time)
                    self._request_times = []

            self._request_times.append(now)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        is_private: bool = False,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            is_private: Whether this is a private endpoint

        Returns:
            API response data

        Raises:
            UpbitAPIError: If API call fails
        """
        await self._ensure_session()
        await self._check_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        headers = {}

        if is_private:
            headers["Authorization"] = f"Bearer {self._generate_jwt(params)}"

        try:
            retryer = AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=5),
                retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
                reraise=True,
            )

            async for attempt in retryer:
                with attempt:
                    logger.debug(
                        "Making Upbit API request",
                        method=method,
                        endpoint=endpoint,
                        attempt=attempt.retry_state.attempt_number,
                    )

                    async with self._session.request(
                        method,
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        data = await response.json()

                        if response.status >= 400:
                            error_msg = data.get("error", {}).get("message", "Unknown error")
                            logger.error(
                                "Upbit API error",
                                status=response.status,
                                error=error_msg,
                            )
                            raise UpbitAPIError(
                                f"Upbit API error: {error_msg}",
                                status_code=response.status,
                                response_data=data,
                            )

                        return data

        except RetryError as e:
            logger.error(
                "Upbit API call failed after retries",
                endpoint=endpoint,
                error=str(e),
            )
            raise UpbitAPIError(
                f"Upbit API call failed after {self._max_retries} retries: {e}"
            ) from e

        except aiohttp.ClientError as e:
            logger.error(
                "Upbit API connection error",
                endpoint=endpoint,
                error=str(e),
            )
            raise UpbitAPIError(f"Upbit API connection error: {e}") from e

    # =========================================================================
    # Public API Methods
    # =========================================================================

    async def get_orderbook(self, ticker: str = "KRW-BTC") -> Orderbook:
        """
        Get current orderbook for a ticker.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")

        Returns:
            Orderbook data
        """
        data = await self._request(
            "GET",
            "/orderbook",
            params={"markets": ticker},
        )

        if isinstance(data, list) and len(data) > 0:
            return Orderbook(**data[0])
        raise UpbitAPIError("Invalid orderbook response")

    async def get_ohlcv(
        self,
        ticker: str = "KRW-BTC",
        interval: str = "day",
        count: int = 30,
    ) -> list[OHLCV]:
        """
        Get OHLCV candlestick data.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            interval: Candle interval (day, minute1, minute60, etc.)
            count: Number of candles to fetch

        Returns:
            List of OHLCV data
        """
        # Map interval to API format
        interval_map = {
            "day": "days",
            "minute1": "minutes/1",
            "minute3": "minutes/3",
            "minute5": "minutes/5",
            "minute10": "minutes/10",
            "minute15": "minutes/15",
            "minute30": "minutes/30",
            "minute60": "minutes/60",
            "minute240": "minutes/240",
            "week": "weeks",
            "month": "months",
        }

        api_interval = interval_map.get(interval, "days")
        endpoint = f"/candles/{api_interval}"

        data = await self._request(
            "GET",
            endpoint,
            params={"market": ticker, "count": count},
        )

        if isinstance(data, list):
            return [
                OHLCV(
                    market=item["market"],
                    timestamp=int(
                        datetime.fromisoformat(
                            item["candle_date_time_utc"].replace("Z", "+00:00")
                        ).timestamp()
                        * 1000
                    ),
                    open=item["opening_price"],
                    high=item["high_price"],
                    low=item["low_price"],
                    close=item["trade_price"],
                    volume=item["candle_acc_trade_volume"],
                )
                for item in data
            ]
        return []

    async def get_current_price(self, ticker: str = "KRW-BTC") -> float:
        """
        Get current price for a ticker.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")

        Returns:
            Current price
        """
        data = await self._request(
            "GET",
            "/ticker",
            params={"markets": ticker},
        )

        if isinstance(data, list) and len(data) > 0:
            return float(data[0].get("trade_price", 0))
        raise UpbitAPIError("Invalid ticker response")

    # =========================================================================
    # Private API Methods
    # =========================================================================

    async def get_balances(self) -> list[Balance]:
        """
        Get account balances.

        Returns:
            List of balances for all currencies
        """
        data = await self._request("GET", "/accounts", is_private=True)

        if isinstance(data, list):
            return [
                Balance(
                    currency=item["currency"],
                    balance=float(item["balance"]),
                    locked=float(item["locked"]),
                    avg_buy_price=float(item.get("avg_buy_price", 0)),
                    avg_buy_price_modified=item.get("avg_buy_price_modified", False),
                    unit_currency=item.get("unit_currency", "KRW"),
                )
                for item in data
            ]
        return []

    async def get_balance(self, currency: str = "KRW") -> float:
        """
        Get balance for a specific currency.

        Args:
            currency: Currency code (e.g., "KRW", "BTC")

        Returns:
            Available balance
        """
        balances = await self.get_balances()
        for balance in balances:
            if balance.currency == currency:
                return balance.balance
        return 0.0

    async def buy_market_order(
        self,
        ticker: str,
        amount: float,
    ) -> Order:
        """
        Place a market buy order.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            amount: Amount in quote currency (KRW) to buy with

        Returns:
            Order information

        Raises:
            InsufficientBalanceError: If insufficient balance
        """
        # Check balance first
        krw_balance = await self.get_balance("KRW")
        if krw_balance < amount:
            raise InsufficientBalanceError(
                currency="KRW",
                available=krw_balance,
                required=amount,
            )

        data = await self._request(
            "POST",
            "/orders",
            params={
                "market": ticker,
                "side": "bid",
                "ord_type": "price",
                "price": str(amount),
            },
            is_private=True,
        )

        logger.info(
            "Buy market order placed",
            ticker=ticker,
            amount=amount,
            order_uuid=data.get("uuid"),
        )

        return Order(**data)

    async def sell_market_order(
        self,
        ticker: str,
        volume: float,
    ) -> Order:
        """
        Place a market sell order.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            volume: Volume of base currency (BTC) to sell

        Returns:
            Order information

        Raises:
            InsufficientBalanceError: If insufficient balance
        """
        # Extract base currency from ticker (e.g., "BTC" from "KRW-BTC")
        base_currency = ticker.split("-")[1] if "-" in ticker else ticker

        # Check balance first
        balance = await self.get_balance(base_currency)
        if balance < volume:
            raise InsufficientBalanceError(
                currency=base_currency,
                available=balance,
                required=volume,
            )

        data = await self._request(
            "POST",
            "/orders",
            params={
                "market": ticker,
                "side": "ask",
                "ord_type": "market",
                "volume": str(volume),
            },
            is_private=True,
        )

        logger.info(
            "Sell market order placed",
            ticker=ticker,
            volume=volume,
            order_uuid=data.get("uuid"),
        )

        return Order(**data)

    async def cancel_order(self, order_uuid: str) -> dict[str, Any]:
        """
        Cancel an order.

        Args:
            order_uuid: UUID of the order to cancel

        Returns:
            Cancellation result
        """
        data = await self._request(
            "DELETE",
            "/order",
            params={"uuid": order_uuid},
            is_private=True,
        )

        logger.info(
            "Order cancelled",
            order_uuid=order_uuid,
        )

        return data

    async def get_order(self, order_uuid: str) -> Order:
        """
        Get order information.

        Args:
            order_uuid: UUID of the order

        Returns:
            Order information
        """
        data = await self._request(
            "GET",
            "/order",
            params={"uuid": order_uuid},
            is_private=True,
        )

        return Order(**data)

    async def health_check(self) -> bool:
        """
        Check if Upbit API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            await self.get_current_price("KRW-BTC")
            return True
        except Exception as e:
            logger.error("Upbit health check failed", error=str(e))
            return False
