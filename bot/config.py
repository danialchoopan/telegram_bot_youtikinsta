import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")

    MAX_FILE_SIZE_GB = float(os.getenv("MAX_FILE_SIZE_GB", "4"))
    MAX_DAILY_DOWNLOADS_PER_USER = int(os.getenv("MAX_DAILY_DOWNLOADS_PER_USER", "10"))
    MAX_CONCURRENT_QUEUED_PER_USER = int(os.getenv("MAX_CONCURRENT_QUEUED_PER_USER", "3"))
    GLOBAL_RATE_LIMIT_PER_MINUTE = int(os.getenv("GLOBAL_RATE_LIMIT_PER_MINUTE", "50"))
    MAX_RESOLUTION = int(os.getenv("MAX_RESOLUTION", "1080"))
    DEFAULT_FORMAT = os.getenv("DEFAULT_FORMAT", "mp4")
    ALLOWED_FORMATS = os.getenv("ALLOWED_FORMATS", "mp4,mkv,mp3,m4a").split(",")
    FORCE_H264 = os.getenv("FORCE_H264", "true").lower() == "true"

    AUTO_OPTIMIZE = os.getenv("AUTO_OPTIMIZE", "true").lower() == "true"
    OPTIMIZATION_PRESET = os.getenv("OPTIMIZATION_PRESET", "medium")
    VIDEO_BITRATE_MBPS = int(os.getenv("VIDEO_BITRATE_MBPS", "4"))
    AUDIO_BITRATE_KBPS = int(os.getenv("AUDIO_BITRATE_KBPS", "128"))
    MAX_OPTIMIZATION_TIME_SECONDS = int(os.getenv("MAX_OPTIMIZATION_TIME_SECONDS", "600"))
    ENABLE_4K_BLOCKING = os.getenv("ENABLE_4K_BLOCKING", "true").lower() == "true"

    DOWNLOAD_PATH = Path(os.getenv("DOWNLOAD_PATH", str(BASE_DIR / "downloads" / "temp")))
    OPTIMIZED_PATH = Path(os.getenv("OPTIMIZED_PATH", str(BASE_DIR / "downloads" / "optimized")))
    LOG_PATH = Path(os.getenv("LOG_PATH", str(BASE_DIR / "logs")))
    DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "database" / "bot.db")))

    FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
    YTDLP_PATH = os.getenv("YTDLP_PATH", "yt-dlp")

    ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "true").lower() == "true"
    ENABLE_PLAYLIST_SUPPORT = os.getenv("ENABLE_PLAYLIST_SUPPORT", "true").lower() == "true"
    ENABLE_THUMBNAIL_EXTRACTION = os.getenv("ENABLE_THUMBNAIL_EXTRACTION", "true").lower() == "true"

    @classmethod
    def ensure_directories(cls):
        for path in [cls.DOWNLOAD_PATH, cls.OPTIMIZED_PATH, cls.LOG_PATH, cls.DB_PATH.parent]:
            path.mkdir(parents=True, exist_ok=True)
