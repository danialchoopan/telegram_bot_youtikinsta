"""
==========================================
  Configuration Management Module
==========================================

Central configuration class that loads all settings from environment variables
(.env file) with sensible defaults. This module is the single source of truth
for all configurable parameters in the application.

Environment Variables:
    TELEGRAM_BOT_TOKEN    - Your Telegram bot token from @BotFather
    ADMIN_USER_ID         - Telegram user ID (chat ID) of the bot administrator
    MAX_RESOLUTION        - Maximum video resolution (default: 1080)
    DEFAULT_FORMAT        - Default output format (mp4/mkv/mp3/m4a)
    ENABLE_4K_BLOCKING    - Block 4K downloads (true/false)
    VIDEO_BITRATE_MBPS    - Video bitrate for optimization
    AUDIO_BITRATE_KBPS    - Audio bitrate for optimization

Usage:
    from bot.config import Config
    token = Config.TELEGRAM_BOT_TOKEN
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration class.

    All settings are loaded from environment variables with fallback defaults.
    This class should not be instantiated - all attributes are class-level.
    """

    # Root directory of the project (parent of bot/)
    BASE_DIR = Path(__file__).resolve().parent.parent

    # ==========================================
    # Telegram Bot Configuration
    # ==========================================
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # Admin user's Telegram chat ID (user_id), not username
    ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

    # ==========================================
    # Rate Limiting & User Limits
    # ==========================================
    # Maximum file size allowed (in GB)
    MAX_FILE_SIZE_GB = float(os.getenv("MAX_FILE_SIZE_GB", "4"))
    # Max downloads per user per day
    MAX_DAILY_DOWNLOADS_PER_USER = int(os.getenv("MAX_DAILY_DOWNLOADS_PER_USER", "10"))
    # Max concurrent items in queue per user
    MAX_CONCURRENT_QUEUED_PER_USER = int(os.getenv("MAX_CONCURRENT_QUEUED_PER_USER", "3"))
    # Global rate limit (downloads per minute across all users)
    GLOBAL_RATE_LIMIT_PER_MINUTE = int(os.getenv("GLOBAL_RATE_LIMIT_PER_MINUTE", "50"))

    # ==========================================
    # Format & Quality Settings
    # ==========================================
    # Maximum resolution allowed (blocks 4K if set to 1080)
    MAX_RESOLUTION = int(os.getenv("MAX_RESOLUTION", "1080"))
    # Default output format when user doesn't specify
    DEFAULT_FORMAT = os.getenv("DEFAULT_FORMAT", "mp4")
    # List of allowed output formats
    ALLOWED_FORMATS = os.getenv("ALLOWED_FORMATS", "mp4,mkv,mp3,m4a").split(",")
    # Force H.264 codec for better Telegram compatibility
    FORCE_H264 = os.getenv("FORCE_H264", "true").lower() == "true"

    # ==========================================
    # Optimization Settings
    # ==========================================
    # Enable automatic optimization for Telegram
    AUTO_OPTIMIZE = os.getenv("AUTO_OPTIMIZE", "true").lower() == "true"
    # FFmpeg preset: fast, medium, slow (slower = better quality)
    OPTIMIZATION_PRESET = os.getenv("OPTIMIZATION_PRESET", "medium")
    # Video bitrate in Mbps for optimization
    VIDEO_BITRATE_MBPS = int(os.getenv("VIDEO_BITRATE_MBPS", "4"))
    # Audio bitrate in kbps for optimization
    AUDIO_BITRATE_KBPS = int(os.getenv("AUDIO_BITRATE_KBPS", "128"))
    # Max time allowed for optimization before timeout
    MAX_OPTIMIZATION_TIME_SECONDS = int(os.getenv("MAX_OPTIMIZATION_TIME_SECONDS", "600"))
    # Block 4K/8K downloads completely
    ENABLE_4K_BLOCKING = os.getenv("ENABLE_4K_BLOCKING", "true").lower() == "true"

    # ==========================================
    # File Paths
    # ==========================================
    # Temporary download directory
    DOWNLOAD_PATH = Path(os.getenv("DOWNLOAD_PATH", str(BASE_DIR / "downloads" / "temp")))
    # Optimized output directory
    OPTIMIZED_PATH = Path(os.getenv("OPTIMIZED_PATH", str(BASE_DIR / "downloads" / "optimized")))
    # Log files directory
    LOG_PATH = Path(os.getenv("LOG_PATH", str(BASE_DIR / "logs")))
    # SQLite database path
    DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "database" / "bot.db")))

    # ==========================================
    # External Tool Paths
    # ==========================================
    # Path to ffmpeg binary (must be in PATH or absolute path)
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
    # Path to yt-dlp binary (must be in PATH or absolute path)
    YTDLP_PATH = os.getenv("YTDLP_PATH", "yt-dlp")

    # ==========================================
    # Feature Toggles
    # ==========================================
    # Enable download analytics tracking
    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    # Enable playlist/batch download support
    ENABLE_PLAYLIST_SUPPORT = os.getenv("ENABLE_PLAYLIST_SUPPORT", "true").lower() == "true"
    # Enable thumbnail extraction from videos
    ENABLE_THUMBNAIL_EXTRACTION = os.getenv("ENABLE_THUMBNAIL_EXTRACTION", "true").lower() == "true"

    @classmethod
    def ensure_directories(cls):
        """
        Create all required directories if they don't exist.

        Called at application startup to ensure the directory structure
        is ready for downloads, logs, and database operations.
        """
        for path in [cls.DOWNLOAD_PATH, cls.OPTIMIZED_PATH, cls.LOG_PATH, cls.DB_PATH.parent]:
            path.mkdir(parents=True, exist_ok=True)
