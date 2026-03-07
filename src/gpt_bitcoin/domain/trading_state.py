"""
Trading state enumeration for the trading workflow.

This module defines the state machine states for trade execution,
enabling proper state transitions and validation.

@MX:NOTE: State machine follows IDLE -> VALIDATING -> PENDING_APPROVAL -> EXECUTING -> COMPLETED/FAILED
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal


class TradingState(StrEnum):
    """
    Trading state enumeration.

    Represents the lifecycle states of a trade request.

    State Transitions:
        IDLE -> VALIDATING: When a trade is requested
        VALIDATING -> PENDING_APPROVAL: When validation passes
        VALIDATING -> FAILED: When validation fails (insufficient balance, etc.)
        PENDING_APPROVAL -> EXECUTING: When user approves
        PENDING_APPROVAL -> IDLE: When user cancels
        EXECUTING -> COMPLETED: When order succeeds
        EXECUTING -> FAILED: When order fails

    @MX:NOTE: States are designed for single-threaded async execution.
    """

    IDLE = "IDLE"
    """Initial state, no active trade request."""

    VALIDATING = "VALIDATING"
    """Validating trade request (balance, parameters)."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    """Waiting for user approval to execute trade."""

    EXECUTING = "EXECUTING"
    """Executing the approved trade order."""

    COMPLETED = "COMPLETED"
    """Trade completed successfully."""

    FAILED = "FAILED"
    """Trade failed due to error."""

    CANCELLED = "CANCELLED"
    """Trade cancelled by user before execution."""


# Type alias for type checking
TradingStateType = Literal[
    "IDLE",
    "VALIDATING",
    "PENDING_APPROVAL",
    "EXECUTING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


__all__ = ["TradingState", "TradingStateType"]
