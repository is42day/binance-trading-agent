"""Validate micro-trading strategy candidates against recent Binance candles.

This script is intentionally conservative: it includes fees and slippage, reports
drawdown, and emits JSON so results can be compared between runs.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

import pandas as pd


BINANCE_REST_BASE = "https://api.binance.com"


@dataclass
class SimulationConfig:
    capital: float
    fee_rate: float
    slippage_rate: float


def fetch_klines(symbol: str, interval: str, days: int) -> pd.DataFrame:
    """Fetch recent Binance klines using the public REST API."""
    end_ms = int(time.time() * 1000)
    interval_ms = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}[interval]
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    rows = []
    cursor = start_ms

    while cursor < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": 1000,
            }
        )
        with urllib.request.urlopen(
            f"{BINANCE_REST_BASE}/api/v3/klines?{params}", timeout=20
        ) as response:
            batch = json.loads(response.read().decode("utf-8"))

        if not batch:
            break

        rows.extend(batch)
        next_cursor = int(batch[-1][0]) + interval_ms
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        time.sleep(0.03)

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    for column in ["open", "high", "low", "close", "volume", "quote_volume"]:
        frame[column] = pd.to_numeric(frame[column])
    frame["time"] = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
    return frame.drop_duplicates("open_time").reset_index(drop=True)


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Add indicators shared by the candidate strategies."""
    frame = frame.copy()
    close = frame["close"]
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    relative_strength = up / down.replace(0, math.nan)

    frame["rsi"] = 100 - (100 / (1 + relative_strength))
    frame["sma20"] = close.rolling(20).mean()
    frame["std20"] = close.rolling(20).std()
    frame["bb_upper"] = frame["sma20"] + 2 * frame["std20"]
    frame["bb_lower"] = frame["sma20"] - 2 * frame["std20"]
    frame["ema9"] = close.ewm(span=9, adjust=False).mean()
    frame["ema21"] = close.ewm(span=21, adjust=False).mean()
    frame["ema50"] = close.ewm(span=50, adjust=False).mean()
    frame["ema96"] = close.ewm(span=96, adjust=False).mean()
    frame["vol_sma20"] = frame["volume"].rolling(20).mean()
    frame["high20"] = frame["high"].rolling(20).max().shift(1)
    return frame


def summarize(
    trades: list[dict],
    equity_curve: list[float],
    frame: pd.DataFrame,
    capital: float,
) -> dict:
    """Convert a simulated equity curve into comparable metrics."""
    days = max((frame["time"].iloc[-1] - frame["time"].iloc[0]).total_seconds() / 86400, 1)
    final_value = equity_curve[-1] if equity_curve else capital
    profit = final_value - capital
    peak = equity_curve[0] if equity_curve else capital
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak)
    wins = sum(1 for trade in trades if trade["pnl"] > 0)

    return {
        "final": round(final_value, 2),
        "pnl": round(profit, 2),
        "daily_eur": round(profit / days, 2),
        "trades": len(trades),
        "win_rate": round(wins / len(trades), 3) if trades else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "days": round(days, 1),
    }


def mean_reversion(frame: pd.DataFrame, config: SimulationConfig) -> dict:
    """RSI plus Bollinger mean-reversion candidate."""
    cash = config.capital
    quantity = 0.0
    entry = 0.0
    trades = []
    equity_curve = []

    for index, row in frame.iterrows():
        price = row.close
        if index < 60 or pd.isna(row.rsi) or pd.isna(row.bb_lower):
            equity_curve.append(cash + quantity * price)
            continue

        if quantity == 0:
            if row.rsi < 28 and price < row.bb_lower and price > row.ema50 * 0.985:
                spend = cash * 0.6
                fill = price * (1 + config.slippage_rate)
                quantity = (spend * (1 - config.fee_rate)) / fill
                cash -= spend
                entry = fill
        else:
            exit_reason = None
            if price <= entry * 0.994:
                exit_reason = "stop"
            elif price >= entry * 1.006:
                exit_reason = "take"
            elif row.rsi > 52 or price >= row.sma20:
                exit_reason = "mean"

            if exit_reason:
                fill = price * (1 - config.slippage_rate)
                proceeds = quantity * fill * (1 - config.fee_rate)
                trades.append({"pnl": proceeds - quantity * entry, "reason": exit_reason})
                cash += proceeds
                quantity = 0.0

        equity_curve.append(cash + quantity * price)

    return summarize(trades, equity_curve, frame, config.capital)


def momentum_breakout(frame: pd.DataFrame, config: SimulationConfig) -> dict:
    """EMA/volume breakout candidate."""
    cash = config.capital
    quantity = 0.0
    entry = 0.0
    high_watermark = 0.0
    trades = []
    equity_curve = []

    for index, row in frame.iterrows():
        price = row.close
        if index < 80 or pd.isna(row.high20):
            equity_curve.append(cash + quantity * price)
            continue

        if quantity == 0:
            if (
                price > row.high20
                and row.ema9 > row.ema21 > row.ema50
                and row.volume > row.vol_sma20 * 1.4
            ):
                spend = cash * 0.5
                fill = price * (1 + config.slippage_rate)
                quantity = (spend * (1 - config.fee_rate)) / fill
                cash -= spend
                entry = fill
                high_watermark = price
        else:
            high_watermark = max(high_watermark, price)
            exit_reason = None
            if price < high_watermark * 0.994:
                exit_reason = "trail"
            elif row.ema9 < row.ema21:
                exit_reason = "ema"
            elif price >= entry * 1.010:
                exit_reason = "take"

            if exit_reason:
                fill = price * (1 - config.slippage_rate)
                proceeds = quantity * fill * (1 - config.fee_rate)
                trades.append({"pnl": proceeds - quantity * entry, "reason": exit_reason})
                cash += proceeds
                quantity = 0.0

        equity_curve.append(cash + quantity * price)

    return summarize(trades, equity_curve, frame, config.capital)


