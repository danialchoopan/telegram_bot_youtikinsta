"""
==========================================
  SQLite Database Module
==========================================

Thread-safe singleton database manager for the Telegram bot.
Handles all data persistence including users, downloads, queue,
and quality statistics.

Database Tables:
    - users: User profiles, preferences, and ban status
    - downloads: Download history with status tracking
    - download_queue: Priority-based download queue
    - quality_stats: Analytics for quality/format distribution

The Database class uses a singleton pattern to ensure only one
connection pool exists across the application.

Usage:
    db = Database()
    user = db.get_or_create_user(user_id=12345)
    db.add_download(user_id=12345, url="...", platform="youtube")
"""

import sqlite3
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager

from bot.config import Config


class Database:
    """
    Thread-safe singleton database manager.

    Uses WAL journal mode for better concurrent read performance.
    Each thread gets its own connection via threading.local().
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one Database instance exists (singleton pattern)."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize database connection and create tables if needed."""
        if self._initialized:
            return
        self._initialized = True
        Config.ensure_directories()
        self.db_path = str(Config.DB_PATH)
        # Thread-local storage for database connections
        self._local = threading.local()
        self._create_tables()

    def _get_conn(self):
        """
        Get or create a thread-local database connection.

        Each thread gets its own connection to avoid SQLite threading issues.
        WAL mode is enabled for better concurrent read performance.
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row  # Enable dict-like access
            self._local.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        return self._local.conn

    @contextmanager
    def _cursor(self):
        """
        Context manager for database cursor operations.

        Automatically commits on success, rolls back on exception.
        """
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _create_tables(self):
        """Create all database tables if they don't exist."""
        with self._cursor() as cur:
            cur.executescript("""
                -- Users table: stores user profiles and preferences
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    language TEXT DEFAULT 'en',
                    registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    total_downloads INTEGER DEFAULT 0,
                    total_size_downloaded REAL DEFAULT 0,
                    last_activity DATETIME,
                    banned_until DATETIME,
                    download_limit_per_day INTEGER DEFAULT 10,
                    preferred_format TEXT DEFAULT 'mp4',
                    preferred_quality TEXT DEFAULT '1080p'
                );

                -- Downloads table: tracks all download requests
                CREATE TABLE IF NOT EXISTS downloads (
                    download_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    url TEXT,
                    platform TEXT,
                    media_type TEXT,
                    selected_format TEXT,
                    original_quality TEXT,
                    output_quality TEXT,
                    original_size_mb REAL,
                    optimized_size_mb REAL,
                    file_path TEXT,
                    status TEXT DEFAULT 'queued',
                    request_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completion_time DATETIME,
                    optimization_time_seconds INTEGER,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    was_4k_detected BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                -- Download queue: priority-based processing queue
                CREATE TABLE IF NOT EXISTS download_queue (
                    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    download_id INTEGER,
                    priority INTEGER DEFAULT 5,
                    position INTEGER,
                    status TEXT DEFAULT 'waiting',
                    enqueue_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    start_time DATETIME,
                    estimated_wait_time_minutes INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (download_id) REFERENCES downloads(download_id)
                );

                -- Quality statistics: analytics for format/resolution usage
                CREATE TABLE IF NOT EXISTS quality_stats (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resolution TEXT,
                    format TEXT,
                    count INTEGER DEFAULT 0,
                    avg_file_size_mb REAL,
                    avg_optimization_time_seconds REAL,
                    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

    # ==========================================
    # User Management Methods
    # ==========================================

    def get_or_create_user(self, user_id: int, username: str = None, full_name: str = None) -> dict:
        """
        Get existing user or create new one.

        Args:
            user_id: Telegram user ID
            username: Telegram username (without @)
            full_name: User's display name

        Returns:
            dict: User record as dictionary
        """
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                # Update last activity for existing user
                cur.execute(
                    "UPDATE users SET last_activity = CURRENT_TIMESTAMP, username = ?, full_name = ? WHERE user_id = ?",
                    (username, full_name, user_id),
                )
                return dict(row)
            # Create new user
            cur.execute(
                "INSERT INTO users (user_id, username, full_name, last_activity) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, username, full_name),
            )
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cur.fetchone())

    def get_user(self, user_id: int) -> dict | None:
        """
        Get user by ID.

        Args:
            user_id: Telegram user ID

        Returns:
            dict: User record or None if not found
        """
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_user_language(self, user_id: int, language: str):
        """Update user's preferred language (en/fa)."""
        with self._cursor() as cur:
            cur.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))

    def update_user_preferences(self, user_id: int, **kwargs):
        """
        Update user preferences (format, quality, limit).

        Only allowed fields are updated to prevent SQL injection.
        """
        allowed = {"preferred_format", "preferred_quality", "download_limit_per_day"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        with self._cursor() as cur:
            cur.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)

    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is currently banned."""
        with self._cursor() as cur:
            cur.execute("SELECT banned_until FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row or not row["banned_until"]:
                return False
            banned_until = datetime.fromisoformat(row["banned_until"])
            return datetime.now() < banned_until

    def ban_user(self, user_id: int, hours: int = 24):
        """
        Ban user for specified number of hours.

        Args:
            user_id: Telegram user ID
            hours: Duration of ban in hours (default: 24)
        """
        banned_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        with self._cursor() as cur:
            cur.execute("UPDATE users SET banned_until = ? WHERE user_id = ?", (banned_until, user_id))

    def is_admin(self, user_id: int) -> bool:
        """Check if user has admin privileges."""
        with self._cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return bool(row and row["is_admin"])

    def set_admin(self, user_id: int, is_admin: bool = True):
        """Grant or revoke admin privileges for a user."""
        with self._cursor() as cur:
            cur.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (is_admin, user_id))

    def get_daily_download_count(self, user_id: int) -> int:
        """Get number of downloads user has made today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM downloads WHERE user_id = ? AND DATE(request_time) = ?",
                (user_id, today),
            )
            return cur.fetchone()["cnt"]

    def can_download(self, user_id: int) -> bool:
        """
        Check if user is allowed to download.

        Returns False if:
        - User is banned
        - User doesn't exist
        - Daily download limit reached
        """
        if self.is_user_banned(user_id):
            return False
        user = self.get_user(user_id)
        if not user:
            return False
        count = self.get_daily_download_count(user_id)
        return count < user["download_limit_per_day"]

    # ==========================================
    # Download Management Methods
    # ==========================================

    def add_download(self, user_id: int, url: str, platform: str, selected_format: str) -> int:
        """
        Create a new download record.

        Returns:
            int: The download_id of the new record
        """
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO downloads (user_id, url, platform, selected_format, status)
                   VALUES (?, ?, ?, ?, 'queued')""",
                (user_id, url, platform, selected_format),
            )
            return cur.lastrowid

    def update_download(self, download_id: int, **kwargs):
        """
        Update download record fields.

        Only whitelisted fields can be updated for security.
        """
        allowed = {
            "media_type", "original_quality", "output_quality",
            "original_size_mb", "optimized_size_mb", "file_path",
            "status", "completion_time", "optimization_time_seconds",
            "error_message", "retry_count", "was_4k_detected",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [download_id]
        with self._cursor() as cur:
            cur.execute(f"UPDATE downloads SET {set_clause} WHERE download_id = ?", values)

    def increment_user_downloads(self, user_id: int, size_mb: float):
        """Increment user's total download count and size."""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET total_downloads = total_downloads + 1, total_size_downloaded = total_size_downloaded + ? WHERE user_id = ?",
                (size_mb, user_id),
            )

    # ==========================================
    # Queue Management Methods
    # ==========================================

    def add_to_queue(self, user_id: int, download_id: int, priority: int = 5) -> int:
        """
        Add a download to the processing queue.

        Args:
            user_id: User who requested the download
            download_id: The download record ID
            priority: Priority level (1=highest, 10=lowest)

        Returns:
            int: The queue_id of the new entry
        """
        with self._cursor() as cur:
            # Get next position in queue
            cur.execute(
                "SELECT MAX(position) as pos FROM download_queue WHERE status IN ('waiting', 'processing')",
            )
            row = cur.fetchone()
            next_pos = (row["pos"] or 0) + 1 if row else 1
            cur.execute(
                """INSERT INTO download_queue (user_id, download_id, priority, position, status)
                   VALUES (?, ?, ?, ?, 'waiting')""",
                (user_id, download_id, priority, next_pos),
            )
            return cur.lastrowid

    def get_next_queue_item(self) -> dict | None:
        """
        Get the next item to process from the queue.

        Items are processed by priority (lowest number = highest priority),
        then by position (FIFO within same priority).

        Returns:
            dict: Queue item with download details, or None if empty
        """
        with self._cursor() as cur:
            cur.execute(
                """SELECT q.*, d.url, d.selected_format, d.platform
                   FROM download_queue q
                   JOIN downloads d ON q.download_id = d.download_id
                   WHERE q.status = 'waiting'
                   ORDER BY q.priority ASC, q.position ASC
                   LIMIT 1"""
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_queue_status(self, queue_id: int, status: str):
        """
        Update queue item status.

        When status is 'processing', also records the start time.
        """
        with self._cursor() as cur:
            if status == "processing":
                cur.execute(
                    "UPDATE download_queue SET status = ?, start_time = CURRENT_TIMESTAMP WHERE queue_id = ?",
                    (status, queue_id),
                )
            else:
                cur.execute(
                    "UPDATE download_queue SET status = ? WHERE queue_id = ?",
                    (status, queue_id),
                )

    def get_user_queue_count(self, user_id: int) -> int:
        """Get number of items user has in queue (waiting or processing)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM download_queue WHERE user_id = ? AND status IN ('waiting', 'processing')",
                (user_id,),
            )
            return cur.fetchone()["cnt"]

    def get_user_position_in_queue(self, user_id: int) -> int:
        """Get user's position in the queue (how many items are ahead)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM download_queue WHERE status = 'waiting'",
            )
            row = cur.fetchone()
            return row["cnt"] if row else 0

    # ==========================================
    # Statistics & Analytics Methods
    # ==========================================

    def update_quality_stats(self, resolution: str, fmt: str, file_size_mb: float, opt_time: float):
        """
        Update quality statistics with new data point.

        Uses running averages to track optimization performance.
        """
        with self._cursor() as cur:
            cur.execute(
                "SELECT stat_id, count, avg_file_size_mb, avg_optimization_time_seconds FROM quality_stats WHERE resolution = ? AND format = ?",
                (resolution, fmt),
            )
            row = cur.fetchone()
            if row:
                # Update running averages
                new_count = row["count"] + 1
                new_avg_size = ((row["avg_file_size_mb"] or 0) * row["count"] + file_size_mb) / new_count
                new_avg_time = ((row["avg_optimization_time_seconds"] or 0) * row["count"] + opt_time) / new_count
                cur.execute(
                    "UPDATE quality_stats SET count = ?, avg_file_size_mb = ?, avg_optimization_time_seconds = ?, last_used = CURRENT_TIMESTAMP WHERE stat_id = ?",
                    (new_count, new_avg_size, new_avg_time, row["stat_id"]),
                )
            else:
                # Insert new stat record
                cur.execute(
                    "INSERT INTO quality_stats (resolution, format, count, avg_file_size_mb, avg_optimization_time_seconds) VALUES (?, ?, 1, ?, ?)",
                    (resolution, fmt, file_size_mb, opt_time),
                )

    def get_bot_stats(self) -> dict:
        """
        Get comprehensive bot statistics for admin dashboard.

        Returns:
            dict: Statistics including user counts, download totals,
                  success rates, format distribution, and queue status
        """
        with self._cursor() as cur:
            stats = {}

            # Total active users
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active = 1")
            stats["total_users"] = cur.fetchone()["cnt"]

            # Total downloads
            cur.execute("SELECT COUNT(*) as cnt FROM downloads")
            stats["total_downloads"] = cur.fetchone()["cnt"]

            # Total data downloaded (in GB)
            cur.execute("SELECT COALESCE(SUM(total_size_downloaded), 0) as total FROM users")
            stats["total_size_gb"] = round(cur.fetchone()["total"] / 1024, 2)

            # Success rate
            cur.execute("SELECT COUNT(*) as cnt FROM downloads WHERE status = 'completed'")
            completed = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM downloads")
            total = cur.fetchone()["cnt"]
            stats["success_rate"] = round((completed / total * 100) if total > 0 else 0, 1)

            # Active queue items
            cur.execute("SELECT COUNT(*) as cnt FROM download_queue WHERE status IN ('waiting', 'processing')")
            stats["active_queue"] = cur.fetchone()["cnt"]

            # Format distribution
            cur.execute("SELECT selected_format, COUNT(*) as cnt FROM downloads WHERE status = 'completed' GROUP BY selected_format")
            stats["format_stats"] = {row["selected_format"]: row["cnt"] for row in cur.fetchall()}

            # Quality distribution
            cur.execute("SELECT output_quality, COUNT(*) as cnt FROM downloads WHERE status = 'completed' GROUP BY output_quality")
            stats["quality_stats"] = {row["output_quality"]: row["cnt"] for row in cur.fetchall()}

            # 4K blocked count
            cur.execute("SELECT COUNT(*) as cnt FROM downloads WHERE was_4k_detected = 1")
            stats["blocked_4k"] = cur.fetchone()["cnt"]

            return stats

    def get_user_stats(self, user_id: int) -> dict:
        """
        Get stats for a specific user.

        Returns:
            dict: User data including today's download count
        """
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            if not user:
                return {}
            cur.execute(
                "SELECT COUNT(*) as cnt FROM downloads WHERE user_id = ? AND DATE(request_time) = DATE('now')",
                (user_id,),
            )
            today_downloads = cur.fetchone()["cnt"]
            return {
                **dict(user),
                "today_downloads": today_downloads,
            }
