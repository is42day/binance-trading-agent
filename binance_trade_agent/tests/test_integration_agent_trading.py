import os
import time
import sqlite3
import pytest
from binance_trade_agent.main import main as agent_main
from binance_trade_agent.config import config

DB_PATH = os.environ.get("PORTFOLIO_DB_PATH", "./data/web_portfolio.db")

@pytest.mark.integration
def test_agent_trading_on_testnet(monkeypatch):
    """
    End-to-end test: Start the agent in testnet mode, ensure it processes signals, executes trades,
    and persists them to the database. Requires real testnet credentials in config.
    """
    # Ensure testnet mode
    monkeypatch.setattr(config, "demo_mode", False)
    monkeypatch.setattr(config, "binance_testnet", True)

    # Remove old trades for a clean test (optional)
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM trades")
        conn.commit()
        conn.close()

    # Start the agent (in a thread or subprocess if needed)
    # For simplicity, call main() directly (should be non-blocking or run for a short time)
    # If main() blocks, consider running in a thread or subprocess

    import subprocess
    import sys
    import signal
    env = os.environ.copy()
    env["SIGNAL_AGENT_TEST_MODE"] = "1"
    agent_proc = subprocess.Popen([sys.executable, '-m', 'binance_trade_agent.main'], env=env)

    # Wait for signals to be processed and trades to be executed
    try:
        time.sleep(30)  # Adjust as needed for your agent's signal frequency
    finally:
        try:
            agent_proc.terminate()
            agent_proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            print("Agent did not exit after SIGTERM, sending SIGKILL...")
            try:
                agent_proc.kill()
                agent_proc.wait(timeout=10)
            except Exception as kill_ex:
                print(f"Failed to kill agent process: {kill_ex}")
        except Exception as ex:
            print(f"Error during agent shutdown: {ex}")

    # Check the database for new trades
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT symbol, side, price, quantity, timestamp FROM trades ORDER BY timestamp DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row is None:
        # Try to print agent logs for debugging
        log_path = "./logs/agent.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                print("\n--- Agent Log Output ---\n" + f.read() + "\n--- End Agent Log ---\n")
        pytest.fail("No trades found in the database. Agent may not have executed any trades. See agent logs above.")
    symbol, side, price, quantity, timestamp = row
    print(f"Trade found: {symbol} {side} {quantity} @ {price} (timestamp: {timestamp})")
    assert symbol in ("BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"), "Unexpected symbol traded."
    assert side in ("BUY", "SELL"), "Trade side should be BUY or SELL."
    assert float(price) > 0, "Trade price should be positive."
    assert float(quantity) > 0, "Trade quantity should be positive."

    # Optionally, stop the agent if needed (depends on your agent's architecture)
    # agent_thread.join(timeout=1)
