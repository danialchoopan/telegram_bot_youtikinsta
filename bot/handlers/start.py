"""
==========================================
  Start Handler Module
==========================================

Handles the /start command and language selection for new users.
When a user first interacts with the bot, they see a welcome message
with language selection buttons (Persian/English).

Flow:
    1. User sends /start
    2. Bot shows welcome message with language buttons
    3. User clicks a language button
    4. Bot saves preference and confirms

Handlers:
    - /start command: Shows welcome message
    - lang_* callback: Handles language selection
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.database import Database
from bot.utils.messages import get_message

# Welcome message shown on /start
MESSAGES_START = {
    "welcome": "👋 Welcome to Media Downloader Bot!\n\nSend me a link from YouTube, Instagram, or TikTok and I'll download it for you.\n\nChoose your language:",
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.

    Creates or retrieves user record and shows language selection.
    """
    db = Database()
    user = update.effective_user

    # Register user in database (or update last activity)
    db.get_or_create_user(user.id, user.username, user.full_name)

    # Create language selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send welcome message with language buttons
    await update.message.reply_text(MESSAGES_START["welcome"], reply_markup=reply_markup)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle language selection callback.

    Saves user's language preference and confirms selection.
    """
    query = update.callback_query
    await query.answer()

    # Extract language code from callback data (e.g., "lang_en" -> "en")
    lang = query.data.replace("lang_", "")

    # Update user's language preference in database
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    # Confirm language selection
    await query.edit_message_text(get_message(lang, "language_selected"))


def get_handlers():
    """
    Return list of handlers for this module.

    Returns:
        list: CommandHandler and CallbackQueryHandler instances
    """
    return [
        CommandHandler("start", start_command),
        CallbackQueryHandler(language_callback, pattern=r"^lang_"),
    ]
