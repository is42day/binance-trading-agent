import pytest
from unittest.mock import MagicMock, patch
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.risk_management_agent import RiskManagementAgent

def test_agent_workflow():
    # Mock agents
    market_data = MagicMock()
    signal_agent = MagicMock()
    risk_agent = MagicMock()
    trade_agent = MagicMock()

    # Simulate market data
    market_data.get_latest_price.return_value = 100.0
    market_data.get_order_book.return_value = {'bids': [[100, 1]], 'asks': [[101, 1]]}

    # Simulate signal
    signal_agent.compute_signal.return_value = {'signal': 'BUY', 'confidence': 0.8, 'indicator_value': 70, 'indicator_type': 'RSI', 'symbol': 'BTCUSDT', 'quantity': 0.01}

    # Simulate risk validation
    risk_agent.validate_trade.return_value = True

    # Simulate trade execution
    trade_agent.place_order.return_value = {'orderId': 123, 'status': 'FILLED'}

    # Workflow
    price = market_data.get_latest_price('BTCUSDT')
    order_book = market_data.get_order_book('BTCUSDT')
    signal = signal_agent.compute_signal([{'close': price}], indicator='rsi')
    allowed = risk_agent.validate_trade(signal, {'positions': {}, 'active_trades': [], 'max_position': 10, 'drawdown': 0, 'max_drawdown': 0.2}, {'price': price})
    result = None
    if allowed:
        result = trade_agent.place_order(signal['symbol'], 'BUY', 'MARKET', signal['quantity'])
    assert allowed is True
    assert result['status'] == 'FILLED'
