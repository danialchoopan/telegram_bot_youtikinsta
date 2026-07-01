"""
==========================================
  Downloader Service
==========================================

Handles media downloads using yt-dlp with format-specific configurations.
Supports multiple output formats and provides progress callbacks.

Supported Formats:
    - MP4 (H.264): Default video format, best Telegram compatibility
    - MKV: Advanced container for power users
    - MP3: Audio extraction at 192kbps
    - M4A: AAC audio at 128kbps
    - Best: Auto-selects optimal format for Telegram

Usage:
    downloader = Downloader()
    file_path, info = downloader.download(url, "mp4")
"""

import os
import logging
import yt_dlp
from bot.config import Config
from bot.utils.helpers import generate_random_string

logger = logging.getLogger(__name__)


class Downloader:
    """
    Media downloader using yt-dlp.

    Downloads media files with format-specific configurations
    and optional progress callbacks for real-time updates.
    """

    def __init__(self):
        """Initialize downloader and ensure download directory exists."""
        Config.ensure_directories()

    def download(self, url: str, format_type: str, progress_callback=None, platform: str = "youtube") -> tuple[str, dict]:
        """Download media from URL."""
        logger.info(f"Downloading: {url} as {format_type} (platform: {platform})")

        filename = f"dl_{generate_random_string(12)}"
        ydl_opts = self._build_opts(format_type, filename, platform)

        if progress_callback:
            ydl_opts["progress_hooks"] = [lambda d: self._progress_hook(d, progress_callback)]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = self._find_file(filename)
                if not file_path:
                    raise FileNotFoundError("Downloaded file not found")
                logger.info(f"Download complete: {file_path}")
                return file_path, info
        except Exception as e:
            logger.error(f"Download failed: {e}")
            # Cleanup on failure
            self._cleanup(filename)
            raise

    def get_info_only(self, url: str) -> dict:
        """
        Extract info from URL without downloading.

        Args:
            url: Media URL

        Returns:
            dict: yt-dlp info dictionary
        """
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _build_opts(self, format_type: str, filename: str, platform: str = "youtube") -> dict:
        """
        Build yt-dlp options for specific format.

        For TikTok/Instagram: use 'best' (merged stream, no format filtering)
        For YouTube: use height-based format selection
        """
        outtmpl = str(Config.DOWNLOAD_PATH / f"{filename}.%(ext)s")

        base_opts = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
        }

        if Config.DOWNLOAD_PROXY:
            base_opts["proxy"] = Config.DOWNLOAD_PROXY

        # Audio formats
        if format_type == "mp3":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
            }
        if format_type == "m4a":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "128"}],
            }

        # TikTok/Instagram: just get best available (these have merged streams)
        if platform in ("tiktok", "instagram"):
            return {
                **base_opts,
                "format": "best",
                "merge_output_format": "mp4",
            }

        # YouTube and others: height-based selection
        if format_type == "best":
            return {
                **base_opts,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "merge_output_format": "mp4",
            }

        if format_type == "mkv":
            return {
                **base_opts,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "merge_output_format": "mkv",
            }

        if format_type == "mp4_720":
            return {
                **base_opts,
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "merge_output_format": "mp4",
            }

        # Default MP4
        return {
            **base_opts,
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "merge_output_format": "mp4",
        }

    def _progress_hook(self, data: dict, callback):
        """
        yt-dlp progress hook that calls the provided callback.

        Reports download percentage, speed, and ETA.
        """
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            current = data.get("downloaded_bytes", 0)
            speed = data.get("speed") or 0
            eta = data.get("eta") or 0
            percent = (current / total * 100) if total > 0 else 0
            callback({
                "stage": "downloading",
                "percent": round(percent, 1),
                "current": current,
                "total": total,
                "speed": speed,
                "eta": eta,
            })
        elif data["status"] == "finished":
            callback({"stage": "download_complete"})

    def _find_file(self, filename_prefix: str) -> str | None:
        """Find downloaded file by filename prefix."""
        for f in os.listdir(Config.DOWNLOAD_PATH):
            if f.startswith(filename_prefix):
                return str(Config.DOWNLOAD_PATH / f)
        return None

    def _cleanup(self, filename_prefix: str):
        """Remove partially downloaded files on failure."""
        for f in os.listdir(Config.DOWNLOAD_PATH):
            if f.startswith(filename_prefix):
                os.remove(str(Config.DOWNLOAD_PATH / f))
