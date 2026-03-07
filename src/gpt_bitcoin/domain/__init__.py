"""
Domain layer containing core business logic entities and value objects.

This module provides:
- Cryptocurrency enum for supported coins
- TradingStrategy enum for strategy types
- RiskTolerance enum for risk levels
- TradingDecision model for AI-generated decisions
- UserPreferences for user settings
- CoinManager for coin management
- StrategyConfig for strategy parameters
- StrategyManager for strategy selection
- TradingService for trade execution
- SecurityService for 2FA and trading limits
- AuditRepository for security audit logging

@MX:NOTE: Core domain entities follow DDD principles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field

# Import trading domain models
from gpt_bitcoin.domain.trading import (
    TradeRequest,
    TradeApproval,
    TradeResult,
    TradingService,
)
from gpt_bitcoin.domain.trading_state import TradingState, TradingStateType
from gpt_bitcoin.domain.trading_mode import TradingMode
from gpt_bitcoin.domain.testnet_config import MockBalance, TestnetConfig
from gpt_bitcoin.domain.security import (
    SecurityService,
    SecuritySettings,
    SecuritySettingsModel,
    SecurityError,
    PinNotSetError,
    PinAlreadySetError,
    SecurityLockedError,
    LimitExceededError,
)
from gpt_bitcoin.domain.audit import AuditRecord, AuditRepository, AuditError
from gpt_bitcoin.domain.trade_history import (
    TradeRecord as TradeHistoryRecord,
    TradeType,
    TradeHistoryService,
    TradeHistoryError,
)


class Cryptocurrency(str, Enum):
    """
    Supported cryptocurrency tickers.

    Each enum value represents a cryptocurrency that can be traded
    on the Upbit exchange in KRW market.

    @MX:NOTE: Ticker format is KRW-{SYMBOL} for KRW market pairs.
    """

    BTC = "KRW-BTC"
    ETH = "KRW-ETH"
    SOL = "KRW-SOL"
    XRP = "KRW-XRP"
    ADA = "KRW-ADA"
    DOGE = "KRW-DOGE"
    AVAX = "KRW-AVAX"
    DOT = "KRW-DOT"

    @property
    def symbol(self) -> str:
        """Get the coin symbol without KRW- prefix."""
        return self.value.replace("KRW-", "")


class TradingStrategy(str, Enum):
    """Trading strategy types."""
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"
    custom = "custom"


class RiskTolerance(str, Enum):
    """Risk tolerance levels for portfolio management."""
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


class TradingDecision(BaseModel):
    """
    AI-generated trading decision.

    Attributes:
        decision: Trading action - buy, sell, or hold
        percentage: Percentage of balance to trade
        reason: Reasoning for the decision
        timestamp: ISO timestamp of the decision
        roi: Return on investment percentage
        btc_balance: BTC balance at decision time
        krw_balance: KRW balance at decision time
        btc_avg_buy_price: Average BTC buy price
        btc_krw_price: BTC/KRW price at execution
    """

    decision: Literal["buy", "sell", "hold"]
    percentage: float = Field(ge=0, le=100, description="Percentage of balance to trade")
    reason: str = Field(default="", description="Reasoning for the decision")
    timestamp: str | None = None
    roi: float | None = Field(default=None, description="Return on investment percentage")
    btc_balance: float = Field(default=0.0, description="BTC balance at decision time")
    krw_balance: float = Field(default=0_000_000.0, description="KRW balance at decision time")
    btc_avg_buy_price: float = Field(default=0_000_000.0, description="Average BTC buy price")
    btc_krw_price: float = Field(default=0_500_000_000.0, description="BTC/KRW price at execution")


class UserPreferences(BaseModel):
    """
    User preferences for trading configuration.

    Stores user's selected cryptocurrency and risk tolerance settings.

    Attributes:
        selected_coin: Currently selected cryptocurrency for trading
        risk_tolerance: User's risk tolerance level

    @MX:NOTE: Preferences can be persisted and restored across sessions.
    """

    selected_coin: Cryptocurrency = Field(
        default=Cryptocurrency.BTC,
        description="Currently selected cryptocurrency",
    )
    risk_tolerance: Literal["conservative", "balanced", "aggressive"] = Field(
        default="balanced",
        description="User's risk tolerance level",
    )


class CoinManager:
    """
    Manager for cryptocurrency selection and information.

    Provides functionality for:
    - Getting and setting the current selected coin
    - Retrieving Upbit ticker symbols
    - Getting coin information

    Example:
        ```python
        manager = CoinManager()
        manager.set_coin(Cryptocurrency.ETH)
        ticker = manager.get_ticker()  # Returns "KRW-ETH"
        ```
    """

    # Coin information database
    COIN_INFO: dict[Cryptocurrency, dict[str, str]] = {
        Cryptocurrency.BTC: {
            "name": "Bitcoin",
            "ticker": "KRW-BTC",
            "description": "Original cryptocurrency, digital gold",
        },
        Cryptocurrency.ETH: {
            "name": "Ethereum",
            "ticker": "KRW-ETH",
            "description": "Smart contract platform",
        },
        Cryptocurrency.SOL: {
            "name": "Solana",
            "ticker": "KRW-SOL",
            "description": "High-performance blockchain",
        },
        Cryptocurrency.XRP: {
            "name": "Ripple",
            "ticker": "KRW-XRP",
            "description": "Cross-border payment solution",
        },
        Cryptocurrency.ADA: {
            "name": "Cardano",
            "ticker": "KRW-ADA",
            "description": "Proof-of-stake blockchain",
        },
        Cryptocurrency.DOGE: {
            "name": "Dogecoin",
            "ticker": "KRW-DOGE",
            "description": "Meme cryptocurrency",
        },
        Cryptocurrency.AVAX: {
            "name": "Avalanche",
            "ticker": "KRW-AVAX",
            "description": "High-throughput blockchain",
        },
        Cryptocurrency.DOT: {
            "name": "Polkadot",
            "ticker": "KRW-DOT",
            "description": "Multi-chain protocol",
        },
    }

    def __init__(self, preferences: UserPreferences | None = None):
        """
        Initialize CoinManager.

        Args:
            preferences: User preferences (creates default if not provided)
        """
        self._preferences = preferences or UserPreferences()

    @property
    def preferences(self) -> UserPreferences:
        """Get current user preferences."""
        return self._preferences

    def get_current_coin(self) -> Cryptocurrency:
        """
        Get the currently selected cryptocurrency.

        Returns:
            The currently selected Cryptocurrency enum value
        """
        return self._preferences.selected_coin

    def set_coin(self, coin: Cryptocurrency) -> None:
        """
        Set the current cryptocurrency.

        Args:
            coin: The cryptocurrency to select
        """
        self._preferences.selected_coin = coin

    def get_ticker(self) -> str:
        """
        Get the Upbit ticker for the current coin.

        Returns:
            Upbit ticker string (e.g., "KRW-BTC")
        """
        return self._preferences.selected_coin.value

    def get_ticker_for_coin(self, coin: Cryptocurrency) -> str:
        """
        Get the Upbit ticker for a specific coin.

        Args:
            coin: The cryptocurrency to get ticker for

        Returns:
            Upbit ticker string
        """
        return coin.value

    def get_supported_coins(self) -> list[Cryptocurrency]:
        """
        Get list of all supported cryptocurrencies.

        Returns:
            List of Cryptocurrency enum values
        """
        return list(Cryptocurrency)

    def is_coin_supported(self, coin: Cryptocurrency) -> bool:
        """
        Check if a cryptocurrency is supported.

        Args:
            coin: The cryptocurrency to check

        Returns:
            True if the coin is supported
        """
        return coin in Cryptocurrency

    def get_coin_info(self, coin: Cryptocurrency) -> dict[str, str] | None:
        """
        Get detailed information about a cryptocurrency.

        Args:
            coin: The cryptocurrency to get info for

        Returns:
            Dictionary with coin information or None if not found
        """
        return self.COIN_INFO.get(coin)


class StrategyConfig(BaseModel):
    """
    Configuration parameters for a trading strategy.

    Defines the parameters that control trading behavior including
    buy/sell limits and technical indicator thresholds.

    @MX:NOTE: Each strategy type has predefined configurations.
    """

    max_buy_percentage: float = Field(
        default=30.0,
        ge=0,
        le=100,
        description="Maximum percentage of balance for buy orders",
    )
    max_sell_percentage: float = Field(
        default=50.0,
        ge=0,
        le=100,
        description="Maximum percentage of holdings for sell orders",
    )
    rsi_oversold: float = Field(
        default=30.0,
        ge=0,
        le=100,
        description="RSI threshold for oversold condition",
    )
    rsi_overbought: float = Field(
        default=70.0,
        ge=0,
        le=100,
        description="RSI threshold for overbought condition",
    )
    stop_loss_percentage: float = Field(
        default=5.0,
        ge=0,
        le=50,
        description="Stop loss percentage",
    )
    take_profit_percentage: float = Field(
        default=10.0,
        ge=0,
        le=100,
        description="Take profit percentage",
    )

    @classmethod
    def conservative(cls) -> "StrategyConfig":
        """Get conservative strategy configuration."""
        return cls(
            max_buy_percentage=20.0,
            max_sell_percentage=30.0,
            rsi_oversold=25.0,
            rsi_overbought=75.0,
            stop_loss_percentage=3.0,
            take_profit_percentage=8.0,
        )

    @classmethod
    def balanced(cls) -> "StrategyConfig":
        """Get balanced strategy configuration."""
        return cls(
            max_buy_percentage=35.0,
            max_sell_percentage=60.0,
            rsi_oversold=30.0,
            rsi_overbought=70.0,
            stop_loss_percentage=5.0,
            take_profit_percentage=12.0,
        )

    @classmethod
    def aggressive(cls) -> "StrategyConfig":
        """Get aggressive strategy configuration."""
        return cls(
            max_buy_percentage=50.0,
            max_sell_percentage=100.0,
            rsi_oversold=35.0,
            rsi_overbought=70.0,
            stop_loss_percentage=8.0,
            take_profit_percentage=20.0,
        )


class StrategyManager:
    """
    Manager for trading strategy selection and configuration.

    Provides functionality for:
    - Getting and setting the current trading strategy
    - Retrieving strategy-specific configuration parameters
    - Loading instruction files for AI prompts
    - Mapping risk tolerance to strategies

    Example:
        ```python
        manager = StrategyManager(strategy=TradingStrategy.aggressive)
        config = manager.get_config()
        prompt = manager.get_system_prompt()
        ```
    """

    # Mapping of strategies to instruction files
    INSTRUCTION_FILES: dict[TradingStrategy, str] = {
        TradingStrategy.conservative: "instructions.md",
        TradingStrategy.balanced: "instructions.md",  # v1 default
        TradingStrategy.aggressive: "instructions_v3.md",
        TradingStrategy.custom: "instructions.md",
    }

    # Default system prompt template
    DEFAULT_PROMPT = """You are a cryptocurrency trading assistant.
