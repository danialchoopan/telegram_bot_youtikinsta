"""
==========================================
  Unit Tests - Helper Utilities
==========================================

Tests for the helper utility functions including:
    - URL validation
    - Platform detection
    - File size formatting
    - Duration formatting
    - Video ID extraction
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.utils.helpers import (
    generate_random_string,
    detect_platform,
    is_valid_url,
    format_size,
    format_duration,
    format_time,
    is_playlist_url,
    extract_video_id,
)


class TestGenerateRandomString:
    """Test random string generation."""

    def test_default_length(self):
        result = generate_random_string()
        assert len(result) == 10

    def test_custom_length(self):
        result = generate_random_string(20)
        assert len(result) == 20

    def test_alphanumeric(self):
        result = generate_random_string(100)
        assert result.isalnum()

    def test_unique(self):
        results = [generate_random_string() for _ in range(10)]
        assert len(set(results)) == 10


class TestDetectPlatform:
    """Test platform detection from URLs."""

    def test_youtube_watch(self):
        assert detect_platform("https://www.youtube.com/watch?v=abc123") == "youtube"

    def test_youtube_short(self):
        assert detect_platform("https://youtu.be/abc123") == "youtube"

    def test_instagram_post(self):
        assert detect_platform("https://www.instagram.com/p/ABC123/") == "instagram"

    def test_instagram_reel(self):
        assert detect_platform("https://www.instagram.com/reel/ABC123/") == "instagram"

    def test_tiktok(self):
        assert detect_platform("https://www.tiktok.com/@user/video/123") == "tiktok"

    def test_tiktok_vm(self):
        assert detect_platform("https://vm.tiktok.com/ABC123/") == "tiktok"

    def test_direct_link(self):
        assert detect_platform("https://example.com/video.mp4") == "direct"

    def test_case_insensitive(self):
        assert detect_platform("HTTPS://WWW.YOUTUBE.COM/watch?v=abc") == "youtube"


class TestIsValidUrl:
    """Test URL validation."""

    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self):
        assert is_valid_url("https://example.com") is True

    def test_valid_with_path(self):
        assert is_valid_url("https://example.com/path/to/video") is True

    def test_valid_with_query(self):
        assert is_valid_url("https://youtube.com/watch?v=abc123") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_no_netloc(self):
        assert is_valid_url("https://") is False

    def test_invalid_empty(self):
        assert is_valid_url("") is False

    def test_invalid_ftp(self):
        assert is_valid_url("ftp://example.com") is False


class TestFormatSize:
    """Test file size formatting."""

    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert format_size(1024) == "1.0 KB"
        assert format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert format_size(1048576) == "1.0 MB"
        assert format_size(1572864) == "1.5 MB"

    def test_gigabytes(self):
        assert format_size(1073741824) == "1.00 GB"
        assert format_size(2147483648) == "2.00 GB"

    def test_zero(self):
        assert format_size(0) == "0 B"


class TestFormatDuration:
    """Test duration formatting."""

    def test_seconds(self):
        assert format_duration(30) == "30s"

    def test_minutes(self):
        assert format_duration(65) == "1:05"
        assert format_duration(120) == "2:00"

    def test_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0s"


class TestFormatTime:
    """Test elapsed time formatting."""

    def test_seconds(self):
        assert format_time(30) == "30s"

    def test_minutes(self):
        assert format_time(65) == "1m 5s"
        assert format_time(120) == "2m 0s"

    def test_hours(self):
        assert format_time(3661) == "1h 1m"

    def test_zero(self):
        assert format_time(0) == "0s"


class TestIsPlaylistUrl:
    """Test playlist URL detection."""

    def test_youtube_playlist(self):
        assert is_playlist_url("https://youtube.com/playlist?list=abc123") is True

    def test_youtube_watch_with_list(self):
        assert is_playlist_url("https://youtube.com/watch?v=abc&list=xyz") is True

    def test_not_playlist(self):
        assert is_playlist_url("https://youtube.com/watch?v=abc123") is False

    def test_direct_link(self):
        assert is_playlist_url("https://example.com/video.mp4") is False


class TestExtractVideoId:
    """Test video ID extraction from URLs."""

    def test_youtube_watch(self):
        assert extract_video_id("https://youtube.com/watch?v=abc123") == "abc123"

    def test_youtube_short(self):
        assert extract_video_id("https://youtu.be/abc123") == "abc123"

    def test_youtube_embed(self):
        assert extract_video_id("https://youtube.com/embed/abc123") == "abc123"

    def test_instagram_post(self):
        assert extract_video_id("https://instagram.com/p/ABC123/") == "ABC123"

    def test_instagram_reel(self):
        assert extract_video_id("https://instagram.com/reel/ABC123/") == "ABC123"

    def test_tiktok_video(self):
        assert extract_video_id("https://tiktok.com/@user/video/123456") == "123456"

    def test_no_match(self):
        assert extract_video_id("https://example.com/video") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
