"""
==========================================
  Unit Tests - Messages Module
==========================================

Tests for the bilingual message system.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.utils.messages import get_message, MESSAGES


class TestMessages:
    """Test message retrieval and formatting."""

    def test_get_english_welcome(self):
        msg = get_message("en", "welcome")
        assert "Welcome" in msg
        assert "Media Downloader Bot" in msg

    def test_get_persian_welcome(self):
        msg = get_message("fa", "welcome")
        assert "خوش آمدید" in msg

    def test_fallback_to_english(self):
        msg = get_message("invalid_lang", "welcome")
        assert "Welcome" in msg

    def test_fallback_to_key(self):
        msg = get_message("en", "nonexistent_key")
        assert msg == "nonexistent_key"

    def test_format_with_kwargs(self):
        msg = get_message("en", "error", error="Test error")
        assert "Test error" in msg

    def test_format_queue_added(self):
        msg = get_message("en", "queue_added", position=3, minutes=6)
        assert "#3" in msg
        assert "6 min" in msg

    def test_format_rate_limit(self):
        msg = get_message("en", "rate_limit", used=5, limit=10)
        assert "5/10" in msg

    def test_format_blocked_4k(self):
        msg = get_message("en", "blocked_4k")
        assert "4K" in msg
        assert "1080p" in msg

    def test_all_keys_exist_in_english(self):
        """Verify all message keys exist in English."""
        required_keys = [
            "welcome", "language_selected", "select_format",
            "format_selected", "queue_added", "complete",
            "error", "blocked_4k", "rate_limit", "settings",
        ]
        for key in required_keys:
            assert key in MESSAGES["en"], f"Missing key: {key}"

    def test_all_keys_exist_in_persian(self):
        """Verify all message keys exist in Persian."""
        required_keys = [
            "welcome", "language_selected", "select_format",
            "format_selected", "queue_added", "complete",
            "error", "blocked_4k", "rate_limit", "settings",
        ]
        for key in required_keys:
            assert key in MESSAGES["fa"], f"Missing key: {key}"

    def test_format_selection_options(self):
        """Verify format selection messages exist."""
        formats = ["mp4", "mkv", "mp3", "m4a", "best"]
        for fmt in formats:
            assert fmt in MESSAGES["en"]
            assert fmt in MESSAGES["fa"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
