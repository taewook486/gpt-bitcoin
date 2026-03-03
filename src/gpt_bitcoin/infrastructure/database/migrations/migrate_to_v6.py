#!/usr/bin/env python3
"""
Migration script from v5 (single-coin) to v6 (multi-coin) architecture.

This script migrates the existing single-coin BTC setup to the new
multi-coin architecture by:
1. Creating the preferences tables
2. Creating default preferences
3. Migrating existing BTC configuration

Usage:
    python -m gpt_bitcoin.infrastructure.database.migrations.migrate_to_v6

@MX:NOTE Migration is idempotent - safe to run multiple times
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Optional

from structlog import get_logger

logger = get_logger(__name__)


class MigrationToV6:
    """Handles migration from v5 to v6 architecture."""

    def __init__(self, db_path: str = "trading_decisions.sqlite"):
        """
        Initialize migration.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def migrate(self) -> None:
        """Execute migration to v6."""
        logger.info("Starting migration to v6", db_path=str(self.db_path))

        # Check if database exists
        if not self.db_path.exists():
            logger.warning("Database file not found, creating new database")
            self._create_database()
            return

        try:
            # Connect to database
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row

            # Check if migration already applied
            if self._is_migration_applied():
                logger.info("Migration already applied, skipping")
                return

            # Apply migration
            self._apply_migration()

            logger.info("Migration to v6 completed successfully")

        except Exception as e:
            logger.error("Migration failed", error=str(e))
            raise
        finally:
            if self.conn:
                self.conn.close()

    def _is_migration_applied(self) -> bool:
        """
        Check if migration has already been applied.

        Returns:
            bool: True if tables exist, False otherwise
        """
        cursor = self.conn.cursor()

        # Check if coin_preferences table exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='coin_preferences'
            """
        )
        result = cursor.fetchone()
        return result is not None

    def _apply_migration(self) -> None:
        """Apply migration steps."""
        logger.info("Applying migration steps")

        # Step 1: Create tables
        self._create_tables()

        # Step 2: Migrate existing data
        self._migrate_data()

        # Step 3: Create default preferences
        self._create_default_preferences()

        self.conn.commit()
        logger.info("Migration steps completed")

    def _create_database(self) -> None:
        """Create new database with v6 schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        self._create_default_preferences()
        self.conn.commit()
        logger.info("New v6 database created")

    def _create_tables(self) -> None:
        """Create v6 tables."""
        cursor = self.conn.cursor()

        # User preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                default_strategy TEXT NOT NULL DEFAULT 'balanced',
                auto_trade INTEGER NOT NULL DEFAULT 1,
                daily_trading_limit_krw REAL NOT NULL DEFAULT 100000.0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Coin preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS coin_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                percentage REAL NOT NULL DEFAULT 20.0,
                strategy TEXT NOT NULL DEFAULT 'balanced',
                UNIQUE(coin)
            )
            """
        )

        # Portfolio tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                avg_buy_price REAL NOT NULL DEFAULT 0.0,
                current_price_krw REAL NOT NULL DEFAULT 0.0,
                value_krw REAL NOT NULL DEFAULT 0.0,
                profit_loss_krw REAL NOT NULL DEFAULT 0.0,
                profit_loss_percentage REAL NOT NULL DEFAULT 0.0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(coin)
            )
            """
        )

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_coin_preferences_coin ON coin_preferences(coin)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_portfolio_coin ON portfolio(coin)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_portfolio_updated_at ON portfolio(updated_at)"
        )

        logger.info("Tables created")

    def _migrate_data(self) -> None:
        """Migrate existing BTC data."""
        cursor = self.conn.cursor()

        # Check if there's existing trading data
        cursor.execute("SELECT COUNT(*) FROM trading_decisions")
        count = cursor.fetchone()[0]

        if count > 0:
            logger.info("Migrating existing BTC data", decision_count=count)

            # Get the most recent strategy used (if available)
            # Default to 'balanced' if no strategy info exists
            strategy = "balanced"

            # Create BTC coin preference
            cursor.execute(
                """
                INSERT OR REPLACE INTO coin_preferences
                (coin, enabled, percentage, strategy)
                VALUES ('BTC', 1, 100.0, ?)
                """,
                (strategy,),
            )

            # Create BTC portfolio entry (will be updated by actual balance later)
            cursor.execute(
                """
                INSERT OR REPLACE INTO portfolio
                (coin, balance, avg_buy_price, current_price_krw, value_krw, profit_loss_krw, profit_loss_percentage)
                VALUES ('BTC', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
                """
            )

            logger.info("BTC data migrated", strategy=strategy)
        else:
            logger.info("No existing data to migrate")

    def _create_default_preferences(self) -> None:
        """Create default preferences if not exist."""
        cursor = self.conn.cursor()

        # Insert default user preferences
        cursor.execute(
            """
            INSERT INTO user_preferences (default_strategy, auto_trade, daily_trading_limit_krw)
            SELECT 'balanced', 1, 100000.0
            WHERE NOT EXISTS (SELECT 1 FROM user_preferences LIMIT 1)
            """
        )

        # Insert default BTC preference if not exists
        cursor.execute(
            """
            INSERT OR IGNORE INTO coin_preferences (coin, enabled, percentage, strategy)
            VALUES ('BTC', 1, 100.0, 'balanced')
            """
        )

        # Insert default BTC portfolio if not exists
        cursor.execute(
            """
            INSERT OR IGNORE INTO portfolio
            (coin, balance, avg_buy_price, current_price_krw, value_krw, profit_loss_krw, profit_loss_percentage)
            VALUES ('BTC', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            """
        )

        logger.info("Default preferences created")


def main() -> None:
    """Main entry point for migration script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate from v5 (single-coin) to v6 (multi-coin) architecture"
    )
    parser.add_argument(
        "--db-path",
        default="trading_decisions.sqlite",
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("Dry run mode - no changes will be made")
        db_path = Path(args.db_path)
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check existing tables
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            logger.info("Existing tables", tables=tables)

            # Check trading decisions count
            if "trading_decisions" in tables:
                cursor.execute("SELECT COUNT(*) FROM trading_decisions")
                count = cursor.fetchone()[0]
                logger.info("Trading decisions to migrate", count=count)

            conn.close()
        else:
            logger.info("Database does not exist, New v6 database would be created.")
    else:
        migration = MigrationToV6(db_path=args.db_path)
        migration.migrate()


if __name__ == "__main__":
    main()
