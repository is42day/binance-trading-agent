import asyncio
import logging
import os
import signal
import sys

from .common.logging_config import setup_logging, get_logger


def main():
    # Setup structured logging
    setup_logging(
        service_name="trading-agent",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        use_json=os.getenv("LOG_FORMAT", "plain").lower() == "json",
    )
    
    logger = get_logger(__name__)

    from .common.config import config
    from .core.autonomous_trading_loop import AutonomousTradingLoop

    config.validate()

    # Get trading configuration from environment
    symbols = os.getenv("TRADING_SYMBOLS", "BTCUSDT").split(",")
    interval = int(os.getenv("TRADING_INTERVAL_SECONDS", "60"))
    duration = int(os.getenv("TRADING_DURATION_MINUTES", "0"))  # 0 = run forever
    strategy = os.getenv("STRATEGY_NAME", "combined")

    logger.info(f"Starting Autonomous Trading Loop...")
    logger.info(f"  Symbols: {symbols}")
    logger.info(f"  Interval: {interval}s")
    logger.info(f"  Duration: {'infinite' if duration == 0 else f'{duration} min'}")
    logger.info(f"  Strategy: {strategy}")
    logger.info(f"  Aggressive mode: {config.testnet_aggressive_mode}")

    # Create trading loop
    trading_loop = AutonomousTradingLoop(
        symbols=symbols,
        trade_interval_seconds=interval,
        duration_minutes=duration,
        strategy_name=strategy,
    )

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, stopping trading loop...")
        trading_loop.stop_flag = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(trading_loop.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        sys.exit(1)
    finally:
        logger.info("Trading agent shutdown complete")


if __name__ == "__main__":
    main()
