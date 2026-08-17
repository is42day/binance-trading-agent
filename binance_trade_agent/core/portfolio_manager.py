"""
Portfolio Management Module - Tracks positions, trades, and P&L using SQLAlchemy ORM
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    String,
    Text,
    UniqueConstraint,
    inspect,
    or_,
    text,
)
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import declarative_base

from binance_trade_agent.core import db

# ============================================================================
# Data Classes
# ============================================================================


def retry_on_db_error(max_retries: int = 3, backoff_seconds: float = 0.5):
    """
    Decorator to retry database operations on transient errors.

    Useful for handling connection resets, serialization failures, etc.
    Only retries OperationalError (connection issues), not data integrity errors.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_seconds: Initial backoff time (doubles each retry)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_backoff = backoff_seconds

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    retries += 1
                    if retries >= max_retries:
                        raise  # Give up after max retries

                    # Log and retry with backoff
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Database operational error (attempt {retries}/{max_retries}): {e}. "
                        f"Retrying in {current_backoff}s..."
                    )
                    time.sleep(current_backoff)
                    current_backoff *= 2  # Exponential backoff

            return func(*args, **kwargs)  # Final attempt

        return wrapper

    return decorator


@dataclass
class Trade:
    """Simple Trade data class for use in tests and APIs"""

    trade_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    order_id: Optional[str] = None
    correlation_id: Optional[str] = None


# Initialize SQLAlchemy
Base = declarative_base()

# ============================================================================
# SQLAlchemy ORM Models (Top-Level Definition)
# ============================================================================


class PositionORM(Base):
    """ORM model for trading positions"""

    __tablename__ = "positions"

    symbol = Column(String, primary_key=True)
    side = Column(String, nullable=False)  # LONG or SHORT
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "market_value": self.quantity * self.current_price,
            "total_pnl": self.realized_pnl + self.unrealized_pnl,
        }


class TradeORM(Base):
    """ORM model for executed trades"""

    __tablename__ = "trades"

    trade_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    order_id = Column(String, nullable=True)
    client_order_id = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_trades_order_id"),
        UniqueConstraint("client_order_id", name="uq_trades_client_order_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "fee": self.fee,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "correlation_id": self.correlation_id,
            "pnl": self.pnl,
            "total_value": (self.quantity * self.price) + self.fee,
        }


