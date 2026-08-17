"""
Execution Policy — validates market conditions and determines order parameters
before any order reaches TradeExecutionAgent.

Usage::

    from binance_trade_agent.core.execution_policy import ExecutionPolicy, ExecutionPolicyEngine

    policy = ExecutionPolicy(
        execution_mode="maker_first",
        max_spread_pct=0.10,
        max_slippage_pct=0.15,
        limit_price_offset_bps=5,
        stale_order_seconds=60,
    )
    engine = ExecutionPolicyEngine(binance_client, policy)
    result = engine.evaluate("BTCUSDT", "BUY", quantity=0.001)
    if result.approved:
        # place the order using result.order_params
        ...
    else:
        # log result.blocked_reason
        ...
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExecutionPolicy:
    """
    Parameters that govern pre-order checks and order type selection.

    Attributes:
        execution_mode:         "market", "limit", or "maker_first".
                                  "maker_first" places a limit order at
                                  (mid_price - offset) for buys /
                                  (mid_price + offset) for sells.
        max_spread_pct:         Reject if (ask - bid) / mid > this value (%).
        max_slippage_pct:       Reject market orders if estimated slippage > this (%).
        limit_price_offset_bps: Basis-point offset from mid price for maker_first limits.
        stale_order_seconds:    Seconds after which an open limit is considered stale.
        depth_limit:            Order-book levels to fetch for slippage estimation.
    """

    execution_mode: str = "maker_first"
    max_spread_pct: float = 0.10  # %
    max_slippage_pct: float = 0.15  # %
    limit_price_offset_bps: int = 5  # basis points (1 bps = 0.01 %)
    stale_order_seconds: int = 60
    depth_limit: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_mode": self.execution_mode,
            "max_spread_pct": self.max_spread_pct,
            "max_slippage_pct": self.max_slippage_pct,
            "limit_price_offset_bps": self.limit_price_offset_bps,
            "stale_order_seconds": self.stale_order_seconds,
            "depth_limit": self.depth_limit,
        }


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------


@dataclass
class ExecutionEvaluation:
    """
    Result of ``ExecutionPolicyEngine.evaluate()``.

    Attributes:
        approved:       True if order may proceed.
        blocked_reason: Machine-readable reason string when not approved.
        symbol:         Trading pair.
        side:           "BUY" or "SELL".
        quantity:       (Normalised) quantity to submit.
        order_type:     Order type to use: "MARKET" or "LIMIT".
        limit_price:    Computed limit price (None for MARKET orders).
        spread_pct:     Observed spread as a percentage.
        slippage_pct:   Estimated slippage for the requested quantity (%).
        mid_price:      Mid-market price at evaluation time.
        metadata:       Extra diagnostic data.
    """

    approved: bool
    symbol: str
    side: str
    quantity: float
    order_type: str
    blocked_reason: Optional[str] = None
    limit_price: Optional[float] = None
    spread_pct: Optional[float] = None
    slippage_pct: Optional[float] = None
    mid_price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "blocked_reason": self.blocked_reason,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "spread_pct": self.spread_pct,
            "slippage_pct": self.slippage_pct,
            "mid_price": self.mid_price,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ExecutionPolicyEngine:
    """
    Pre-order validation layer. Consumes a BinanceAPIClient and an
    ExecutionPolicy and produces an ExecutionEvaluation that callers
    can act on before touching the exchange.
    """

    def __init__(self, binance_client, policy: Optional[ExecutionPolicy] = None):
        """
        Args:
            binance_client: Instance of BinanceAPIClient (or compatible).
            policy:         ExecutionPolicy configuration. Defaults to safe defaults.
        """
        self._client = binance_client
        self.policy = policy or ExecutionPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> ExecutionEvaluation:
        """
        Run all pre-order checks and determine how to place the order.

        Steps:
          1. Exchange filter validation (quantity / price normalisation).
          2. Order-book fetch → spread check.
          3. Slippage estimation for MARKET / maker_first.
          4. Compute limit price when policy is limit or maker_first.

        Args:
            symbol:   Trading pair.
            side:     "BUY" or "SELL".
            quantity: Requested quantity.
            price:    Optional explicit limit price (used for execution_mode="limit").

        Returns:
            ExecutionEvaluation — inspect ``.approved`` before placing an order.
        """
        symbol = symbol.upper()
        side = side.upper()

        # Step 1: exchange filter validation
        try:
            validation = self._client.validate_order_params(
                symbol,
                side,
                "LIMIT" if self.policy.execution_mode != "market" else "MARKET",
                quantity,
                price,
            )
        except Exception as exc:
            return self._blocked(
                symbol,
                side,
                quantity,
                reason="filter_validation_error",
                metadata={"error": str(exc)},
            )

        if not validation["valid"]:
            return self._blocked(
                symbol,
                side,
                quantity,
                reason="filter_validation_failed",
                metadata={"errors": validation["errors"]},
            )

        normalised_qty = validation["normalized_quantity"]

        # Step 2: fetch order book and check spread
        try:
            book = self._client.get_order_book(symbol, limit=self.policy.depth_limit)
            bids = [(float(p), float(q)) for p, q in book.get("bids", [])]
            asks = [(float(p), float(q)) for p, q in book.get("asks", [])]
        except Exception as exc:
            return self._blocked(
                symbol,
                side,
                normalised_qty,
                reason="order_book_fetch_error",
                metadata={"error": str(exc)},
            )

        if not bids or not asks:
            return self._blocked(
                symbol,
                side,
                normalised_qty,
                reason="order_book_empty",
            )

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid_price * 100

        if spread_pct > self.policy.max_spread_pct:
            return self._blocked(
                symbol,
                side,
                normalised_qty,
                reason="spread_too_wide",
                spread_pct=spread_pct,
                mid_price=mid_price,
                metadata={
                    "spread_pct": round(spread_pct, 6),
                    "max_spread_pct": self.policy.max_spread_pct,
                },
            )

        # Step 3: slippage check (for market and maker_first)
        slippage_pct: Optional[float] = None
        if self.policy.execution_mode in ("market", "maker_first"):
            try:
                slippage_result = self._client.estimate_market_order_slippage(
                    symbol, side, normalised_qty, limit=self.policy.depth_limit
                )
                slippage_pct = slippage_result["slippage_pct"]
            except Exception as exc:
                # Log but don't block on slippage estimation failure
                logger.warning("Slippage estimation failed for %s: %s", symbol, exc)

            if slippage_pct is not None and slippage_pct > self.policy.max_slippage_pct:
                return self._blocked(
                    symbol,
                    side,
                    normalised_qty,
                    reason="slippage_too_high",
                    spread_pct=spread_pct,
                    slippage_pct=slippage_pct,
                    mid_price=mid_price,
                    metadata={
                        "slippage_pct": round(slippage_pct, 6),
                        "max_slippage_pct": self.policy.max_slippage_pct,
                    },
                )

        # Step 4: determine order type and limit price
        order_type, limit_price = self._resolve_order_params(side, mid_price, price, validation)

        logger.info(
            "Execution approved: %s %s %s qty=%.8f mode=%s spread=%.4f%% slippage=%s",
            side,
            symbol,
            order_type,
            normalised_qty,
            self.policy.execution_mode,
            spread_pct,
            f"{slippage_pct:.4f}%" if slippage_pct is not None else "N/A",
        )

        return ExecutionEvaluation(
            approved=True,
            symbol=symbol,
            side=side,
            quantity=normalised_qty,
            order_type=order_type,
            limit_price=limit_price,
            spread_pct=round(spread_pct, 6),
            slippage_pct=round(slippage_pct, 6) if slippage_pct is not None else None,
            mid_price=mid_price,
            metadata={
                "execution_mode": self.policy.execution_mode,
                "normalised_qty": normalised_qty,
                "best_bid": best_bid,
                "best_ask": best_ask,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_order_params(
        self,
        side: str,
        mid_price: float,
        explicit_price: Optional[float],
        validation: dict,
    ):
        """Return (order_type, limit_price) based on policy and inputs."""
        mode = self.policy.execution_mode

        if mode == "market":
            return "MARKET", None

        if mode == "limit":
            if explicit_price is not None:
                lp = validation.get("normalized_price") or explicit_price
            else:
                # Fall back to mid price, tick-rounded via validation
                lp = mid_price
            return "LIMIT", lp

        # maker_first: offset from mid price to improve fill probability as maker
        offset_pct = self.policy.limit_price_offset_bps / 10000.0
        if side == "BUY":
            # Bid below mid to be passive
            raw_price = mid_price * (1 - offset_pct)
        else:
            # Ask above mid to be passive
            raw_price = mid_price * (1 + offset_pct)

        # Round to tick size via validate_order_params
        try:
            vr = self._client.validate_order_params(
                validation["symbol"], side, "LIMIT", validation["normalized_quantity"], raw_price
            )
            lp = vr.get("normalized_price") or raw_price
        except Exception:
            lp = raw_price

        return "LIMIT", lp

    def _blocked(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reason: str,
        spread_pct: Optional[float] = None,
        slippage_pct: Optional[float] = None,
        mid_price: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> ExecutionEvaluation:
        logger.warning(
            "Execution BLOCKED: %s %s reason=%s spread=%s slippage=%s",
            side,
            symbol,
            reason,
            f"{spread_pct:.4f}%" if spread_pct is not None else "N/A",
            f"{slippage_pct:.4f}%" if slippage_pct is not None else "N/A",
        )
        return ExecutionEvaluation(
            approved=False,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="NONE",
            blocked_reason=reason,
            spread_pct=spread_pct,
            slippage_pct=slippage_pct,
            mid_price=mid_price,
            metadata=metadata or {},
        )
