"""
Integration tests for UserPreferencesRepository.

This module tests:
- CRUD operations for user preferences
- Portfolio allocation validation
- Migration from single-coin setup
- Cache invalidation
- Error handling

@MX:NOTE Tests use in-memory SQLite for isolation and speed
"""

import asyncio
import sqlite3
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy
from gpt_bitcoin.domain.models.user_preferences import CoinPreference, UserPreferences
from gpt_bitcoin.infrastructure.database.preferences_repository import (
    SQLiteUserPreferencesRepository,
)
from gpt_bitcoin.infrastructure.exceptions import DataFetchError


@pytest_asyncio.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        db_path = Path(f.name)
        yield db_path
    # Cleanup
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass  # Windows may have file locks


@pytest_asyncio.fixture
async def repository(temp_db):
    """Create repository with temporary database."""
    repo = SQLiteUserPreferencesRepository(
        db_path=str(temp_db),
        cache_ttl_seconds=1,  # Short TTL for testing
        pool_size=2,
    )
    yield repo
    # Cleanup
    await repo.close()


class TestUserPreferencesRepository:
    """Test suite for UserPreferencesRepository."""

    @pytest.mark.asyncio
    async def test_get_default_preferences(self, repository):
        """Test getting default preferences when none exist."""
        prefs = await repository.get_preferences()

        assert prefs is not None
        assert prefs.default_strategy == TradingStrategy.BALANCED
        assert prefs.auto_trade is True
        assert prefs.daily_trading_limit_krw == 100000.0

        # Should have BTC as default coin
        assert len(prefs.coins) == 1
        assert prefs.coins[0].coin == Cryptocurrency.BTC
        assert prefs.coins[0].enabled is True
        assert prefs.coins[0].percentage == 100.0

    @pytest.mark.asyncio
    async def test_update_preferences(self, repository):
        """Test updating user preferences."""
        # Get initial preferences
        initial = await repository.get_preferences()
        assert initial is not None

        # Create new preferences with multiple coins
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.AGGRESSIVE,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=50.0,
                    strategy=TradingStrategy.BALANCED,
                ),
                CoinPreference(
                    coin=Cryptocurrency.ETH,
                    enabled=True,
                    percentage=30.0,
                    strategy=TradingStrategy.AGGRESSIVE,
                ),
                CoinPreference(
                    coin=Cryptocurrency.SOL,
                    enabled=True,
                    percentage=20.0,
                    strategy=TradingStrategy.CONSERVATIVE,
                ),
            ],
            auto_trade=False,
            daily_trading_limit_krw=50000.0,
        )

        # Update preferences
        await repository.update_preferences(new_prefs)

        # Verify update
        updated = await repository.get_preferences()
        assert updated.default_strategy == TradingStrategy.AGGRESSIVE
        assert updated.auto_trade is False
        assert updated.daily_trading_limit_krw == 50000.0
        assert len(updated.coins) == 3

    @pytest.mark.asyncio
    async def test_add_coin(self, repository):
        """Test adding a new coin."""
        # Get initial preferences
        initial = await repository.get_preferences()

        # Add ETH coin (need to adjust percentages)
        eth_coin = CoinPreference(
            coin=Cryptocurrency.ETH,
            enabled=True,
            percentage=30.0,
            strategy=TradingStrategy.AGGRESSIVE,
        )

        # First, update BTC to 70% to make room
        new_coins = [
            CoinPreference(
                coin=Cryptocurrency.BTC,
                enabled=True,
                percentage=70.0,
                strategy=TradingStrategy.BALANCED,
            )
        ]
        new_prefs = UserPreferences(
            default_strategy=initial.default_strategy,
            coins=new_coins,
            auto_trade=initial.auto_trade,
            daily_trading_limit_krw=initial.daily_trading_limit_krw,
        )
        await repository.update_preferences(new_prefs)

        # Now add ETH
        await repository.add_coin(eth_coin)

        # Verify addition
        updated = await repository.get_preferences()
        assert len(updated.coins) == 2

        eth_pref = updated.get_coin_preference(Cryptocurrency.ETH)
        assert eth_pref is not None
        assert eth_pref.coin == Cryptocurrency.ETH
        assert eth_pref.percentage == 30.0

    @pytest.mark.asyncio
    async def test_remove_coin(self, repository):
        """Test removing a coin."""
        # Setup: Add multiple coins
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=60.0,
                    strategy=TradingStrategy.BALANCED,
                ),
                CoinPreference(
                    coin=Cryptocurrency.ETH,
                    enabled=True,
                    percentage=40.0,
                    strategy=TradingStrategy.AGGRESSIVE,
                ),
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        await repository.update_preferences(new_prefs)

        # Remove ETH
        await repository.remove_coin(Cryptocurrency.ETH)

        # Verify removal
        updated = await repository.get_preferences()
        assert len(updated.coins) == 1
        assert updated.coins[0].coin == Cryptocurrency.BTC

        # ETH should no longer exist
        eth_pref = updated.get_coin_preference(Cryptocurrency.ETH)
        assert eth_pref is None

    @pytest.mark.asyncio
    async def test_update_coin_strategy(self, repository):
        """Test updating strategy for a specific coin."""
        # Get initial preferences
        initial = await repository.get_preferences()

        # Update BTC strategy to AGGRESSIVE
        await repository.update_coin_strategy(Cryptocurrency.BTC, TradingStrategy.AGGRESSIVE)

        # Verify update
        updated = await repository.get_preferences()
        btc_pref = updated.get_coin_preference(Cryptocurrency.BTC)
        assert btc_pref is not None
        assert btc_pref.strategy == TradingStrategy.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, repository):
        """Test that cache is invalidated on update."""
        # Get initial preferences (caches them)
        initial = await repository.get_preferences()

        # Update preferences
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.CONSERVATIVE,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=100.0,
                    strategy=TradingStrategy.CONSERVATIVE,
                )
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        await repository.update_preferences(new_prefs)

        # Get again - should return updated values
        updated = await repository.get_preferences()
        assert updated.default_strategy == TradingStrategy.CONSERVATIVE

    @pytest.mark.asyncio
    async def test_cache_ttl(self, repository):
        """Test that cache expires after TTL."""
        # Get initial preferences (caches them)
        initial = await repository.get_preferences()

        # Wait for cache to expire (TTL is 1 second)
        await asyncio.sleep(1.5)

        # Get again - should fetch from database, not cache
        # We can verify this by checking the cache status
        assert repository._cache is None or repository._cache.is_expired()

    @pytest.mark.asyncio
    async def test_portfolio_allocation_validation(self, repository):
        """Test that portfolio allocation validates to 100%."""
        # Try to create preferences with invalid allocation
        with pytest.raises(ValueError, match="Portfolio allocation must sum to 100%"):
            UserPreferences(
                default_strategy=TradingStrategy.BALANCED,
                coins=[
                    CoinPreference(
                        coin=Cryptocurrency.BTC,
                        enabled=True,
                        percentage=50.0,
                        strategy=TradingStrategy.BALANCED,
                    ),
                    CoinPreference(
                        coin=Cryptocurrency.ETH,
                        enabled=True,
                        percentage=30.0,  # Total: 80%
                        strategy=TradingStrategy.AGGRESSIVE,
                    ),
                ],
                auto_trade=True,
                daily_trading_limit_krw=100000.0,
            )

    @pytest.mark.asyncio
    async def test_invalid_percentage_range(self, repository):
        """Test that invalid percentage values are rejected."""
        with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
            CoinPreference(
                coin=Cryptocurrency.BTC,
                enabled=True,
                percentage=150.0,  # Invalid: > 100
                strategy=TradingStrategy.BALANCED,
            )

    @pytest.mark.asyncio
    async def test_remove_nonexistent_coin(self, repository):
        """Test removing a coin that doesn't exist."""
        # Try to remove ETH when only BTC exists
        with pytest.raises(DataFetchError, match="not found in preferences"):
            await repository.remove_coin(Cryptocurrency.ETH)

    @pytest.mark.asyncio
    async def test_update_nonexistent_coin_strategy(self, repository):
        """Test updating strategy for nonexistent coin."""
        with pytest.raises(DataFetchError, match="not found in preferences"):
            await repository.update_coin_strategy(Cryptocurrency.ETH, TradingStrategy.AGGRESSIVE)

    @pytest.mark.asyncio
    async def test_concurrent_access(self, repository):
        """Test concurrent access to repository."""
        # Create multiple concurrent read operations
        tasks = [repository.get_preferences() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All results should be the same (from cache after first fetch)
        for result in results:
            assert result.default_strategy == TradingStrategy.BALANCED
            assert len(result.coins) == 1

    @pytest.mark.asyncio
    async def test_connection_pool(self, repository):
        """Test connection pool functionality."""
        # Execute multiple operations to test pool
        for _ in range(3):
            prefs = await repository.get_preferences()
            assert prefs is not None

        # Pool should have been used
        assert len(repository._pool) <= repository.pool_size

    @pytest.mark.asyncio
    async def test_disabled_coin_excluded_from_allocation(self, repository):
        """Test that disabled coins are excluded from allocation validation."""
        # Create preferences with one disabled coin
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=100.0,
                    strategy=TradingStrategy.BALANCED,
                ),
                CoinPreference(
                    coin=Cryptocurrency.ETH,
                    enabled=False,  # Disabled
                    percentage=50.0,  # Should be ignored
                    strategy=TradingStrategy.AGGRESSIVE,
                ),
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        # Should not raise error because ETH is disabled
        assert new_prefs.default_strategy == TradingStrategy.BALANCED

    @pytest.mark.asyncio
    async def test_add_coin(self, repository):
        """Test adding a new coin."""
        # Get initial preferences
        initial = await repository.get_preferences()

        # Add ETH coin (need to adjust percentages)
        eth_coin = CoinPreference(
            coin=Cryptocurrency.ETH,
            enabled=True,
            percentage=30.0,
            strategy=TradingStrategy.AGGRESSIVE,
        )

        # First, update BTC to 70% to make room
        new_coins = [
            CoinPreference(
                coin=Cryptocurrency.BTC,
                enabled=True,
                percentage=70.0,
                strategy=TradingStrategy.BALANCED,
            )
        ]
        new_prefs = UserPreferences(
            default_strategy=initial.default_strategy,
            coins=new_coins,
            auto_trade=initial.auto_trade,
            daily_trading_limit_krw=initial.daily_trading_limit_krw,
        )
        await repository.update_preferences(new_prefs)

        # Now add ETH
        await repository.add_coin(eth_coin)

        # Verify addition
        updated = await repository.get_preferences()
        assert len(updated.coins) == 2

        eth_pref = updated.get_coin_preference(Cryptocurrency.ETH)
        assert eth_pref is not None
        assert eth_pref.coin == Cryptocurrency.ETH
        assert eth_pref.percentage == 30.0

    @pytest.mark.asyncio
    async def test_remove_coin(self, repository):
        """Test removing a coin."""
        # Setup: Add multiple coins
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=60.0,
                    strategy=TradingStrategy.BALANCED,
                ),
                CoinPreference(
                    coin=Cryptocurrency.ETH,
                    enabled=True,
                    percentage=40.0,
                    strategy=TradingStrategy.AGGRESSIVE,
                ),
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        await repository.update_preferences(new_prefs)

        # Remove ETH
        await repository.remove_coin(Cryptocurrency.ETH)

        # Verify removal
        updated = await repository.get_preferences()
        assert len(updated.coins) == 1
        assert updated.coins[0].coin == Cryptocurrency.BTC

        # ETH should no longer exist
        eth_pref = updated.get_coin_preference(Cryptocurrency.ETH)
        assert eth_pref is None

    @pytest.mark.asyncio
    async def test_update_coin_strategy(self, repository):
        """Test updating strategy for a specific coin."""
        # Get initial preferences
        initial = await repository.get_preferences()

        # Update BTC strategy to AGGRESSIVE
        await repository.update_coin_strategy(Cryptocurrency.BTC, TradingStrategy.AGGRESSIVE)

        # Verify update
        updated = await repository.get_preferences()
        btc_pref = updated.get_coin_preference(Cryptocurrency.BTC)
        assert btc_pref is not None
        assert btc_pref.strategy == TradingStrategy.AGGRESSIVE

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, repository):
        """Test that cache is invalidated on update."""
        # Get initial preferences (caches them)
        initial = await repository.get_preferences()

        # Update preferences
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.CONSERVATIVE,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=100.0,
                    strategy=TradingStrategy.CONSERVATIVE,
                )
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        await repository.update_preferences(new_prefs)

        # Get again - should return updated values
        updated = await repository.get_preferences()
        assert updated.default_strategy == TradingStrategy.CONSERVATIVE

    @pytest.mark.asyncio
    async def test_cache_ttl(self, repository):
        """Test that cache expires after TTL."""
        # Get initial preferences (caches them)
        initial = await repository.get_preferences()

        # Wait for cache to expire (TTL is 1 second)
        await asyncio.sleep(1.5)

        # Get again - should fetch from database, not cache
        # We can verify this by checking the cache status
        assert repository._cache is None or repository._cache.is_expired()

    @pytest.mark.asyncio
    async def test_portfolio_allocation_validation(self, repository):
        """Test that portfolio allocation validates to 100%."""
        # Try to create preferences with invalid allocation
        with pytest.raises(ValueError, match="Portfolio allocation must sum to 100%"):
            UserPreferences(
                default_strategy=TradingStrategy.BALANCED,
                coins=[
                    CoinPreference(
                        coin=Cryptocurrency.BTC,
                        enabled=True,
                        percentage=50.0,
                        strategy=TradingStrategy.BALANCED,
                    ),
                    CoinPreference(
                        coin=Cryptocurrency.ETH,
                        enabled=True,
                        percentage=30.0,  # Total: 80%
                        strategy=TradingStrategy.AGGRESSIVE,
                    ),
                ],
                auto_trade=True,
                daily_trading_limit_krw=100000.0,
            )

    @pytest.mark.asyncio
    async def test_invalid_percentage_range(self, repository):
        """Test that invalid percentage values are rejected."""
        with pytest.raises(ValueError, match="Percentage must be between 0 and 100"):
            CoinPreference(
                coin=Cryptocurrency.BTC,
                enabled=True,
                percentage=150.0,  # Invalid: > 100
                strategy=TradingStrategy.BALANCED,
            )

    @pytest.mark.asyncio
    async def test_remove_nonexistent_coin(self, repository):
        """Test removing a coin that doesn't exist."""
        # Try to remove ETH when only BTC exists
        with pytest.raises(DataFetchError, match="not found in preferences"):
            await repository.remove_coin(Cryptocurrency.ETH)

    @pytest.mark.asyncio
    async def test_update_nonexistent_coin_strategy(self, repository):
        """Test updating strategy for nonexistent coin."""
        with pytest.raises(DataFetchError, match="not found in preferences"):
            await repository.update_coin_strategy(Cryptocurrency.ETH, TradingStrategy.AGGRESSIVE)

    @pytest.mark.asyncio
    async def test_concurrent_access(self, repository):
        """Test concurrent access to repository."""
        # Create multiple concurrent read operations
        tasks = [repository.get_preferences() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All results should be the same (from cache after first fetch)
        for result in results:
            assert result.default_strategy == TradingStrategy.BALANCED
            assert len(result.coins) == 1

    @pytest.mark.asyncio
    async def test_connection_pool(self, repository):
        """Test connection pool functionality."""
        # Execute multiple operations to test pool
        for _ in range(3):
            prefs = await repository.get_preferences()
            assert prefs is not None

        # Pool should have been used
        assert len(repository._pool) <= repository.pool_size

    @pytest.mark.asyncio
    async def test_disabled_coin_excluded_from_allocation(self, repository):
        """Test that disabled coins are excluded from allocation validation."""
        # Create preferences with one disabled coin
        new_prefs = UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=100.0,
                    strategy=TradingStrategy.BALANCED,
                ),
                CoinPreference(
                    coin=Cryptocurrency.ETH,
                    enabled=False,  # Disabled
                    percentage=50.0,  # Should be ignored
                    strategy=TradingStrategy.AGGRESSIVE,
                ),
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )
        # Should not raise error because ETH is disabled
        assert new_prefs.default_strategy == TradingStrategy.BALANCED


