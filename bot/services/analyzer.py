"""
==========================================
  Media Analyzer Service
==========================================

Analyzes media URLs to extract metadata before download.
Uses yt-dlp to fetch video/audio information without downloading.

Capabilities:
    - Extract title, duration, thumbnail, and available formats
    - Detect platform (YouTube, Instagram, TikTok, etc.)
    - Determine original resolution and file size
    - Check for 4K content
    - Generate format selection options based on media properties

Usage:
    analyzer = MediaAnalyzer()
    info = analyzer.get_info("https://youtube.com/watch?v=...")
    print(info["title"], info["is_4k"])
"""

import yt_dlp
from bot.config import Config
from bot.utils.helpers import detect_platform


class MediaAnalyzer:
    """
    Analyzes media URLs using yt-dlp.

    Extracts metadata without downloading to enable format selection
    and 4K detection before committing to a download.
    """

    def __init__(self):
        """Initialize analyzer with yt-dlp options (no download, quiet mode)."""
        self.ydl_opts = {
            "quiet": True,          # Suppress console output
            "no_warnings": True,    # Suppress warnings
            "skip_download": True,  # Only extract info, don't download
        }

    def get_info(self, url: str) -> dict:
        """
        Analyze a media URL and return metadata.

        Args:
            url: Media URL (YouTube, Instagram, TikTok, or direct link)

        Returns:
            dict: Media information including title, duration, formats, etc.

        Raises:
            ValueError: If the URL cannot be analyzed
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._format_info(info, url)
        except Exception as e:
            raise ValueError(f"Could not analyze link: {str(e)}")

    def _format_info(self, info: dict, url: str) -> dict:
        """
        Format raw yt-dlp info into structured metadata.

        Extracts key properties like resolution, file size, and media type.
        """
        platform = detect_platform(url)
        title = info.get("title", "Unknown")
        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", None)

        # Analyze available formats
        formats = info.get("formats", [])
        original_height = 0
        original_size = 0
        available_resolutions = set()

        for f in formats:
            # Track video resolutions
            height = f.get("height")
            if height:
                available_resolutions.add(height)
                if height > original_height:
                    original_height = height

            # Track largest file size
            filesize = f.get("filesize") or f.get("filesize_approx")
            if filesize and filesize > original_size:
                original_size = filesize

        # Sort resolutions descending (1080, 720, 480, ...)
        available_resolutions = sorted(available_resolutions, reverse=True)

        # Determine media type (video, audio, or unknown)
        has_video = any(f.get("vcodec") and f["vcodec"] != "none" for f in formats)
        has_audio = any(f.get("acodec") and f["acodec"] != "none" for f in formats)

        if has_video and has_audio:
            media_type = "video"
        elif has_audio:
            media_type = "audio"
        else:
            media_type = "unknown"

        # Check if content is 4K (2160p or higher)
        is_4k = original_height >= 2160

        return {
            "url": url,
            "title": title,
            "duration": duration,
            "thumbnail": thumbnail,
            "platform": platform,
            "media_type": media_type,
            "original_height": original_height,
            "original_size": original_size,
            "available_resolutions": available_resolutions,
            "is_4k": is_4k,
            "formats_available": self._get_format_options(media_type, original_height),
        }

    def _get_format_options(self, media_type: str, max_height: int) -> list:
        """
        Generate format options based on media properties.

        For audio-only content, only audio formats are shown.
        For video content, shows video formats up to the max resolution.
        """
        if media_type == "audio":
            return ["mp3", "m4a"]

        options = []

        # Cap height at MAX_RESOLUTION if 4K blocking is enabled
        capped_height = min(max_height, Config.MAX_RESOLUTION) if Config.ENABLE_4K_BLOCKING else max_height

        # Add video format options based on available resolution
        if capped_height >= 1080:
            options.append(("mp4", "📹 MP4 1080p"))
            options.append(("mkv", "🎬 MKV 1080p"))
        if capped_height >= 720:
            options.append(("mp4_720", "📹 MP4 720p"))

        # Always offer audio-only options
        options.append(("mp3", "🎵 MP3 Audio"))
        options.append(("m4a", "🎶 M4A Audio"))

        # Always offer "Best for Telegram" option
        options.append(("best", "⚡ Best for Telegram"))

        return options

    def check_4k(self, url: str) -> bool:
        """
        Check if a URL contains 4K content.

        Args:
            url: Media URL to check

        Returns:
            bool: True if 4K content detected, False otherwise
        """
        if not Config.ENABLE_4K_BLOCKING:
            return False
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                for f in info.get("formats", []):
                    height = f.get("height", 0)
                    if height >= 2160:
                        return True
                return False
        except Exception:
            return False

    def estimate_size(self, url: str, format_type: str) -> int:
        """
        Estimate download file size in bytes.

        For audio: calculates based on duration and bitrate.
        For video: finds the largest compatible format size.

        Args:
            url: Media URL
            format_type: Output format (mp4, mkv, mp3, m4a)

        Returns:
            int: Estimated size in bytes (0 if unknown)
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Audio size estimation (duration * bitrate)
                if format_type in ("mp3", "m4a"):
                    duration = info.get("duration", 0)
                    bitrate = 192 if format_type == "mp3" else 128
                    return int(duration * bitrate * 1000 / 8)

                # Video size estimation (find largest compatible format)
                best_size = 0
                for f in info.get("formats", []):
                    if f.get("vcodec") and f["vcodec"] != "none":
                        height = f.get("height", 0)
                        if height <= Config.MAX_RESOLUTION:
                            size = f.get("filesize") or f.get("filesize_approx") or 0
                            if size > best_size:
                                best_size = size
                return best_size
        except Exception:
            return 0
