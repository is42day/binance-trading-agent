# binance_trade_agent/main.py

import asyncio
import signal
import sys

async def run_forever():
    try:
        print("Binance Trade Agent started. Waiting for events...")
        # This loop keeps the process alive until it's interrupted (e.g., by Docker or Supervisor)
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        print("Binance Trade Agent shutting down gracefully...")

def main():
    loop = asyncio.get_event_loop()

    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        print(f"Received signal {sig}, shutting down.")
        stop_event.set()

    # Register shutdown signals (Ctrl+C, SIGTERM)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        loop.create_task(run_forever())
        loop.run_until_complete(stop_event.wait())
    finally:
        loop.close()
        print("Exited Binance Trade Agent.")

if __name__ == "__main__":
    main()
