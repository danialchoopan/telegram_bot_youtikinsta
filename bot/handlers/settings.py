from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.database import Database
from bot.utils.messages import get_message


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    user = update.effective_user
    user_data = db.get_user(user.id)

    if not user_data:
        await update.message.reply_text("Send /start first to register.")
        return

    lang = user_data.get("language", "en")
    today = db.get_daily_download_count(user.id)

    text = get_message(lang, "settings",
        language="فارسی" if lang == "fa" else "English",
        format=user_data.get("preferred_format", "mp4").upper(),
        quality=user_data.get("preferred_quality", "1080p"),
        today=today,
        limit=user_data.get("download_limit_per_day", 10),
    )

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
    query = update.callback_query
    await query.answer()

    action = query.data
    db = Database()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)
    lang = user_data.get("language", "en") if user_data else "en"

    if action == "set_format":
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
        keyboard = [
            [
                InlineKeyboardButton("🇮🇷 فارسی", callback_data="setlang_fa"),
                InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌐 Select language:", reply_markup=reply_markup)


async def format_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    fmt = query.data.replace("setfmt_", "")
    db = Database()
    db.update_user_preferences(query.from_user.id, preferred_format=fmt)

    user_data = db.get_user(query.from_user.id)
    lang = user_data.get("language", "en") if user_data else "en"
    await query.edit_message_text(get_message(lang, "format_changed", format=fmt.upper()))


async def quality_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    qual = query.data.replace("setqual_", "")
    db = Database()
    db.update_user_preferences(query.from_user.id, preferred_quality=qual)

    user_data = db.get_user(query.from_user.id)
    lang = user_data.get("language", "en") if user_data else "en"
    await query.edit_message_text(get_message(lang, "quality_changed", quality=qual))


async def language_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("setlang_", "")
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    await query.edit_message_text(get_message(lang, "language_selected"))


def get_handlers():
    return [
        CommandHandler("settings", settings_command),
        CallbackQueryHandler(settings_callback, pattern=r"^set_(format|quality|language)$"),
        CallbackQueryHandler(format_select_callback, pattern=r"^setfmt_"),
        CallbackQueryHandler(quality_select_callback, pattern=r"^setqual_"),
        CallbackQueryHandler(language_select_callback, pattern=r"^setlang_"),
    ]
