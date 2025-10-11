"""
RiskManagementAgent: Validates trades against risk rules (stop-loss, take-profit, limits, etc.)
"""
class RiskManagementAgent:
    def __init__(self):
        pass

    def validate_trade(self, signal: dict, portfolio: dict, market_data: dict) -> bool:
        """
        Validate a trade signal against risk management rules.
        Args:
            signal (dict): Signal info (e.g., {'symbol': ..., 'side': ..., 'price': ...}).
            portfolio (dict): Current portfolio state.
            market_data (dict): Latest market data.
        Returns:
            bool: True if trade is allowed, False otherwise.
        """
        # Example rules:
        # 1. Only one trade per symbol per interval
        if signal['symbol'] in portfolio.get('active_trades', []):
            return False
        # 2. Position limits
        if portfolio.get('positions', {}).get(signal['symbol'], 0) + signal.get('quantity', 0) > portfolio.get('max_position', 10):
            return False
        # 3. Max drawdown
        if portfolio.get('drawdown', 0) > portfolio.get('max_drawdown', 0.2):
            return False
        # 4. Stop-loss / take-profit (example, extensible)
        if 'stop_loss' in signal and market_data.get('price', 0) < signal['stop_loss']:
            return False
        if 'take_profit' in signal and market_data.get('price', 0) > signal['take_profit']:
            return False
        # Add more rules as needed
        return True

# Extensibility: Add more rules by extending validate_trade or subclassing RiskManagementAgent
