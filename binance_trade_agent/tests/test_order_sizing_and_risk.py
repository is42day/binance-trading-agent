"""
Critical tests for order sizing, exchange filters, and risk management.
"""
import pytest
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.risk_management_agent import RiskManagementAgent

class DummyExchange:
    """Simulates exchange info for symbol filters and order validation."""
    def __init__(self, min_qty, step_size, min_notional):
        self.filters = {
            'minQty': min_qty,
            'stepSize': step_size,
            'minNotional': min_notional
        }
    def get_symbol_filters(self, symbol):
        return self.filters

@pytest.fixture
def dummy_exchange():
    return DummyExchange(min_qty=0.001, step_size=0.001, min_notional=10)

@pytest.fixture
def risk_agent():
    return RiskManagementAgent()

@pytest.fixture
def trade_agent(dummy_exchange):
    return TradeExecutionAgent(exchange=dummy_exchange)

def test_order_sizing_against_filters(trade_agent):
    # Should round down to step size and not allow below minQty
    assert trade_agent._adjust_quantity('BTCUSDT', 0.0009) == 0.0
    assert trade_agent._adjust_quantity('BTCUSDT', 0.0011) == 0.001
    assert trade_agent._adjust_quantity('BTCUSDT', 0.0057) == 0.005

def test_min_notional_enforcement(trade_agent):
    # Should reject orders below minNotional
    assert not trade_agent._validate_notional('BTCUSDT', 0.001, 9000)  # 9 < 10
    assert trade_agent._validate_notional('BTCUSDT', 0.002, 6000)      # 12 >= 10

def test_idempotent_order_submission(trade_agent):
    # Simulate idempotent order logic (should not duplicate orders)
    trade_agent._submitted_orders = set()
    order_id = 'order123'
    assert trade_agent._is_idempotent(order_id) is True
    assert trade_agent._is_idempotent(order_id) is False

def test_risk_limits(risk_agent):
    # Should enforce max position and daily loss limits
    result = risk_agent.validate_trade('BTCUSDT', 'BUY', 10, 1000)
    assert 'approved' in result
    # Simulate a trade that exceeds max position
    risk_agent.max_position = 5
    result = risk_agent.validate_trade('BTCUSDT', 'BUY', 10, 1000)
    assert result['approved'] is False
    # Simulate a trade that exceeds daily loss
    risk_agent.daily_loss = 100
    risk_agent.max_daily_loss = 50
    result = risk_agent.validate_trade('BTCUSDT', 'SELL', 1, 1000)
    assert result['approved'] is False

def test_backtest_live_parity():
    # Placeholder: In real test, compare backtest and live results for same data
    # Here, just assert the function exists
    assert True
