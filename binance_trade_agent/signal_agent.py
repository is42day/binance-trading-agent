# binance_trade_agent/signal_agent.py
"""
SignalAgent: Computes trading signals (BUY/SELL/HOLD) from OHLCV candlestick data using technical indicators.
Supports RSI and MACD, with stubs for additional indicators.
"""
import math

class SignalAgent:
    def __init__(self, rsi_overbought=70, rsi_oversold=30, macd_signal_window=9):
        """
        Initialize SignalAgent with indicator thresholds.
        Args:
            rsi_overbought (float): RSI value above which market is considered overbought.
            rsi_oversold (float): RSI value below which market is considered oversold.
            macd_signal_window (int): Window for MACD signal line.
        """
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_signal_window = macd_signal_window

    def compute_rsi(self, closes, period=14):
        """
        Compute RSI from closing prices.
        Args:
            closes (list of float): Closing prices.
            period (int): RSI period.
        Returns:
            float: RSI value.
        """
        if not closes or len(closes) < period + 1:
            raise ValueError("Not enough data for RSI calculation.")
        gains = []
        losses = []
        for i in range(1, period + 1):
            delta = closes[-i] - closes[-i-1]
            if delta > 0:
                gains.append(delta)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-delta)
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def compute_macd(self, closes, fast_period=12, slow_period=26, signal_period=9):
        """
        Compute MACD and signal line from closing prices.
        Args:
            closes (list of float): Closing prices.
            fast_period (int): Fast EMA period.
            slow_period (int): Slow EMA period.
            signal_period (int): Signal line EMA period.
        Returns:
            tuple: (macd, signal, histogram)
        """
        if not closes or len(closes) < slow_period + signal_period:
            raise ValueError("Not enough data for MACD calculation.")
        def ema(data, period):
            k = 2 / (period + 1)
            ema_vals = [data[0]]
            for price in data[1:]:
                ema_vals.append(price * k + ema_vals[-1] * (1 - k))
            return ema_vals
        fast_ema = ema(closes, fast_period)
        slow_ema = ema(closes, slow_period)
        macd_line = [f - s for f, s in zip(fast_ema[-len(slow_ema):], slow_ema)]
        signal_line = ema(macd_line, signal_period)
        histogram = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        return macd_line[-1], signal_line[-1], histogram[-1]

    def compute_ma(self, closes, period=20):
        """
        Stub for moving average (MA) calculation.
        """
        if not closes or len(closes) < period:
            raise ValueError("Not enough data for MA calculation.")
        return sum(closes[-period:]) / period

    def compute_signal(self, ohlcv, indicator='rsi'):
        """
        Compute trading signal from OHLCV data and selected indicator.
        Args:
            ohlcv (list of dict): Each dict must have 'close' key.
            indicator (str): 'rsi' or 'macd'.
        Returns:
            dict: {signal, confidence, indicator_value, indicator_type}
        """
        if not ohlcv or not isinstance(ohlcv, list):
            raise ValueError("OHLCV data must be a non-empty list.")
        closes = []
        for candle in ohlcv:
            if not isinstance(candle, dict) or 'close' not in candle:
                raise ValueError("Malformed OHLCV data: missing 'close' key.")
            try:
                closes.append(float(candle['close']))
            except Exception:
                raise ValueError("Non-numeric close value in OHLCV data.")
        if indicator == 'rsi':
            rsi = self.compute_rsi(closes)
            if rsi > self.rsi_overbought:
                signal = 'SELL'
            elif rsi < self.rsi_oversold:
                signal = 'BUY'
            else:
                signal = 'HOLD'
            return {
                'signal': signal,
                'confidence': abs(rsi - 50) / 50,
                'indicator_value': rsi,
                'indicator_type': 'RSI'
            }
        elif indicator == 'macd':
            macd, signal_line, hist = self.compute_macd(closes)
            if hist > 0 and macd > signal_line:
                signal = 'BUY'
            elif hist < 0 and macd < signal_line:
                signal = 'SELL'
            else:
                signal = 'HOLD'
            return {
                'signal': signal,
                'confidence': abs(hist) / (abs(macd) + 1e-6),
                'indicator_value': macd,
                'indicator_type': 'MACD'
            }
        else:
            raise ValueError(f"Unsupported indicator: {indicator}")

    # Stub for custom indicator
    def compute_custom(self, ohlcv, **kwargs):
        """
        Placeholder for custom indicator logic.
        """
        pass

if __name__ == "__main__":
    # Example usage
    sample_ohlcv = [
        {'close': 100}, {'close': 102}, {'close': 101}, {'close': 103}, {'close': 105},
        {'close': 104}, {'close': 106}, {'close': 108}, {'close': 107}, {'close': 109},
        {'close': 110}, {'close': 111}, {'close': 112}, {'close': 113}, {'close': 114},
        {'close': 115}, {'close': 116}, {'close': 117}, {'close': 118}, {'close': 119},
        {'close': 120}, {'close': 121}, {'close': 122}, {'close': 123}, {'close': 124},
        {'close': 125}, {'close': 126}, {'close': 127}, {'close': 128}, {'close': 129},
        {'close': 130}
    ]
    agent = SignalAgent()
    print("RSI signal:", agent.compute_signal(sample_ohlcv, indicator='rsi'))
    print("MACD signal:", agent.compute_signal(sample_ohlcv, indicator='macd'))
