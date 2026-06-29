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

    def download(self, url: str, format_type: str, progress_callback=None) -> tuple[str, dict]:
        """
        Download media from URL.

        Args:
            url: Media URL to download
            format_type: Output format (mp4, mkv, mp3, m4a, mp4_720, best)
            progress_callback: Optional callback for progress updates

        Returns:
            tuple: (file_path, info_dict)

        Raises:
            FileNotFoundError: If downloaded file cannot be found
            Exception: If download fails
        """
        logger.info(f"Downloading: {url} as {format_type}")

        # Generate unique filename to avoid collisions
        filename = f"dl_{generate_random_string(12)}"

        # Build yt-dlp options based on format
        ydl_opts = self._build_opts(format_type, filename)

        # Add progress hook if callback provided
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

    def _build_opts(self, format_type: str, filename: str) -> dict:
        """
        Build yt-dlp options for specific format.

        Each format has optimized settings for quality and compatibility.
        """
        # Base output template with random filename
        outtmpl = str(Config.DOWNLOAD_PATH / f"{filename}.%(ext)s")

        # Common options shared across all formats
        base_opts = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }

        # Add proxy if configured
        if Config.DOWNLOAD_PROXY:
            base_opts["proxy"] = Config.DOWNLOAD_PROXY

        # MP3: Extract audio and convert to MP3
        if format_type == "mp3":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        # M4A: Extract audio and convert to M4A (AAC)
        if format_type == "m4a":
            return {
                **base_opts,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "128",
                }],
            }

        # MKV: Download video in MKV container
        if format_type == "mkv":
            height = self._get_height_for_format(format_type)
            return {
                **base_opts,
                "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                "merge_output_format": "mkv",
            }

        # MP4 720p: Download at 720p max
        if format_type == "mp4_720":
            return {
                **base_opts,
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "merge_output_format": "mp4",
            }

        # Best: Auto-select optimal format for Telegram
        if format_type == "best":
            return {
                **base_opts,
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "merge_output_format": "mp4",
                "format_sort": ["res:1080", "codec:h264", "size"],
            }

        # Default MP4: Download at specified height
        height = self._get_height_for_format(format_type)
        return {
            **base_opts,
            "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
            "merge_output_format": "mp4",
        }

    def _get_height_for_format(self, format_type: str) -> int:
        """Map format type to maximum height."""
        mapping = {"mp4": 1080, "mkv": 1080, "mp4_720": 720}
        return mapping.get(format_type, Config.MAX_RESOLUTION)

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
