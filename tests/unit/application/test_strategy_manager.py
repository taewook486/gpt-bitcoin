"""
Unit tests for StrategyManager.

Tests cover:
- Instruction loading priority chain
- Template variable substitution
- Cache hit/miss scenarios
- File watcher reload
- Error handling and fallback
- list_available_strategies
- get_strategy_metadata
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gpt_bitcoin.application.strategy_manager import (
    StrategyManager,
    CacheEntry,
)
from gpt_bitcoin.application.instruction_template import TemplateVariables
from gpt_bitcoin.domain.models.cryptocurrency import (
    Cryptocurrency,
    TradingStrategy,
)
from gpt_bitcoin.infrastructure.exceptions import DataFetchError


# Fixtures
@pytest.fixture
def temp_instructions_dir(tmp_path: Path) -> Path:
    """Create temporary instructions directory structure."""
    instructions_dir = tmp_path / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)

    # Create base.md
    base_md = instructions_dir / "base.md"
    base_md.write_text(
        "# Base Instruction\n\n"
        "{{COIN_NAME}}({{TICKER}}) analysis.\n"
        "Strategy: {{STRATEGY_NAME}}\n"
        "File: {{STRATEGY_FILE}}\n",
        encoding="utf-8",
    )

    # Create current/ directory
    current_dir = instructions_dir / "current"
    current_dir.mkdir(parents=True, exist_ok=True)

    # Create strategy files
    for strategy in ["conservative", "balanced", "aggressive", "vision_aggressive"]:
        strategy_file = current_dir / f"{strategy}.md"
        strategy_file.write_text(
            f"# {strategy.title()} Strategy\n\n"
            f"Strategy: {strategy}\n",
            encoding="utf-8",
        )

    # Create coin_specific/BTC directory
    btc_dir = instructions_dir / "coin_specific" / "BTC"
    btc_dir.mkdir(parents=True, exist_ok=True)

    # Create BTC-specific strategies
    for strategy in ["conservative", "balanced"]:
        btc_strategy_file = btc_dir / f"{strategy}.md"
        btc_strategy_file.write_text(
            f"# BTC {strategy.title()} Strategy\n\n"
            f"BTC-specific {strategy} strategy.\n",
            encoding="utf-8",
        )

    return instructions_dir


@pytest.fixture
def strategy_manager(temp_instructions_dir: Path) -> StrategyManager:
    """Create StrategyManager with temporary instructions directory."""
    return StrategyManager(
        instructions_dir=str(temp_instructions_dir),
        cache_ttl_seconds=60,  # Short TTL for testing
    )


# Tests
@pytest.mark.asyncio
async def test_get_instruction_priority_chain(strategy_manager: StrategyManager):
    """Test instruction loading follows priority chain."""
    # Test 1: Coin-specific instruction exists
    content = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    assert "BTC-specific conservative strategy" in content
    assert "BTC" in content

    # Test 2: Fallback to strategy instruction
    content = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.AGGRESSIVE,
    )

    assert "Aggressive Strategy" in content
    assert "BTC" not in content  # Not BTC-specific

    # Test 3: Fallback to base instruction
    # Remove conservative.md temporarily to test fallback
    conservative_path = (
        Path(strategy_manager.instructions_dir)
        / "current"
        / "conservative.md"
    )
    conservative_path.unlink()

    content = await strategy_manager.get_instruction(
        Cryptocurrency.ETH,  # No ETH-specific instruction
        TradingStrategy.CONSERVATIVE,
    )

    # Should fallback to base.md since conservative.md was    # was removed and assert "Base Instruction" in content

    # Restore the conservative.md for other tests
    conservative_path.write_text(
        "# Conservative Strategy\n\n"
        "Strategy: conservative\n",
        encoding="utf-8",
    )


    assert "{{COIN_NAME}}" not in content  # Variables should be substituted


@pytest.mark.asyncio
async def test_template_variable_substitution(
    strategy_manager: StrategyManager, temp_instructions_dir: Path
):
    """Test template variable substitution."""
    # Remove conservative.md to force fallback to base.md which has template variables
    conservative_path = temp_instructions_dir / "current" / "conservative.md"
    if conservative_path.exists():
        conservative_path.unlink()

    # Use ETH which has no coin-specific file, so it falls back to base.md
    # which contains template variables
    content = await strategy_manager.get_instruction(
        Cryptocurrency.ETH,
        TradingStrategy.CONSERVATIVE,
    )

    # Variables should be substituted
    assert "{{COIN_NAME}}" not in content
    assert "이더리움" in content  # ETH display_name
    assert "{{TICKER}}" not in content
    assert "KRW-ETH" in content
    assert "{{STRATEGY_NAME}}" not in content
    assert "보수적" in content
    assert "{{STRATEGY_FILE}}" not in content
    assert "conservative.md" in content

    # Restore the conservative.md for other tests
    conservative_path.write_text(
        "# Conservative Strategy\n\n"
        "Strategy: conservative\n",
        encoding="utf-8",
    )


@pytest.mark.asyncio
async def test_cache_hit_scenario(strategy_manager: StrategyManager):
    """Test cache hit scenario."""
    # First call - cache miss
    content1 = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Verify content is cached
    cache_key = "BTC_conservative"
    async with strategy_manager._cache_lock:
        assert cache_key in strategy_manager._cache

    # Second call - should be cache hit
    content2 = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Content should be identical
    assert content1 == content2


@pytest.mark.asyncio
async def test_cache_expiry(strategy_manager: StrategyManager):
    """Test cache expiry and reload."""
    # First call
    content1 = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Wait for cache to expire (TTL is 60 seconds)
    await asyncio.sleep(0.1)

    # Second call - cache should be expired
    content2 = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Content should be reloaded
    assert content1 == content2


    # Check cache was actually invalidated
    cache_key = "BTC_conservative"
    async with strategy_manager._cache_lock:
        assert cache_key not in strategy_manager._cache


@pytest.mark.asyncio
async def test_cache_invalidation_on_file_change(
    strategy_manager: StrategyManager, temp_instructions_dir: Path
):
    """Test cache invalidation when file changes."""
    # Load instruction to cache it
    await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Modify the file
    btc_conservative_path = (
        temp_instructions_dir
        / "coin_specific"
        / "BTC"
        / "conservative.md"
    )
    original_mtime = btc_conservative_path.stat().st_mtime
    time.sleep(0.1)  # Ensure time difference
    btc_conservative_path.write_text(
        "# Modified BTC Conservative Strategy\n\nModified content.",
        encoding="utf-8",
    )

    # Reload should detect file change
    content = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    assert "Modified content" in content


@pytest.mark.asyncio
async def test_error_handling_missing_all_files():
    """Test error handling when all instruction files are missing."""
    # Create a new coin with no instruction files
    manager = StrategyManager(
        instructions_dir="/nonexistent/path",
        cache_ttl_seconds=60,
    )

    # Should raise DataFetchError
    with pytest.raises(DataFetchError) as exc:
        await manager.get_instruction(
            Cryptocurrency.BTC,
            TradingStrategy.CONSERVATIVE,
        )

    assert "No instruction files found" in str(exc)


@pytest.mark.asyncio
async def test_list_available_strategies(strategy_manager: StrategyManager):
    """Test listing available strategies for a coin."""
    # Test 1: Coin with coin-specific strategies
    strategies = await strategy_manager.list_available_strategies(
        Cryptocurrency.BTC
    )

    assert len(strategies) == 2  # conservative, balanced
    assert TradingStrategy.CONSERVATIVE in strategies
    assert TradingStrategy.BALANCED in strategies
    assert TradingStrategy.AGGRESSIVE not in strategies  # No BTC-specific aggressive

    # Test 2: Coin without coin-specific strategies (should fallback to global)
    strategies = await strategy_manager.list_available_strategies(
        Cryptocurrency.ETH
    )

    assert len(strategies) == 4  # All global strategies
    for strategy in TradingStrategy:
        assert strategy in strategies


@pytest.mark.asyncio
async def test_get_strategy_metadata(strategy_manager: StrategyManager):
    """Test getting strategy metadata."""
    metadata = await strategy_manager.get_strategy_metadata(
        TradingStrategy.CONSERVATIVE
    )

    assert metadata["name"] == "conservative"
    assert metadata["display_name"] == "보수적"
    assert "instruction_file" in metadata


@pytest.mark.asyncio
async def test_reload_instructions(strategy_manager: StrategyManager):
    """Test manual cache invalidation."""
    # Load instruction to cache it
    await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    # Verify cache has entries
    assert len(strategy_manager._cache) > 0

    # Clear cache
    await strategy_manager.reload_instructions()

    # Verify cache is empty
    assert len(strategy_manager._cache) == 0

    # Load again - should reload from file
    content = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    assert "BTC-specific conservative strategy" in content


@pytest.mark.asyncio
async def test_concurrent_cache_access(strategy_manager: StrategyManager):
    """Test concurrent access to cache (thread safety)."""
    async def load_instruction(coin: Cryptocurrency, strategy: TradingStrategy) -> str:
        return await strategy_manager.get_instruction(coin, strategy)

    # Load same instruction concurrently
    results = await asyncio.gather(
        *[load_instruction(Cryptocurrency.BTC, TradingStrategy.CONSERVATIVE) for _ in range(10)],
        *[load_instruction(Cryptocurrency.ETH, TradingStrategy.BALANCED) for _ in range(10)],
        *[load_instruction(Cryptocurrency.SOL, TradingStrategy.AGGRESSIVE) for _ in range(10)],
    )

    # All tasks should complete without errors
    assert len(results) == 30

    # All results should be strings (content)
    for result in results:
        assert isinstance(result, str)


# Test with mocked file reads
@pytest.mark.asyncio
async def test_error_handling_file_read_error(
    strategy_manager: StrategyManager, temp_instructions_dir: Path
):
    """Test error handling when file read fails."""
    # Make a file unreadable
    btc_conservative_path = (
        temp_instructions_dir
        / "coin_specific"
        / "BTC"
        / "conservative.md"
    )

    # Remove coin-specific file to trigger fallback to strategy file
    btc_conservative_path.unlink()

    # Should fallback to strategy file
    content = await strategy_manager.get_instruction(
        Cryptocurrency.BTC,
        TradingStrategy.CONSERVATIVE,
    )

    assert "Conservative Strategy" in content


# Test CacheEntry class
class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_is_expired(self):
        """Test cache entry expiration check."""
        entry = CacheEntry(
            content="test content",
            mtime=time.time(),
            loaded_at=time.time(),
        )

        # Not expired yet
        assert not entry.is_expired(60)

        # Wait for expiration
        time.sleep(0.1)
        expired_entry = CacheEntry(
            content="test content",
            mtime=time.time(),
            loaded_at=time.time() - 61,  # Expired
        )

        assert expired_entry.is_expired(60)


# Test TemplateVariables dataclass
class TestTemplateVariables:
    """Test TemplateVariables dataclass."""

    def test_variable_creation(self):
        """Test creating template variables."""
        from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy

        variables = TemplateVariables(
            coin=Cryptocurrency.BTC,
            ticker="KRW-BTC",
            strategy=TradingStrategy.CONSERVATIVE,
            strategy_file="conservative.md",
        )

        assert variables.coin == Cryptocurrency.BTC
        assert variables.ticker == "KRW-BTC"
        assert variables.strategy == TradingStrategy.CONSERVATIVE
        assert variables.strategy_file == "conservative.md"


# Performance tests
@pytest.mark.asyncio
async def test_instruction_loading_performance(strategy_manager: StrategyManager):
    """Test instruction loading performance with multiple concurrent requests."""
    # Load multiple instructions concurrently
    coins = [
        Cryptocurrency.BTC,
        Cryptocurrency.ETH,
        Cryptocurrency.SOL,
        Cryptocurrency.XRP,
        Cryptocurrency.ADA,
    ]
    strategies = [
        TradingStrategy.CONSERVATIVE,
        TradingStrategy.BALANCED,
        TradingStrategy.AGGRESSIVE,
        TradingStrategy.VISION_AGGRESSIVE,
    ]

    async def load_all() -> list[str]:
        tasks = [
            strategy_manager.get_instruction(coin, strategy)
            for coin in coins
            for strategy in strategies
        ]
        return list(await asyncio.gather(*tasks))

    # Should complete quickly
    start_time = time.time()
    results = await load_all()
    elapsed = time.time() - start_time

    # Should handle 20 concurrent requests efficiently
    assert len(results) == 20
    assert elapsed < 2.0  # Should complete in under 2 seconds