class ExchangeOrderORM(Base):
    """ORM model for exchange order lifecycle tracking."""

    __tablename__ = "exchange_orders"

    client_order_id = Column(String, primary_key=True)
    order_id = Column(String, nullable=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    order_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    executed_quantity = Column(Float, nullable=False, default=0.0)
    last_booked_quantity = Column(Float, nullable=False, default=0.0)
    price = Column(Float, nullable=True)
    avg_fill_price = Column(Float, nullable=True)
    fee = Column(Float, nullable=False, default=0.0)
    correlation_id = Column(String, nullable=True)
    cancel_reason = Column(String, nullable=True)
    raw_response = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_reconciled_at = Column(DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary."""
        raw_response = None
        if self.raw_response:
            try:
                raw_response = json.loads(self.raw_response)
            except (json.JSONDecodeError, TypeError):
                raw_response = self.raw_response

        return {
            "client_order_id": self.client_order_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "status": self.status,
            "quantity": self.quantity,
            "executed_quantity": self.executed_quantity,
            "last_booked_quantity": self.last_booked_quantity,
            "price": self.price,
            "avg_fill_price": self.avg_fill_price,
            "fee": self.fee,
            "correlation_id": self.correlation_id,
            "cancel_reason": self.cancel_reason,
            "raw_response": raw_response,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_reconciled_at": (
                self.last_reconciled_at.isoformat() if self.last_reconciled_at else None
            ),
        }


class HeartbeatORM(Base):
    """ORM model for service heartbeat monitoring"""

    __tablename__ = "heartbeat"

    service_name = Column(String, primary_key=True)
    last_update = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default="healthy")
    details = Column(String, nullable=True)  # JSON-encoded details

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        details = {}
        if self.details:
            try:
                details = json.loads(self.details)
            except (json.JSONDecodeError, TypeError):
                details = {"raw": self.details}

        return {
            "service_name": self.service_name,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "status": self.status,
            "details": details,
        }


class SystemStateORM(Base):
    """ORM model for shared system control state."""

    __tablename__ = "system_state"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    updated_by = Column(String, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }


class TradingDecisionORM(Base):
    """ORM model for the trading decision journal."""

    __tablename__ = "trading_decisions"

    id = Column(String, primary_key=True)  # UUID
    symbol = Column(String, nullable=False)
    signal = Column(String, nullable=False)  # BUY | SELL | HOLD
    strategy = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    blocked_reason = Column(String, nullable=True)  # None when not blocked
    risk_approved = Column(String, nullable=False, default="false")  # "true"/"false"
    execution_policy = Column(Text, nullable=True)  # JSON blob
    metadata_ = Column("metadata", Text, nullable=True)  # JSON blob - extra context
    timestamp = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        exec_policy = None
        if self.execution_policy:
            try:
                exec_policy = json.loads(self.execution_policy)
            except (json.JSONDecodeError, TypeError):
                exec_policy = self.execution_policy

        extra_meta = None
        if self.metadata_:
            try:
                extra_meta = json.loads(self.metadata_)
            except (json.JSONDecodeError, TypeError):
                extra_meta = self.metadata_

        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal": self.signal,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "blocked_reason": self.blocked_reason,
            "risk_approved": self.risk_approved == "true",
            "execution_policy": exec_policy,
            "metadata": extra_meta,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ============================================================================
# Portfolio Manager - SQLAlchemy-Based Implementation
# ============================================================================


class PortfolioManager:
    """Manages portfolio positions, trades, and P&L using SQLAlchemy ORM"""

    def __init__(self, db_path: str = "/app/data/portfolio.db", use_shared_session: bool = True):
        """
        Initialize portfolio manager with SQLAlchemy session.

        Args:
            db_path: Path to SQLite database (used only if DATABASE_URL not set)
            use_shared_session: If True, uses shared session factory from db module.
                               If False, creates own engine (legacy mode for tests).
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._read_cache: Dict[str, Any] = {}
        self._read_cache_expires_at: Dict[str, float] = {}
        self._read_cache_ttl_seconds = float(os.getenv("PORTFOLIO_READ_CACHE_TTL_SECONDS", "0.25"))
        self._dispose_on_clear = (
            not db.os.getenv("DATABASE_URL") and db_path != "/app/data/portfolio.db"
        )

        if use_shared_session:
            # Use centralized DB configuration (recommended)
            # Set DB_PATH env var if db_path provided and DATABASE_URL not set
            if not db.os.getenv("DATABASE_URL") and db_path != "/app/data/portfolio.db":
                normalized_path = db.normalize_sqlite_path(db_path)
                if db.os.environ.get("DB_PATH") != normalized_path:
                    db.os.environ["DB_PATH"] = normalized_path
                    db.reset_engine()

            self.engine = db.get_engine()
            self.SessionLocal = db.get_session_factory()
            Base.metadata.create_all(self.engine, checkfirst=True)
            self._ensure_runtime_schema_compatibility()
            self.db_path = None  # Not used with shared session
        else:
            # Legacy mode: create own SQLite engine (for backward compatibility)
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            self.db_path = db.normalize_sqlite_path(db_path)
            self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
            Base.metadata.create_all(self.engine, checkfirst=True)
            self._ensure_runtime_schema_compatibility()
            self.SessionLocal = sessionmaker(bind=self.engine)

    def _ensure_runtime_schema_compatibility(self):
        """
        Patch older SQLite/dev schemas that predate recent nullable columns.

        Production PostgreSQL should be managed by Alembic. This guard keeps
        local SQLite databases and legacy test DBs readable after model changes.
        """
        if self.engine.dialect.name != "sqlite":
            return

        inspector = inspect(self.engine)
        tables = set(inspector.get_table_names())
        if "trades" not in tables:
            return

        trade_columns = {column["name"] for column in inspector.get_columns("trades")}
        exchange_order_columns = (
            {column["name"] for column in inspector.get_columns("exchange_orders")}
            if "exchange_orders" in tables
            else set()
        )
        with self.engine.begin() as connection:
            if "client_order_id" not in trade_columns:
                connection.execute(text("ALTER TABLE trades ADD COLUMN client_order_id VARCHAR"))
            if "exchange_orders" in tables:
                if "last_booked_quantity" not in exchange_order_columns:
                    connection.execute(
                        text(
                            "ALTER TABLE exchange_orders ADD COLUMN"
                            " last_booked_quantity REAL NOT NULL DEFAULT 0.0"
                        )
                    )
                if "cancel_reason" not in exchange_order_columns:
                    connection.execute(
                        text("ALTER TABLE exchange_orders ADD COLUMN cancel_reason VARCHAR")
                    )

        Base.metadata.create_all(self.engine, checkfirst=True)

    def get_session(self) -> SQLAlchemySession:
        """Get a new database session"""
        return self.SessionLocal()

    def _get_cached_read(self, key: str):
        if self._read_cache_ttl_seconds <= 0:
            return None
        if time.monotonic() >= self._read_cache_expires_at.get(key, 0):
            self._read_cache.pop(key, None)
            self._read_cache_expires_at.pop(key, None)
            return None
        return self._read_cache.get(key)

    def _set_cached_read(self, key: str, value: Any):
        if self._read_cache_ttl_seconds <= 0:
            return
        self._read_cache[key] = value
        self._read_cache_expires_at[key] = time.monotonic() + self._read_cache_ttl_seconds

    def _clear_read_cache(self):
        self._read_cache.clear()
        self._read_cache_expires_at.clear()

    @retry_on_db_error(max_retries=3, backoff_seconds=0.5)
    def add_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        fee: float,
        order_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        pnl: Optional[float] = None,
        client_order_id: Optional[str] = None,
    ) -> TradeORM:
        """
        Add a new trade to the portfolio and update position atomically.

        Uses a single transaction to ensure consistency between trade insertion
        and position updates. This prevents partial updates in concurrent scenarios.
        """
        session = self.get_session()
        try:
            # Use session.begin() for explicit transaction control
            with session.begin():
                trade = TradeORM(
                    trade_id=trade_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    fee=fee,
                    timestamp=datetime.now(),
                    order_id=order_id,
                    client_order_id=client_order_id,
                    correlation_id=correlation_id,
                    pnl=pnl,
                )
                session.add(trade)

                # Update position in same transaction (atomic operation)
                self._update_position_from_trade(session, trade)

            # Transaction automatically committed if no exception
            self._clear_read_cache()
            self.logger.info(f"Added trade: {side} {quantity} {symbol} @ ${price:.2f}")
            return trade

        except Exception as e:
            # Transaction automatically rolled back on exception
            self.logger.error(f"Error adding trade: {str(e)}")
            raise
        finally:
            session.close()

    def _update_position_from_trade(self, session: SQLAlchemySession, trade):
        """Update position based on new trade"""
        try:
            # Handle both TradeORM objects and dictionaries
            if isinstance(trade, dict):
                symbol = trade.get("symbol")
                side = trade.get("side")
                quantity = trade.get("quantity")
                price = trade.get("price")
                fee = trade.get("fee", 0.001)  # Default fee
            else:
                # Assume it's a TradeORM object
                symbol = trade.symbol
                side = trade.side
                quantity = trade.quantity
                price = trade.price
                fee = getattr(trade, "fee", 0.001)  # Default fee

            # Validate required fields
            if not symbol or not side or quantity is None or price is None:
                error_msg = f"Invalid trade data: symbol={symbol}, side={side}, quantity={quantity}, price={price}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

            position = session.query(PositionORM).filter_by(symbol=symbol).first()

            if position is None:
                # Create new position
                side_str = "LONG" if side == "BUY" else "SHORT"
                quantity_val = quantity if side == "BUY" else -quantity

                position = PositionORM(
                    symbol=symbol,
                    side=side_str,
                    quantity=quantity_val,
                    average_price=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    realized_pnl=-fee,
                    timestamp=datetime.now(),
                )
                session.add(position)
            else:
                # Update existing position
                if side == "BUY":
                    if position.quantity >= 0:
                        # Adding to long position
                        total_value = (position.quantity * position.average_price) + (
                            quantity * price
                        )
                        total_quantity = position.quantity + quantity
                        position.average_price = (
                            total_value / total_quantity if total_quantity > 0 else 0
                        )
                        position.quantity = total_quantity
                    else:
                        # Reducing short position or going long
                        if abs(position.quantity) >= quantity:
                            pnl = (position.average_price - price) * quantity
                            position.realized_pnl += pnl - fee
                            position.quantity += quantity
                        else:
                            cover_quantity = abs(position.quantity)
                            cover_pnl = (position.average_price - price) * cover_quantity
                            position.realized_pnl += cover_pnl

                            remaining_quantity = quantity - cover_quantity
                            position.quantity = remaining_quantity
                            position.average_price = price
                            position.side = "LONG"
                            position.realized_pnl -= fee

                else:  # SELL
                    if position.quantity > 0:
                        # Reducing long position
                        if position.quantity >= quantity:
                            pnl = (price - position.average_price) * quantity
                            position.realized_pnl += pnl - fee
                            position.quantity -= quantity
                        else:
                            close_quantity = position.quantity
                            close_pnl = (price - position.average_price) * close_quantity
                            position.realized_pnl += close_pnl

                            remaining_quantity = quantity - close_quantity
                            position.quantity = -remaining_quantity
                            position.average_price = price
                            position.side = "SHORT"
                            position.realized_pnl -= fee
                    else:
                        # Adding to short position
                        total_value = (abs(position.quantity) * position.average_price) + (
                            quantity * price
                        )
                        total_quantity = abs(position.quantity) + quantity
                        position.average_price = total_value / total_quantity
                        position.quantity = -total_quantity

                position.timestamp = datetime.now()

            self.logger.info(f"Position updated for {symbol}")
        except Exception as e:
            self.logger.error(f"Error updating position: {str(e)}")
            raise

    def update_market_prices(self, prices: Dict[str, float]):
        """Update current market prices for all positions"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()

            for position in positions:
                if position.symbol in prices:
                    position.current_price = prices[position.symbol]

                    # Calculate unrealized PnL
                    if position.quantity > 0:
                        position.unrealized_pnl = (
                            position.current_price - position.average_price
                        ) * position.quantity
                    elif position.quantity < 0:
                        position.unrealized_pnl = (
                            position.average_price - position.current_price
                        ) * abs(position.quantity)
                    else:
                        position.unrealized_pnl = 0.0

            session.commit()
            self._clear_read_cache()
            self.logger.info(f"Updated prices for {len(prices)} symbols")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating market prices: {str(e)}")
            raise
        finally:
            session.close()

    def get_position(self, symbol: str) -> Optional[PositionORM]:
        """Get position for a specific symbol"""
        session = self.get_session()
        try:
            position = session.query(PositionORM).filter_by(symbol=symbol).first()
            return position
        finally:
            session.close()

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions as dictionaries"""
        cache_key = "all_positions"
        cached = self._get_cached_read(cache_key)
        if cached is not None:
            return cached

        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            result = [pos.to_dict() for pos in positions]
            self._set_cached_read(cache_key, result)
            return result
        finally:
            session.close()

    def get_trade_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a trade by exchange order ID."""
        if not order_id:
            return None

        session = self.get_session()
        try:
            trade = session.query(TradeORM).filter_by(order_id=str(order_id)).first()
            return trade.to_dict() if trade else None
        finally:
            session.close()

    def get_trade_by_client_order_id(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        """Get a trade by exchange client order ID."""
        if not client_order_id:
            return None

        session = self.get_session()
        try:
            trade = session.query(TradeORM).filter_by(client_order_id=client_order_id).first()
            return trade.to_dict() if trade else None
        finally:
            session.close()

    @retry_on_db_error(max_retries=3, backoff_seconds=0.5)
    def upsert_exchange_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update exchange order lifecycle state."""
        client_order_id = order_data.get("client_order_id")
        if not client_order_id:
            raise ValueError("client_order_id is required")

        now = datetime.now()
        session = self.get_session()
        try:
            with session.begin():
                order = session.get(ExchangeOrderORM, client_order_id)
                if order is None:
                    order = ExchangeOrderORM(
                        client_order_id=client_order_id,
                        created_at=order_data.get("created_at") or now,
                        updated_at=now,
                        symbol=order_data["symbol"],
                        side=order_data["side"],
                        order_type=order_data["order_type"],
                        status=order_data.get("status", "UNKNOWN"),
                        quantity=float(order_data.get("quantity") or 0),
                        executed_quantity=float(order_data.get("executed_quantity") or 0),
                    )
                    session.add(order)

                order.order_id = str(order_data.get("order_id") or order.order_id or "")
                order.symbol = order_data.get("symbol", order.symbol)
                order.side = order_data.get("side", order.side)
                order.order_type = order_data.get("order_type", order.order_type)
                order.status = order_data.get("status", order.status)
                order.quantity = float(order_data.get("quantity", order.quantity) or 0)
                order.executed_quantity = float(
                    order_data.get("executed_quantity", order.executed_quantity) or 0
                )
                if "last_booked_quantity" in order_data:
                    order.last_booked_quantity = float(order_data["last_booked_quantity"] or 0)
                order.price = order_data.get("price", order.price)
                order.avg_fill_price = order_data.get("avg_fill_price", order.avg_fill_price)
                order.fee = float(order_data.get("fee", order.fee) or 0)
                order.correlation_id = order_data.get("correlation_id", order.correlation_id)
                if "cancel_reason" in order_data:
                    order.cancel_reason = order_data["cancel_reason"]
                raw_response = order_data.get("raw_response")
                if raw_response is not None:
                    order.raw_response = json.dumps(raw_response, default=str)
                order.updated_at = now
                if order_data.get("last_reconciled_at"):
                    order.last_reconciled_at = order_data["last_reconciled_at"]

            self._clear_read_cache()
            return self.get_exchange_order(client_order_id) or {}
        finally:
            session.close()

    def get_exchange_order(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        """Get an exchange order by client order ID."""
        session = self.get_session()
        try:
            order = session.get(ExchangeOrderORM, client_order_id)
            return order.to_dict() if order else None
        finally:
            session.close()

    def get_open_exchange_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get locally tracked orders that may still need reconciliation.

        Filled orders are returned only when no matching local trade exists. This
        covers the crash window between recording an exchange fill and booking
        the portfolio trade.
        """
        reconcilable_statuses = {"NEW", "PARTIALLY_FILLED", "PENDING_NEW", "UNKNOWN", "FILLED"}
        session = self.get_session()
        try:
            query = session.query(ExchangeOrderORM).filter(
                ExchangeOrderORM.status.in_(reconcilable_statuses)
            )
            if symbol:
                query = query.filter_by(symbol=symbol)

            results = []
            for order in query.order_by(ExchangeOrderORM.created_at.asc()):
                if order.status == "FILLED":
                    existing_trade = None
                    if order.client_order_id:
                        existing_trade = (
                            session.query(TradeORM)
                            .filter_by(client_order_id=order.client_order_id)
                            .first()
                        )
                    if not existing_trade and order.order_id:
                        existing_trade = (
                            session.query(TradeORM).filter_by(order_id=order.order_id).first()
                        )
                    if existing_trade:
                        continue
                results.append(order.to_dict())
            return results
        finally:
            session.close()

    def get_terminal_exchange_orders(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Return orders in terminal states (FILLED, CANCELED, REJECTED, EXPIRED)."""
        terminal_statuses = {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}
        session = self.get_session()
        try:
            query = session.query(ExchangeOrderORM).filter(
                ExchangeOrderORM.status.in_(terminal_statuses)
            )
            if symbol:
                query = query.filter_by(symbol=symbol)
            query = query.order_by(ExchangeOrderORM.updated_at.desc()).limit(limit)
            return [o.to_dict() for o in query.all()]
        finally:
            session.close()

    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            return sum(pos.quantity * pos.current_price for pos in positions)
        finally:
            session.close()

    def get_exposure_summary(self, initial_equity: Optional[float] = None) -> Dict[str, Any]:
        """Return cash-free exposure metrics for risk controls and dashboards.

        The portfolio database tracks positions and P&L, not exchange cash balances.
        For risk checks we estimate account equity as configured initial equity plus
        realized/unrealized P&L, then compare absolute deployed position value to it.
        """
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            realized_pnl = sum(pos.realized_pnl for pos in positions)
            unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            deployed_value = sum(abs(pos.quantity * pos.current_price) for pos in positions)
            long_value = sum(
                pos.quantity * pos.current_price for pos in positions if pos.quantity > 0
            )
            short_value = sum(
                abs(pos.quantity * pos.current_price) for pos in positions if pos.quantity < 0
            )
            active_positions = [pos for pos in positions if abs(pos.quantity) > 0]
            starting_equity = (
                float(initial_equity)
                if initial_equity is not None
                else float(os.getenv("PORTFOLIO_INITIAL_VALUE", "100000.0"))
            )
            estimated_equity = max(starting_equity + realized_pnl + unrealized_pnl, 0.0)
            estimated_cash = estimated_equity - deployed_value
            exposure_pct = deployed_value / estimated_equity if estimated_equity > 0 else 0.0

            return {
                "starting_equity": starting_equity,
                "estimated_equity": estimated_equity,
                "estimated_cash": estimated_cash,
                "deployed_value": deployed_value,
                "long_value": long_value,
                "short_value": short_value,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "total_pnl": realized_pnl + unrealized_pnl,
                "exposure_pct": exposure_pct,
                "active_positions_count": len(active_positions),
                "positions": {
                    pos.symbol: {
                        "quantity": pos.quantity,
                        "value": abs(pos.quantity * pos.current_price),
                        "side": pos.side,
                        "average_price": pos.average_price,
                        "current_price": pos.current_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                        "realized_pnl": pos.realized_pnl,
                    }
                    for pos in active_positions
                },
            }
        finally:
            session.close()

    def get_total_pnl(self) -> float:
        """Calculate total P&L across all positions"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            return sum((pos.realized_pnl + pos.unrealized_pnl) for pos in positions)
        finally:
            session.close()

    def get_trade_history(
        self, symbol: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get trade history, optionally filtered by symbol"""
        cache_key = f"trade_history:{symbol}:{limit}"
        cached = self._get_cached_read(cache_key)
        if cached is not None:
            return cached

        session = self.get_session()
        try:
            query = session.query(TradeORM)

            if symbol:
                query = query.filter_by(symbol=symbol)

            query = query.order_by(TradeORM.timestamp.desc())

            if limit:
                query = query.limit(limit)

            trades = query.all()

            result = [trade.to_dict() for trade in trades]
            self._set_cached_read(cache_key, result)
            return result
        finally:
            session.close()

    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Calculate portfolio statistics"""
        cache_key = "portfolio_stats"
        cached = self._get_cached_read(cache_key)
        if cached is not None:
            return cached

        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            trades = session.query(TradeORM).all()

            total_value = sum(pos.quantity * pos.current_price for pos in positions)
            total_pnl = sum((pos.realized_pnl + pos.unrealized_pnl) for pos in positions)
            total_fees = sum(trade.fee for trade in trades)

            # Calculate win rate
            profitable_trades = [t for t in trades if t.pnl and t.pnl > 0]
            win_rate = len(profitable_trades) / len(trades) if trades else 0.0

            # Calculate max drawdown
            running_pnl = 0.0
            peak_pnl = 0.0
            max_drawdown = 0.0

            for trade in sorted(trades, key=lambda x: x.timestamp):
                if trade.pnl:
                    running_pnl += trade.pnl
                    peak_pnl = max(peak_pnl, running_pnl)
                    drawdown = peak_pnl - running_pnl
                    max_drawdown = max(max_drawdown, drawdown)

            result = {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_fees": total_fees,
                "number_of_trades": len(trades),
                "win_rate": win_rate,
                "max_drawdown": max_drawdown,
                "positions_count": len(positions),
            }
            result.update(self.get_exposure_summary())
            self._set_cached_read(cache_key, result)
            return result
        finally:
            session.close()

    def export_to_json(self) -> str:
        """Export portfolio data to JSON"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            trades = session.query(TradeORM).all()
            exchange_orders = session.query(ExchangeOrderORM).all()

            data = {
                "positions": [pos.to_dict() for pos in positions],
                "trades": [trade.to_dict() for trade in trades],
                "exchange_orders": [order.to_dict() for order in exchange_orders],
                "stats": self.get_portfolio_stats(),
                "export_timestamp": datetime.now().isoformat(),
            }

            return json.dumps(data, indent=2)
        finally:
            session.close()

    def clear_portfolio(self):
        """Clear all positions and trades (for testing/reset)"""
        session = self.get_session()
        try:
            session.query(PositionORM).delete()
            session.query(TradeORM).delete()
            session.query(ExchangeOrderORM).delete()
            session.commit()
            self._clear_read_cache()
            self.logger.info("Portfolio cleared")
        finally:
            session.close()
            if self._dispose_on_clear:
                self.engine.dispose()
                if db.os.getenv("DB_PATH"):
                    db.reset_engine()

    # ========================================================================
    # Heartbeat Management - Service Liveness Monitoring
    # ========================================================================

    @retry_on_db_error(max_retries=3, backoff_seconds=0.5)
    def update_heartbeat(
        self, service_name: str, status: str = "healthy", details: Optional[Dict[str, Any]] = None
    ):
        """
        Update or create a heartbeat record for a service.

        Args:
            service_name: Name of the service (e.g., "trading-agent", "api", "dashboard")
            status: Status string (e.g., "healthy", "degraded", "unhealthy")
            details: Optional dict with additional details (will be JSON-encoded)
        """
        session = self.get_session()
        try:
            with session.begin():
                details_json = json.dumps(details) if details else None

                # Try to update existing heartbeat
                heartbeat = (
                    session.query(HeartbeatORM)
                    .filter(HeartbeatORM.service_name == service_name)
                    .first()
                )

                if heartbeat:
                    heartbeat.last_update = datetime.now()
                    heartbeat.status = status
                    heartbeat.details = details_json
                else:
                    # Create new heartbeat
                    heartbeat = HeartbeatORM(
                        service_name=service_name,
                        last_update=datetime.now(),
                        status=status,
                        details=details_json,
                    )
                    session.add(heartbeat)

                self.logger.debug(f"Updated heartbeat for {service_name}: {status}")
        finally:
            session.close()

    @retry_on_db_error(max_retries=3, backoff_seconds=0.5)
    def try_claim_heartbeat(
        self,
        service_name: str,
        stale_after_seconds: float,
        status: str = "starting",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Atomically claim a heartbeat lease for service_name.

        Returns True if no row exists yet, or the existing row is either
        marked "stopped" or stale (last_update older than
        stale_after_seconds) — i.e. this call successfully takes the lease.
        Returns False if a live, fresh heartbeat already exists, meaning
        another instance holds it.

        A plain read-then-write (get_heartbeat + update_heartbeat) has a
        TOCTOU race: two instances starting together can both read "no
        live heartbeat" before either writes. This uses a single
        UPDATE ... WHERE for the steal-a-stale-lease case, which SQLite
        evaluates atomically (concurrent writers to the same row serialize
        at the file-lock level), and falls back to an INSERT guarded by the
        service_name primary key for the no-row-yet case, so at most one of
        two racing first-time claims can succeed.
        """
        details_json = json.dumps(details) if details else None
        now = datetime.now()
        stale_cutoff = now - timedelta(seconds=stale_after_seconds)

        session = self.get_session()
        try:
            updated = (
                session.query(HeartbeatORM)
                .filter(
                    HeartbeatORM.service_name == service_name,
                    or_(
                        HeartbeatORM.status == "stopped",
                        HeartbeatORM.last_update < stale_cutoff,
                    ),
                )
                .update(
                    {
                        HeartbeatORM.status: status,
                        HeartbeatORM.last_update: now,
                        HeartbeatORM.details: details_json,
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                session.commit()
                return True

            session.rollback()

            exists = (
                session.query(HeartbeatORM.service_name)
                .filter(HeartbeatORM.service_name == service_name)
                .first()
            )
            if exists is not None:
                return False

            try:
                session.add(
                    HeartbeatORM(
                        service_name=service_name,
                        last_update=now,
                        status=status,
                        details=details_json,
                    )
                )
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
        finally:
            session.close()

    def get_heartbeat(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest heartbeat record for a service.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with heartbeat data, or None if not found
        """
        session = self.get_session()
        try:
            heartbeat = (
                session.query(HeartbeatORM)
                .filter(HeartbeatORM.service_name == service_name)
                .first()
            )

            return heartbeat.to_dict() if heartbeat else None
        finally:
            session.close()

    def get_all_heartbeats(self) -> List[Dict[str, Any]]:
        """
        Get all heartbeat records from all services.

        Returns:
            List of heartbeat dictionaries
        """
        session = self.get_session()
        try:
            heartbeats = session.query(HeartbeatORM).all()
            return [hb.to_dict() for hb in heartbeats]
        finally:
            session.close()

    # ========================================================================
    # Shared System State
    # ========================================================================

    @retry_on_db_error(max_retries=3, backoff_seconds=0.5)
    def set_system_state(self, key: str, value: str, updated_by: Optional[str] = None):
        """Set a shared system state key."""
        session = self.get_session()
        try:
            with session.begin():
                state = session.query(SystemStateORM).filter_by(key=key).first()
                if state:
                    state.value = value
                    state.updated_at = datetime.now()
                    state.updated_by = updated_by
                else:
                    session.add(
                        SystemStateORM(
                            key=key,
                            value=value,
                            updated_at=datetime.now(),
                            updated_by=updated_by,
                        )
                    )
        finally:
            session.close()

    def get_system_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a shared system state key."""
        session = self.get_session()
        try:
            state = session.query(SystemStateORM).filter_by(key=key).first()
            return state.to_dict() if state else None
        finally:
            session.close()


# ============================================================================
# Demo Function
# ============================================================================


def demo_portfolio_management():
    """Demo portfolio management functionality"""
    print("=== Portfolio Management Demo ===\n")

    # Initialize portfolio
    portfolio = PortfolioManager("/app/data/demo_portfolio.db")
    portfolio.clear_portfolio()

    # Add demo trades
    trades_data = [
        ("trade_1", "BTCUSDT", "BUY", 0.1, 50000.0, 5.0, "order_1", "corr_1"),
        ("trade_2", "BTCUSDT", "SELL", 0.05, 52000.0, 2.5, "order_2", "corr_2"),
        ("trade_3", "ETHUSDT", "BUY", 1.0, 3000.0, 3.0, "order_3", "corr_3"),
    ]

    for trade_id, symbol, side, quantity, price, fee, order_id, corr_id in trades_data:
        portfolio.add_trade(trade_id, symbol, side, quantity, price, fee, order_id, corr_id)

    # Update market prices
    portfolio.update_market_prices({"BTCUSDT": 51000.0, "ETHUSDT": 3100.0})

    # Show positions
    print("Current Positions:")
    for pos in portfolio.get_all_positions():
        print(
            f"  {pos['symbol']}: {pos['quantity']} @ ${pos['average_price']:.2f} "
            f"(Current: ${pos['current_price']:.2f}, PnL: ${pos['total_pnl']:.2f})"
        )

    # Show stats
    stats = portfolio.get_portfolio_stats()
    print("\nPortfolio Stats:")
    for key, value in stats.items():
        if isinstance(value, float):
            if "value" in key or "pnl" in key or "fee" in key:
                print(f"  {key}: ${value:.2f}")
            elif "rate" in key:
                print(f"  {key}: {value:.1%}")
            else:
                print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # Show trade history
    print("\nTrade History (last 5):")
    for trade in portfolio.get_trade_history(limit=5):
        print(
            f"  {trade['timestamp']}: {trade['side']} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}"
        )

    print("\nPortfolio JSON export available via portfolio.export_to_json()")


if __name__ == "__main__":
    demo_portfolio_management()


# ============================================================================
# Exports for external use
# ============================================================================
__all__ = [
    "Base",
    "PositionORM",
    "TradeORM",
    "ExchangeOrderORM",
    "SystemStateORM",
    "PortfolioManager",
    "demo_portfolio_management",
]
