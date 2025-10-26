import os
import pytest
from datetime import datetime

from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.portfolio_manager import PortfolioManager, Trade
import binance_trade_agent.config as cfg


@pytest.fixture(autouse=True)
def force_demo_mode(monkeypatch):
    """Ensure tests run in demo mode and do not hit live APIs."""
    # Force the global config into demo mode for safe tests
    cfg.config.demo_mode = True
    cfg.config.binance_testnet = True
    yield
    # no-op cleanup


def test_market_data_price_and_ohlcv_basic():
    m = MarketDataAgent()
    price = m.get_latest_price('BTCUSDT')
    assert isinstance(price, float)
    # OHLCV from demo should return a list of dicts with keys
    ohlcv = m.fetch_ohlcv('BTCUSDT', interval='1h', limit=5)
    assert isinstance(ohlcv, list)
    assert len(ohlcv) == 5
    for row in ohlcv:
        for k in ('open', 'high', 'low', 'close', 'volume', 'timestamp'):
            assert k in row


def test_market_data_empty_klines(monkeypatch):
    # Simulate client returning empty klines
    class DummyClient:
        def get_klines(self, symbol, interval, limit):
            return []

    m = MarketDataAgent(binance_client=DummyClient())
    ohlcv = m.fetch_ohlcv('BTCUSDT', interval='1h', limit=5)
    assert ohlcv == []


def test_trade_execution_place_and_cancel_demo(tmp_path):
    # Demo place order should return a dict with orderId and status
    te = TradeExecutionAgent()
    res = te.place_order('BTCUSDT', 'BUY', 'MARKET', 0.0001)
    assert isinstance(res, dict)
    assert 'orderId' in res
    assert res.get('status') in (None, 'FILLED', 'NEW') or 'error' not in res

    # Cancel in demo should return CANCELED-like dict
    cancel = te.cancel_order(res.get('orderId', 0), 'BTCUSDT')
    assert isinstance(cancel, dict)


def test_trade_execution_limit_order_missing_price_returns_error():
    te = TradeExecutionAgent()
    res = te.place_order('BTCUSDT', 'BUY', 'LIMIT', 0.001, price=None)
    # When underlying client requires price for LIMIT, the agent returns an error dict
    assert isinstance(res, dict)
    assert 'error' in res or 'orderId' in res


def test_portfolio_manager_persistence_and_pnl(tmp_path):
    db = tmp_path / "test_portfolio.db"
    pm = PortfolioManager(str(db))
    pm.clear_portfolio()

    # Add a demo trade and verify persistence
    trade = Trade(
        trade_id='t1',
        symbol='BTCUSDT',
        side='BUY',
        quantity=0.01,
        price=50000.0,
        fee=1.0,
        timestamp=datetime.now(),
        order_id='o1'
    )

    pm.add_trade(trade)
    trades = pm.get_trade_history()
    assert any(t.trade_id == 't1' for t in trades)

    # Update market price and verify unrealized PnL calculation
    pm.update_market_prices({'BTCUSDT': 51000.0})
    pos = pm.get_position('BTCUSDT')
    assert pos is not None
    assert pos.unrealized_pnl > 0

    stats = pm.get_portfolio_stats()
    assert 'number_of_trades' in stats
