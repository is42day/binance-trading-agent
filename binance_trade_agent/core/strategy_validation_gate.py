"""
Strategy Validation Gate — reads the gate artifact JSON produced by
``micro_strategy_validator.py --output-gate`` and answers whether a symbol
is cleared to trade.

Gate rules (in priority order):
  1. File missing → HOLD ("gate_missing")
  2. File stale (age > ttl_seconds) → HOLD ("gate_stale")
  3. Symbol not present in gate → HOLD ("symbol_not_in_gate")
  4. gate_pass = False → HOLD (reason from gate file)
  5. Otherwise → cleared to trade

Usage::

    from binance_trade_agent.core.strategy_validation_gate import ValidationGate

    gate = ValidationGate()                          # reads default path
    result = gate.check("BTCUSDT")
    if result.cleared:
        # signal can proceed
        ...
    else:
        journal.record(..., blocked_reason=result.reason)
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_GATE_PATH = os.getenv(
    "STRATEGY_GATE_PATH",
    "data/strategy_validation/latest.json",
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GateResult:
    """
    Result of a gate check for a specific symbol.

    Attributes:
        cleared:      True if the symbol is cleared to trade.
        reason:       Machine-readable reason (None when cleared).
        symbol:       Symbol that was checked.
        age_seconds:  Age of the gate file in seconds.
        gate_data:    Raw gate entry for the symbol (or None).
    """
    cleared: bool
    symbol: str
    age_seconds: Optional[float]
    reason: Optional[str] = None
    gate_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cleared": self.cleared,
            "symbol": self.symbol,
            "age_seconds": self.age_seconds,
            "reason": self.reason,
            "gate_data": self.gate_data,
        }


# ---------------------------------------------------------------------------
# Gate reader
# ---------------------------------------------------------------------------

class ValidationGate:
    """
    Reads and evaluates the strategy validation gate artifact.

    Args:
        gate_path: Path to the gate JSON file.
                   Defaults to ``data/strategy_validation/latest.json``
                   (or ``STRATEGY_GATE_PATH`` env var).
    """

    def __init__(self, gate_path: Optional[str] = None):
        self._gate_path = Path(gate_path or DEFAULT_GATE_PATH)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def check(self, symbol: str) -> GateResult:
        """
        Check whether *symbol* is cleared to trade.

        Returns a :class:`GateResult`.  Callers should check ``.cleared``
        before proceeding with signal execution.
        """
        symbol = symbol.upper()

        # 1. File existence
        if not self._gate_path.exists():
            logger.warning("Strategy gate file not found: %s", self._gate_path)
            return GateResult(cleared=False, symbol=symbol, age_seconds=None, reason="gate_missing")

        # 2. Load
        try:
            artifact = self._load()
        except Exception as exc:
            logger.error("Failed to read strategy gate: %s", exc)
            return GateResult(cleared=False, symbol=symbol, age_seconds=None, reason="gate_read_error")

        # 3. Staleness
        age = self._age_seconds(artifact)
        ttl = artifact.get("ttl_seconds", 86400)
        if age is None or age > ttl:
            logger.warning("Strategy gate is stale: age=%.0fs ttl=%ds", age or -1, ttl)
            return GateResult(cleared=False, symbol=symbol, age_seconds=age, reason="gate_stale")

        # 4. Symbol presence
        symbols = artifact.get("symbols", {})
        if symbol not in symbols:
            logger.warning("Symbol %s not found in strategy gate", symbol)
            return GateResult(
                cleared=False, symbol=symbol, age_seconds=age,
                reason="symbol_not_in_gate", gate_data=None,
            )

        # 5. Gate pass evaluation
        entry = symbols[symbol]
        if not entry.get("gate_pass", False):
            reason = entry.get("gate_reason", "gate_fail")
            logger.warning("Strategy gate BLOCKED for %s: %s", symbol, reason)
            return GateResult(
                cleared=False, symbol=symbol, age_seconds=age,
                reason=reason, gate_data=entry,
            )

        logger.debug("Strategy gate CLEARED for %s (age=%.0fs)", symbol, age)
        return GateResult(cleared=True, symbol=symbol, age_seconds=age, gate_data=entry)

    def get_artifact(self) -> Optional[Dict[str, Any]]:
        """Return the full gate artifact, or None if unreadable."""
        if not self._gate_path.exists():
            return None
        try:
            return self._load()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Any]:
        with open(self._gate_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _age_seconds(artifact: Dict[str, Any]) -> Optional[float]:
        generated_at_str = artifact.get("generated_at")
        if not generated_at_str:
            return None
        try:
            # Accept both "Z" suffix and explicit UTC offset
            generated_at_str = generated_at_str.replace("Z", "+00:00")
            generated_at = datetime.fromisoformat(generated_at_str)
            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            return (now - generated_at).total_seconds()
        except ValueError:
            return None


# ---------------------------------------------------------------------------
# Module-level singleton (lazy)
# ---------------------------------------------------------------------------

_gate: Optional[ValidationGate] = None


def get_validation_gate(gate_path: Optional[str] = None) -> ValidationGate:
    """Return the module-level ValidationGate singleton."""
    global _gate
    if _gate is None or gate_path is not None:
        _gate = ValidationGate(gate_path)
    return _gate
