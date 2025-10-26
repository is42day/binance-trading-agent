"""
IMPORTANT: Always import SignalType directly from this file, not from the strategies package.
"""
"""
Base Strategy Interface

Defines the contract that all trading strategies must implement
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    """Result of strategy analysis"""
    signal: SignalType
    confidence: float  # 0.0 to 1.0
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    indicators: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.indicators is None:
            self.indicators = {}
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'signal': self.signal.value,
            'confidence': self.confidence,
            'price_target': self.price_target,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'indicators': self.indicators,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    All strategies must implement:
    - analyze(): Main strategy logic
    - get_name(): Strategy identifier
    - get_description(): Human readable description
    - get_parameters(): Strategy configuration parameters
    """
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy with parameters
        
        Args:
            parameters: Strategy-specific configuration parameters
        """
        self.parameters = parameters or {}
        self.name = self.get_name()
        self.description = self.get_description()
        
        # Validate parameters on initialization
        self._validate_parameters()
    
    @abstractmethod
    def analyze(self, market_data: List[Dict[str, Any]], symbol: str = None) -> StrategyResult:
        """
        Analyze market data and generate trading signal
        
        Args:
            market_data: List of OHLCV candles with keys: open, high, low, close, volume
            symbol: Trading symbol (optional, for symbol-specific logic)
            
        Returns:
            StrategyResult with signal, confidence, and supporting data
        """
        pass
    
    @abstractmethod 
    def get_name(self) -> str:
        """Return unique strategy name"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable strategy description"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return strategy parameters with defaults and descriptions"""
        pass
    
    def _validate_parameters(self):
        """Validate strategy parameters"""
        required_params = self.get_parameters()
        for param_name, param_config in required_params.items():
            if param_config.get('required', False) and param_name not in self.parameters:
                raise ValueError(f"Required parameter '{param_name}' missing for strategy '{self.name}'")
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """Get parameter value with fallback to default"""
        param_config = self.get_parameters().get(name, {})
        return self.parameters.get(name, param_config.get('default', default))
    
    def set_parameter(self, name: str, value: Any):
        """Set parameter value with validation"""
        param_config = self.get_parameters().get(name)
        if param_config is None:
            raise ValueError(f"Unknown parameter '{name}' for strategy '{self.name}'")
        
        # Type validation if specified
        expected_type = param_config.get('type')
        if expected_type and not isinstance(value, expected_type):
            try:
                value = expected_type(value)
            except (ValueError, TypeError):
                raise ValueError(f"Parameter '{name}' must be of type {expected_type.__name__}")
        
        # Range validation if specified  
        min_val = param_config.get('min')
        max_val = param_config.get('max')
        if min_val is not None and value < min_val:
            raise ValueError(f"Parameter '{name}' must be >= {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"Parameter '{name}' must be <= {max_val}")
            
        self.parameters[name] = value
    
    def requires_minimum_data(self) -> int:
        """Return minimum number of candles required for analysis"""
        return 1
    
    def supports_symbol(self, symbol: str) -> bool:
        """Check if strategy supports given symbol"""
        return True  # Default: support all symbols
    
    def get_risk_metrics(self, market_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate risk metrics for the strategy"""
        if not market_data:
            return {'volatility': 0.0, 'risk_level': 0.5}
        
        # Calculate simple volatility
        closes = [float(candle['close']) for candle in market_data[-20:]]  # Last 20 periods
        if len(closes) < 2:
            return {'volatility': 0.0, 'risk_level': 0.5}
        
        # Simple volatility calculation
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = (sum(r**2 for r in returns) / len(returns)) ** 0.5
        
        # Risk level based on volatility
        risk_level = min(volatility * 10, 1.0)  # Scale and cap at 1.0
        
        return {
            'volatility': volatility,
            'risk_level': risk_level
        }
    
    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', parameters={self.parameters})>"