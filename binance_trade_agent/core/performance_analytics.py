"""
Performance Analytics Module
Tracks and calculates trading performance metrics:
- Win rate
- Profit factor
- Sharpe ratio
- Maximum drawdown
- Risk-adjusted returns
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single trade"""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    is_closed: bool = False
    notes: str = ""


class PerformanceAnalytics:
    """
    Performance tracking and analytics for the trading system.
    Calculates key metrics like win rate, Sharpe ratio, and drawdown.
    """

    def __init__(self, initial_capital: float = 100000.0, risk_free_rate: float = 0.02):
        """
        Initialize performance analytics.

        Args:
            initial_capital: Starting capital for calculations
            risk_free_rate: Annual risk-free rate for Sharpe calculation (default 2%)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_free_rate = risk_free_rate

        # Trade tracking
        self.trades: List[TradeRecord] = []
        self.open_positions: Dict[str, TradeRecord] = {}

        # Daily returns for Sharpe calculation
        self.daily_returns: List[float] = []
        self.daily_equity: List[float] = [initial_capital]
        self.daily_timestamps: List[datetime] = [datetime.now()]

        # Peak tracking for drawdown
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.current_drawdown = 0.0
        self.current_drawdown_pct = 0.0

        # Session tracking
        self.session_start = datetime.now()

        logger.info(f"Performance Analytics initialized with capital: ${initial_capital:,.2f}")

    def record_trade_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        notes: str = "",
    ) -> TradeRecord:
        """
        Record a new trade entry.

        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            entry_price: Entry price
            quantity: Trade quantity
            notes: Optional trade notes

        Returns:
            TradeRecord for the new trade
        """
        trade = TradeRecord(
            symbol=symbol,
            side=side.lower(),
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
            notes=notes,
        )

        self.trades.append(trade)
        self.open_positions[symbol] = trade

        logger.info(f"Trade entry recorded: {side.upper()} {quantity} {symbol} @ ${entry_price:,.2f}")

        return trade

    def record_trade_exit(
        self,
        symbol: str,
        exit_price: float,
        notes: str = "",
    ) -> Optional[TradeRecord]:
        """
        Record a trade exit and calculate P&L.

        Args:
            symbol: Trading pair
            exit_price: Exit price
            notes: Optional exit notes

        Returns:
            Updated TradeRecord or None if no open position
        """
        if symbol not in self.open_positions:
            logger.warning(f"No open position found for {symbol}")
            return None

        trade = self.open_positions.pop(symbol)
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.is_closed = True

        # Calculate P&L
        if trade.side == "buy":
            trade.pnl = (exit_price - trade.entry_price) * trade.quantity
            trade.pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.quantity
            trade.pnl_pct = (trade.entry_price - exit_price) / trade.entry_price * 100

        # Update capital
        self.current_capital += trade.pnl

        # Update drawdown tracking
        self._update_drawdown()

        if notes:
            trade.notes = f"{trade.notes} | Exit: {notes}" if trade.notes else notes

        logger.info(
            f"Trade exit recorded: {symbol} @ ${exit_price:,.2f}, "
            f"P&L: ${trade.pnl:,.2f} ({trade.pnl_pct:+.2f}%)"
        )

        return trade

    def _update_drawdown(self):
        """Update drawdown calculations"""
        # Update peak
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        # Calculate current drawdown
        self.current_drawdown = self.peak_capital - self.current_capital
        self.current_drawdown_pct = (self.current_drawdown / self.peak_capital) * 100 if self.peak_capital > 0 else 0

        # Update max drawdown
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
            self.max_drawdown_pct = self.current_drawdown_pct

    def record_daily_equity(self, equity: Optional[float] = None):
        """
        Record daily equity for Sharpe ratio calculation.
        Call this once per day or at regular intervals.

        Args:
            equity: Current equity value (uses current_capital if not provided)
        """
        equity = equity or self.current_capital

        if len(self.daily_equity) > 0:
            prev_equity = self.daily_equity[-1]
            daily_return = (equity - prev_equity) / prev_equity if prev_equity > 0 else 0
            self.daily_returns.append(daily_return)

        self.daily_equity.append(equity)
        self.daily_timestamps.append(datetime.now())

    def get_closed_trades(self) -> List[TradeRecord]:
        """Get all closed trades"""
        return [t for t in self.trades if t.is_closed]

    def get_winning_trades(self) -> List[TradeRecord]:
        """Get all winning trades (P&L > 0)"""
        return [t for t in self.trades if t.is_closed and t.pnl and t.pnl > 0]

    def get_losing_trades(self) -> List[TradeRecord]:
        """Get all losing trades (P&L < 0)"""
        return [t for t in self.trades if t.is_closed and t.pnl and t.pnl < 0]

    def calculate_win_rate(self) -> float:
        """
        Calculate win rate as percentage of winning trades.

        Returns:
            Win rate as percentage (0-100)
        """
        closed_trades = self.get_closed_trades()
        if not closed_trades:
            return 0.0

        winning = len(self.get_winning_trades())
        return (winning / len(closed_trades)) * 100

    def calculate_profit_factor(self) -> float:
        """
        Calculate profit factor (gross profit / gross loss).
        A profit factor > 1 indicates a profitable system.

        Returns:
            Profit factor (higher is better)
        """
        winning = self.get_winning_trades()
        losing = self.get_losing_trades()

        gross_profit = sum(t.pnl for t in winning if t.pnl)
        gross_loss = abs(sum(t.pnl for t in losing if t.pnl))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    def calculate_average_win(self) -> float:
        """Calculate average winning trade amount"""
        winning = self.get_winning_trades()
        if not winning:
            return 0.0
        return sum(t.pnl for t in winning if t.pnl) / len(winning)

    def calculate_average_loss(self) -> float:
        """Calculate average losing trade amount (as positive number)"""
        losing = self.get_losing_trades()
        if not losing:
            return 0.0
        return abs(sum(t.pnl for t in losing if t.pnl) / len(losing))

    def calculate_risk_reward_ratio(self) -> float:
        """
        Calculate risk/reward ratio (average win / average loss).

        Returns:
            Risk/reward ratio (higher is better)
        """
        avg_win = self.calculate_average_win()
        avg_loss = self.calculate_average_loss()

        if avg_loss == 0:
            return float('inf') if avg_win > 0 else 0.0

        return avg_win / avg_loss

    def calculate_sharpe_ratio(self, periods_per_year: int = 252) -> float:
        """
        Calculate Sharpe ratio from daily returns.

        Args:
            periods_per_year: Trading periods per year (252 for daily)

        Returns:
            Annualized Sharpe ratio
        """
        if len(self.daily_returns) < 2:
            return 0.0

        returns = np.array(self.daily_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # Daily risk-free rate
        daily_rf = self.risk_free_rate / periods_per_year

        # Annualized Sharpe ratio
        sharpe = (mean_return - daily_rf) / std_return * np.sqrt(periods_per_year)

        return float(sharpe)

    def calculate_sortino_ratio(self, periods_per_year: int = 252) -> float:
        """
        Calculate Sortino ratio (uses only downside deviation).

        Args:
            periods_per_year: Trading periods per year

        Returns:
            Annualized Sortino ratio
        """
        if len(self.daily_returns) < 2:
            return 0.0

        returns = np.array(self.daily_returns)
        mean_return = np.mean(returns)

        # Calculate downside deviation (only negative returns)
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            return float('inf') if mean_return > 0 else 0.0

        downside_std = np.std(negative_returns, ddof=1)

        if downside_std == 0:
            return 0.0

        # Daily risk-free rate
        daily_rf = self.risk_free_rate / periods_per_year

        # Annualized Sortino ratio
        sortino = (mean_return - daily_rf) / downside_std * np.sqrt(periods_per_year)

        return float(sortino)

    def calculate_total_return(self) -> float:
        """Calculate total return percentage"""
        return ((self.current_capital - self.initial_capital) / self.initial_capital) * 100

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.

        Returns:
            Dictionary with all performance metrics
        """
        closed_trades = self.get_closed_trades()
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl) if closed_trades else 0

        return {
            # Capital metrics
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_pnl": total_pnl,
            "total_return_pct": self.calculate_total_return(),

            # Trade statistics
            "total_trades": len(self.trades),
            "closed_trades": len(closed_trades),
            "open_positions": len(self.open_positions),
            "winning_trades": len(self.get_winning_trades()),
            "losing_trades": len(self.get_losing_trades()),

            # Performance ratios
            "win_rate": self.calculate_win_rate(),
            "profit_factor": self.calculate_profit_factor(),
            "risk_reward_ratio": self.calculate_risk_reward_ratio(),
            "average_win": self.calculate_average_win(),
            "average_loss": self.calculate_average_loss(),

            # Risk metrics
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "sortino_ratio": self.calculate_sortino_ratio(),
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "current_drawdown": self.current_drawdown,
            "current_drawdown_pct": self.current_drawdown_pct,

            # Session info
            "session_start": self.session_start.isoformat(),
            "session_duration": str(datetime.now() - self.session_start),
            "last_updated": datetime.now().isoformat(),
        }

    def get_trade_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent trade history.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries
        """
        trades = sorted(self.trades, key=lambda t: t.entry_time, reverse=True)[:limit]

        return [
            {
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "is_closed": t.is_closed,
                "notes": t.notes,
            }
            for t in trades
        ]

    def get_symbol_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance breakdown by symbol.

        Returns:
            Dictionary of symbol -> performance metrics
        """
        symbols = set(t.symbol for t in self.trades)
        result = {}

        for symbol in symbols:
            symbol_trades = [t for t in self.trades if t.symbol == symbol and t.is_closed]
            winning = [t for t in symbol_trades if t.pnl and t.pnl > 0]
            losing = [t for t in symbol_trades if t.pnl and t.pnl < 0]

            total_pnl = sum(t.pnl for t in symbol_trades if t.pnl)

            result[symbol] = {
                "total_trades": len(symbol_trades),
                "winning_trades": len(winning),
                "losing_trades": len(losing),
                "win_rate": (len(winning) / len(symbol_trades) * 100) if symbol_trades else 0,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(symbol_trades) if symbol_trades else 0,
            }

        return result

    def reset(self):
        """Reset all analytics (for new session)"""
        self.trades = []
        self.open_positions = {}
        self.daily_returns = []
        self.daily_equity = [self.initial_capital]
        self.daily_timestamps = [datetime.now()]
        self.current_capital = self.initial_capital
        self.peak_capital = self.initial_capital
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.current_drawdown = 0.0
        self.current_drawdown_pct = 0.0
        self.session_start = datetime.now()

        logger.info("Performance Analytics reset")


# Singleton instance
_performance_analytics: Optional[PerformanceAnalytics] = None


def get_performance_analytics(initial_capital: float = 100000.0) -> PerformanceAnalytics:
    """Get or create the singleton performance analytics instance"""
    global _performance_analytics
    if _performance_analytics is None:
        _performance_analytics = PerformanceAnalytics(initial_capital)
    return _performance_analytics
