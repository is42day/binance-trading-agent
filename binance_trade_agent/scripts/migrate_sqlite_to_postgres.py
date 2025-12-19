#!/usr/bin/env python3
"""
SQLite to PostgreSQL Data Migration Script

Migrates trading data from existing SQLite database to PostgreSQL.
Handles:
- Trades table migration
- Positions table migration
- Idempotent operation (can be run multiple times safely)
- Validation and counts
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from binance_trade_agent.core.portfolio_manager import Base, PositionORM, TradeORM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SQLiteToPostgresMigrator:
    """Handles migration from SQLite to PostgreSQL"""

    def __init__(
        self,
        sqlite_path: str,
        postgres_url: str,
        delete_target_tables: bool = False,
    ):
        """
        Initialize migrator.

        Args:
            sqlite_path: Path to SQLite database file
            postgres_url: PostgreSQL connection URL
            delete_target_tables: If True, DELETE all rows from target tables before migration
        """
        self.sqlite_path = sqlite_path
        self.postgres_url = postgres_url
        self.delete_target_tables = delete_target_tables

        # Create engines
        logger.info(f"Connecting to SQLite: {sqlite_path}")
        self.sqlite_engine = create_engine(f"sqlite:///{sqlite_path}", echo=False)

        logger.info(f"Connecting to PostgreSQL: {postgres_url.split('@')[0]}***")
        self.postgres_engine = create_engine(postgres_url, echo=False)

        # Create session factories
        self.SQLiteSession = sessionmaker(bind=self.sqlite_engine)
        self.PostgresSession = sessionmaker(bind=self.postgres_engine)

    def verify_sqlite_exists(self) -> bool:
        """Verify SQLite database file exists and has tables"""
        if not os.path.exists(self.sqlite_path):
            logger.error(f"SQLite database not found: {self.sqlite_path}")
            return False

        sqlite_session = self.SQLiteSession()
        try:
            # Check if tables exist
            result = sqlite_session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]

            if "trades" not in tables and "positions" not in tables:
                logger.error("No 'trades' or 'positions' tables found in SQLite database")
                return False

            logger.info(f"Found tables in SQLite: {tables}")
            return True

        finally:
            sqlite_session.close()

    def verify_postgres_schema(self) -> bool:
        """Verify PostgreSQL schema exists"""
        postgres_session = self.PostgresSession()
        try:
            # Check if tables exist
            result = postgres_session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result]

            if "trades" not in tables and "positions" not in tables:
                logger.error(
                    "PostgreSQL schema not initialized. Run 'alembic upgrade head' first."
                )
                return False

            logger.info(f"Found tables in PostgreSQL: {tables}")
            return True

        finally:
            postgres_session.close()

    def get_counts(self) -> Dict[str, Dict[str, int]]:
        """Get row counts from both databases"""
        counts = {"sqlite": {}, "postgres": {}}

        # SQLite counts
        sqlite_session = self.SQLiteSession()
        try:
            counts["sqlite"]["trades"] = sqlite_session.query(TradeORM).count()
            counts["sqlite"]["positions"] = sqlite_session.query(PositionORM).count()
        finally:
            sqlite_session.close()

        # PostgreSQL counts
        postgres_session = self.PostgresSession()
        try:
            counts["postgres"]["trades"] = postgres_session.query(TradeORM).count()
            counts["postgres"]["positions"] = postgres_session.query(PositionORM).count()
        finally:
            postgres_session.close()

        return counts

    def clear_postgres_tables(self):
        """Delete all rows from PostgreSQL tables"""
        logger.warning("Deleting all rows from PostgreSQL tables...")
        postgres_session = self.PostgresSession()
        try:
            with postgres_session.begin():
                # Delete in correct order (positions may reference trades)
                deleted_positions = postgres_session.query(PositionORM).delete()
                deleted_trades = postgres_session.query(TradeORM).delete()

            logger.info(f"Deleted {deleted_trades} trades, {deleted_positions} positions")

        finally:
            postgres_session.close()

    def migrate_trades(self, batch_size: int = 100) -> int:
        """
        Migrate trades from SQLite to PostgreSQL.

        Args:
            batch_size: Number of rows to process at once

        Returns:
            Number of trades migrated
        """
        logger.info("Migrating trades...")
        sqlite_session = self.SQLiteSession()
        postgres_session = self.PostgresSession()

        migrated_count = 0
        skipped_count = 0

        try:
            # Get all trades from SQLite
            sqlite_trades = sqlite_session.query(TradeORM).all()
            total = len(sqlite_trades)
            logger.info(f"Found {total} trades in SQLite")

            # Process in batches
            for i in range(0, total, batch_size):
                batch = sqlite_trades[i : i + batch_size]

                with postgres_session.begin():
                    for trade in batch:
                        # Check if trade already exists (by trade_id)
                        existing = (
                            postgres_session.query(TradeORM)
                            .filter_by(trade_id=trade.trade_id)
                            .first()
                        )

                        if existing:
                            skipped_count += 1
                            continue

                        # Create new trade object (don't reuse SQLite object)
                        new_trade = TradeORM(
                            trade_id=trade.trade_id,
                            symbol=trade.symbol,
                            side=trade.side,
                            quantity=trade.quantity,
                            price=trade.price,
                            fee=trade.fee,
                            timestamp=trade.timestamp,
                            order_id=trade.order_id,
                            correlation_id=trade.correlation_id,
                            pnl=trade.pnl,
                        )
                        postgres_session.add(new_trade)
                        migrated_count += 1

                logger.info(f"Migrated {migrated_count}/{total} trades...")

            logger.info(
                f"✅ Trades migration complete: {migrated_count} migrated, {skipped_count} skipped (already exist)"
            )
            return migrated_count

        except Exception as e:
            logger.error(f"Error migrating trades: {e}")
            raise

        finally:
            sqlite_session.close()
            postgres_session.close()

    def migrate_positions(self, batch_size: int = 100) -> int:
        """
        Migrate positions from SQLite to PostgreSQL.

        Args:
            batch_size: Number of rows to process at once

        Returns:
            Number of positions migrated
        """
        logger.info("Migrating positions...")
        sqlite_session = self.SQLiteSession()
        postgres_session = self.PostgresSession()

        migrated_count = 0
        updated_count = 0

        try:
            # Get all positions from SQLite
            sqlite_positions = sqlite_session.query(PositionORM).all()
            total = len(sqlite_positions)
            logger.info(f"Found {total} positions in SQLite")

            # Process in batches
            for i in range(0, total, batch_size):
                batch = sqlite_positions[i : i + batch_size]

                with postgres_session.begin():
                    for position in batch:
                        # Check if position already exists (by symbol)
                        existing = (
                            postgres_session.query(PositionORM)
                            .filter_by(symbol=position.symbol)
                            .first()
                        )

                        if existing:
                            # Update existing position with latest data
                            existing.side = position.side
                            existing.quantity = position.quantity
                            existing.average_price = position.average_price
                            existing.current_price = position.current_price
                            existing.unrealized_pnl = position.unrealized_pnl
                            existing.realized_pnl = position.realized_pnl
                            existing.timestamp = position.timestamp
                            updated_count += 1
                        else:
                            # Create new position
                            new_position = PositionORM(
                                symbol=position.symbol,
                                side=position.side,
                                quantity=position.quantity,
                                average_price=position.average_price,
                                current_price=position.current_price,
                                unrealized_pnl=position.unrealized_pnl,
                                realized_pnl=position.realized_pnl,
                                timestamp=position.timestamp,
                            )
                            postgres_session.add(new_position)
                            migrated_count += 1

                logger.info(f"Processed {migrated_count + updated_count}/{total} positions...")

            logger.info(
                f"✅ Positions migration complete: {migrated_count} created, {updated_count} updated"
            )
            return migrated_count + updated_count

        except Exception as e:
            logger.error(f"Error migrating positions: {e}")
            raise

        finally:
            sqlite_session.close()
            postgres_session.close()

    def validate_migration(self) -> bool:
        """
        Validate migration by comparing counts.

        Returns:
            True if validation passes
        """
        logger.info("Validating migration...")
        counts = self.get_counts()

        sqlite_trades = counts["sqlite"]["trades"]
        postgres_trades = counts["postgres"]["trades"]
        sqlite_positions = counts["sqlite"]["positions"]
        postgres_positions = counts["postgres"]["positions"]

        logger.info(
            f"SQLite:     {sqlite_trades} trades, {sqlite_positions} positions"
        )
        logger.info(
            f"PostgreSQL: {postgres_trades} trades, {postgres_positions} positions"
        )

        # Allow postgres to have more or equal rows (idempotent runs)
        trades_valid = postgres_trades >= sqlite_trades
        positions_valid = postgres_positions >= sqlite_positions

        if trades_valid and positions_valid:
            logger.info("✅ Validation passed!")
            return True
        else:
            logger.error("❌ Validation failed: PostgreSQL has fewer rows than SQLite")
            return False

    def run(self):
        """Execute full migration"""
        logger.info("=" * 80)
        logger.info("SQLite to PostgreSQL Migration")
        logger.info("=" * 80)

        # Verify source exists
        if not self.verify_sqlite_exists():
            return False

        # Verify target schema exists
        if not self.verify_postgres_schema():
            logger.error(
                "Run 'alembic upgrade head' first to create PostgreSQL schema"
            )
            return False

        # Show initial counts
        logger.info("\n📊 Initial counts:")
        initial_counts = self.get_counts()
        logger.info(f"  SQLite:     {initial_counts['sqlite']['trades']} trades, {initial_counts['sqlite']['positions']} positions")
        logger.info(f"  PostgreSQL: {initial_counts['postgres']['trades']} trades, {initial_counts['postgres']['positions']} positions")

        # Clear target tables if requested
        if self.delete_target_tables:
            confirm = input(
                "\n⚠️  You are about to DELETE all data from PostgreSQL tables. Type 'DELETE' to confirm: "
            )
            if confirm != "DELETE":
                logger.info("❌ Deletion cancelled by user")
                return False
            self.clear_postgres_tables()

        # Migrate data
        logger.info("\n🚀 Starting migration...")
        try:
            trades_migrated = self.migrate_trades()
            positions_migrated = self.migrate_positions()

            # Validate
            logger.info("")
            if self.validate_migration():
                logger.info("\n✅ Migration completed successfully!")
                return True
            else:
                logger.error("\n❌ Migration validation failed!")
                return False

        except Exception as e:
            logger.error(f"\n❌ Migration failed: {e}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate trading data from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_DB_PATH", "/app/data/portfolio.db"),
        help="Path to SQLite database file",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://trading_user:trading_pass_CHANGE_ME@localhost:5432/binance_trading",
        ),
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--delete-target",
        action="store_true",
        help="DELETE all rows from PostgreSQL tables before migration (DANGEROUS!)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts (for automation)",
    )

    args = parser.parse_args()

    # Show configuration
    print("\n📋 Migration Configuration:")
    print(f"  SQLite path:    {args.sqlite_path}")
    print(f"  PostgreSQL URL: {args.database_url.split('@')[0]}***")
    print(f"  Delete target:  {args.delete_target}")
    print("")

    if not args.yes:
        confirm = input("Proceed with migration? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ Migration cancelled")
            sys.exit(0)

    # Run migration
    migrator = SQLiteToPostgresMigrator(
        sqlite_path=args.sqlite_path,
        postgres_url=args.database_url,
        delete_target_tables=args.delete_target,
    )

    success = migrator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
