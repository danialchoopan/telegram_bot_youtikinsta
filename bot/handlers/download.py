"""
==========================================
  Download Handler Module
==========================================

Handles URL submissions and format selection for media downloads.
This is the core handler that processes user download requests.

Flow:
    1. User sends a URL (YouTube, Instagram, TikTok, or direct link)
    2. Bot validates the URL and checks user limits
    3. Bot analyzes the media (resolution, duration, size)
    4. If 4K content, shows warning with lower quality options
    5. If playlist, shows batch download options
    6. Otherwise, shows format selection keyboard
    7. User selects format (MP4/MKV/MP3/M4A/Best)
    8. Download is added to queue for processing

Handlers:
    - Text message handler: Detects URLs and initiates download flow
    - dl_* callback: Handles format selection
    - playlist_* callback: Handles playlist batch operations
    - warn_* callback: Handles format compatibility warnings
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters

from bot.config import Config
from bot.database import Database
from bot.services.analyzer import MediaAnalyzer
from bot.utils.helpers import is_valid_url, detect_platform, format_size, format_duration, is_playlist_url
from bot.utils.messages import get_message

# Initialize media analyzer (reusable across requests)
analyzer = MediaAnalyzer()


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming URL messages.

    Validates the URL, checks user limits, analyzes media,
    and shows format selection options.
    """
    db = Database()
    user = update.effective_user

    # Register user if first time
    db.get_or_create_user(user.id, user.username, user.full_name)

    # Get user's language preference
    user_data = db.get_user(user.id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Check whitelist
    if not db.can_use_bot(user.id):
        await update.message.reply_text("⛔ Access denied. You are not whitelisted.\nAsk admin to add you.")
        return

    # Check if user can download (not banned, within daily limit)
    if not db.can_download(user.id):
        used = db.get_daily_download_count(user.id)
        limit = user_data.get("download_limit_per_day", 10) if user_data else 10
        await update.message.reply_text(get_message(lang, "rate_limit", used=used, limit=limit))
        return

    # Check if user has too many items in queue
    if db.get_user_queue_count(user.id) >= Config.MAX_CONCURRENT_QUEUED_PER_USER:
        await update.message.reply_text(get_message(lang, "queue_full"))
        return

    url = update.message.text.strip()

    # Validate URL format
    if not is_valid_url(url):
        await update.message.reply_text(get_message(lang, "invalid_url"))
        return

    # Handle playlist URLs
    if is_playlist_url(url):
        if not Config.ENABLE_PLAYLIST_SUPPORT:
            await update.message.reply_text("⚠️ Playlist support is disabled.")
            return
        await handle_playlist(update, context, url, lang, db)
        return

    # Detect platform (YouTube, Instagram, TikTok, etc.)
    platform = detect_platform(url)

    # Show analyzing message
    await update.message.reply_text(get_message(lang, "analyzing", platform=platform.title()))

    # Analyze media in background thread (non-blocking)
    try:
        info = await asyncio.get_event_loop().run_in_executor(None, analyzer.get_info, url)
    except ValueError as e:
        await update.message.reply_text(get_message(lang, "error", error=str(e)))
        return

    # Handle 4K content - show warning with lower quality options
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

    # Build format selection keyboard
    title = info["title"][:50]
    duration = format_duration(info["duration"]) if info["duration"] else "N/A"
    size = format_size(info["original_size"]) if info["original_size"] else "N/A"

    # Create keyboard rows with format options
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

    # Show media info and format options
    await update.message.reply_text(
        get_message(lang, "select_format", title=title, duration=duration, size=size),
        reply_markup=reply_markup,
    )


async def handle_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, lang: str, db: Database):
    """
    Handle playlist URLs with batch download options.

    Shows playlist info and format selection for batch download.
    """
    user_id = update.effective_user.id

    # Show analyzing message
    await update.message.reply_text(get_message(lang, "analyzing", platform="Playlist"))

    try:
        # Get playlist info
        info = await asyncio.get_event_loop().run_in_executor(None, analyzer.get_info, url)

        # For playlists, we get basic info
        title = info.get("title", "Unknown Playlist")
        video_count = len(info.get("formats", [])) or 1

        # Show playlist options
        keyboard = [
            [
                InlineKeyboardButton("📹 MP4 All", callback_data=f"pl_{url}|mp4"),
                InlineKeyboardButton("🎵 MP3 All", callback_data=f"pl_{url}|mp3"),
            ],
            [
                InlineKeyboardButton("🎶 M4A All", callback_data=f"pl_{url}|m4a"),
            ],
            [
                InlineKeyboardButton("❌ Cancel", callback_data="pl_cancel"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        msg = f"""🎬 Playlist detected: {title}
📊 {video_count} items found

🎯 Format for all items:"""

        await update.message.reply_text(msg, reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(get_message(lang, "error", error=str(e)))


async def playlist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle playlist format selection.

    Adds all playlist items to the queue.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "pl_cancel":
        await query.edit_message_text("❌ Playlist download cancelled.")
        return

    # Parse callback data: "pl_{url}|{format}"
    data = query.data[3:]  # Skip "pl_" prefix only
    url, format_type = data.rsplit("|", 1)

    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Add playlist items to queue
    platform = detect_platform(url)
    download_id = db.add_download(user_id, url, platform, format_type)
    queue_id = db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)

    queue_pos = db.get_user_position_in_queue(user_id)

    # Confirm playlist download
    format_names = {"mp4": "MP4", "mp3": "MP3", "m4a": "M4A"}
    format_name = format_names.get(format_type, format_type)

    await query.edit_message_text(
        f"✅ Playlist added to queue with {format_name}\n"
        f"📊 Position: #{queue_pos}\n"
        f"⏱️ Estimated wait: ~{queue_pos * 5} min\n\n"
        f"Items will be processed one by one."
    )


async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle format selection callback.

    Creates download and queue records, then informs user of queue position.
    Shows format compatibility warning for MKV.
    """
    query = update.callback_query
    await query.answer()

    # Parse callback data: "dl_{url}|{format}"
    data = query.data[3:]  # Skip "dl_" prefix only
    url, format_type = data.rsplit("|", 1)

    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Show format compatibility warning for MKV
    if format_type == "mkv":
        keyboard = [
            [
                InlineKeyboardButton("Continue with MKV", callback_data=f"dl_confirm_{url}|mkv"),
                InlineKeyboardButton("Switch to MP4", callback_data=f"dl_{url}|mp4"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ Format Not Compatible\n\n"
            "The selected format (MKV) may not play on all devices.\n"
            "We recommend MP4 for best Telegram compatibility.\n\n"
            "Continue anyway?",
            reply_markup=reply_markup,
        )
        return

    # Confirm format selection
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

    # Create download record in database
    platform = detect_platform(url)
    download_id = db.add_download(user_id, url, platform, format_type)

    # Add to queue (admin users get priority 1, regular users get priority 5)
    queue_id = db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)

    # Inform user of queue position
    queue_pos = db.get_user_position_in_queue(user_id)
    await query.message.reply_text(
        get_message(lang, "queue_added", position=queue_pos, minutes=queue_pos * 2)
    )


async def confirm_mkv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle MKV confirmation callback."""
    query = update.callback_query
    await query.answer()

    # Parse callback data: "dl_confirm_{url}|{format}"
    data = query.data[11:]  # Skip "dl_confirm_" prefix only
    url, format_type = data.rsplit("|", 1)

    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    # Confirm format selection
    await query.edit_message_text(get_message(lang, "format_selected", format="MKV", codec="H.264", quality="1080p"))

    # Create download record in database
    platform = detect_platform(url)
    download_id = db.add_download(user_id, url, platform, format_type)

    # Add to queue
    queue_id = db.add_to_queue(user_id, download_id, priority=1 if db.is_admin(user_id) else 5)

    # Inform user of queue position
    queue_pos = db.get_user_position_in_queue(user_id)
    await query.message.reply_text(
        get_message(lang, "queue_added", position=queue_pos, minutes=queue_pos * 2)
    )


def get_handlers():
    """
    Return list of handlers for this module.

    - MessageHandler: Catches all text messages that look like URLs
    - CallbackQueryHandler: Handles format selection callbacks (dl_*)
    - CallbackQueryHandler: Handles playlist callbacks (pl_*)
    """
    return [
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url),
        CallbackQueryHandler(confirm_mkv_callback, pattern=r"^dl_confirm_"),
        CallbackQueryHandler(format_callback, pattern=r"^dl_"),
        CallbackQueryHandler(playlist_callback, pattern=r"^pl_"),
    ]
