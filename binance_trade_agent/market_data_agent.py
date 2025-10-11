# binance_trade_agent/market_data_agent.py

from binance_trade_agent.binance_client import BinanceAPIClient

class MarketDataAgent:
    """
    Agent for retrieving market data from Binance. Can be extended to implement
    prompt-driven or scheduled data pulls in an AI pipeline.
    """

    def __init__(self, binance_client=None):
        self.client = binance_client or BinanceAPIClient()

    def fetch_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol.
        """
        return self.client.get_latest_price(symbol)

    def fetch_order_book(self, symbol: str, limit=10):
        """
        Get order book for a symbol.
        """
        return self.client.get_order_book(symbol, limit=limit)

    def fetch_balance(self, asset: str) -> float:
        """
        Get balance for specific asset.
        """
        return self.client.get_balance(asset)

    def get_latest_price(self, symbol: str) -> float:
        """
        Alias for fetch_price to support orchestrator compatibility.
        """
        return self.fetch_price(symbol)

# Example usage (for manual/debug test, not run in production agent loop):
if __name__ == "__main__":
    agent = MarketDataAgent()
    price = agent.fetch_price("BTCUSDT")
    print("BTCUSDT Latest Price:", price)
    order_book = agent.fetch_order_book("BTCUSDT")
    print("BTCUSDT Order Book:", order_book)
    balance = agent.fetch_balance("USDT")
    print("USDT balance:", balance)
