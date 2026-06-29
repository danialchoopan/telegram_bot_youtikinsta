"""
==========================================
  Queue Worker Service
==========================================

Background worker that processes download queue items.
Sends ONE message per download that gets edited with real-time progress.

Progress stages:
    📥 Downloading... 45% (1.2MB/2.6MB)
    🔄 Optimizing for Telegram...
    📤 Uploading... 78%
    ✅ Done! (original: 2.6GB -> optimized: 1.1GB)
"""

import os
import asyncio
import logging
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
        """Start the background processing loop."""
        self.running = True
        self._loop = asyncio.get_event_loop()
        asyncio.create_task(self._process_loop())

    async def stop(self):
        self.running = False

    async def _process_loop(self):
        """Main loop: process queue items and clean up temp files periodically."""
        cleanup_counter = 0
        while self.running:
            try:
                # Clean temp files every 60 iterations (~2 minutes)
                cleanup_counter += 1
                if cleanup_counter >= 60:
                    cleanup_counter = 0
                    self._cleanup_old_files()

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
        lang = self._get_user_lang(user_id)

        self.db.update_queue_status(queue_id, "processing")
        self.db.update_download(download_id, status="downloading")
        self.current_task = item

        # Send ONE initial message, we'll edit it with progress
        progress_msg = await self._safe_send(user_id, "📥 Preparing download...")
        msg_id = progress_msg.message_id if progress_msg else None

        try:
            # Stage 1: Download with progress hook
            download_progress = {"msg_id": msg_id, "user_id": user_id, "lang": lang}

            file_path, info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.downloader.download(
                    url, format_type,
                    progress_callback=lambda d: self._on_download_progress(d, download_progress)
                )
            )

            # Update message: downloading done
            if msg_id:
                await self._safe_edit(user_id, msg_id, "🔄 Optimizing for Telegram...")

            # Record original file size
            original_size = os.path.getsize(file_path)
            height = info.get("height")
            quality_label = f"{height}p" if height else "audio"
            self.db.update_download(
                download_id, status="optimizing",
                original_size_mb=round(original_size / (1024 * 1024), 2),
                original_quality=quality_label,
            )

            # Stage 2: Optimize
            optimized_path = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.optimizer.optimize(file_path, format_type)
            )

            optimized_size = os.path.getsize(optimized_path)

            # Update message: optimizing done
            if msg_id:
                await self._safe_edit(user_id, msg_id, "📤 Uploading to Telegram...")

            # Stage 3: Upload
            self.db.update_download(
                download_id, status="uploading",
                optimized_size_mb=round(optimized_size / (1024 * 1024), 2),
                file_path=optimized_path,
                output_quality=self._get_quality_label(optimized_path, info),
            )

            await self._send_file(user_id, optimized_path, info, format_type, original_size, optimized_size)

            # Update message: done
            if msg_id:
                reduction = round((1 - optimized_size / original_size) * 100, 1) if original_size > 0 else 0
                title = info.get("title", "media")[:30]
                done_text = (
                    f"✅ Done!\n\n"
                    f"📁 {title}\n"
                    f"📦 {format_size(original_size)} → {format_size(optimized_size)} ({reduction}% smaller)\n"
                    f"🎥 {self._get_quality_label(optimized_path, info)}"
                )
                await self._safe_edit(user_id, msg_id, done_text)

            # Stage 4: Update records
            self.db.update_download(download_id, status="completed", completion_time=datetime.now().isoformat())
            self.db.increment_user_downloads(user_id, round(optimized_size / (1024 * 1024), 2))
            self.db.update_queue_status(queue_id, "completed")

            # Stage 5: Cleanup
            self._cleanup(file_path, optimized_path)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            self.db.update_download(download_id, status="failed", error_message=str(e))
            self.db.update_queue_status(queue_id, "failed")
            if msg_id:
                await self._safe_edit(user_id, msg_id, f"❌ Error: {str(e)[:200]}")
            else:
                await self._safe_send(user_id, f"❌ Error: {str(e)[:200]}")
            self._cleanup_files(item)

        finally:
            self.current_task = None

    def _on_download_progress(self, data: dict, ctx: dict):
        """Update progress message during download (runs in thread)."""
        if data["stage"] != "downloading":
            return

        msg_id = ctx.get("msg_id")
        if not msg_id:
            return

        total = data.get("total", 0)
        current = data.get("current", 0)
        speed = data.get("speed", 0)

        if total > 0:
            pct = round(current / total * 100, 1)
            speed_mb = round(speed / (1024 * 1024), 1) if speed else 0
            text = f"📥 Downloading... {pct}%\n{format_size(current)} / {format_size(total)}\n⚡ {speed_mb} MB/s"

            # Use stored loop reference (safe from worker thread)
            if hasattr(self, '_loop') and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._safe_edit(ctx["user_id"], msg_id, text),
                    self._loop,
                )

    async def _send_file(self, user_id: int, file_path: str, info: dict, format_type: str, original_size: int, optimized_size: int):
        """Send the file to user with long timeout."""
        title = info.get("title", "media")
        timeout = {"read_timeout": 300, "write_timeout": 300, "connect_timeout": 30}

        try:
            if format_type in ("mp3", "m4a"):
                with open(file_path, "rb") as f:
                    await self.app.bot.send_audio(user_id, f, title=title, **timeout)
            else:
                with open(file_path, "rb") as f:
                    await self.app.bot.send_video(user_id, f, supports_streaming=True, **timeout)
        except Exception as e:
            logger.error(f"Send failed: {e}, trying document fallback")
            with open(file_path, "rb") as f:
                await self.app.bot.send_document(user_id, f, read_timeout=300, write_timeout=300)

    async def _safe_send(self, user_id: int, text: str):
        """Send message, return message object or None."""
        try:
            return await self.app.bot.send_message(user_id, text)
        except Exception:
            return None

    async def _safe_edit(self, user_id: int, msg_id: int, text: str):
        """Edit message, silently ignore if fails."""
        try:
            await self.app.bot.edit_message_text(text, user_id, msg_id)
        except Exception:
            pass

    def _get_user_lang(self, user_id: int) -> str:
        user = self.db.get_user(user_id)
        return user.get("language", "en") if user else "en"

    def _get_quality_label(self, file_path: str, info: dict) -> str:
        height = info.get("height") or 0
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
            file_path = item.get("file_path")
            if file_path:
                self._cleanup(file_path)
        except Exception:
            pass

    def _cleanup_old_files(self):
        """Remove files older than 30 minutes from temp directories."""
        import time
        now = time.time()
        max_age = 30 * 60  # 30 minutes

        for dir_path in [Config.DOWNLOAD_PATH, Config.OPTIMIZED_PATH]:
            try:
                if not dir_path.exists():
                    continue
                for f in dir_path.iterdir():
                    if f.is_file() and f.suffix != ".gitkeep":
                        if now - f.stat().st_mtime > max_age:
                            f.unlink()
                            logger.info(f"Cleaned old file: {f.name}")
            except Exception as e:
                logger.error(f"Cleanup error in {dir_path}: {e}")
