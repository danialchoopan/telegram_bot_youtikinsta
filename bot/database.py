import sqlite3
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager

from bot.config import Config


class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        Config.ensure_directories()
        self.db_path = str(Config.DB_PATH)
        self._local = threading.local()
        self._create_tables()

    def _get_conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _create_tables(self):
        with self._cursor() as cur:
            cur.executescript("""
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

    def get_or_create_user(self, user_id: int, username: str = None, full_name: str = None) -> dict:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE users SET last_activity = CURRENT_TIMESTAMP, username = ?, full_name = ? WHERE user_id = ?",
                    (username, full_name, user_id),
                )
                return dict(row)
            cur.execute(
                "INSERT INTO users (user_id, username, full_name, last_activity) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, username, full_name),
            )
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return dict(cur.fetchone())

    def get_user(self, user_id: int) -> dict | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_user_language(self, user_id: int, language: str):
        with self._cursor() as cur:
            cur.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))

    def update_user_preferences(self, user_id: int, **kwargs):
        allowed = {"preferred_format", "preferred_quality", "download_limit_per_day"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        with self._cursor() as cur:
            cur.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)

    def is_user_banned(self, user_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT banned_until FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row or not row["banned_until"]:
                return False
            banned_until = datetime.fromisoformat(row["banned_until"])
            return datetime.now() < banned_until

    def ban_user(self, user_id: int, hours: int = 24):
        banned_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        with self._cursor() as cur:
            cur.execute("UPDATE users SET banned_until = ? WHERE user_id = ?", (banned_until, user_id))

    def is_admin(self, user_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return bool(row and row["is_admin"])

    def set_admin(self, user_id: int, is_admin: bool = True):
        with self._cursor() as cur:
            cur.execute("UPDATE users SET is_admin = ? WHERE user_id = ?", (is_admin, user_id))

    def get_daily_download_count(self, user_id: int) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM downloads WHERE user_id = ? AND DATE(request_time) = ?",
                (user_id, today),
            )
            return cur.fetchone()["cnt"]

    def can_download(self, user_id: int) -> bool:
        if self.is_user_banned(user_id):
            return False
        user = self.get_user(user_id)
        if not user:
            return False
        count = self.get_daily_download_count(user_id)
        return count < user["download_limit_per_day"]

    def add_download(self, user_id: int, url: str, platform: str, selected_format: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO downloads (user_id, url, platform, selected_format, status)
                   VALUES (?, ?, ?, ?, 'queued')""",
                (user_id, url, platform, selected_format),
            )
            return cur.lastrowid

    def update_download(self, download_id: int, **kwargs):
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
        with self._cursor() as cur:
            cur.execute(
                "UPDATE users SET total_downloads = total_downloads + 1, total_size_downloaded = total_size_downloaded + ? WHERE user_id = ?",
                (size_mb, user_id),
            )

    def add_to_queue(self, user_id: int, download_id: int, priority: int = 5) -> int:
        with self._cursor() as cur:
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
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM download_queue WHERE user_id = ? AND status IN ('waiting', 'processing')",
                (user_id,),
            )
            return cur.fetchone()["cnt"]

    def get_queue_position(self, queue_id: int) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT position FROM download_queue WHERE queue_id = ?", (queue_id,)
            )
            row = cur.fetchone()
            return row["position"] if row else 0

    def get_user_position_in_queue(self, user_id: int) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM download_queue WHERE status = 'waiting'",
            )
            row = cur.fetchone()
            return row["cnt"] if row else 0

    def update_quality_stats(self, resolution: str, fmt: str, file_size_mb: float, opt_time: float):
        with self._cursor() as cur:
            cur.execute(
                "SELECT stat_id, count, avg_file_size_mb, avg_optimization_time_seconds FROM quality_stats WHERE resolution = ? AND format = ?",
                (resolution, fmt),
            )
            row = cur.fetchone()
            if row:
                new_count = row["count"] + 1
                new_avg_size = ((row["avg_file_size_mb"] or 0) * row["count"] + file_size_mb) / new_count
                new_avg_time = ((row["avg_optimization_time_seconds"] or 0) * row["count"] + opt_time) / new_count
                cur.execute(
                    "UPDATE quality_stats SET count = ?, avg_file_size_mb = ?, avg_optimization_time_seconds = ?, last_used = CURRENT_TIMESTAMP WHERE stat_id = ?",
                    (new_count, new_avg_size, new_avg_time, row["stat_id"]),
                )
            else:
                cur.execute(
                    "INSERT INTO quality_stats (resolution, format, count, avg_file_size_mb, avg_optimization_time_seconds) VALUES (?, ?, 1, ?, ?)",
                    (resolution, fmt, file_size_mb, opt_time),
                )

    def get_bot_stats(self) -> dict:
        with self._cursor() as cur:
            stats = {}
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active = 1")
            stats["total_users"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM downloads")
            stats["total_downloads"] = cur.fetchone()["cnt"]
            cur.execute("SELECT COALESCE(SUM(total_size_downloaded), 0) as total FROM users")
            stats["total_size_gb"] = round(cur.fetchone()["total"] / 1024, 2)
            cur.execute("SELECT COUNT(*) as cnt FROM downloads WHERE status = 'completed'")
            completed = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM downloads")
            total = cur.fetchone()["cnt"]
            stats["success_rate"] = round((completed / total * 100) if total > 0 else 0, 1)
            cur.execute("SELECT COUNT(*) as cnt FROM download_queue WHERE status IN ('waiting', 'processing')")
            stats["active_queue"] = cur.fetchone()["cnt"]
            cur.execute("SELECT selected_format, COUNT(*) as cnt FROM downloads WHERE status = 'completed' GROUP BY selected_format")
            stats["format_stats"] = {row["selected_format"]: row["cnt"] for row in cur.fetchall()}
            cur.execute("SELECT output_quality, COUNT(*) as cnt FROM downloads WHERE status = 'completed' GROUP BY output_quality")
            stats["quality_stats"] = {row["output_quality"]: row["cnt"] for row in cur.fetchall()}
            cur.execute("SELECT COUNT(*) as cnt FROM downloads WHERE was_4k_detected = 1")
            stats["blocked_4k"] = cur.fetchone()["cnt"]
            return stats

    def get_user_stats(self, user_id: int) -> dict:
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
