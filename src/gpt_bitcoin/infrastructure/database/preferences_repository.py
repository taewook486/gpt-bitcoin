"""
User preferences repository for multi-coin trading configuration.

This module provides async CRUD operations for user preferences with:
- SQLite storage using aiosqlite
- In-memory caching with TTL
- Connection pooling
- Error handling and logging

@MX:NOTE Repository uses abstract base class for dependency injection and testing
"""

import asyncio
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import aiosqlite
from structlog import get_logger

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy
from gpt_bitcoin.domain.models.user_preferences import (
    CoinPreference,
    UserPreferences,
)
from gpt_bitcoin.infrastructure.exceptions import ConfigurationError, DataFetchError

logger = get_logger(__name__)


class UserPreferencesRepository(ABC):
    """
    Abstract base class for user preferences repository.

    @MX:ANCHOR Repository interface for dependency injection and testing
    @MX:REASON Enables mock implementations for unit tests
    """

    @abstractmethod
    async def get_preferences(self) -> UserPreferences:
        """
        Get current user preferences with caching.

        Returns:
            UserPreferences: Current user preferences

        Raises:
            DataFetchError: If preferences cannot be retrieved
        """
        pass

    @abstractmethod
    async def update_preferences(self, prefs: UserPreferences) -> None:
        """
        Update user preferences and invalidate cache.

        Args:
            prefs: UserPreferences to save

        Raises:
            ConfigurationError: If preferences are invalid
            DataFetchError: If update fails
        """
        pass

    @abstractmethod
    async def add_coin(self, coin: CoinPreference) -> None:
        """
        Add coin to preferences, validate allocation.

        Args:
            coin: CoinPreference to add

        Raises:
            ConfigurationError: If allocation exceeds 100%
            DataFetchError: If operation fails
        """
        pass

    @abstractmethod
    async def remove_coin(self, coin: Cryptocurrency) -> None:
        """
        Remove coin from preferences.

        Args:
            coin: Cryptocurrency to remove

        Raises:
            DataFetchError: If coin doesn't exist or operation fails
        """
        pass

    @abstractmethod
    async def update_coin_strategy(
        self, coin: Cryptocurrency, strategy: TradingStrategy
    ) -> None:
        """
        Update strategy for specific coin.

        Args:
            coin: Cryptocurrency to update
            strategy: New trading strategy

        Raises:
            DataFetchError: If coin doesn't exist or update fails
        """
        pass


