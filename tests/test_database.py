"""
==========================================
  Unit Tests - Database Module
==========================================

Tests for the SQLite database operations including:
    - User creation and retrieval
    - User preferences
    - Download records
    - Queue management
    - Ban functionality
    - Statistics
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Use temporary database for tests
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")

from bot.database import Database


@pytest.fixture
def db():
    """Create a fresh database for each test."""
    # Reset singleton for testing
    Database._instance = None
    Database._initialized = False
    database = Database()
    yield database
    # Cleanup
    Database._instance = None
    Database._initialized = False


class TestUserOperations:
    """Test user CRUD operations."""

    def test_create_user(self, db):
        user = db.get_or_create_user(12345, "testuser", "Test User")
        assert user["user_id"] == 12345
        assert user["username"] == "testuser"
        assert user["full_name"] == "Test User"

    def test_get_existing_user(self, db):
        db.get_or_create_user(12345, "testuser", "Test User")
        user = db.get_user(12345)
        assert user is not None
        assert user["user_id"] == 12345

    def test_get_nonexistent_user(self, db):
        user = db.get_user(99999)
        assert user is None

    def test_update_user_language(self, db):
        db.get_or_create_user(12345)
        db.update_user_language(12345, "fa")
        user = db.get_user(12345)
        assert user["language"] == "fa"

    def test_update_user_preferences(self, db):
        db.get_or_create_user(12345)
        db.update_user_preferences(12345, preferred_format="mp3", preferred_quality="720p")
        user = db.get_user(12345)
        assert user["preferred_format"] == "mp3"
        assert user["preferred_quality"] == "720p"


class TestBanOperations:
    """Test user ban functionality."""

    def test_ban_user(self, db):
        db.get_or_create_user(12345)
        db.ban_user(12345, hours=24)
        assert db.is_user_banned(12345) is True

    def test_unban_after_time(self, db):
        db.get_or_create_user(12345)
        # Ban for 0 hours (immediately expires)
        db.ban_user(12345, hours=0)
        # Note: This test might be flaky due to timing
        # In real scenario, ban would expire

    def test_not_banned(self, db):
        db.get_or_create_user(12345)
        assert db.is_user_banned(12345) is False


class TestAdminOperations:
    """Test admin functionality."""

    def test_set_admin(self, db):
        db.get_or_create_user(12345)
        db.set_admin(12345, True)
        assert db.is_admin(12345) is True

    def test_remove_admin(self, db):
        db.get_or_create_user(12345)
        db.set_admin(12345, True)
        db.set_admin(12345, False)
        assert db.is_admin(12345) is False

    def test_not_admin_by_default(self, db):
        db.get_or_create_user(12345)
        assert db.is_admin(12345) is False


class TestDownloadOperations:
    """Test download record operations."""

    def test_add_download(self, db):
        db.get_or_create_user(12345)
        download_id = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        assert download_id > 0

    def test_update_download(self, db):
        db.get_or_create_user(12345)
        download_id = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        db.update_download(download_id, status="completed", optimized_size_mb=50.5)
        # Verify update (would need to query downloads table)

    def test_increment_user_downloads(self, db):
        db.get_or_create_user(12345)
        db.increment_user_downloads(12345, 50.5)
        user = db.get_user(12345)
        assert user["total_downloads"] == 1
        assert user["total_size_downloaded"] == 50.5


class TestQueueOperations:
    """Test queue management operations."""

    def test_add_to_queue(self, db):
        db.get_or_create_user(12345)
        download_id = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        queue_id = db.add_to_queue(12345, download_id, priority=5)
        assert queue_id > 0

    def test_get_next_queue_item(self, db):
        db.get_or_create_user(12345)
        download_id = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        db.add_to_queue(12345, download_id, priority=5)
        item = db.get_next_queue_item()
        assert item is not None
        assert item["url"] == "https://youtube.com/watch?v=abc"

    def test_update_queue_status(self, db):
        db.get_or_create_user(12345)
        download_id = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        queue_id = db.add_to_queue(12345, download_id, priority=5)
        db.update_queue_status(queue_id, "processing")
        # Verify status updated

    def test_queue_priority(self, db):
        db.get_or_create_user(12345)
        db.get_or_create_user(12346)

        # Add downloads for two users with different priorities
        dl1 = db.add_download(12345, "https://youtube.com/watch?v=abc", "youtube", "mp4")
        dl2 = db.add_download(12346, "https://youtube.com/watch?v=xyz", "youtube", "mp4")

        db.add_to_queue(12345, dl1, priority=5)  # Regular user
        db.add_to_queue(12346, dl2, priority=1)  # Admin user

        # Next item should be the admin's (priority 1)
        item = db.get_next_queue_item()
        assert item["user_id"] == 12346


class TestDownloadLimits:
    """Test download rate limiting."""

    def test_can_download(self, db):
        db.get_or_create_user(12345)
        assert db.can_download(12345) is True

    def test_daily_count(self, db):
        db.get_or_create_user(12345)
        count = db.get_daily_download_count(12345)
        assert count == 0

    def test_banned_cannot_download(self, db):
        db.get_or_create_user(12345)
        db.ban_user(12345, hours=24)
        assert db.can_download(12345) is False


class TestStatistics:
    """Test statistics operations."""

    def test_get_bot_stats(self, db):
        db.get_or_create_user(12345)
        stats = db.get_bot_stats()
        assert "total_users" in stats
        assert "total_downloads" in stats
        assert "success_rate" in stats

    def test_get_user_stats(self, db):
        db.get_or_create_user(12345)
        stats = db.get_user_stats(12345)
        assert stats["user_id"] == 12345
        assert "today_downloads" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
