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
