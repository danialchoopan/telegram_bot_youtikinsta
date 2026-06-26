"""
==========================================
  Helper Utilities Module
==========================================

Common utility functions used throughout the application.
Provides URL validation, platform detection, formatting, and string generation.

Functions:
    - generate_random_string: Create random filenames
    - detect_platform: Identify media platform from URL
    - is_valid_url: Validate URL format
    - format_size: Convert bytes to human-readable size
    - format_duration: Convert seconds to time string
    - format_time: Convert seconds to elapsed time string
    - is_playlist_url: Check if URL is a playlist
    - extract_video_id: Extract video/post ID from URL
"""

import re
import string
import random
from urllib.parse import urlparse


def generate_random_string(length: int = 10) -> str:
    """
    Generate random alphanumeric string for filenames.

    Args:
        length: Length of string to generate

    Returns:
        str: Random string (e.g., "aB3xY7zQ9w")
    """
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def detect_platform(url: str) -> str:
    """
    Detect media platform from URL.

    Returns:
        str: Platform name (youtube, instagram, tiktok, or direct)
    """
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url or "instagr.am" in url:
        return "instagram"
    if "tiktok.com" in url or "vm.tiktok.com" in url:
        return "tiktok"
    return "direct"


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.

    Returns True if URL has valid scheme (http/https) and network location.
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def format_size(size_bytes: float) -> str:
    """
    Convert bytes to human-readable file size.

    Examples:
        1024 -> "1.0 KB"
        1048576 -> "1.0 MB"
        1073741824 -> "1.00 GB"
    """
    if size_bytes < 1024:
        return f"{size_bytes:.0f} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: int) -> str:
    """
    Convert seconds to duration string.

    Examples:
        65 -> "1:05"
        3661 -> "1:01:01"
    """
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}:{secs:02d}"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}:{secs:02d}"


def format_time(seconds: int) -> str:
    """
    Convert seconds to elapsed time string.

    Examples:
        65 -> "1m 5s"
        3661 -> "1h 1m"
    """
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def is_playlist_url(url: str) -> bool:
    """Check if URL is a playlist (YouTube, etc.)."""
    return "playlist" in url.lower() or "list=" in url.lower()


def extract_video_id(url: str) -> str | None:
    """
    Extract video/post ID from URL.

    Supports:
        - YouTube: watch?v=..., youtu.be/..., embed/...
        - Instagram: /p/..., /reel/..., /tv/...
        - TikTok: /video/...

    Returns:
        str: Video/post ID, or None if not found
    """
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)",
        r"instagram\.com\/(?:p|reel|tv)\/([A-Za-z0-9_-]+)",
        r"tiktok\.com\/@[^/]+\/video\/(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
