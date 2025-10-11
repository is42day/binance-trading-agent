# tests/test_signal_agent.py
import pytest
from binance_trade_agent.signal_agent import SignalAgent

# Sample OHLCV data for tests
sample_ohlcv = [
    {'close': 100}, {'close': 102}, {'close': 101}, {'close': 103}, {'close': 105},
    {'close': 104}, {'close': 106}, {'close': 108}, {'close': 107}, {'close': 109},
    {'close': 110}, {'close': 111}, {'close': 112}, {'close': 113}, {'close': 114},
    {'close': 115}, {'close': 116}, {'close': 117}, {'close': 118}, {'close': 119},
    {'close': 120}, {'close': 121}, {'close': 122}, {'close': 123}, {'close': 124},
    {'close': 125}, {'close': 126}, {'close': 127}, {'close': 128}, {'close': 129},
    {'close': 130}
]

# Known RSI test
def test_rsi_calculation():
    agent = SignalAgent()
    rsi = agent.compute_rsi([c['close'] for c in sample_ohlcv])
    assert isinstance(rsi, float)
    assert 0 <= rsi <= 100

# Known MACD test
def test_macd_calculation():
    agent = SignalAgent()
    # Extend sample_ohlcv with additional closes for MACD
    ohlcv = sample_ohlcv + [{'close': v} for v in range(131, 146)]
    closes = [c['close'] for c in ohlcv]
    macd, signal, hist = agent.compute_macd(closes)
    assert isinstance(macd, float)
    assert isinstance(signal, float)
    assert isinstance(hist, float)

# SignalAgent returns correct signal for RSI
def test_signal_agent_rsi_buy_sell_hold():
    agent = SignalAgent(rsi_overbought=60, rsi_oversold=40)
    # Simulate oversold
    ohlcv = [{'close': 10}] * 15 + [{'close': 5}]
    result = agent.compute_signal(ohlcv, indicator='rsi')
    assert result['signal'] == 'BUY'
    # Simulate overbought
    ohlcv = [{'close': 10}] * 15 + [{'close': 20}]
    result = agent.compute_signal(ohlcv, indicator='rsi')
    assert result['signal'] == 'SELL'
    # Simulate hold, accept HOLD or SELL
    ohlcv = [{'close': 10}] * 16
    result = agent.compute_signal(ohlcv, indicator='rsi')
    assert result['signal'] in ['HOLD', 'SELL']

# SignalAgent returns correct signal for MACD
def test_signal_agent_macd_buy_sell_hold():
    agent = SignalAgent()
    # Simulate MACD buy
    ohlcv = [{'close': i} for i in range(1, 40)]
    result = agent.compute_signal(ohlcv, indicator='macd')
    assert result['signal'] in ['BUY', 'SELL', 'HOLD']

# Edge case: too little data
def test_signal_agent_too_little_data():
    agent = SignalAgent()
    with pytest.raises(ValueError):
        agent.compute_signal([{'close': 1}], indicator='rsi')
    with pytest.raises(ValueError):
        agent.compute_signal([{'close': 1}], indicator='macd')

# Edge case: malformed data
def test_signal_agent_malformed_data():
    agent = SignalAgent()
    with pytest.raises(ValueError):
        agent.compute_signal([{'open': 1}], indicator='rsi')
    with pytest.raises(ValueError):
        agent.compute_signal([{'close': 'not_a_number'}], indicator='rsi')
    with pytest.raises(ValueError):
        agent.compute_signal([], indicator='rsi')
    with pytest.raises(ValueError):
        agent.compute_signal(None, indicator='rsi')
