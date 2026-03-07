"""
Trading domain models and service for real trade execution.

This module provides:
- TradeRequest: Domain model for trade requests
- TradeApproval: Domain model for trade approval workflow
- TradeResult: Domain model for trade execution results
- TradingService: Domain service for managing trade lifecycle

@MX:NOTE: TradingService enforces approval-before-execution pattern for safety.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from gpt_bitcoin.domain.trading_state import TradingState

if TYPE_CHECKING:
    from gpt_bitcoin.config.settings import Settings
    from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient
    from gpt_bitcoin.infrastructure.logging import BoundLogger as Logger


# =============================================================================
# Domain Models
# =============================================================================


@dataclass
class TradeRequest:
    """
    Internal trade request dataclass.

    Stores the original trade request details for processing.
    This is an internal representation used by TradingService.

    Attributes:
        ticker: Market ticker (e.g., "KRW-BTC")
        amount: Amount in KRW (for buy) or coin quantity (for sell)
        side: Trade side - "buy" or "sell"
        timestamp: When the request was created

    @MX:NOTE: Use TradeRequest only internally; external APIs use Pydantic models.
    """

    ticker: str
    amount: float
    side: Literal["buy", "sell"]
    timestamp: datetime = field(default_factory=datetime.now)


class TradeApproval(BaseModel):
    """
    Trade approval model for user confirmation workflow.

    Contains all information needed for the user to make an informed
    decision about approving or rejecting a trade.

    Attributes:
        request_id: Unique identifier for this approval request
        ticker: Market ticker (e.g., "KRW-BTC")
        side: Trade side - "buy" or "sell"
        amount: Amount in KRW (buy) or coin quantity (sell)
        estimated_price: Estimated execution price (current market)
        estimated_quantity: Estimated coin quantity (for buy orders)
        fee_estimate: Estimated trading fee
        warnings: List of warning messages to display
        approved: Whether the trade has been approved
        approved_at: Timestamp when approved (if approved)
        expires_at: When this approval request expires

    @MX:NOTE: Approval expires after 30 seconds to prevent stale price execution.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "req-123e4567-e89b-12d3-a456-426614174000",
                "ticker": "KRW-BTC",
                "side": "buy",
                "amount": 10000.0,
                "estimated_price": 50000000.0,
                "estimated_quantity": 0.0002,
                "fee_estimate": 5.0,
                "warnings": [],
                "approved": False,
                "approved_at": None,
                "expires_at": "2026-03-04T12:00:30Z",
            }
        }
    )

    request_id: str = Field(description="Unique identifier for this approval request")
    ticker: str = Field(description="Market ticker (e.g., KRW-BTC)")
    side: Literal["buy", "sell"] = Field(description="Trade side")
    amount: float = Field(ge=0, description="Amount in KRW (buy) or quantity (sell)")
    estimated_price: float | None = Field(default=None, description="Estimated execution price")
    estimated_quantity: float | None = Field(default=None, description="Estimated coin quantity")
    fee_estimate: float | None = Field(default=None, description="Estimated trading fee")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    approved: bool = Field(default=False, description="Whether approved")
    approved_at: datetime | None = Field(default=None, description="Approval timestamp")
    expires_at: datetime | None = Field(default=None, description="Expiration timestamp")

    def is_expired(self) -> bool:
        """Check if this approval request has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def mark_approved(self) -> None:
        """Mark this approval as approved with current timestamp."""
        self.approved = True
        self.approved_at = datetime.now()


class TradeResult(BaseModel):
    """
    Trade execution result model.

    Contains the outcome of a trade execution, whether successful or failed.

    Attributes:
        success: Whether the trade executed successfully
        order_id: Upbit order UUID (if successful)
        ticker: Market ticker that was traded
        side: Trade side that was executed
        executed_price: Actual execution price
        executed_amount: Actual executed amount/quantity
        fee: Actual fee charged
        error_message: Error message (if failed)
        timestamp: When the result was generated

    @MX:ANCHOR: TradeResult is returned by all TradingService execution methods.
        fan_in: 3 (web_ui, main.py, test_trading.py)
        @MX:REASON: Unified result model across all execution paths.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "order_id": "uuid-1234-5678",
                "ticker": "KRW-BTC",
                "side": "buy",
                "executed_price": 50000000.0,
                "executed_amount": 0.0002,
                "fee": 5.0,
                "error_message": None,
                "timestamp": "2026-03-04T12:00:00Z",
            }
        }
    )

    success: bool = Field(description="Whether trade succeeded")
    order_id: str | None = Field(default=None, description="Upbit order UUID")
    ticker: str | None = Field(default=None, description="Market ticker traded")
    side: Literal["buy", "sell"] | None = Field(default=None, description="Trade side executed")
    executed_price: float | None = Field(default=None, description="Actual execution price")
    executed_amount: float | None = Field(default=None, description="Actual amount/quantity")
    fee: float | None = Field(default=None, description="Actual fee charged")
    error_message: str | None = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.now, description="Result timestamp")