class TestMigrationToV6:
    """Test suite for migration script."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create temporary database path."""
        return tmp_path / "test_migration.sqlite"

    def test_migration_creates_tables(self, temp_db_path):
        """Test that migration creates required tables."""
        from gpt_bitcoin.infrastructure.database.migrations.migrate_to_v6 import (
            MigrationToV6,
        )

        migration = MigrationToV6(db_path=str(temp_db_path))
        migration.migrate()

        # Verify tables exist
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        assert "user_preferences" in tables
        assert "coin_preferences" in tables
        assert "portfolio" in tables

        conn.close()

    def test_migration_idempotent(self, temp_db_path):
        """Test that migration is idempotent."""
        from gpt_bitcoin.infrastructure.database.migrations.migrate_to_v6 import (
            MigrationToV6,
        )

        # Run migration twice
        migration = MigrationToV6(db_path=str(temp_db_path))
        migration.migrate()
        migration.migrate()  # Should not fail

        # Verify single set of data
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        count = cursor.fetchone()[0]
        assert count == 1

        conn.close()

    def test_migration_from_existing_db(self, temp_db_path):
        """Test migration from existing v5 database."""
        from gpt_bitcoin.infrastructure.database.migrations.migrate_to_v6 import (
            MigrationToV6,
        )

        # Create v5 database with trading_decisions table
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE trading_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("INSERT INTO trading_decisions (decision) VALUES ('buy')")
        conn.commit()
        conn.close()

        # Run migration
        migration = MigrationToV6(db_path=str(temp_db_path))
        migration.migrate()

        # Verify v5 data preserved
        conn = sqlite3.connect(str(temp_db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM trading_decisions")
        count = cursor.fetchone()[0]
        assert count == 1

        conn.close()