class CacheEntry:
    """Cache entry with TTL support."""

    def __init__(self, data: UserPreferences, ttl_seconds: int = 3600):
        """
        Initialize cache entry.

        Args:
            data: Cached preferences data
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds


class SQLiteUserPreferencesRepository(UserPreferencesRepository):
    """
    SQLite implementation of UserPreferencesRepository.

    @MX:NOTE Uses connection pooling and caching for performance optimization
    """

    def __init__(
        self,
        db_path: str = "trading_decisions.sqlite",
        cache_ttl_seconds: int = 3600,
        pool_size: int = 5,
    ):
        """
        Initialize SQLite repository.

        Args:
            db_path: Path to SQLite database file
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
            pool_size: Connection pool size (default: 5)
        """
        self.db_path = Path(db_path)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.pool_size = pool_size
        self._cache: Optional[CacheEntry] = None
        self._pool: list[aiosqlite.Connection] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False

    async def _initialize(self) -> None:
        """
        Initialize database schema and connection pool.

        @MX:WARN Async initialization required before any database operations
        @MX:REASON Connection pool must be created before first query
        """
        if self._initialized:
            return

        async with self._pool_lock:
            if self._initialized:
                return

            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create connection pool
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                conn.row_factory = aiosqlite.Row
                self._pool.append(conn)

            # Run migrations
            await self._run_migrations()

            self._initialized = True
            logger.info(
                "Repository initialized",
                db_path=str(self.db_path),
                pool_size=self.pool_size,
                cache_ttl=self.cache_ttl_seconds,
            )

    async def _run_migrations(self) -> None:
        """Run database migrations from SQL file."""
        migration_path = (
            Path(__file__).parent
            / "migrations"
            / "001_add_preferences.sql"
        )

        if not migration_path.exists():
            logger.warning(
                "Migration file not found, skipping",
                path=str(migration_path),
            )
            return

        migration_sql = migration_path.read_text(encoding="utf-8")

        # Get connection from pool
        conn = await self._get_connection()
        try:
            # Execute migration (split by semicolons for multiple statements)
            statements = [
                stmt.strip() for stmt in migration_sql.split(";") if stmt.strip()
            ]
            for statement in statements:
                if statement:
                    await conn.execute(statement)
            await conn.commit()
            logger.info("Database migrations completed", count=len(statements))
        finally:
            await self._return_connection(conn)

    async def _get_connection(self) -> aiosqlite.Connection:
        """
        Get connection from pool.

        Returns:
            aiosqlite.Connection: Database connection
        """
        async with self._pool_lock:
            if self._pool:
                return self._pool.pop()
            # Create new connection if pool is empty
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            return conn

    async def _return_connection(self, conn: aiosqlite.Connection) -> None:
        """
        Return connection to pool.

        Args:
            conn: Connection to return
        """
        async with self._pool_lock:
            if len(self._pool) < self.pool_size:
                self._pool.append(conn)
            else:
                await conn.close()

    async def _invalidate_cache(self) -> None:
        """Invalidate cache."""
        self._cache = None
        logger.debug("Cache invalidated")

    async def _get_cached_preferences(self) -> Optional[UserPreferences]:
        """
        Get cached preferences if valid.

        Returns:
            Optional[UserPreferences]: Cached preferences or None if expired/missing
        """
        if self._cache is None:
            return None

        if self._cache.is_expired():
            self._cache = None
            logger.debug("Cache expired")
            return None

        logger.debug("Cache hit")
        return self._cache.data

    async def get_preferences(self) -> UserPreferences:
        """
        Get current user preferences with caching.

        Returns:
            UserPreferences: Current user preferences

        Raises:
            DataFetchError: If preferences cannot be retrieved
        """
        await self._initialize()

        # Check cache first
        cached = await self._get_cached_preferences()
        if cached is not None:
            return cached

        # Fetch from database
        conn = await self._get_connection()
        try:
            # Get global preferences
            cursor = await conn.execute(
                "SELECT * FROM user_preferences LIMIT 1"
            )
            prefs_row = await cursor.fetchone()

            if prefs_row is None:
                # Create default preferences
                default_prefs = self._create_default_preferences()
                await self._save_preferences(default_prefs)
                return default_prefs

            # Get coin preferences
            cursor = await conn.execute(
                "SELECT * FROM coin_preferences"
            )
            coin_rows = await cursor.fetchall()

            # Build UserPreferences
            preferences = self._build_preferences(prefs_row, coin_rows)

            # Update cache
            self._cache = CacheEntry(preferences, self.cache_ttl_seconds)

            logger.info(
                "Preferences loaded",
                coin_count=len(preferences.coins),
                auto_trade=preferences.auto_trade,
            )

            return preferences

        except Exception as e:
            logger.error("Failed to get preferences", error=str(e))
            raise DataFetchError(
                f"Failed to retrieve preferences: {e}",
                source="database",
            ) from e
        finally:
            await self._return_connection(conn)

    async def update_preferences(self, prefs: UserPreferences) -> None:
        """
        Update user preferences and invalidate cache.

        Args:
            prefs: UserPreferences to save

        Raises:
            ConfigurationError: If preferences are invalid
            DataFetchError: If update fails
        """
        await self._initialize()

        # Validate preferences
        try:
            # Re-validate using __post_init__
            prefs._validate_allocation()
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid preferences: {e}",
                setting_name="user_preferences",
            ) from e

        await self._save_preferences(prefs)
        await self._invalidate_cache()

        logger.info(
            "Preferences updated",
            coin_count=len(prefs.coins),
            auto_trade=prefs.auto_trade,
        )

    async def _save_preferences(self, prefs: UserPreferences) -> None:
        """
        Save preferences to database.

        Args:
            prefs: Preferences to save
        """
        conn = await self._get_connection()
        try:
            # Update global preferences
            await conn.execute(
                """
                UPDATE user_preferences
                SET default_strategy = ?,
                    auto_trade = ?,
                    daily_trading_limit_krw = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (
                    prefs.default_strategy.value,
                    1 if prefs.auto_trade else 0,
                    prefs.daily_trading_limit_krw,
                ),
            )

            # Clear existing coin preferences
            await conn.execute("DELETE FROM coin_preferences")

            # Insert coin preferences
            for coin_pref in prefs.coins:
                await conn.execute(
                    """
                    INSERT INTO coin_preferences (coin, enabled, percentage, strategy)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        coin_pref.coin.value,
                        1 if coin_pref.enabled else 0,
                        coin_pref.percentage,
                        coin_pref.strategy.value,
                    ),
                )

            await conn.commit()

        except Exception as e:
            logger.error("Failed to save preferences", error=str(e))
            await conn.rollback()
            raise DataFetchError(
                f"Failed to save preferences: {e}",
                source="database",
            ) from e
        finally:
            await self._return_connection(conn)

    async def add_coin(self, coin: CoinPreference) -> None:
        """
        Add coin to preferences, Validate allocation.

        Args:
            coin: CoinPreference to add

        Raises:
            ConfigurationError: If allocation exceeds 100%
            DataFetchError: If operation fails
        """
        await self._initialize()

        # Get current preferences
        current_prefs = await self.get_preferences()

        # Check if coin already exists
        existing = current_prefs.get_coin_preference(coin.coin)
        if existing is not None:
            raise ConfigurationError(
                f"Coin {coin.coin.value} already exists in preferences",
                setting_name="coin_preferences",
            )

        # Create new preferences with added coin
        new_coins = current_prefs.coins + [coin]

        # Validate new allocation
        try:
            new_prefs = UserPreferences(
                default_strategy=current_prefs.default_strategy,
                coins=new_coins,
                auto_trade=current_prefs.auto_trade,
                daily_trading_limit_krw=current_prefs.daily_trading_limit_krw,
            )
        except ValueError as e:
            raise ConfigurationError(
                f"Invalid allocation after adding coin: {e}",
                setting_name="coin_preferences",
            ) from e

        # Save updated preferences
        await self.update_preferences(new_prefs)

        logger.info(
            "Coin added",
            coin=coin.coin.value,
            percentage=coin.percentage,
            strategy=coin.strategy.value,
        )

    async def remove_coin(self, coin: Cryptocurrency) -> None:
        """
        Remove coin from preferences.

        Args:
            coin: Cryptocurrency to remove

        Raises:
            DataFetchError: If coin doesn't exist or operation fails
        """
        await self._initialize()

        # Get current preferences
        current_prefs = await self.get_preferences()

        # Check if coin exists
        existing = current_prefs.get_coin_preference(coin)
        if existing is None:
            raise DataFetchError(
                f"Coin {coin.value} not found in preferences",
                source="database",
            )

        # Remove coin from list
        new_coins = [c for c in current_prefs.coins if c.coin != coin]

        # Create updated preferences
        new_prefs = UserPreferences(
            default_strategy=current_prefs.default_strategy,
            coins=new_coins,
            auto_trade=current_prefs.auto_trade,
            daily_trading_limit_krw=current_prefs.daily_trading_limit_krw,
        )

        # Save updated preferences
        await self.update_preferences(new_prefs)

        logger.info("Coin removed", coin=coin.value)

    async def update_coin_strategy(
        self, coin: Cryptocurrency, strategy: TradingStrategy
    ) -> None:
        """
        Update strategy for specific coin.

        Args:
            coin: Cryptocurrency to update
            strategy: New trading strategy

        Raises:
            DataFetchError: If coin doesn't exist or update fails
        """
        await self._initialize()

        # Get current preferences
        current_prefs = await self.get_preferences()

        # Check if coin exists
        existing = current_prefs.get_coin_preference(coin)
        if existing is None:
            raise DataFetchError(
                f"Coin {coin.value} not found in preferences",
                source="database",
            )

        # Update strategy
        new_coins = [
            CoinPreference(
                coin=c.coin,
                enabled=c.enabled,
                percentage=c.percentage,
                strategy=strategy if c.coin == coin else c.strategy,
            )
            for c in current_prefs.coins
        ]

        # Create updated preferences
        new_prefs = UserPreferences(
            default_strategy=current_prefs.default_strategy,
            coins=new_coins,
            auto_trade=current_prefs.auto_trade,
            daily_trading_limit_krw=current_prefs.daily_trading_limit_krw,
        )

        # Save updated preferences
        await self.update_preferences(new_prefs)

        logger.info(
            "Coin strategy updated",
            coin=coin.value,
            old_strategy=existing.strategy.value,
            new_strategy=strategy.value,
        )

    def _create_default_preferences(self) -> UserPreferences:
        """
        Create default preferences for new users.

        Returns:
            UserPreferences: Default preferences with BTC enabled
        """
        return UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(
                    coin=Cryptocurrency.BTC,
                    enabled=True,
                    percentage=100.0,
                    strategy=TradingStrategy.BALANCED,
                )
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )

    def _build_preferences(
        self, prefs_row: aiosqlite.Row, coin_rows: list[aiosqlite.Row]
    ) -> UserPreferences:
        """
        Build UserPreferences from database rows.

        Args:
            prefs_row: User preferences row
            coin_rows: Coin preferences rows

        Returns:
            UserPreferences: Constructed preferences object
        """
        coins = []
        for row in coin_rows:
            coin_pref = CoinPreference(
                coin=Cryptocurrency(row["coin"]),
                enabled=bool(row["enabled"]),
                percentage=float(row["percentage"]),
                strategy=TradingStrategy(row["strategy"]),
            )
            coins.append(coin_pref)

        return UserPreferences(
            default_strategy=TradingStrategy(prefs_row["default_strategy"]),
            coins=coins,
            auto_trade=bool(prefs_row["auto_trade"]),
            daily_trading_limit_krw=float(prefs_row["daily_trading_limit_krw"]),
        )

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._pool_lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()
            self._initialized = False
        logger.info("Repository connections closed")
