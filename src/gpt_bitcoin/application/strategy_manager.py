"""
Strategy manager for instruction file loading and caching.

This module provides:
- Instruction file loading with priority chain
- Template variable substitution
- File modification time tracking and auto-reload
- Graceful error handling with fallback
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from gpt_bitcoin.application.instruction_template import (
    InstructionTemplateEngine,
    TemplateVariables,
)
from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy
from gpt_bitcoin.infrastructure.exceptions import DataFetchError

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """
    Cache entry with modification time tracking.

    Attributes:
        content: Cached instruction content
        mtime: File modification time
        loaded_at: Cache load timestamp
    """

    content: str
    mtime: float
    loaded_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.loaded_at > ttl_seconds


class StrategyManager:
    """
    Manages instruction file loading with caching and template substitution.

    @MX:NOTE Instruction loading follows priority chain:
        1. coin_specific/{coin}/{strategy}.md
        2. current/{strategy}.md
        3. base.md (fallback)

    Attributes:
        instructions_dir: Root directory for instruction files
        cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        template_engine: Template substitution engine
    """

    def __init__(
        self,
        instructions_dir: str = "instructions",
        cache_ttl_seconds: int = 3600,
    ):
        """
        Initialize strategy manager.

        Args:
            instructions_dir: Root directory for instruction files
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self.instructions_dir = Path(instructions_dir)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.template_engine = InstructionTemplateEngine(self.instructions_dir)
        self._cache: dict[str, CacheEntry] = {}
        self._cache_lock = asyncio.Lock()

        logger.info(
            "Strategy manager initialized",
            instructions_dir=str(self.instructions_dir),
            cache_ttl_seconds=cache_ttl_seconds,
        )

    async def get_instruction(
        self,
        coin: Cryptocurrency,
        strategy: TradingStrategy,
    ) -> str:
        """
        Get instruction text for coin+strategy combination.

        Priority chain:
        1. coin_specific/{coin}/{strategy}.md
        2. current/{strategy}.md
        3. base.md (fallback)

        Args:
            coin: Cryptocurrency enum value
            strategy: TradingStrategy enum value

        Returns:
            Instruction text with variables substituted

        Raises:
            DataFetchError: If all instruction files fail to load
        """
        cache_key = f"{coin.value}_{strategy.value}"

        # Check cache first
        async with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached and not cached.is_expired(self.cache_ttl_seconds):
                logger.debug(
                    "Instruction cache hit",
                    coin=coin.value,
                    strategy=strategy.value,
                )
                return cached.content

            elif cached:
                # Cache expired, check for file changes
                file_path = self._get_coin_specific_path(coin, strategy)
                if file_path.exists():
                    current_mtime = file_path.stat().st_mtime
                    if current_mtime <= cached.mtime:
                        # File not modified, use cached content
                        return cached.content

                # File modified, invalidate cache
                del self._cache[cache_key]
                logger.debug(
                    "Instruction cache invalidated (file modified)",
                    coin=coin.value,
                    strategy=strategy.value,
                )

        # Load instruction with priority chain
        content = await self._load_instruction_with_fallback(coin, strategy)

        # Template substitution
        variables = TemplateVariables(
            coin=coin,
            ticker=coin.upbit_ticker,
            strategy=strategy,
            strategy_file=strategy.instruction_file,
        )

        rendered_content = self.template_engine.render(content, variables)

        # Store in cache
        # Determine which file was actually loaded for mtime tracking
        coin_specific_path = self._get_coin_specific_path(coin, strategy)
        strategy_path = self._get_strategy_path(strategy)
        base_path = self.instructions_dir / "base.md"

        if coin_specific_path.exists():
            file_path = coin_specific_path
        elif strategy_path.exists():
            file_path = strategy_path
        else:
            file_path = base_path

        mtime = file_path.stat().st_mtime if file_path.exists() else time.time()

        async with self._cache_lock:
            self._cache[cache_key] = CacheEntry(
                content=rendered_content,
                mtime=mtime,
            )
            logger.debug(
                "Instruction cached",
                coin=coin.value,
                strategy=strategy.value,
            )

        return rendered_content

    async def _load_instruction_with_fallback(
        self,
        coin: Cryptocurrency,
        strategy: TradingStrategy,
    ) -> str:
        """
        Load instruction with fallback chain.

        Args:
            coin: Cryptocurrency enum value
            strategy: TradingStrategy enum value

        Returns:
            Instruction content

        Raises:
            DataFetchError: If all instruction files fail to load
        """
        # Try coin-specific instruction
        coin_specific_path = self._get_coin_specific_path(coin, strategy)
        if coin_specific_path.exists():
            try:
                content = coin_specific_path.read_text(encoding="utf-8")
                logger.info(
                    "Loaded coin-specific instruction",
                    coin=coin.value,
                    strategy=strategy.value,
                    path=str(coin_specific_path),
                )
                return content
            except Exception as e:
                logger.warning(
                    "Failed to load coin-specific instruction, trying fallback",
                    coin=coin.value,
                    strategy=strategy.value,
                    error=str(e),
                )

        # Fallback to strategy-specific instruction
        strategy_path = self._get_strategy_path(strategy)
        if strategy_path.exists():
            try:
                content = strategy_path.read_text(encoding="utf-8")
                logger.info(
                    "Loaded strategy instruction",
                    strategy=strategy.value,
                    path=str(strategy_path),
                )
                return content
            except Exception as e:
                logger.warning(
                    "Failed to load strategy instruction, trying fallback",
                    strategy=strategy.value,
                    error=str(e),
                )

        # Fallback to base instruction
        base_path = self.instructions_dir / "base.md"
        if base_path.exists():
            try:
                content = base_path.read_text(encoding="utf-8")
                logger.warning(
                    "Using base instruction fallback",
                    coin=coin.value,
                    strategy=strategy.value,
                )
                return content
            except Exception as e:
                logger.error(
                    "Failed to load base instruction",
                    error=str(e),
                )
                raise DataFetchError(
                    f"Failed to load instruction for {coin.value}/{strategy.value}: {e}",
                    source="instruction_files",
                ) from e

        raise DataFetchError(
            f"No instruction files found for {coin.value}/{strategy.value}",
            source="instruction_files",
        )

    def _get_coin_specific_path(self, coin: Cryptocurrency, strategy: TradingStrategy) -> Path:
        """Get path to coin-specific instruction file."""
        return self.instructions_dir / "coin_specific" / coin.value / f"{strategy.value}.md"

    def _get_strategy_path(self, strategy: TradingStrategy) -> Path:
        """Get path to strategy-specific instruction file."""
        return self.instructions_dir / "current" / f"{strategy.value}.md"

    async def reload_instructions(self) -> None:
        """
        Reload all instruction files (cache invalidation).

        This clears the cache and forces reload on next access.
        """
        async with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            logger.info(
                "Instruction cache cleared (manual reload)",
                cache_size=cache_size,
            )

    async def list_available_strategies(
        self,
        coin: Cryptocurrency,
    ) -> list[TradingStrategy]:
        """
        List strategies available for a specific coin.

        Checks for coin-specific instruction files first.
        If no coin-specific files, falls back to global strategies.

        Args:
            coin: Cryptocurrency enum value

        Returns:
            List of available TradingStrategy enum values
        """
        available: list[TradingStrategy] = []

        # Check coin-specific strategies
        coin_specific_dir = self.instructions_dir / "coin_specific" / coin.value

        if coin_specific_dir.exists():
            for strategy in TradingStrategy:
                strategy_path = coin_specific_dir / f"{strategy.value}.md"
                if strategy_path.exists():
                    available.append(strategy)

        # If coin-specific strategies found, return them
        if available:
            return available

        # Otherwise, check global strategies
        for strategy in TradingStrategy:
            strategy_path = self._get_strategy_path(strategy)
            if strategy_path.exists():
                available.append(strategy)

        logger.info(
            "Available strategies for coin",
            coin=coin.value,
            strategies=[s.value for s in available],
        )

        return available

    async def get_strategy_metadata(
        self,
        strategy: TradingStrategy,
    ) -> dict[str, any]:
        """
        Get metadata for a trading strategy.

        Args:
            strategy: TradingStrategy enum value

        Returns:
            Dictionary with strategy metadata (risk level, target return, etc.)
        """
        # Read strategy instruction file to extract metadata
        strategy_path = self._get_strategy_path(strategy)

        if not strategy_path.exists():
            raise DataFetchError(
                f"Strategy file not found: {strategy.value}",
                source="instruction_files",
            )

        content = strategy_path.read_text(encoding="utf-8")

        # Extract metadata from frontmatter
        metadata: dict[str, any] = {
            "name": strategy.value,
            "display_name": strategy.display_name,
            "instruction_file": str(strategy.instruction_file),
        }

        # Parse frontmatter for metadata
        lines = content.split("\n")
        in_frontmatter = False
        for line in lines:
            if line.startswith("> **") and "**" in line:
                # Extract key-value pair
                key_value = line[3:-2].strip()
                if ":" in key_value:
                    key, value = key_value.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    metadata[key] = value
                    in_frontmatter = True
            elif in_frontmatter and line.strip() == "":
                in_frontmatter = False

        return metadata
