import os
import asyncio
import logging
import time
from datetime import datetime

from bot.config import Config
from bot.database import Database
from bot.services.downloader import Downloader
from bot.services.optimizer import QualityOptimizer
from bot.utils.helpers import format_size, format_time

logger = logging.getLogger(__name__)


class QueueWorker:
    def __init__(self, app):
        self.app = app
        self.db = Database()
        self.downloader = Downloader()
        self.optimizer = QualityOptimizer()
        self.running = False
        self.current_task = None

    async def start(self):
        self.running = True
        asyncio.create_task(self._process_loop())

    async def stop(self):
        self.running = False

    async def _process_loop(self):
        while self.running:
            try:
                item = self.db.get_next_queue_item()
                if item:
                    await self._process_item(item)
                else:
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Queue loop error: {e}")
                await asyncio.sleep(5)

    async def _process_item(self, item: dict):
        queue_id = item["queue_id"]
        download_id = item["download_id"]
        user_id = item["user_id"]
        url = item["url"]
        format_type = item["selected_format"]

        self.db.update_queue_status(queue_id, "processing")
        self.db.update_download(download_id, status="downloading")
        self.current_task = item

        try:
            await self._send_progress(user_id, "🔄 Starting download...", lang=self._get_user_lang(user_id))

            file_path, info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.downloader.download(url, format_type)
            )

            original_size = os.path.getsize(file_path)
            self.db.update_download(
                download_id,
                status="optimizing",
                original_size_mb=round(original_size / (1024 * 1024), 2),
                original_quality=f"{info.get('height', 'audio')}p",
            )

            optimized_path = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.optimizer.optimize(file_path, format_type)
            )

            optimized_size = os.path.getsize(optimized_path)
            opt_time = 0

            self.db.update_download(
                download_id,
                status="uploading",
                optimized_size_mb=round(optimized_size / (1024 * 1024), 2),
                file_path=optimized_path,
                output_quality=self._get_quality_label(optimized_path, info),
            )

            await self._send_to_user(user_id, optimized_path, info, format_type, original_size, optimized_size)

            self.db.update_download(
                download_id,
                status="completed",
                completion_time=datetime.now().isoformat(),
            )
            self.db.increment_user_downloads(user_id, round(optimized_size / (1024 * 1024), 2))
            self.db.update_queue_status(queue_id, "completed")

            self._cleanup(file_path, optimized_path)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.db.update_download(download_id, status="failed", error_message=str(e))
            self.db.update_queue_status(queue_id, "failed")
            lang = self._get_user_lang(user_id)
            await self._send_error(user_id, str(e), lang)
            self._cleanup_files(item)

        finally:
            self.current_task = None

    async def _send_to_user(self, user_id: int, file_path: str, info: dict, format_type: str, original_size: int, optimized_size: int):
        lang = self._get_user_lang(user_id)
        title = info.get("title", "media")
        duration = info.get("duration", 0)
        resolution = f"{info.get('width', 0)}x{info.get('height', 0)}"

        from bot.utils.messages import get_message

        caption = get_message(lang, "complete",
            title=title,
            original=format_size(original_size),
            optimized=format_size(optimized_size),
            resolution=resolution,
            audio="AAC 128kbps" if format_type in ("mp4", "mkv") else format_type.upper(),
            time=format_time(duration),
        )

        try:
            if format_type in ("mp3", "m4a"):
                with open(file_path, "rb") as f:
                    await self.app.bot.send_audio(
                        user_id, f,
                        title=title,
                        caption=caption[:1024],
                    )
            else:
                with open(file_path, "rb") as f:
                    await self.app.bot.send_video(
                        user_id, f,
                        caption=caption[:1024],
                        supports_streaming=True,
                    )
        except Exception as e:
            logger.error(f"Send failed: {e}")
            with open(file_path, "rb") as f:
                await self.app.bot.send_document(user_id, f, caption=caption[:1024])

    async def _send_progress(self, user_id: int, text: str, lang: str = "en"):
        try:
            await self.app.bot.send_message(user_id, text)
        except Exception:
            pass

    async def _send_error(self, user_id: int, error: str, lang: str = "en"):
        from bot.utils.messages import get_message
        try:
            await self.app.bot.send_message(user_id, get_message(lang, "error", error=error[:500]))
        except Exception:
            pass

    def _get_user_lang(self, user_id: int) -> str:
        user = self.db.get_user(user_id)
        return user.get("language", "en") if user else "en"

    def _get_quality_label(self, file_path: str, info: dict) -> str:
        height = info.get("height", 0)
        if height >= 1080:
            return "1080p"
        elif height >= 720:
            return "720p"
        elif height >= 480:
            return "480p"
        return "audio"

    def _cleanup(self, *files):
        for f in files:
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

    def _cleanup_files(self, item: dict):
        try:
            download_id = item.get("download_id")
            if download_id:
                download = self.db.get_user(item["user_id"])
                file_path = item.get("file_path")
                if file_path:
                    self._cleanup(file_path)
        except Exception:
            pass
