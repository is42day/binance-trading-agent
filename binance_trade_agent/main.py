import asyncio
import logging
import os
import signal
import sys

from .common.logging_config import setup_logging, get_logger


async def run_forever(stop_event):
    logger = get_logger(__name__)
    try:
        logger.info("Binance Trade Agent started. Waiting for events...")
        # This loop keeps the process alive until stop_event is set
        while not stop_event.is_set():
            await asyncio.sleep(1)
        logger.info("Stop event received. Exiting main loop...")
    except asyncio.CancelledError:
        logger.info("Binance Trade Agent shutting down gracefully...")


def main():
    # Setup structured logging
    setup_logging(
        service_name="trading-agent",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        use_json=os.getenv("LOG_FORMAT", "plain").lower() == "json",
    )
    
    logger = get_logger(__name__)

    from .common.config import config

    config.validate()

    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        loop.call_soon_threadsafe(stop_event.set)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logger.info("Starting Binance Trade Agent...")

        # Integration test mode: trigger a trade immediately if SIGNAL_AGENT_TEST_MODE is set
        if os.environ.get("SIGNAL_AGENT_TEST_MODE", "").lower() in ("1", "true", "yes"):
            from .core.orchestrator import TradingOrchestrator

            orchestrator = TradingOrchestrator()
            symbol = "BTCUSDT"
            quantity = config.get_default_quantity(symbol)
            logger.info(f"[TEST MODE] Triggering single trading workflow for {symbol}...")
            loop.run_until_complete(orchestrator.execute_trading_workflow(symbol, quantity))

        loop.run_until_complete(run_forever(stop_event))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutting down...")
        loop.close()


if __name__ == "__main__":
    main()