def micro_grid(frame: pd.DataFrame, config: SimulationConfig) -> dict:
    """Conservative long-only micro-grid candidate."""
    cash = config.capital
    positions = []
    trades = []
    equity_curve = []
    slot_cash = config.capital * 0.10
    max_slots = 5
    grid_step = 0.0035
    take_profit = 0.0045
    stop_loss = 0.018
    anchor = frame.close.iloc[min(60, len(frame) - 1)]

    for index, row in frame.iterrows():
        price = row.close
        if index < 80 or pd.isna(row.sma20):
            equity_curve.append(cash + sum(position["quantity"] * price for position in positions))
            continue

        anchor = 0.995 * anchor + 0.005 * row.sma20
        remaining_positions = []
        for position in positions:
            exit_reason = None
            if price >= position["entry"] * (1 + take_profit):
                exit_reason = "take"
            elif price <= position["entry"] * (1 - stop_loss):
                exit_reason = "stop"

            if exit_reason:
                fill = price * (1 - config.slippage_rate)
                proceeds = position["quantity"] * fill * (1 - config.fee_rate)
                trades.append(
                    {"pnl": proceeds - position["quantity"] * position["entry"], "reason": exit_reason}
                )
                cash += proceeds
            else:
                remaining_positions.append(position)
        positions = remaining_positions

        buy_level = anchor * (1 - grid_step * (len(positions) + 1))
        if len(positions) < max_slots and cash >= slot_cash and price < buy_level and row.rsi < 48:
            fill = price * (1 + config.slippage_rate)
            quantity = (slot_cash * (1 - config.fee_rate)) / fill
            cash -= slot_cash
            positions.append({"entry": fill, "quantity": quantity})

        equity_curve.append(cash + sum(position["quantity"] * price for position in positions))

    return summarize(trades, equity_curve, frame, config.capital)


def maker_reversion_grid(frame: pd.DataFrame, config: SimulationConfig) -> dict:
    """Maker-first pullback grid with wider bands and lower turnover.

    This candidate assumes fills happen via passive limit orders, so it applies
    configured fees but not taker slippage. It is designed for paper validation
    before any live use because maker-fill assumptions can be optimistic.
    """
    cash = config.capital
    positions = []
    trades = []
    equity_curve = []
    slot_cash = config.capital * 0.08
    max_slots = 3
    z_entry = 1.2
    take_profit = 0.016
    stop_loss = 0.04

    for index, row in frame.iterrows():
        price = row.close
        if index < 120 or pd.isna(row.sma20) or pd.isna(row.rsi):
            equity_curve.append(cash + sum(position["quantity"] * price for position in positions))
            continue

        remaining_positions = []
        for position in positions:
            exit_reason = None
            if price >= position["entry"] * (1 + take_profit):
                exit_reason = "take"
            elif price <= position["entry"] * (1 - stop_loss):
                exit_reason = "stop"
            elif row.rsi > 58 and price >= row.sma20:
                exit_reason = "mean"

            if exit_reason:
                proceeds = position["quantity"] * price * (1 - config.fee_rate)
                trades.append(
                    {"pnl": proceeds - position["quantity"] * position["entry"], "reason": exit_reason}
                )
                cash += proceeds
            else:
                remaining_positions.append(position)
        positions = remaining_positions

        std20 = row.std20 if not pd.isna(row.std20) and row.std20 else None
        z_score = (price - row.sma20) / std20 if std20 else 0
        trend_ok = price > row.ema96 * 0.995 if "ema96" in frame.columns else True
        volume_ok = price > 0
        if "vol_sma20" in frame.columns and not pd.isna(row.vol_sma20):
            volume_ok = row.volume >= row.vol_sma20 * 0.8

        if (
            trend_ok
            and volume_ok
            and len(positions) < max_slots
            and cash >= slot_cash
            and z_score <= -z_entry
            and row.rsi <= 42
        ):
            quantity = (slot_cash * (1 - config.fee_rate)) / price
            cash -= slot_cash
            positions.append({"entry": price, "quantity": quantity})

        equity_curve.append(cash + sum(position["quantity"] * price for position in positions))

    return summarize(trades, equity_curve, frame, config.capital)


STRATEGIES: dict[str, Callable[[pd.DataFrame, SimulationConfig], dict]] = {
    "mean_reversion": mean_reversion,
    "momentum_breakout": momentum_breakout,
    "micro_grid": micro_grid,
    "maker_reversion_grid": maker_reversion_grid,
}


def run_validation(args: argparse.Namespace) -> dict:
    config = SimulationConfig(
        capital=args.capital,
        fee_rate=args.fee_rate,
        slippage_rate=args.slippage_rate,
    )
    results = {}
    for symbol in args.symbols:
        frame = add_indicators(fetch_klines(symbol, args.interval, args.days))
        results[symbol] = {
            strategy_name: strategy(frame, config)
            for strategy_name, strategy in STRATEGIES.items()
        }

    return {
        "assumptions": {
            "symbols": args.symbols,
            "interval": args.interval,
            "days": args.days,
            "capital": args.capital,
            "fee_rate": args.fee_rate,
            "slippage_rate": args.slippage_rate,
        },
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    parser.add_argument("--interval", default="1m", choices=["1m", "5m", "15m", "1h"])
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--capital", type=float, default=2500.0)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument("--slippage-rate", type=float, default=0.0002)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run_validation(parse_args()), indent=2))


if __name__ == "__main__":
    main()
