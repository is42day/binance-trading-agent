"""
Paper Trading Mode - Test strategies with real data, no real money

This module provides paper trading functionality that:
1. Connects to REAL Binance mainnet for market data
2. Simulates order execution without placing real orders
3. Tracks hypothetical P&L, win rate, etc.
4. Logs every decision for analysis

Use this to validate strategies before risking real capital.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PaperTrade:
    """Represents a simulated trade"""

    trade_id: str
    symbol: str
    side: str  # BUY or SELL
    entry_price: float
    quantity: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED
    strategy: str = ""
    signal_confidence: float = 0.0
    signal_metadata: dict = field(default_factory=dict)

    def close(self, exit_price: float):
        """Close the trade and calculate P&L"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.status = "CLOSED"

        if self.side == "BUY":
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_percent = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SELL (short)
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_percent = ((self.entry_price - exit_price) / self.entry_price) * 100

        # Subtract simulated fees (0.1% each way)
        fee_rate = 0.001
        self.pnl -= self.entry_price * self.quantity * fee_rate
        self.pnl -= exit_price * self.quantity * fee_rate

        return self


@dataclass
class PaperPortfolio:
    """Tracks paper trading portfolio state"""

    initial_balance: float = 10000.0  # Starting USDT
    current_balance: float = 10000.0
    open_positions: Dict[str, PaperTrade] = field(default_factory=dict)
    closed_trades: List[PaperTrade] = field(default_factory=list)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_balance: float = 10000.0

    def get_stats(self) -> dict:
        """Get portfolio statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_win = 0
        avg_loss = 0

        wins = [t for t in self.closed_trades if t.pnl and t.pnl > 0]
        losses = [t for t in self.closed_trades if t.pnl and t.pnl < 0]

        if wins:
            avg_win = sum(t.pnl for t in wins) / len(wins)
        if losses:
            avg_loss = sum(t.pnl for t in losses) / len(losses)

        profit_factor = (
            abs(sum(t.pnl for t in wins)) / abs(sum(t.pnl for t in losses))
            if losses and sum(t.pnl for t in losses) != 0
            else 0
        )

        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "total_pnl": self.total_pnl,
            "total_pnl_percent": (self.total_pnl / self.initial_balance) * 100,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percent": (
                (self.max_drawdown / self.peak_balance) * 100 if self.peak_balance > 0 else 0
            ),
            "open_positions": len(self.open_positions),
        }


class PaperTradingEngine:
    """
    Paper trading engine that simulates trading with real market data.

    Features:
    - Uses real Binance mainnet data (not testnet)
    - Simulates realistic order fills with slippage
    - Tracks all trades and performance metrics
    - Persists state to disk for session continuity
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        data_dir: str = "data/paper_trading",
        use_mainnet_data: bool = True,
    ):
        """
        Initialize paper trading engine.

        Args:
            initial_balance: Starting USDT balance
            data_dir: Directory to store paper trading data
            use_mainnet_data: If True, fetch real prices from mainnet
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.use_mainnet_data = use_mainnet_data
        self.portfolio = PaperPortfolio(
            initial_balance=initial_balance,
            current_balance=initial_balance,
            peak_balance=initial_balance,
        )

        # Slippage simulation (basis points)
        self.slippage_bps = 5  # 0.05% slippage

        # Trade log file
        self.trade_log_file = self.data_dir / "trade_log.jsonl"
        self.signal_log_file = self.data_dir / "signal_log.jsonl"

        # Load existing state if available
        self._load_state()

        logger.info(
            f"Paper trading engine initialized: balance=${initial_balance:.2f}, "
            f"mainnet_data={use_mainnet_data}"
        )

    def _get_real_price(self, symbol: str) -> float:
        """
        Get real price from Binance mainnet (not testnet).

        This is the key difference - we always use real market data.
        """
        import requests

        try:
            response = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": symbol},
                timeout=5,
            )
            data = response.json()
            return float(data["price"])
        except Exception as e:
            logger.error(f"Failed to get real price for {symbol}: {e}")
            return 0.0

    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply realistic slippage to price"""
        slippage = price * (self.slippage_bps / 10000)
        if side == "BUY":
            return price + slippage  # Pay more when buying
        else:
            return price - slippage  # Get less when selling

    def execute_paper_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        strategy: str = "",
        signal_confidence: float = 0.0,
        signal_metadata: dict = None,
    ) -> dict:
        """
        Execute a paper trade.

        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Amount to trade
            strategy: Strategy that generated the signal
            signal_confidence: Confidence level of the signal
            signal_metadata: Additional signal data for analysis

        Returns:
            Trade execution result
        """
        # Get real price
        real_price = self._get_real_price(symbol)
        if real_price == 0:
            return {"success": False, "error": "Failed to get market price"}

        # Apply slippage
        fill_price = self._apply_slippage(real_price, side)

        # Calculate trade value
        trade_value = fill_price * quantity

        # Check if we have enough balance for buys
        if side == "BUY":
            if trade_value > self.portfolio.current_balance:
                return {
                    "success": False,
                    "error": f"Insufficient balance: need ${trade_value:.2f}, have ${self.portfolio.current_balance:.2f}",
                }

        # Check if we have position to sell
        if side == "SELL":
            if symbol not in self.portfolio.open_positions:
                return {"success": False, "error": f"No open position for {symbol}"}

        # Generate trade ID
        trade_id = f"PAPER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"

        if side == "BUY":
            # Open new position
            trade = PaperTrade(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                entry_price=fill_price,
                quantity=quantity,
                entry_time=datetime.now(),
                strategy=strategy,
                signal_confidence=signal_confidence,
                signal_metadata=signal_metadata or {},
            )

            self.portfolio.open_positions[symbol] = trade
            self.portfolio.current_balance -= trade_value

            self._log_trade(trade, "OPEN")
            self._save_state()  # Save after opening position

            return {
                "success": True,
                "trade_id": trade_id,
                "action": "OPENED_LONG",
                "symbol": symbol,
                "price": fill_price,
                "quantity": quantity,
                "value": trade_value,
                "remaining_balance": self.portfolio.current_balance,
            }

        else:  # SELL
            # Close existing position
            trade = self.portfolio.open_positions.pop(symbol)
            trade.close(fill_price)

            # Update portfolio
            self.portfolio.closed_trades.append(trade)
            self.portfolio.total_trades += 1
            self.portfolio.total_pnl += trade.pnl
            self.portfolio.current_balance += trade_value

            if trade.pnl > 0:
                self.portfolio.winning_trades += 1
            else:
                self.portfolio.losing_trades += 1

            # Track peak and drawdown
            if self.portfolio.current_balance > self.portfolio.peak_balance:
                self.portfolio.peak_balance = self.portfolio.current_balance

            drawdown = self.portfolio.peak_balance - self.portfolio.current_balance
            if drawdown > self.portfolio.max_drawdown:
                self.portfolio.max_drawdown = drawdown

            self._log_trade(trade, "CLOSED")
            self._save_state()

            return {
                "success": True,
                "trade_id": trade_id,
                "action": "CLOSED_LONG",
                "symbol": symbol,
                "entry_price": trade.entry_price,
                "exit_price": fill_price,
                "quantity": quantity,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "remaining_balance": self.portfolio.current_balance,
            }

    def log_signal(
        self,
        symbol: str,
        action: str,
        confidence: float,
        strategy: str,
        metadata: dict,
        executed: bool,
        rejection_reason: str = None,
    ):
        """Log a signal (whether executed or not) for analysis"""

        # Convert numpy types to Python native types for JSON serialization
        def convert_numpy(obj):
            if hasattr(obj, "item"):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            return obj

        signal_data = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "action": action,
            "confidence": float(confidence) if confidence else 0,
            "strategy": strategy,
            "executed": executed,
            "rejection_reason": rejection_reason,
            "metadata": convert_numpy(metadata) if metadata else {},
        }

        try:
            with open(self.signal_log_file, "a") as f:
                f.write(json.dumps(signal_data, default=str) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log signal: {e}")

    def _log_trade(self, trade: PaperTrade, event: str):
        """Log trade to file"""
        trade_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "trade": {
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "strategy": trade.strategy,
                "signal_confidence": trade.signal_confidence,
            },
            "portfolio_balance": self.portfolio.current_balance,
        }

        with open(self.trade_log_file, "a") as f:
            f.write(json.dumps(trade_data) + "\n")

        logger.info(
            f"[PAPER] Trade {event}: {trade.symbol} {trade.side} @ ${trade.entry_price:.2f}"
            + (f" -> ${trade.exit_price:.2f} (P&L: ${trade.pnl:.2f})" if trade.exit_price else "")
        )

    def _save_state(self):
        """Save portfolio state to disk"""
        state_file = self.data_dir / "portfolio_state.json"

        # Calculate unrealized P&L for open positions
        unrealized_pnl = 0.0
        positions_value = 0.0
        open_positions_detail = {}

        for symbol, trade in self.portfolio.open_positions.items():
            current_price = self._get_real_price(symbol)
            if current_price > 0:
                position_value = current_price * trade.quantity
                positions_value += position_value
                entry_value = trade.entry_price * trade.quantity
                position_pnl = position_value - entry_value
                unrealized_pnl += position_pnl

                open_positions_detail[symbol] = {
                    "trade_id": trade.trade_id,
                    "entry_price": trade.entry_price,
                    "current_price": current_price,
                    "quantity": trade.quantity,
                    "entry_time": trade.entry_time.isoformat(),
                    "strategy": trade.strategy,
                    "value": position_value,
                    "pnl": position_pnl,
                    "pnl_percent": (position_pnl / entry_value) * 100 if entry_value > 0 else 0,
                }
            else:
                # Can't get price, use entry price
                open_positions_detail[symbol] = {
                    "trade_id": trade.trade_id,
                    "entry_price": trade.entry_price,
                    "current_price": trade.entry_price,
                    "quantity": trade.quantity,
                    "entry_time": trade.entry_time.isoformat(),
                    "strategy": trade.strategy,
                    "value": trade.entry_price * trade.quantity,
                    "pnl": 0,
                    "pnl_percent": 0,
                }
                positions_value += trade.entry_price * trade.quantity

        # Get base stats and add calculated values
        stats = self.portfolio.get_stats()
        stats["unrealized_pnl"] = unrealized_pnl
        stats["positions_value"] = positions_value
        stats["total_value"] = self.portfolio.current_balance + positions_value
        stats["total_pnl_with_unrealized"] = self.portfolio.total_pnl + unrealized_pnl

        state = {
            "saved_at": datetime.now().isoformat(),
            "portfolio": stats,
            "open_positions": open_positions_detail,
        }

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        """Load portfolio state from disk"""
        state_file = self.data_dir / "portfolio_state.json"

        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)

                # Restore basic stats
                stats = state.get("portfolio", {})
                self.portfolio.current_balance = stats.get(
                    "current_balance", self.portfolio.initial_balance
                )
                self.portfolio.total_pnl = stats.get("total_pnl", 0)
                self.portfolio.total_trades = stats.get("total_trades", 0)
                self.portfolio.winning_trades = stats.get("winning_trades", 0)
                self.portfolio.losing_trades = stats.get("losing_trades", 0)
                self.portfolio.max_drawdown = stats.get("max_drawdown", 0)
                self.portfolio.peak_balance = stats.get(
                    "current_balance", self.portfolio.initial_balance
                )

                # Restore open positions
                open_positions = state.get("open_positions", {})
                for symbol, pos_data in open_positions.items():
                    trade = PaperTrade(
                        trade_id=pos_data.get("trade_id", f"PAPER_RESTORED_{symbol}"),
                        symbol=symbol,
                        side="BUY",  # Assume all open positions are long for now
                        entry_price=pos_data.get("entry_price", 0),
                        quantity=pos_data.get("quantity", 0),
                        entry_time=datetime.fromisoformat(
                            pos_data.get("entry_time", datetime.now().isoformat())
                        ),
                        strategy=pos_data.get("strategy", "unknown"),
                    )
                    self.portfolio.open_positions[symbol] = trade
                    logger.info(f"Restored open position: {symbol} @ ${trade.entry_price:.2f}")

                logger.info(
                    f"Loaded paper trading state: balance=${self.portfolio.current_balance:.2f}, positions={len(self.portfolio.open_positions)}"
                )
            except Exception as e:
                logger.warning(f"Failed to load paper trading state: {e}")

    def get_portfolio_summary(self) -> dict:
        """Get current portfolio summary"""
        stats = self.portfolio.get_stats()

        # Add current position values
        position_values = {}
        total_position_value = 0

        for symbol, trade in self.portfolio.open_positions.items():
            current_price = self._get_real_price(symbol)
            if current_price > 0:
                current_value = current_price * trade.quantity
                unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
                position_values[symbol] = {
                    "entry_price": trade.entry_price,
                    "current_price": current_price,
                    "quantity": trade.quantity,
                    "value": current_value,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_percent": (
                        unrealized_pnl / (trade.entry_price * trade.quantity)
                    )
                    * 100,
                }
                total_position_value += current_value

        stats["position_values"] = position_values
        stats["total_equity"] = stats["current_balance"] + total_position_value

        return stats

    def reset(self, initial_balance: float = None):
        """Reset paper trading to fresh state"""
        if initial_balance:
            self.portfolio.initial_balance = initial_balance

        self.portfolio = PaperPortfolio(
            initial_balance=self.portfolio.initial_balance,
            current_balance=self.portfolio.initial_balance,
            peak_balance=self.portfolio.initial_balance,
        )

        # Archive old logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.trade_log_file.exists():
            self.trade_log_file.rename(self.data_dir / f"trade_log_{timestamp}.jsonl")
        if self.signal_log_file.exists():
            self.signal_log_file.rename(self.data_dir / f"signal_log_{timestamp}.jsonl")

        self._save_state()
        logger.info(f"Paper trading reset: balance=${self.portfolio.initial_balance:.2f}")


# Global paper trading instance
_paper_engine: Optional[PaperTradingEngine] = None


def get_paper_trading_engine(initial_balance: float = 10000.0) -> PaperTradingEngine:
    """Get or create the global paper trading engine"""
    global _paper_engine
    if _paper_engine is None:
        _paper_engine = PaperTradingEngine(initial_balance=initial_balance)
    return _paper_engine
