"""
Combined Edge Strategy - The Main Trading Strategy

This is the recommended strategy for live trading. It combines:
1. Edge Strategy (primary) - Fear/Greed, Funding Rates, Volume Anomalies
2. Smart Entry (filter) - S/R levels, Volatility compression, Order flow
3. Traditional TA (confirmation) - RSI, MACD, Trend

Philosophy:
- Use alternative data for WHAT to trade (edge signals)
- Use smart entry for WHEN to trade (entry timing)
- Use traditional TA for CONFIRMATION (reduce false signals)

This layered approach should reduce the number of trades but increase
their quality - focusing on high-conviction setups.
"""

import logging
from datetime import datetime
from typing import Optional

from .base_strategy import BaseStrategy
from .bollinger_strategy import BollingerBandsStrategy
from .edge_strategy import EdgeStrategy
from .macd_strategy import MACDStrategy
from .rsi_strategy import RSIStrategy
from .smart_entry_strategy import SmartEntryStrategy

logger = logging.getLogger(__name__)


class CombinedEdgeStrategy(BaseStrategy):
    """
    Master strategy combining edge signals with traditional confirmation.
    
    Trade Hierarchy:
    1. Edge signal (Fear/Greed + Funding) must agree
    2. Smart entry conditions must be favorable
    3. At least 1 traditional indicator must confirm
    
    This is CONSERVATIVE by design - we want fewer, better trades.
    """
    
    def __init__(self, market_data_agent=None, config: dict = None):
        super().__init__(market_data_agent)
        self.name = "combined_edge"
        
        config = config or {}
        
        # Initialize sub-strategies
        self.edge_strategy = EdgeStrategy(market_data_agent)
        self.smart_entry = SmartEntryStrategy(market_data_agent)
        self.rsi_strategy = RSIStrategy()
        self.macd_strategy = MACDStrategy()
        self.bollinger_strategy = BollingerBandsStrategy()
        
        # Thresholds
        self.edge_min_confidence = config.get("edge_min_confidence", 0.4)
        self.entry_min_score = config.get("entry_min_score", 0.3)
        self.ta_confirmation_required = config.get("ta_confirmation_required", 1)
        
        # Position sizing based on conviction
        self.max_position_pct = config.get("max_position_pct", 0.10)  # 10% max per trade
        self.conviction_multipliers = {
            "high": 1.0,    # Full size
            "medium": 0.5,  # Half size
            "low": 0.0,     # No trade
        }
    
    def _get_edge_signal(self, symbol: str, ohlcv_data: list) -> dict:
        """Get signal from edge strategy"""
        try:
            return self.edge_strategy.generate_signal(symbol, ohlcv_data)
        except Exception as e:
            logger.error(f"Edge strategy error: {e}")
            return {"action": "HOLD", "confidence": 0}
    
    def _get_entry_signal(self, symbol: str, ohlcv_data: list) -> dict:
        """Get signal from smart entry strategy"""
        try:
            return self.smart_entry.generate_signal(symbol, ohlcv_data)
        except Exception as e:
            logger.error(f"Smart entry error: {e}")
            return {"action": "HOLD", "entry_score": 0}
    
    def _get_ta_confirmations(self, symbol: str, ohlcv_data: list) -> dict:
        """Get confirmations from traditional TA strategies"""
        confirmations = {
            "bullish": 0,
            "bearish": 0,
            "details": {}
        }
        
        # RSI
        try:
            rsi_signal = self.rsi_strategy.generate_signal(symbol, ohlcv_data)
            if rsi_signal.get("action") == "BUY":
                confirmations["bullish"] += 1
                confirmations["details"]["rsi"] = "bullish"
            elif rsi_signal.get("action") == "SELL":
                confirmations["bearish"] += 1
                confirmations["details"]["rsi"] = "bearish"
            else:
                confirmations["details"]["rsi"] = "neutral"
        except Exception as e:
            logger.warning(f"RSI error: {e}")
            confirmations["details"]["rsi"] = "error"
        
        # MACD
        try:
            macd_signal = self.macd_strategy.generate_signal(symbol, ohlcv_data)
            if macd_signal.get("action") == "BUY":
                confirmations["bullish"] += 1
                confirmations["details"]["macd"] = "bullish"
            elif macd_signal.get("action") == "SELL":
                confirmations["bearish"] += 1
                confirmations["details"]["macd"] = "bearish"
            else:
                confirmations["details"]["macd"] = "neutral"
        except Exception as e:
            logger.warning(f"MACD error: {e}")
            confirmations["details"]["macd"] = "error"
        
        # Bollinger
        try:
            bb_signal = self.bollinger_strategy.generate_signal(symbol, ohlcv_data)
            if bb_signal.get("action") == "BUY":
                confirmations["bullish"] += 1
                confirmations["details"]["bollinger"] = "bullish"
            elif bb_signal.get("action") == "SELL":
                confirmations["bearish"] += 1
                confirmations["details"]["bollinger"] = "bearish"
            else:
                confirmations["details"]["bollinger"] = "neutral"
        except Exception as e:
            logger.warning(f"Bollinger error: {e}")
            confirmations["details"]["bollinger"] = "error"
        
        return confirmations
    
    def _calculate_conviction(
        self,
        edge_confidence: float,
        entry_score: float,
        ta_confirmations: int,
        ta_conflicts: int
    ) -> str:
        """
        Calculate overall conviction level.
        
        Returns: 'high', 'medium', or 'low'
        """
        score = 0
        
        # Edge confidence contribution (0-40 points)
        score += edge_confidence * 40
        
        # Entry score contribution (0-30 points)
        score += entry_score * 30
        
        # TA confirmation contribution (0-30 points)
        ta_net = ta_confirmations - ta_conflicts
        score += (ta_net / 3) * 30  # Max 3 confirmations
        
        if score >= 60:
            return "high"
        elif score >= 35:
            return "medium"
        else:
            return "low"
    
    def generate_signal(self, symbol: str, ohlcv_data: list = None) -> dict:
        """
        Generate trading signal using the combined edge approach.
        
        Decision flow:
        1. Get edge signal (primary)
        2. Check entry conditions (filter)
        3. Get TA confirmations (validation)
        4. Combine for final decision
        """
        if ohlcv_data is None:
            ohlcv_data = self._fetch_ohlcv(symbol)
        
        if not ohlcv_data or len(ohlcv_data) < 100:
            return self._create_signal("HOLD", 0.0, {"error": "Insufficient data"})
        
        current_price = ohlcv_data[-1]["close"]
        
        # Step 1: Get edge signal
        edge_signal = self._get_edge_signal(symbol, ohlcv_data)
        edge_action = edge_signal.get("action", "HOLD")
        edge_confidence = edge_signal.get("confidence", 0)
        
        # Step 2: Get entry conditions
        entry_signal = self._get_entry_signal(symbol, ohlcv_data)
        entry_score = entry_signal.get("entry_score", 0)
        entry_direction = entry_signal.get("direction_bias", 0)
        
        # Step 3: Get TA confirmations
        ta_confirmations = self._get_ta_confirmations(symbol, ohlcv_data)
        
        # Step 4: Decision logic
        final_action = "HOLD"
        final_confidence = 0.0
        rejection_reason = None
        
        # Check edge signal first
        if edge_action == "HOLD" or edge_confidence < self.edge_min_confidence:
            rejection_reason = f"Edge signal weak (action={edge_action}, confidence={edge_confidence:.2f})"
        
        # Check entry conditions
        elif entry_score < self.entry_min_score:
            rejection_reason = f"Entry conditions unfavorable (score={entry_score:.2f})"
        
        # Check for conflicting signals
        elif (edge_action == "BUY" and entry_direction < -0.2):
            rejection_reason = "Edge says BUY but entry timing bearish"
        elif (edge_action == "SELL" and entry_direction > 0.2):
            rejection_reason = "Edge says SELL but entry timing bullish"
        
        else:
            # Check TA confirmations
            if edge_action == "BUY":
                confirmations = ta_confirmations["bullish"]
                conflicts = ta_confirmations["bearish"]
            else:  # SELL
                confirmations = ta_confirmations["bearish"]
                conflicts = ta_confirmations["bullish"]
            
            if confirmations < self.ta_confirmation_required:
                rejection_reason = f"Insufficient TA confirmation ({confirmations}/{self.ta_confirmation_required})"
            elif conflicts >= confirmations:
                rejection_reason = f"TA conflict: {confirmations} confirm vs {conflicts} conflict"
            else:
                # All checks passed - generate signal
                final_action = edge_action
                
                # Calculate conviction
                conviction = self._calculate_conviction(
                    edge_confidence, entry_score, confirmations, conflicts
                )
                
                if conviction == "low":
                    rejection_reason = "Overall conviction too low"
                    final_action = "HOLD"
                else:
                    # Scale confidence based on conviction
                    base_confidence = (edge_confidence + entry_score) / 2
                    conviction_mult = self.conviction_multipliers[conviction]
                    final_confidence = base_confidence * conviction_mult
        
        # Build detailed response
        return self._create_signal(
            action=final_action,
            confidence=final_confidence,
            metadata={
                "strategy": self.name,
                "symbol": symbol,
                "price": current_price,
                "rejection_reason": rejection_reason,
                "edge": {
                    "action": edge_action,
                    "confidence": edge_confidence,
                    "factors": edge_signal.get("factors", {}),
                },
                "entry": {
                    "score": entry_score,
                    "direction_bias": entry_direction,
                    "zone": entry_signal.get("support_resistance", {}).get("current_zone"),
                    "volatility_compressed": entry_signal.get("volatility", {}).get("compressed", False),
                },
                "ta_confirmations": ta_confirmations,
                "conviction": conviction if final_action != "HOLD" else "none",
                "position_size_multiplier": (
                    self.conviction_multipliers.get(conviction, 0)
                    if final_action != "HOLD" else 0
                ),
            }
        )
    
    def _create_signal(self, action: str, confidence: float, metadata: dict) -> dict:
        """Create standardized signal response"""
        return {
            "action": action,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            **metadata
        }


# Convenience factory functions
def create_conservative_edge_strategy(market_data_agent=None):
    """Create a conservative edge strategy - fewer trades, higher quality"""
    return CombinedEdgeStrategy(
        market_data_agent=market_data_agent,
        config={
            "edge_min_confidence": 0.5,
            "entry_min_score": 0.4,
            "ta_confirmation_required": 2,
            "max_position_pct": 0.05,
        }
    )


def create_balanced_edge_strategy(market_data_agent=None):
    """Create a balanced edge strategy - moderate trade frequency"""
    return CombinedEdgeStrategy(
        market_data_agent=market_data_agent,
        config={
            "edge_min_confidence": 0.4,
            "entry_min_score": 0.3,
            "ta_confirmation_required": 1,
            "max_position_pct": 0.10,
        }
    )
