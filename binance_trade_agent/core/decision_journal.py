"""
Decision Journal — persists every trading decision (BUY/SELL/HOLD) with
full context so the operator can understand why each action was taken or
skipped.

Usage::

    from binance_trade_agent.core.decision_journal import DecisionJournal

    journal = DecisionJournal()
    journal.record(
        symbol="BTCUSDT",
        signal="HOLD",
        strategy="adaptive_core_micro",
        confidence=0.0,
        blocked_reason="strategy_validation_gate_negative",
        risk_approved=False,
        execution_policy={"mode": "maker_first"},
        metadata={"component": "micro", "gate_age_seconds": 3700},
    )

    latest = journal.get_latest("BTCUSDT")
    history = journal.get_history("BTCUSDT", limit=50)
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from binance_trade_agent.core import db
from binance_trade_agent.core.portfolio_manager import TradingDecisionORM

logger = logging.getLogger(__name__)


class DecisionJournal:
    """Persist and query trading decisions."""

    def __init__(self, session_factory=None):
        """
        Args:
            session_factory: A callable returning a SQLAlchemy Session.
                             Defaults to the global ``db.SessionLocal``.
        """
        self._session_factory = session_factory or db.SessionLocal

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record(
        self,
        symbol: str,
        signal: str,
        strategy: Optional[str] = None,
        confidence: Optional[float] = None,
        blocked_reason: Optional[str] = None,
        risk_approved: bool = False,
        execution_policy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Persist a trading decision.

        Args:
            symbol:           Trading pair e.g. "BTCUSDT"
            signal:           "BUY", "SELL", or "HOLD"
            strategy:         Strategy name that produced the signal
            confidence:       Signal confidence [0.0, 1.0]
            blocked_reason:   Why the signal was not executed (None = not blocked)
            risk_approved:    Whether risk management approved the signal
            execution_policy: Dict describing how the order would be placed
            metadata:         Arbitrary extra context (strategy component, gate age, …)
            timestamp:        Decision time (defaults to now)

        Returns:
            The generated decision UUID string.
        """
        decision_id = str(uuid.uuid4())
        now = timestamp or datetime.utcnow()

        row = TradingDecisionORM(
            id=decision_id,
            symbol=symbol.upper(),
            signal=signal.upper(),
            strategy=strategy,
            confidence=confidence,
            blocked_reason=blocked_reason,
            risk_approved="true" if risk_approved else "false",
            execution_policy=json.dumps(execution_policy) if execution_policy else None,
            metadata_=json.dumps(metadata) if metadata else None,
            timestamp=now,
        )

        try:
            with self._session_factory() as session:
                session.add(row)
                session.commit()
            logger.debug(
                "Decision recorded: id=%s symbol=%s signal=%s blocked=%s",
                decision_id,
                symbol,
                signal,
                blocked_reason,
            )
        except Exception:
            logger.exception("Failed to persist trading decision for %s", symbol)

        return decision_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_latest(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Return the most recent decision, optionally filtered by symbol.

        Args:
            symbol: If supplied, only consider decisions for this pair.

        Returns:
            Decision dict or None if no decisions exist.
        """
        try:
            with self._session_factory() as session:
                query = session.query(TradingDecisionORM).order_by(
                    TradingDecisionORM.timestamp.desc()
                )
                if symbol:
                    query = query.filter(TradingDecisionORM.symbol == symbol.upper())
                row = query.first()
                return row.to_dict() if row else None
        except Exception:
            logger.exception("Failed to query latest decision for %s", symbol)
            return None

    def get_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return the most recent ``limit`` decisions, newest first.

        Args:
            symbol: Optional symbol filter.
            limit:  Maximum number of records to return.

        Returns:
            List of decision dicts.
        """
        try:
            with self._session_factory() as session:
                query = session.query(TradingDecisionORM).order_by(
                    TradingDecisionORM.timestamp.desc()
                )
                if symbol:
                    query = query.filter(TradingDecisionORM.symbol == symbol.upper())
                rows = query.limit(limit).all()
                return [r.to_dict() for r in rows]
        except Exception:
            logger.exception("Failed to query decision history for %s", symbol)
            return []


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_journal: Optional[DecisionJournal] = None


def get_decision_journal() -> DecisionJournal:
    """Return the module-level DecisionJournal singleton."""
    global _journal
    if _journal is None:
        _journal = DecisionJournal()
    return _journal
