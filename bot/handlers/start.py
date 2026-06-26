from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.database import Database
from bot.utils.messages import get_message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)

    keyboard = [
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MESSAGES_START["welcome"], reply_markup=reply_markup)


MESSAGES_START = {
    "welcome": "👋 Welcome to Media Downloader Bot!\n\nSend me a link from YouTube, Instagram, or TikTok and I'll download it for you.\n\nChoose your language:",
}


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    await query.edit_message_text(get_message(lang, "language_selected"))


def get_handlers():
    return [
        CommandHandler("start", start_command),
        CallbackQueryHandler(language_callback, pattern=r"^lang_"),
    ]
