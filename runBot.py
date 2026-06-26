#!/usr/bin/env python3
"""
==========================================
  Media Downloader Telegram Bot - Runner
==========================================

Main entry point for the Telegram bot application.
This script initializes and starts the bot with all handlers,
queue workers, and background services.

Usage:
    python runBot.py              # Normal mode
    python runBot.py --debug      # Debug mode with verbose logging

Requirements:
    - Python 3.10+
    - ffmpeg installed and in PATH
    - .env file configured with Telegram bot token

Author: MiMoCode
"""

import os
import sys
import logging
from pathlib import Path

# Ensure the project root is in the Python path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from telegram.ext import ApplicationBuilder

from bot.config import Config
from bot.database import Database
from bot.services.queue_worker import QueueWorker
from bot.handlers import start, download, admin, settings


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        debug: If True, set logging level to DEBUG

    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Create log directory if it doesn't exist
    Config.LOG_PATH.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(Config.LOG_PATH / "bot.log"), encoding="utf-8"),
        ],
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {'DEBUG' if debug else 'INFO'} level")
    return logger


def validate_config() -> bool:
    """
    Validate that required configuration is present.

    Returns:
        True if configuration is valid, False otherwise
    """
    if not Config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env file!")
        print("Please copy .env.example to .env and add your bot token.")
        return False

    if not Config.ADMIN_USERNAME:
        print("WARNING: ADMIN_USERNAME not set. Admin features may not work correctly.")

    return True


def main():
    """Main entry point for the bot application."""

    # Check for debug mode flag
    debug_mode = "--debug" in sys.argv

    # Setup logging
    logger = setup_logging(debug=debug_mode)
    logger.info("=" * 50)
    logger.info("Media Downloader Bot - Starting Up")
    logger.info("=" * 50)

    # Ensure required directories exist
    Config.ensure_directories()
    logger.info("Directory structure verified")

    # Validate configuration
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    Database()
    logger.info("Database initialized successfully")

    # Build the Telegram application
    logger.info("Building Telegram application...")
    app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Register all command handlers
    logger.info("Registering handlers...")
    for handler in start.get_handlers():
        app.add_handler(handler)
    for handler in download.get_handlers():
        app.add_handler(handler)
    for handler in admin.get_handlers():
        app.add_handler(handler)
    for handler in settings.get_handlers():
        app.add_handler(handler)
    logger.info("All handlers registered")

    # Initialize queue worker for background processing
    queue_worker = QueueWorker(app)

    # Define startup and shutdown hooks
    async def post_init(application):
        """Called after the application is initialized."""
        await queue_worker.start()
        logger.info("Queue worker started")
        logger.info("Bot is now running! Press Ctrl+C to stop.")

    async def post_shutdown(application):
        """Called when the application is shutting down."""
        await queue_worker.stop()
        logger.info("Queue worker stopped")
        logger.info("Bot has been shut down gracefully")

    # Attach lifecycle hooks
    app.post_init = post_init
    app.post_shutdown = post_shutdown

    # Start the bot with polling
    logger.info(f"Starting polling (bot token: ...{Config.TELEGRAM_BOT_TOKEN[-8:]})")
    try:
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