Analyze the provided market data and make trading decisions.
Current strategy: {strategy}
Max buy: {max_buy}% | Max sell: {max_sell}%
RSI oversold: {rsi_oversold} | RSI overbought: {rsi_overbought}
"""

    def __init__(
        self,
        strategy: TradingStrategy = TradingStrategy.balanced,
        instructions_dir: str = ".",
    ):
        """
        Initialize StrategyManager.

        Args:
            strategy: Initial trading strategy
            instructions_dir: Directory containing instruction files
        """
        self._current_strategy = strategy
        self._instructions_dir = Path(instructions_dir)

    @property
    def current_strategy(self) -> TradingStrategy:
        """Get the current trading strategy."""
        return self._current_strategy

    def set_strategy(self, strategy: TradingStrategy) -> None:
        """
        Set the current trading strategy.

        Args:
            strategy: The strategy to use
        """
        self._current_strategy = strategy

    def get_config(self) -> StrategyConfig:
        """
        Get configuration for the current strategy.

        Returns:
            StrategyConfig with parameters for current strategy
        """
        return self.get_config_for_strategy(self._current_strategy)

    def get_config_for_strategy(self, strategy: TradingStrategy) -> StrategyConfig:
        """
        Get configuration for a specific strategy.

        Args:
            strategy: The strategy to get config for

        Returns:
            StrategyConfig with parameters for the specified strategy
        """
        config_map = {
            TradingStrategy.conservative: StrategyConfig.conservative,
            TradingStrategy.balanced: StrategyConfig.balanced,
            TradingStrategy.aggressive: StrategyConfig.aggressive,
            TradingStrategy.custom: StrategyConfig.balanced,
        }
        return config_map.get(strategy, StrategyConfig.balanced)()

    def get_instruction_file(self) -> Path:
        """
        Get the instruction file path for current strategy.

        Returns:
            Path to the instruction file
        """
        filename = self.INSTRUCTION_FILES.get(
            self._current_strategy,
            "instructions.md",
        )
        return self._instructions_dir / filename

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for AI based on current strategy.

        Returns:
            System prompt string with strategy-specific parameters
        """
        config = self.get_config()

        # Try to load from instruction file
        instruction_file = self.get_instruction_file()
        if instruction_file.exists():
            try:
                return instruction_file.read_text(encoding="utf-8")
            except Exception:
                pass

        # Fall back to default prompt
        return self.DEFAULT_PROMPT.format(
            strategy=self._current_strategy.value,
            max_buy=config.max_buy_percentage,
            max_sell=config.max_sell_percentage,
            rsi_oversold=config.rsi_oversold,
            rsi_overbought=config.rsi_overbought,
        )

    def strategy_from_risk_tolerance(
        self,
        risk_tolerance: RiskTolerance,
    ) -> TradingStrategy:
        """
        Map risk tolerance to trading strategy.

        Args:
            risk_tolerance: User's risk tolerance level

        Returns:
            Corresponding TradingStrategy
        """
        mapping = {
            RiskTolerance.conservative: TradingStrategy.conservative,
            RiskTolerance.balanced: TradingStrategy.balanced,
            RiskTolerance.aggressive: TradingStrategy.aggressive,
        }
        return mapping.get(risk_tolerance, TradingStrategy.balanced)


__all__ = [
    "Cryptocurrency",
    "TradingStrategy",
    "RiskTolerance",
    "TradingDecision",
    "UserPreferences",
    "CoinManager",
    "StrategyConfig",
    "StrategyManager",
    # Trading domain
    "TradingState",
    "TradingStateType",
    "TradeRequest",
    "TradeApproval",
    "TradeResult",
    "TradingService",
    # Trading mode
    "TradingMode",
    "MockBalance",
    "TestnetConfig",
    # Security domain
    "SecurityService",
    "SecuritySettings",
    "SecuritySettingsModel",
    "SecurityError",
    "PinNotSetError",
    "PinAlreadySetError",
    "SecurityLockedError",
    "LimitExceededError",
    # Audit domain
    "AuditRecord",
    "AuditRepository",
    "AuditError",
    # Trade history domain
    "TradeHistoryRecord",
    "TradeType",
    "TradeHistoryService",
    "TradeHistoryError",
]
