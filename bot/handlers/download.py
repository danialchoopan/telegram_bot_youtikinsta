import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

from bot.config import Config
from bot.database import Database
from bot.services.analyzer import MediaAnalyzer
from bot.utils.helpers import is_valid_url, detect_platform, format_size, format_duration, is_playlist_url
from bot.utils.messages import get_message


analyzer = MediaAnalyzer()


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)

    if not db.can_download(user.id):
        lang = db.get_user(user.id).get("language", "en") if db.get_user(user.id) else "en"
        user_data = db.get_user(user.id)
        used = db.get_daily_download_count(user.id)
        limit = user_data.get("download_limit_per_day", 10) if user_data else 10
        await update.message.reply_text(get_message(lang, "rate_limit", used=used, limit=limit))
        return

    if db.get_user_queue_count(user.id) >= Config.MAX_CONCURRENT_QUEUED_PER_USER:
        lang = db.get_user(user.id).get("language", "en") if db.get_user(user.id) else "en"
        await update.message.reply_text(get_message(lang, "queue_full"))
        return

    url = update.message.text.strip()

    if not is_valid_url(url):
        lang = db.get_user(user.id).get("language", "en") if db.get_user(user.id) else "en"
        await update.message.reply_text(get_message(lang, "invalid_url"))
        return

    if is_playlist_url(url) and not Config.ENABLE_PLAYLIST_SUPPORT:
        lang = db.get_user(user.id).get("language", "en") if db.get_user(user.id) else "en"
        await update.message.reply_text("⚠️ Playlist support is disabled.")
        return

    platform = detect_platform(url)
    user_data = db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    await update.message.reply_text(get_message(lang, "analyzing", platform=platform.title()))

    try:
        info = await asyncio.get_event_loop().run_in_executor(None, analyzer.get_info, url)
    except ValueError as e:
        await update.message.reply_text(get_message(lang, "error", error=str(e)))
        return

    if info["is_4k"] and Config.ENABLE_4K_BLOCKING:
        keyboard = [
            [
                InlineKeyboardButton("1080p", callback_data=f"dl_{url}|mp4"),
                InlineKeyboardButton("720p", callback_data=f"dl_{url}|mp4_720"),
            ],
            [
                InlineKeyboardButton("🎵 MP3", callback_data=f"dl_{url}|mp3"),
                InlineKeyboardButton("🎶 M4A", callback_data=f"dl_{url}|m4a"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(get_message(lang, "blocked_4k"), reply_markup=reply_markup)
        return

    title = info["title"][:50]
    duration = format_duration(info["duration"]) if info["duration"] else "N/A"
    size = format_size(info["original_size"]) if info["original_size"] else "N/A"

    keyboard = []
    row = []
    for fmt_key, fmt_label in info["formats_available"]:
        row.append(InlineKeyboardButton(fmt_label, callback_data=f"dl_{url}|{fmt_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_message(lang, "select_format", title=title, duration=duration, size=size),
        reply_markup=reply_markup,
    )


async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.replace("dl_", "")
    url, format_type = data.rsplit("|", 1)

    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    format_names = {
        "mp4": "MP4 (H.264)",
        "mkv": "MKV",
        "mp3": "MP3",
        "m4a": "M4A",
        "mp4_720": "MP4 720p",
        "best": "Best for Telegram",
    }
    format_name = format_names.get(format_type, format_type)
    await query.edit_message_text(get_message(lang, "format_selected", format=format_name, codec="H.264", quality="1080p"))

    platform = detect_platform(url)
    download_id = db.add_download(user_id, url, platform, format_type)
    queue_id = db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)

    queue_pos = db.get_user_position_in_queue(user_id)
    await query.message.reply_text(
        get_message(lang, "queue_added", position=queue_pos, minutes=queue_pos * 2)
    )


def get_handlers():
    return [
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url),
        CallbackQueryHandler(format_callback, pattern=r"^dl_"),
    ]
