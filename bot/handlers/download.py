"""
==========================================
  Download Handler Module
==========================================

Handles URL submissions and format selection.
Uses short IDs in callback_data to avoid Telegram's 64-byte limit.

URLs are stored in a dict with short IDs:
    dl_abc123 -> {"url": "https://...", "platform": "tiktok"}
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

from bot.config import Config
from bot.database import Database
from bot.services.analyzer import MediaAnalyzer
from bot.utils.helpers import is_valid_url, detect_platform, format_size, format_duration, is_playlist_url, generate_random_string
from bot.utils.messages import get_message

analyzer = MediaAnalyzer()

# Store URLs by short ID (in-memory, lives for bot session)
_url_store = {}


def _store_url(url: str, platform: str, title: str = "") -> str:
    """Store URL and return short ID."""
    short_id = generate_random_string(8)
    _url_store[short_id] = {"url": url, "platform": platform, "title": title}
    return short_id


def _get_url(short_id: str) -> dict | None:
    """Retrieve URL info by short ID."""
    return _url_store.get(short_id)


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming URL messages."""
    db = Database()
    user = update.effective_user

    db.get_or_create_user(user.id, user.username, user.full_name)

    user_data = db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Whitelist check
    if not db.can_use_bot(user.id):
        await update.message.reply_text("⛔ Access denied. You are not whitelisted.")
        return

    # Rate limit check
    if not db.can_download(user.id):
        used = db.get_daily_download_count(user.id)
        limit = user_data.get("download_limit_per_day", 10) if user_data else 10
        await update.message.reply_text(get_message(lang, "rate_limit", used=used, limit=limit))
        return

    # Queue limit check
    if db.get_user_queue_count(user.id) >= Config.MAX_CONCURRENT_QUEUED_PER_USER:
        await update.message.reply_text(get_message(lang, "queue_full"))
        return

    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text(get_message(lang, "invalid_url"))
        return

    # Handle playlists
    if is_playlist_url(url):
        if not Config.ENABLE_PLAYLIST_SUPPORT:
            await update.message.reply_text("⚠️ Playlist support is disabled.")
            return
        await handle_playlist(update, context, url, lang, db)
        return

    platform = detect_platform(url)

    # Show analyzing message
    await update.message.reply_text(get_message(lang, "analyzing", platform=platform.title()))

    # Analyze media
    try:
        info = await asyncio.get_event_loop().run_in_executor(None, analyzer.get_info, url)
    except Exception as e:
        await update.message.reply_text(get_message(lang, "error", error=str(e)[:300]))
        return

    # Store URL with short ID and title
    short_id = _store_url(url, platform, info.get("title", ""))

    # Handle 4K content
    if info["is_4k"] and Config.ENABLE_4K_BLOCKING:
        keyboard = [
            [InlineKeyboardButton("1080p", callback_data=f"dl_{short_id}|mp4"),
             InlineKeyboardButton("720p", callback_data=f"dl_{short_id}|mp4_720")],
            [InlineKeyboardButton("🎵 MP3", callback_data=f"dl_{short_id}|mp3"),
             InlineKeyboardButton("🎶 M4A", callback_data=f"dl_{short_id}|m4a")],
        ]
        await update.message.reply_text(get_message(lang, "blocked_4k"), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Build format selection keyboard
    title = info["title"][:50]
    duration = format_duration(info["duration"]) if info["duration"] else "N/A"
    size = format_size(info["original_size"]) if info["original_size"] else "N/A"

    keyboard = []
    row = []
    for fmt_key, fmt_label in info["formats_available"]:
        row.append(InlineKeyboardButton(fmt_label, callback_data=f"dl_{short_id}|{fmt_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        get_message(lang, "select_format", title=title, duration=duration, size=size),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, lang: str, db: Database):
    """Handle playlist URLs."""
    await update.message.reply_text(get_message(lang, "analyzing", platform="Playlist"))

    try:
        info = await asyncio.get_event_loop().run_in_executor(None, analyzer.get_info, url)
        title = info.get("title", "Unknown Playlist")
        video_count = len(info.get("formats", [])) or 1

        short_id = _store_url(url, "youtube", info.get("title", ""))

        keyboard = [
            [InlineKeyboardButton("📹 MP4 All", callback_data=f"pl_{short_id}|mp4"),
             InlineKeyboardButton("🎵 MP3 All", callback_data=f"pl_{short_id}|mp3")],
            [InlineKeyboardButton("❌ Cancel", callback_data="pl_cancel")],
        ]

        await update.message.reply_text(
            f"🎬 Playlist: {title}\n📊 {video_count} items\n\n🎯 Format for all:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        await update.message.reply_text(get_message(lang, "error", error=str(e)[:300]))


async def playlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle playlist format selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "pl_cancel":
        await query.edit_message_text("❌ Cancelled.")
        return

    data = query.data[3:]  # Skip "pl_"
    short_id, format_type = data.rsplit("|", 1)

    url_info = _get_url(short_id)
    if not url_info:
        await query.edit_message_text("❌ Session expired. Send the link again.")
        return

    db = Database()
    user_id = query.from_user.id
    platform = url_info["platform"]
    url = url_info["url"]

    download_id = db.add_download(user_id, url, platform, format_type, title=url_info.get("title", ""))
    db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)
    queue_pos = db.get_user_position_in_queue(user_id)

    format_names = {"mp4": "MP4", "mp3": "MP3", "m4a": "M4A"}
    await query.edit_message_text(
        f"✅ Playlist queued as {format_names.get(format_type, format_type)}\n"
        f"📊 Position: #{queue_pos}\n⏱️ ~{queue_pos * 5} min"
    )


async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle format selection callback."""
    query = update.callback_query
    await query.answer()

    data = query.data[3:]  # Skip "dl_"
    short_id, format_type = data.rsplit("|", 1)

    url_info = _get_url(short_id)
    if not url_info:
        await query.edit_message_text("❌ Session expired. Send the link again.")
        return

    db = Database()
    user_id = query.from_user.id
    lang = (db.get_user(user_id) or {}).get("language", "en")
    platform = url_info["platform"]
    url = url_info["url"]

    # MKV compatibility warning
    if format_type == "mkv":
        keyboard = [
            [InlineKeyboardButton("Continue MKV", callback_data=f"dl_{short_id}|mkv_go"),
             InlineKeyboardButton("Switch to MP4", callback_data=f"dl_{short_id}|mp4")],
        ]
        await query.edit_message_text(
            "⚠️ MKV may not play on all devices.\nContinue?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if format_type == "mkv_go":
        format_type = "mkv"

    # Confirm and queue
    format_names = {
        "mp4": "MP4 (H.264)", "mkv": "MKV", "mp3": "MP3",
        "m4a": "M4A", "mp4_720": "MP4 720p", "best": "Full Quality",
    }
    format_name = format_names.get(format_type, format_type)

    download_id = db.add_download(user_id, url, platform, format_type, title=url_info.get("title", ""))
    db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)
    queue_pos = db.get_user_position_in_queue(user_id)

    await query.edit_message_text(
        f"✅ {format_name} selected\n"
        f"📊 Queue position: #{queue_pos}\n"
        f"⏱️ ~{queue_pos * 2} min"
    )


def get_handlers():
    return [
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url),
        CallbackQueryHandler(format_callback, pattern=r"^dl_"),
        CallbackQueryHandler(playlist_callback, pattern=r"^pl_"),
    ]
