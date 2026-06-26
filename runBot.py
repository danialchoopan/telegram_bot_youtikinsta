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
    python runBot.py --setup      # First-run setup wizard

Requirements:
    - Python 3.10+
    - ffmpeg installed and in PATH
    - .env file configured with Telegram bot token

Author: MiMoCode
"""

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path

# Ensure the project root is in the Python path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from telegram.ext import ApplicationBuilder

from bot.config import Config
from bot.database import Database
from bot.services.queue_worker import QueueWorker
from bot.handlers import start, download, admin, settings


# ==========================================
# First-Run Setup Wizard
# ==========================================

def check_dependencies() -> dict:
    """
    Check if required system dependencies are installed.

    Returns:
        dict: Status of each dependency (ffmpeg, python)
    """
    deps = {"ffmpeg": False, "python": False}

    # Check Python version
    if sys.version_info >= (3, 10):
        deps["python"] = True

    # Check ffmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        deps["ffmpeg"] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        deps["ffmpeg"] = False

    return deps


def install_ffmpeg() -> bool:
    """
    Attempt to install ffmpeg based on the OS.

    Returns:
        bool: True if installation succeeded or already installed
    """
    system = sys.platform

    if system == "linux":
        # Try apt-get (Debian/Ubuntu)
        try:
            subprocess.run(
                ["sudo", "apt-get", "update"],
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", "ffmpeg"],
                capture_output=True,
                timeout=120,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try yum (CentOS/RHEL)
        try:
            subprocess.run(
                ["sudo", "yum", "install", "-y", "ffmpeg"],
                capture_output=True,
                timeout=120,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    elif system == "darwin":
        # macOS with Homebrew
        try:
            subprocess.run(
                ["brew", "install", "ffmpeg"],
                capture_output=True,
                timeout=300,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return False


def setup_wizard():
    """
    Interactive first-run setup wizard.

    Guides user through:
    1. Checking system dependencies
    2. Creating .env file with bot token
    3. Setting admin user ID
    4. Configuring basic settings
    """
    print("\n" + "=" * 50)
    print("  🔧 FIRST-TIME SETUP WIZARD")
    print("=" * 50 + "\n")

    # Step 1: Check dependencies
    print("📋 Step 1: Checking system dependencies...")
    deps = check_dependencies()

    if not deps["python"]:
        print("❌ Python 3.10+ is required!")
        print("   Please install Python 3.10 or newer.")
        return False

    print("✅ Python 3.10+ detected")

    if not deps["ffmpeg"]:
        print("⚠️  ffmpeg not found!")
        print("   Attempting to install ffmpeg...")

        if install_ffmpeg():
            print("✅ ffmpeg installed successfully")
        else:
            print("❌ Could not install ffmpeg automatically.")
            print("   Please install ffmpeg manually:")
            print("   - Ubuntu/Debian: sudo apt install ffmpeg")
            print("   - macOS: brew install ffmpeg")
            print("   - Windows: https://ffmpeg.org/download.html")
            return False
    else:
        print("✅ ffmpeg detected")

    # Step 2: Create .env file
    print("\n📋 Step 2: Configuring bot...")
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"

    if env_file.exists():
        print("⚠️  .env file already exists!")
        overwrite = input("   Overwrite? (y/N): ").lower()
        if overwrite != "y":
            print("   Using existing .env file")
            return True

    # Copy example file
    if env_example.exists():
        shutil.copy(env_example, env_file)
    else:
        # Create minimal .env file
        with open(env_file, "w") as f:
            f.write("# Telegram Bot Configuration\n")
            f.write("TELEGRAM_BOT_TOKEN=\n")
            f.write("ADMIN_USER_ID=\n")
            f.write("\n")
            f.write("# Limits\n")
            f.write("MAX_RESOLUTION=1080\n")
            f.write("DEFAULT_FORMAT=mp4\n")
            f.write("ENABLE_4K_BLOCKING=true\n")
            f.write("\n")
            f.write("# Paths\n")
            f.write("DOWNLOAD_PATH=./downloads/temp/\n")
            f.write("OPTIMIZED_PATH=./downloads/optimized/\n")
            f.write("LOG_PATH=./logs/\n")
            f.write("DB_PATH=./database/bot.db\n")

    # Step 3: Get bot token
    print("\n📋 Step 3: Telegram Bot Token")
    print("   Get your token from @BotFather on Telegram")
    bot_token = input("   Enter your bot token: ").strip()

    if not bot_token:
        print("❌ Bot token is required!")
        return False

    # Step 4: Get admin user ID
    print("\n📋 Step 4: Admin Configuration")
    print("   Send /start to @userinfobot on Telegram to get your user ID")
    admin_user_id = input("   Enter admin user ID (chat ID): ").strip()

    # Update .env file
    with open(env_file, "r") as f:
        content = f.read()

    content = content.replace("TELEGRAM_BOT_TOKEN=", f"TELEGRAM_BOT_TOKEN={bot_token}")
    if admin_user_id:
        content = content.replace("ADMIN_USER_ID=", f"ADMIN_USER_ID={admin_user_id}")

    with open(env_file, "w") as f:
        f.write(content)

    # Step 5: Create directories
    print("\n📋 Step 5: Creating directory structure...")
    Config.ensure_directories()
    print("✅ Directories created")

    # Step 6: Initialize database
    print("\n📋 Step 6: Initializing database...")
    Database()
    print("✅ Database initialized")

    # Set admin in database if user ID provided
    if admin_user_id:
        db = Database()
        # Admin will be auto-promoted when they first use admin commands
        print(f"✅ Admin user ID set: {admin_user_id}")

    print("\n" + "=" * 50)
    print("  ✅ SETUP COMPLETE!")
    print("=" * 50)
    print("\nBot is ready to run!")
    print("Start with: python runBot.py")
    print("\n")

    return True


# ==========================================
# Logging Setup
# ==========================================

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


# ==========================================
# Configuration Validation
# ==========================================

def validate_config() -> bool:
    """
    Validate that required configuration is present.

    Returns:
        True if configuration is valid, False otherwise
    """
    if not Config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env file!")
        print("Run: python runBot.py --setup")
        print("Or copy .env.example to .env and add your bot token.")
        return False

    if not Config.ADMIN_USER_ID:
        print("WARNING: ADMIN_USER_ID not set. Admin features may not work correctly.")

    return True


# ==========================================
# Main Entry Point
# ==========================================

def main():
    """Main entry point for the bot application."""

    # Check for command line flags
    debug_mode = "--debug" in sys.argv
    setup_mode = "--setup" in sys.argv

    # Run setup wizard if requested
    if setup_mode:
        success = setup_wizard()
        if success:
            print("Starting bot...")
        else:
            print("Setup failed. Please try again.")
            sys.exit(1)

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
