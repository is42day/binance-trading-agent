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
    
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...")
        stop_event.set()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("Starting Binance Trade Agent...")
        loop.run_until_complete(run_forever())
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error in main loop: {e}")
        sys.exit(1)
    finally:
        print("Shutting down...")
        loop.close()

if __name__ == "__main__":
    main()
