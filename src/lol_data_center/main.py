"""Main application entry point."""

import asyncio
import signal
from typing import Any

from lol_data_center.achievements.evaluator import AchievementEvaluator
from lol_data_center.database.engine import close_db, init_db
from lol_data_center.logging_config import configure_logging, get_logger
from lol_data_center.services.polling_service import PollingService

logger = get_logger(__name__)


async def main() -> None:
    """Main application entry point."""
    configure_logging()
    logger.info("Starting LoL Data Center")

    # Initialize database
    logger.info("Initializing database")
    await init_db()

    # Initialize services
    polling_service = PollingService()
    achievement_evaluator = AchievementEvaluator()

    # Subscribe achievement evaluator to events
    achievement_evaluator.subscribe()

    # Setup shutdown handling
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig: Any) -> None:
        logger.info("Received shutdown signal", signal=sig)
        shutdown_event.set()

    # Register signal handlers (Unix-like systems)
    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, handle_shutdown, sig)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass

    try:
        # Start polling service
        await polling_service.start()

        logger.info("LoL Data Center is running. Press Ctrl+C to stop.")

        # Wait for shutdown
        await shutdown_event.wait()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        # Cleanup
        logger.info("Shutting down...")

        await polling_service.stop()
        await achievement_evaluator.close()
        await close_db()

        logger.info("LoL Data Center stopped")


if __name__ == "__main__":
    asyncio.run(main())