# =============================================================================
# Trading Service
# =============================================================================


class TradingService:
    """
    Domain service for managing trade lifecycle.

    This service enforces the approval-before-execution pattern:
    1. User requests a trade (buy/sell)
    2. Service validates and returns approval request
    3. User reviews and approves
    4. Service executes the approved trade

    State Management:
        - Maintains internal state for the current trade request
        - Only one trade can be processed at a time
        - State transitions follow TradingState enum

    Example:
        ```python
        service = TradingService(upbit_client, settings, logger)

        # Step 1: Request buy order
        approval = await service.request_buy_order("KRW-BTC", 10000)

        # Step 2: User reviews approval details
        print(f"Buying {approval.estimated_quantity} BTC for {approval.amount} KRW")

        # Step 3: User approves and execution
        approval.mark_approved()
        result = await service.execute_approved_trade(approval)

        if result.success:
            print(f"Order placed: {result.order_id}")
        ```

    @MX:NOTE: TradingService is stateful and not thread-safe.
        Use separate instances for concurrent trading.
    """

    # Approval timeout in seconds
    APPROVAL_TIMEOUT_SECONDS: int = 30

    # Minimum order amount in KRW (Upbit policy)
    MIN_ORDER_KRW: float = 5000.0

    def __init__(
        self,
        upbit_client: UpbitClient,
        settings: Settings,
        logger: Logger | None = None,
    ):
        """
        Initialize TradingService.

        Args:
            upbit_client: Upbit API client for order execution
            settings: Application settings for configuration
            logger: Optional logger for logging (creates default if None)
        """
        self._upbit_client = upbit_client
        self._settings = settings
        self._logger = logger

        # Internal state
        self._state = TradingState.IDLE
        self._pending_request: TradeRequest | None = None

    @property
    def state(self) -> TradingState:
        """Get current trading state."""
        return self._state

    @property
    def pending_request(self) -> TradeRequest | None:
        """Get current pending request (if any)."""
        return self._pending_request

    async def request_buy_order(
        self,
        ticker: str,
        amount_krw: float,
    ) -> TradeApproval:
        """
        Request a buy order and return approval details.

        Validates the order parameters and checks balance before
        creating an approval request for user confirmation.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            amount_krw: Amount in KRW to buy with

        Returns:
            TradeApproval: Approval request with estimated details

        Raises:
            ValueError: If amount is below minimum or balance insufficient

        @MX:NOTE: This method does NOT execute the trade.
            User must approve via execute_approved_trade().
        """
        # Transition to validating state
        self._state = TradingState.VALIDATING

        try:
            # Validate minimum order amount
            if amount_krw < self.MIN_ORDER_KRW:
                raise ValueError(
                    f"최소 주문 금액은 {self.MIN_ORDER_KRW:,.0f} KRW입니다"
                )

            # Check KRW balance
            krw_balance = await self._upbit_client.get_balance("KRW")
            if krw_balance < amount_krw:
                raise ValueError(
                    f"잔액 부족: 필요 {amount_krw:,.0f} KRW, 보유 {krw_balance:,.0f} KRW"
                )

            # Create pending request
            self._pending_request = TradeRequest(
                ticker=ticker,
                amount=amount_krw,
                side="buy",
                timestamp=datetime.now(),
            )

            # Get current price for estimation
            try:
                orderbook = await self._upbit_client.get_orderbook(ticker)
                estimated_price = (
                    orderbook.orderbook_units[0].ask_price
                    if orderbook.orderbook_units
                    else None
                )
                estimated_quantity = (
                    amount_krw / estimated_price if estimated_price else None
                )
            except Exception:
                # If we can't get price, proceed without estimation
                estimated_price = None
                estimated_quantity = None

            # Transition to pending approval
            self._state = TradingState.PENDING_APPROVAL

            # Create approval request
            return TradeApproval(
                request_id=str(uuid.uuid4()),
                ticker=ticker,
                side="buy",
                amount=amount_krw,
                estimated_price=estimated_price,
                estimated_quantity=estimated_quantity,
                fee_estimate=amount_krw * 0.0005,  # 0.05% fee estimate
                warnings=[],
                expires_at=datetime.now() + timedelta(seconds=self.APPROVAL_TIMEOUT_SECONDS),
            )

        except Exception:
            # Reset state on error
            self._state = TradingState.IDLE
            self._pending_request = None
            raise

    async def request_sell_order(
        self,
        ticker: str,
        quantity: float,
    ) -> TradeApproval:
        """
        Request a sell order and return approval details.

        Validates the order parameters and checks coin holdings before
        creating an approval request for user confirmation.

        Args:
            ticker: Market ticker (e.g., "KRW-BTC")
            quantity: Quantity of coins to sell

        Returns:
            TradeApproval: Approval request with estimated details

        Raises:
            ValueError: If quantity is invalid or holdings insufficient

        @MX:NOTE: This method does NOT execute the trade.
            User must approve via execute_approved_trade().
        """
        # Transition to validating state
        self._state = TradingState.VALIDATING

        try:
            # Validate quantity
            if quantity <= 0:
                raise ValueError("매도 수량은 0보다 커야 합니다")

            # Extract base currency from ticker (e.g., "BTC" from "KRW-BTC")
            base_currency = ticker.split("-")[1] if "-" in ticker else ticker

            # Check coin balance
            coin_balance = await self._upbit_client.get_balance(base_currency)
            if coin_balance < quantity:
                raise ValueError(
                    f"보유량 부족: 필요 {quantity} {base_currency}, 보유 {coin_balance} {base_currency}"
                )

            # Create pending request
            self._pending_request = TradeRequest(
                ticker=ticker,
                amount=quantity,
                side="sell",
                timestamp=datetime.now(),
            )

            # Get current price for estimation
            try:
                orderbook = await self._upbit_client.get_orderbook(ticker)
                estimated_price = (
                    orderbook.orderbook_units[0].bid_price
                    if orderbook.orderbook_units
                    else None
                )
            except Exception:
                estimated_price = None

            # Transition to pending approval
            self._state = TradingState.PENDING_APPROVAL

            # Create approval request
            return TradeApproval(
                request_id=str(uuid.uuid4()),
                ticker=ticker,
                side="sell",
                amount=quantity,
                estimated_price=estimated_price,
                estimated_quantity=quantity,
                fee_estimate=(estimated_price or 0) * quantity * 0.0005,  # 0.05% fee
                warnings=[],
                expires_at=datetime.now() + timedelta(seconds=self.APPROVAL_TIMEOUT_SECONDS),
            )

        except Exception:
            # Reset state on error
            self._state = TradingState.IDLE
            self._pending_request = None
            raise

    async def execute_approved_trade(
        self,
        approval: TradeApproval,
    ) -> TradeResult:
        """
        Execute an approved trade.

        Validates the approval and executes the trade through Upbit API.
        The approval must be marked as approved and not expired.

        Args:
            approval: The approved trade request

        Returns:
            TradeResult: Result of the trade execution

        @MX:WARN: This method executes REAL trades with REAL money.
            Ensure user has explicitly approved before calling.
            @MX:REASON: Direct API call to Upbit exchange with financial impact.

        @MX:ANCHOR: execute_approved_trade is the single entry point for trade execution.
            fan_in: 3 (buy flow, sell flow, test mocks)
            @MX:REASON: Centralizes all trade execution for consistent error handling.
        """
        # Validate approval
        if not approval.approved:
            return TradeResult(
                success=False,
                ticker=approval.ticker,
                side=approval.side,
                error_message="승인되지 않은 거래입니다",
            )

        if approval.is_expired():
            self._state = TradingState.FAILED
            self._pending_request = None
            return TradeResult(
                success=False,
                ticker=approval.ticker,
                side=approval.side,
                error_message="승인이 만료되었습니다. 다시 요청해주세요",
            )

        # Verify pending request matches
        if self._pending_request is None:
            return TradeResult(
                success=False,
                ticker=approval.ticker,
                side=approval.side,
                error_message="대기 중인 주문 요청이 없습니다",
            )

        # Transition to executing state
        self._state = TradingState.EXECUTING

        try:
            # Execute the trade
            if self._pending_request.side == "buy":
                order = await self._upbit_client.buy_market_order(
                    ticker=approval.ticker,
                    amount=approval.amount,
                )
            else:
                order = await self._upbit_client.sell_market_order(
                    ticker=approval.ticker,
                    volume=approval.amount,
                )

            # Transition to completed
            self._state = TradingState.COMPLETED

            # Log success
            if self._logger:
                self._logger.info(
                    "Trade executed successfully",
                    order_id=order.uuid,
                    ticker=approval.ticker,
                    side=approval.side,
                    amount=approval.amount,
                )

            return TradeResult(
                success=True,
                order_id=order.uuid,
                ticker=approval.ticker,
                side=approval.side,
                executed_price=order.price,
                executed_amount=order.executed_volume or order.volume,
                fee=order.fee,
            )

        except Exception as e:
            # Transition to failed
            self._state = TradingState.FAILED

            error_msg = str(e)

            # Log error
            if self._logger:
                self._logger.error(
                    "Trade execution failed",
                    error=error_msg,
                    ticker=approval.ticker,
                    side=approval.side,
                )

            return TradeResult(
                success=False,
                ticker=approval.ticker,
                side=approval.side,
                error_message=error_msg,
            )

        finally:
            # Reset state
            self._pending_request = None
            self._state = TradingState.IDLE

    def cancel_pending_request(self) -> None:
        """
        Cancel the current pending request.

        Resets the service to IDLE state and clears any pending request.
        """
        self._state = TradingState.IDLE
        self._pending_request = None


__all__ = [
    "TradeApproval",
    "TradeRequest",
    "TradeResult",
    "TradingService",
]
