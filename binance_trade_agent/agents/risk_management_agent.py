"""
Enhanced Risk Management Agent with comprehensive risk controls
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ..common.config import config


class RiskLevel(Enum):
    """Risk severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskRule:
    """Risk management rule configuration"""

    name: str
    enabled: bool
    level: RiskLevel
    description: str
    parameters: Dict[str, Any]


@dataclass
class RiskAssessment:
    """Risk assessment result"""

    approved: bool
    risk_level: RiskLevel
    reasons: List[str]
    warnings: List[str]
    recommended_quantity: Optional[float] = None
    max_position_size: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None


class EnhancedRiskManagementAgent:
    """
    Enhanced Risk Management Agent with comprehensive controls:
    - Position sizing limits
    - Stop-loss/take-profit management
    - Maximum drawdown protection
    - Frequency-based constraints
    - Symbol-specific rules
    - Portfolio-level risk controls
    """

    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)

        # Load risk configuration from config system
        risk_config = config.get_risk_config()

        self.config = {
            # Position sizing rules
            "max_position_per_symbol": risk_config["max_position_per_symbol"],
            "max_total_exposure": risk_config["max_total_exposure"],
            "max_single_trade_size": risk_config["max_single_trade_size"],
            # Stop-loss and take-profit
            "default_stop_loss_pct": risk_config["default_stop_loss_pct"],
            "default_take_profit_pct": risk_config["default_take_profit_pct"],
            "trailing_stop_enabled": True,
            "trailing_stop_pct": risk_config["trailing_stop_pct"],
            # Drawdown protection
            "max_daily_drawdown": risk_config["max_daily_drawdown"],
            "max_total_drawdown": risk_config["max_total_drawdown"],
            "drawdown_pause_hours": 24,  # Pause trading for 24h after max drawdown
            # Frequency controls
            "max_trades_per_hour": 100,
            "max_trades_per_day": 500,
            "min_time_between_trades": 5,  # 5 seconds minimum between trades
            # Symbol-specific rules
            "symbol_rules": {
                symbol: config.get_symbol_risk_config(symbol) for symbol in ["BTCUSDT", "ETHUSDT"]
            },
            # Market conditions
            "volatility_threshold": risk_config["volatility_threshold"],
            "market_hours_only": False,  # Trade 24/7 for crypto
            "news_impact_pause": False,  # Pause during high-impact news
            # Emergency controls
            "emergency_stop": False,  # Emergency stop all trading
            "max_consecutive_losses": 5,  # Stop after 5 consecutive losses
            "loss_streak_pause_hours": 6,  # Pause for 6h after loss streak
        }

        # Load custom config if provided
        if config_file:
            self.load_config(config_file)

        # Initialize risk rules
        self.risk_rules = self._initialize_risk_rules()

        # Trade tracking for frequency controls
        self.recent_trades: List[Dict[str, Any]] = []
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.daily_trades = 0
        self.last_daily_reset = datetime.now().date()

        # Drawdown tracking
        self.peak_portfolio_value = 0.0
        self.current_drawdown = 0.0
        self.daily_start_value = 0.0
        self.drawdown_pause_until = None

        # Trailing stop tracking - tracks highest price for each position
        # Format: {symbol: {"entry_price": float, "side": str, "highest_price": float, "lowest_price": float, "current_stop": float}}
        self.trailing_stops: Dict[str, Dict[str, float]] = {}

        self.logger.info("Enhanced Risk Management Agent initialized")

    def _initialize_risk_rules(self) -> List[RiskRule]:
        """Initialize all risk management rules"""
        return [
            RiskRule(
                name="position_size_limit",
                enabled=True,
                level=RiskLevel.HIGH,
                description="Limit position size per symbol",
                parameters={"max_position_pct": self.config["max_position_per_symbol"]},
            ),
            RiskRule(
                name="total_exposure_limit",
                enabled=True,
                level=RiskLevel.CRITICAL,
                description="Limit total portfolio exposure",
                parameters={"max_exposure_pct": self.config["max_total_exposure"]},
            ),
            RiskRule(
                name="single_trade_size_limit",
                enabled=True,
                level=RiskLevel.MEDIUM,
                description="Limit individual trade size",
                parameters={"max_trade_pct": self.config["max_single_trade_size"]},
            ),
            RiskRule(
                name="stop_loss_required",
                enabled=True,
                level=RiskLevel.HIGH,
                description="Require stop-loss for all positions",
                parameters={"stop_loss_pct": self.config["default_stop_loss_pct"]},
            ),
            RiskRule(
                name="drawdown_protection",
                enabled=True,
                level=RiskLevel.CRITICAL,
                description="Protect against excessive drawdown",
                parameters={
                    "max_daily_dd": self.config["max_daily_drawdown"],
                    "max_total_dd": self.config["max_total_drawdown"],
                },
            ),
            RiskRule(
                name="frequency_control",
                enabled=True,
                level=RiskLevel.MEDIUM,
                description="Control trading frequency",
                parameters={
                    "max_hourly": self.config["max_trades_per_hour"],
                    "max_daily": self.config["max_trades_per_day"],
                    "min_interval": self.config["min_time_between_trades"],
                },
            ),
            RiskRule(
                name="consecutive_loss_protection",
                enabled=True,
                level=RiskLevel.HIGH,
                description="Pause trading after consecutive losses",
                parameters={
                    "max_losses": self.config["max_consecutive_losses"],
                    "pause_hours": self.config["loss_streak_pause_hours"],
                },
            ),
            RiskRule(
                name="emergency_stop",
                enabled=True,
                level=RiskLevel.CRITICAL,
                description="Emergency stop all trading",
                parameters={"enabled": self.config["emergency_stop"]},
            ),
        ]

    def validate_trade(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_value: float = 100000.0,  # Default portfolio value
        current_positions: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive trade validation with enhanced risk controls
        """
        self.logger.info(f"Validating trade: {side} {quantity} {symbol} @ ${price}")

        # Initialize assessment
        assessment = RiskAssessment(
            approved=True, risk_level=RiskLevel.LOW, reasons=[], warnings=[]
        )

        # Check emergency stop
        if self.config["emergency_stop"]:
            assessment.approved = False
            assessment.risk_level = RiskLevel.CRITICAL
            assessment.reasons.append("Emergency stop is active")
            return self._format_assessment_result(assessment)

        # Check drawdown pause
        if self.drawdown_pause_until and datetime.now() < self.drawdown_pause_until:
            assessment.approved = False
            assessment.risk_level = RiskLevel.HIGH
            assessment.reasons.append(
                f"Trading paused due to drawdown until {self.drawdown_pause_until}"
            )
            return self._format_assessment_result(assessment)

        # Update daily trade counter
        self._update_daily_counter()

        # Run all risk checks
        self._check_position_sizing(
            assessment,
            symbol,
            side,
            quantity,
            price,
            portfolio_value,
            current_positions,
        )
        self._check_frequency_limits(assessment)
        self._check_drawdown_limits(assessment, portfolio_value)
        self._check_consecutive_losses(assessment)
        self._check_symbol_specific_rules(assessment, symbol, quantity, price, portfolio_value)
        self._check_volatility_conditions(assessment, symbol, market_data)

        # Calculate position sizing recommendations
        self._calculate_position_sizing(assessment, symbol, side, quantity, price, portfolio_value)

        # Calculate stop-loss and take-profit levels
        self._calculate_stop_loss_take_profit(assessment, symbol, side, price)

        # Record trade attempt for frequency tracking
        self._record_trade_attempt(symbol, side, quantity, price, assessment.approved)

        # Final risk level determination
        if not assessment.approved:
            assessment.risk_level = RiskLevel.CRITICAL
        elif len(assessment.warnings) > 2:
            assessment.risk_level = RiskLevel.HIGH
        elif len(assessment.warnings) > 0:
            assessment.risk_level = RiskLevel.MEDIUM

        result = self._format_assessment_result(assessment)
        self.logger.info(
            f"Risk assessment: {assessment.risk_level.value} - Approved: {assessment.approved}"
        )

        return result

    def _check_position_sizing(
        self,
        assessment: RiskAssessment,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_value: float,
        current_positions: Optional[Dict[str, Any]] = None,
    ):
        """Check position sizing limits"""
        trade_value = quantity * price
        trade_pct = trade_value / portfolio_value

        # Check single trade size limit
        max_trade_pct = self.config["max_single_trade_size"]
        if trade_pct > max_trade_pct:
            assessment.approved = False
            assessment.reasons.append(
                f"Trade size {trade_pct:.2%} exceeds maximum {max_trade_pct:.2%}"
            )

        # Check per-symbol position limit
        max_position_pct = self.config["max_position_per_symbol"]
        if current_positions and symbol in current_positions:
            current_position_value = current_positions[symbol].get("value", 0)
            if side.lower() == "buy":
                new_position_value = current_position_value + trade_value
            else:
                new_position_value = max(0, current_position_value - trade_value)

            new_position_pct = new_position_value / portfolio_value
            if new_position_pct > max_position_pct:
                assessment.approved = False
                assessment.reasons.append(
                    f"Position would be {new_position_pct:.2%}, exceeds limit {max_position_pct:.2%}"
                )

        # Check total exposure
        if current_positions:
            total_exposure = sum(pos.get("value", 0) for pos in current_positions.values())
            total_exposure_pct = total_exposure / portfolio_value

            if total_exposure_pct > self.config["max_total_exposure"]:
                assessment.warnings.append(
                    f"Total exposure {total_exposure_pct:.2%} near limit {self.config['max_total_exposure']:.2%}"
                )

    def _check_frequency_limits(self, assessment: RiskAssessment):
        """Check trading frequency limits"""
        now = datetime.now()

        # Check minimum time between trades
        if self.last_trade_time:
            time_since_last = (now - self.last_trade_time).total_seconds()
            min_interval = self.config["min_time_between_trades"]
            if time_since_last < min_interval:
                assessment.approved = False
                assessment.reasons.append(
                    f"Too soon since last trade ({time_since_last:.0f}s < {min_interval}s)"
                )

        # Check hourly limit
        hour_ago = now - timedelta(hours=1)
        recent_trades = [t for t in self.recent_trades if t["timestamp"] > hour_ago]
        max_hourly = self.config["max_trades_per_hour"]
        if len(recent_trades) >= max_hourly:
            assessment.approved = False
            assessment.reasons.append(
                f"Hourly trade limit reached ({len(recent_trades)}/{max_hourly})"
            )

        # Check daily limit
        max_daily = self.config["max_trades_per_day"]
        if self.daily_trades >= max_daily:
            assessment.approved = False
            assessment.reasons.append(
                f"Daily trade limit reached ({self.daily_trades}/{max_daily})"
            )

    def _check_drawdown_limits(self, assessment: RiskAssessment, portfolio_value: float):
        """Check drawdown protection limits"""
        # Update peak portfolio value
        if portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = portfolio_value

        # Calculate current drawdown
        if self.peak_portfolio_value > 0:
            self.current_drawdown = (
                self.peak_portfolio_value - portfolio_value
            ) / self.peak_portfolio_value

        # Check total drawdown limit
        max_total_dd = self.config["max_total_drawdown"]
        if self.current_drawdown > max_total_dd:
            assessment.approved = False
            assessment.reasons.append(
                f"Total drawdown {self.current_drawdown:.2%} exceeds limit {max_total_dd:.2%}"
            )
            # Set pause period
            self.drawdown_pause_until = datetime.now() + timedelta(
                hours=self.config["drawdown_pause_hours"]
            )

        # Check daily drawdown (simplified - would need start-of-day value)
        daily_dd_limit = self.config["max_daily_drawdown"]
        if self.daily_start_value > 0:
            daily_drawdown = (self.daily_start_value - portfolio_value) / self.daily_start_value
            if daily_drawdown > daily_dd_limit:
                assessment.warnings.append(
                    f"Daily drawdown {daily_drawdown:.2%} approaching limit {daily_dd_limit:.2%}"
                )

    def _check_consecutive_losses(self, assessment: RiskAssessment):
        """Check consecutive loss protection"""
        max_losses = self.config["max_consecutive_losses"]
        if self.consecutive_losses >= max_losses:
            assessment.approved = False
            assessment.reasons.append(
                f"Maximum consecutive losses reached ({self.consecutive_losses}/{max_losses})"
            )

    def _check_symbol_specific_rules(
        self,
        assessment: RiskAssessment,
        symbol: str,
        quantity: float,
        price: float,
        portfolio_value: float,
    ):
        """Check symbol-specific risk rules"""
        if symbol in self.config["symbol_rules"]:
            rules = self.config["symbol_rules"][symbol]
            trade_value = quantity * price
            trade_pct = trade_value / portfolio_value

            max_position = rules.get("max_position", self.config["max_position_per_symbol"])
            if trade_pct > max_position:
                assessment.warnings.append(
                    f"Trade size {trade_pct:.2%} approaches {symbol} limit {max_position:.2%}"
                )

    def _check_volatility_conditions(
        self,
        assessment: RiskAssessment,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
    ):
        """Check market volatility conditions"""
        if market_data and "volatility" in market_data:
            volatility = market_data["volatility"]
            threshold = self.config["volatility_threshold"]

            if volatility > threshold:
                assessment.warnings.append(
                    f"High volatility detected ({volatility:.2%} > {threshold:.2%})"
                )

                # Reduce recommended position size in high volatility
                if assessment.recommended_quantity:
                    volatility_multiplier = (
                        self.config["symbol_rules"]
                        .get(symbol, {})
                        .get("volatility_multiplier", 1.0)
                    )
                    assessment.recommended_quantity *= 1 / (1 + volatility * volatility_multiplier)

    def _calculate_position_sizing(
        self,
        assessment: RiskAssessment,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        portfolio_value: float,
    ):
        """Calculate recommended position sizing"""
        max_trade_value = portfolio_value * self.config["max_single_trade_size"]
        current_trade_value = quantity * price

        if current_trade_value > max_trade_value:
            recommended_quantity = max_trade_value / price
            assessment.recommended_quantity = recommended_quantity
            assessment.warnings.append(
                f"Recommended quantity: {recommended_quantity:.6f} (vs requested {quantity:.6f})"
            )

        # Set maximum position size for reference
        max_position_value = portfolio_value * self.config["max_position_per_symbol"]
        assessment.max_position_size = max_position_value / price

    def _calculate_stop_loss_take_profit(
        self, assessment: RiskAssessment, symbol: str, side: str, price: float
    ):
        """Calculate stop-loss and take-profit levels"""
        stop_loss_pct = self.config["default_stop_loss_pct"]
        take_profit_pct = self.config["default_take_profit_pct"]

        if side.lower() == "buy":
            assessment.stop_loss_price = price * (1 - stop_loss_pct)
            assessment.take_profit_price = price * (1 + take_profit_pct)
        else:  # sell/short
            assessment.stop_loss_price = price * (1 + stop_loss_pct)
            assessment.take_profit_price = price * (1 - take_profit_pct)

    def _record_trade_attempt(
        self, symbol: str, side: str, quantity: float, price: float, approved: bool
    ):
        """Record trade attempt for frequency tracking"""
        trade_record = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "approved": approved,
        }

        self.recent_trades.append(trade_record)

        # Clean old trade records (keep last 24 hours)
        cutoff = datetime.now() - timedelta(hours=24)
        self.recent_trades = [t for t in self.recent_trades if t["timestamp"] > cutoff]

        if approved:
            self.last_trade_time = datetime.now()
            self.daily_trades += 1

    def _update_daily_counter(self):
        """Update daily trade counter"""
        today = datetime.now().date()
        if today != self.last_daily_reset:
            self.daily_trades = 0
            self.last_daily_reset = today
            self.daily_start_value = 0.0  # Would be set from portfolio manager

    def _format_assessment_result(self, assessment: RiskAssessment) -> Dict[str, Any]:
        """Format risk assessment result"""
        return {
            "approved": assessment.approved,
            "risk_level": assessment.risk_level.value,
            "reason": ("; ".join(assessment.reasons) if assessment.reasons else "Trade approved"),
            "warnings": assessment.warnings,
            "recommended_quantity": assessment.recommended_quantity,
            "max_position_size": assessment.max_position_size,
            "stop_loss_price": assessment.stop_loss_price,
            "take_profit_price": assessment.take_profit_price,
            "risk_score": len(assessment.reasons) + len(assessment.warnings) * 0.5,
        }

    def record_trade_result(self, trade_id: str, pnl: float):
        """Record trade result for consecutive loss tracking"""
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.logger.info(
            f"Trade {trade_id} result: ${pnl:.2f}, consecutive losses: {self.consecutive_losses}"
        )

    def set_emergency_stop(self, enabled: bool, reason: str = ""):
        """Set emergency stop"""
        self.config["emergency_stop"] = enabled
        if enabled:
            self.logger.critical(f"EMERGENCY STOP ACTIVATED: {reason}")
        else:
            self.logger.info("Emergency stop deactivated")

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk management status"""
        return {
            "emergency_stop": self.config["emergency_stop"],
            "consecutive_losses": self.consecutive_losses,
            "daily_trades": self.daily_trades,
            "current_drawdown": self.current_drawdown,
            "drawdown_pause_until": (
                self.drawdown_pause_until.isoformat() if self.drawdown_pause_until else None
            ),
            "last_trade_time": (self.last_trade_time.isoformat() if self.last_trade_time else None),
            "recent_trades_count": len(self.recent_trades),
            "risk_rules_active": sum(1 for rule in self.risk_rules if rule.enabled),
            "trailing_stops_active": len(self.trailing_stops),
        }

    # ==================== Trailing Stop Methods ====================

    def register_trailing_stop(
        self,
        symbol: str,
        entry_price: float,
        side: str,
        initial_stop: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Register a new position for trailing stop tracking.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            entry_price: Entry price of the position
            side: 'buy' for long, 'sell' for short
            initial_stop: Optional initial stop-loss price (defaults to config default)
            
        Returns:
            Dictionary with trailing stop info
        """
        trailing_pct = self.config.get("trailing_stop_pct", 0.02)  # Default 2%
        
        if initial_stop is None:
            if side.lower() == "buy":
                initial_stop = entry_price * (1 - self.config["default_stop_loss_pct"])
            else:
                initial_stop = entry_price * (1 + self.config["default_stop_loss_pct"])
        
        self.trailing_stops[symbol] = {
            "entry_price": entry_price,
            "side": side.lower(),
            "highest_price": entry_price,
            "lowest_price": entry_price,
            "current_stop": initial_stop,
            "trailing_pct": trailing_pct,
            "registered_at": datetime.now().isoformat(),
        }
        
        self.logger.info(
            f"Trailing stop registered for {symbol}: entry={entry_price}, "
            f"side={side}, initial_stop={initial_stop:.2f}"
        )
        
        return self.trailing_stops[symbol]

    def update_trailing_stop(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Update the trailing stop based on current price.
        
        For LONG positions: Stop trails up as price rises (locks in profits)
        For SHORT positions: Stop trails down as price falls (locks in profits)
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            
        Returns:
            Updated trailing stop info with 'stop_triggered' flag
        """
        if symbol not in self.trailing_stops:
            return {"error": f"No trailing stop registered for {symbol}"}
        
        ts = self.trailing_stops[symbol]
        trailing_pct = ts.get("trailing_pct", self.config.get("trailing_stop_pct", 0.02))
        stop_triggered = False
        
        if ts["side"] == "buy":
            # LONG position - track highest price, trail stop up
            if current_price > ts["highest_price"]:
                ts["highest_price"] = current_price
                # Calculate new trailing stop
                new_stop = current_price * (1 - trailing_pct)
                # Only move stop UP (never down)
                if new_stop > ts["current_stop"]:
                    old_stop = ts["current_stop"]
                    ts["current_stop"] = new_stop
                    self.logger.info(
                        f"Trailing stop updated for {symbol}: "
                        f"{old_stop:.2f} -> {new_stop:.2f} (price: {current_price:.2f})"
                    )
            
            # Check if stop triggered
            if current_price <= ts["current_stop"]:
                stop_triggered = True
                self.logger.warning(
                    f"Trailing stop TRIGGERED for {symbol} LONG: "
                    f"price={current_price:.2f} <= stop={ts['current_stop']:.2f}"
                )
        
        else:
            # SHORT position - track lowest price, trail stop down
            if current_price < ts["lowest_price"]:
                ts["lowest_price"] = current_price
                # Calculate new trailing stop
                new_stop = current_price * (1 + trailing_pct)
                # Only move stop DOWN (never up)
                if new_stop < ts["current_stop"]:
                    old_stop = ts["current_stop"]
                    ts["current_stop"] = new_stop
                    self.logger.info(
                        f"Trailing stop updated for {symbol}: "
                        f"{old_stop:.2f} -> {new_stop:.2f} (price: {current_price:.2f})"
                    )
            
            # Check if stop triggered
            if current_price >= ts["current_stop"]:
                stop_triggered = True
                self.logger.warning(
                    f"Trailing stop TRIGGERED for {symbol} SHORT: "
                    f"price={current_price:.2f} >= stop={ts['current_stop']:.2f}"
                )
        
        # Update lowest price tracking for longs too
        ts["lowest_price"] = min(ts["lowest_price"], current_price)
        ts["highest_price"] = max(ts["highest_price"], current_price)
        
        # Calculate profit from entry
        if ts["side"] == "buy":
            profit_pct = (current_price - ts["entry_price"]) / ts["entry_price"]
        else:
            profit_pct = (ts["entry_price"] - current_price) / ts["entry_price"]
        
        return {
            **ts,
            "current_price": current_price,
            "profit_pct": profit_pct,
            "stop_triggered": stop_triggered,
        }

    def check_trailing_stop_triggered(self, symbol: str, current_price: float) -> bool:
        """
        Quick check if trailing stop is triggered without updating.
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            
        Returns:
            True if stop is triggered, False otherwise
        """
        if symbol not in self.trailing_stops:
            return False
        
        ts = self.trailing_stops[symbol]
        
        if ts["side"] == "buy":
            return current_price <= ts["current_stop"]
        else:
            return current_price >= ts["current_stop"]

    def close_trailing_stop(self, symbol: str, close_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Close and remove trailing stop tracking for a position.
        
        Args:
            symbol: Trading pair
            close_price: Optional close price for P&L calculation
            
        Returns:
            Final trailing stop info with P&L if close_price provided
        """
        if symbol not in self.trailing_stops:
            return {"error": f"No trailing stop found for {symbol}"}
        
        ts = self.trailing_stops.pop(symbol)
        
        result = {
            **ts,
            "closed_at": datetime.now().isoformat(),
        }
        
        if close_price:
            if ts["side"] == "buy":
                pnl_pct = (close_price - ts["entry_price"]) / ts["entry_price"]
            else:
                pnl_pct = (ts["entry_price"] - close_price) / ts["entry_price"]
            
            result["close_price"] = close_price
            result["pnl_pct"] = pnl_pct
            
            self.logger.info(
                f"Trailing stop closed for {symbol}: "
                f"entry={ts['entry_price']:.2f}, close={close_price:.2f}, "
                f"PnL={pnl_pct*100:.2f}%"
            )
        
        return result

    def get_trailing_stop_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trailing stop information for a symbol or all symbols.
        
        Args:
            symbol: Optional specific symbol, or None for all
            
        Returns:
            Trailing stop info dictionary
        """
        if symbol:
            if symbol in self.trailing_stops:
                return self.trailing_stops[symbol]
            return {"error": f"No trailing stop found for {symbol}"}
        
        return {
            "active_stops": len(self.trailing_stops),
            "positions": self.trailing_stops,
        }

    def update_all_trailing_stops(self, prices: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Update all trailing stops with current prices.
        
        Args:
            prices: Dictionary of {symbol: current_price}
            
        Returns:
            Dictionary of updated trailing stop info for each symbol
        """
        results = {}
        triggered = []
        
        for symbol, ts_info in list(self.trailing_stops.items()):
            if symbol in prices:
                result = self.update_trailing_stop(symbol, prices[symbol])
                results[symbol] = result
                if result.get("stop_triggered"):
                    triggered.append(symbol)
        
        if triggered:
            self.logger.warning(f"Trailing stops triggered for: {triggered}")
        
        return results

    def load_config(self, config_file: str):
        """Load risk configuration from file"""
        try:
            with open(config_file, "r") as f:
                custom_config = json.load(f)
            self.config.update(custom_config)
            self.logger.info(f"Loaded risk config from {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_file}: {str(e)}")

    def save_config(self, config_file: str):
        """Save current risk configuration to file"""
        try:
            with open(config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Saved risk config to {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {str(e)}")


# Backward compatibility - original class name
class RiskManagementAgent(EnhancedRiskManagementAgent):
    """Legacy alias for backwards compatibility"""

    pass


# Demo function
def demo_enhanced_risk_management():
    """Demo enhanced risk management functionality"""
    print("=== Enhanced Risk Management Demo ===")

    # Initialize risk agent
    risk_agent = EnhancedRiskManagementAgent()

    # Test various trade scenarios
    test_scenarios = [
        {
            "name": "Normal trade",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.001,
            "price": 50000.0,
            "portfolio_value": 100000.0,
        },
        {
            "name": "Large trade (should warn)",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.05,
            "price": 50000.0,
            "portfolio_value": 100000.0,
        },
        {
            "name": "Oversized trade (should reject)",
            "symbol": "ETHUSDT",
            "side": "buy",
            "quantity": 50.0,
            "price": 3000.0,
            "portfolio_value": 100000.0,
        },
    ]

    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        result = risk_agent.validate_trade(
            symbol=scenario["symbol"],
            side=scenario["side"],
            quantity=scenario["quantity"],
            price=scenario["price"],
            portfolio_value=scenario["portfolio_value"],
        )

        print(f"Approved: {result['approved']}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Reason: {result['reason']}")
        if result["warnings"]:
            print(f"Warnings: {', '.join(result['warnings'])}")
        if result["recommended_quantity"]:
            print(f"Recommended Quantity: {result['recommended_quantity']:.6f}")
        if result["stop_loss_price"]:
            print(f"Stop Loss: ${result['stop_loss_price']:.2f}")
        if result["take_profit_price"]:
            print(f"Take Profit: ${result['take_profit_price']:.2f}")

    # Show risk status
    print("\n--- Risk Status ---")
    status = risk_agent.get_risk_status()
    for key, value in status.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    demo_enhanced_risk_management()
