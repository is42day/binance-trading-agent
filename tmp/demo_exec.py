from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.portfolio_manager import PortfolioManager, Trade
from datetime import datetime

print('Starting demo execution script')
exec_agent = TradeExecutionAgent()
# use place_order (the TradeExecutionAgent wrapper uses place_order)
result = exec_agent.place_order('BTCUSDT', 'BUY', 'MARKET', 0.0001)
print('place_order result:', result)

p = PortfolioManager('/app/data/web_portfolio.db')
trade_id = str(result.get('orderId') if isinstance(result, dict) and result.get('orderId') else int(datetime.now().timestamp()))
price = float(result.get('price')) if isinstance(result, dict) and result.get('price') not in (None, '0', '0.00000000') else 110000.0
trade = Trade(
    trade_id=trade_id,
    symbol='BTCUSDT',
    side='BUY',
    quantity=0.0001,
    price=price,
    fee=0.0,
    timestamp=datetime.now(),
    order_id=result.get('orderId') if isinstance(result, dict) else None
)

p.add_trade(trade)
print('trade added', trade.trade_id)

trades = p.get_trade_history(limit=5)
for t in trades:
    print('TRADE:', t.trade_id, t.symbol, t.side, t.quantity, t.price)
