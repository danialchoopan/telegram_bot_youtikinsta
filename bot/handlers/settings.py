"""
==========================================
  Settings Handler Module
==========================================

User preferences management through interactive inline keyboards.
Allows users to customize their download experience.

Commands:
    /settings - Show current settings and options

Settings Available:
    - Default format (MP4/MKV/MP3/M4A)
    - Preferred quality (1080p/720p/480p/Audio)
    - Language (English/Persian)

Flow:
    1. User sends /settings
    2. Bot shows current settings with option buttons
    3. User clicks an option (Format/Quality/Language)
    4. Bot shows selection keyboard for that option
    5. User makes selection
    6. Bot saves preference and confirms
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.database import Database
from bot.utils.messages import get_message


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /settings command.

    Shows user's current settings and provides buttons to change them.
    """
    db = Database()
    user = update.effective_user
    user_data = db.get_user(user.id)

    # User must register first with /start
    if not user_data:
        await update.message.reply_text("Send /start first to register.")
        return

    lang = user_data.get("language", "en")
    today = db.get_daily_download_count(user.id)

    # Build settings message
    text = get_message(lang, "settings",
        language="فارسی" if lang == "fa" else "English",
        format=user_data.get("preferred_format", "mp4").upper(),
        quality=user_data.get("preferred_quality", "1080p"),
        today=today,
        limit=user_data.get("download_limit_per_day", 10),
    )

    # Create settings option buttons
    keyboard = [
        [
            InlineKeyboardButton("📹 Format", callback_data="set_format"),
            InlineKeyboardButton("📐 Quality", callback_data="set_quality"),
        ],
        [
            InlineKeyboardButton("🌐 Language", callback_data="set_language"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle settings option selection (Format/Quality/Language).

    Shows the appropriate selection keyboard for the chosen option.
    """
    query = update.callback_query
    await query.answer()

    action = query.data
    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    if action == "set_format":
        # Show format selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("MP4", callback_data="setfmt_mp4"),
                InlineKeyboardButton("MKV", callback_data="setfmt_mkv"),
            ],
            [
                InlineKeyboardButton("MP3", callback_data="setfmt_mp3"),
                InlineKeyboardButton("M4A", callback_data="setfmt_m4a"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎯 Select default format:", reply_markup=reply_markup)

    elif action == "set_quality":
        # Show quality selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("1080p", callback_data="setqual_1080p"),
                InlineKeyboardButton("720p", callback_data="setqual_720p"),
            ],
            [
                InlineKeyboardButton("480p", callback_data="setqual_480p"),
                InlineKeyboardButton("Audio", callback_data="setqual_audio"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📐 Select preferred quality:", reply_markup=reply_markup)

    elif action == "set_language":
        # Show language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌐 Select language:", reply_markup=reply_markup)


async def format_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle format selection (MP4/MKV/MP3/M4A)."""
    query = update.callback_query
    await query.answer()

    # Extract format from callback data
    fmt = query.data.replace("setfmt_", "")

    # Save preference to database
    db = Database()
    db.update_user_preferences(query.from_user.id, preferred_format=fmt)

    # Confirm change
    user_data = db.get_user(query.from_user.id)
    lang = user_data.get("language", "en") if user_data else "en"
    await query.edit_message_text(get_message(lang, "format_changed", format=fmt.upper()))


async def quality_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quality selection (1080p/720p/480p/Audio)."""
    query = update.callback_query
    await query.answer()

    # Extract quality from callback data
    qual = query.data.replace("setqual_", "")

    # Save preference to database
    db = Database()
    db.update_user_preferences(query.from_user.id, preferred_quality=qual)

    # Confirm change
    user_data = db.get_user(query.from_user.id)
    lang = user_data.get("language", "en") if user_data else "en"
    await query.edit_message_text(get_message(lang, "quality_changed", quality=qual))


async def language_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection (English/Persian)."""
    query = update.callback_query
    await query.answer()

    # Extract language from callback data
    lang = query.data.replace("setlang_", "")

    # Save preference to database
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    # Confirm change
    await query.edit_message_text(get_message(lang, "language_selected"))


def get_handlers():
    """
    Return list of settings handlers.

    Includes:
    - /settings command
    - Settings option callbacks (set_format, set_quality, set_language)
    - Selection callbacks (setfmt_, setqual_, setlang_)
    """
    return [
        CommandHandler("settings", settings_command),
        CallbackQueryHandler(settings_callback, pattern=r"^set_(format|quality|language)$"),
        CallbackQueryHandler(format_select_callback, pattern=r"^setfmt_"),
        CallbackQueryHandler(quality_select_callback, pattern=r"^setqual_"),
        CallbackQueryHandler(language_select_callback, pattern=r"^setlang_"),
    ]
