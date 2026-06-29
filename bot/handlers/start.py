"""
==========================================
  Start Handler Module
==========================================

Handles the /start command and language selection for new users.
Admin users get a management panel with inline buttons.

Flow:
    1. User sends /start
    2. Bot shows welcome message with language buttons
    3. User clicks a language button
    4. Bot saves preference and confirms
    5. Admin gets additional management panel

Handlers:
    - /start command: Shows welcome message
    - lang_* callback: Handles language selection
    - admin_panel callback: Shows admin dashboard
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.config import Config
from bot.database import Database
from bot.utils.messages import get_message

MESSAGES_START = {
    "welcome": "👋 Welcome to Media Downloader Bot!\n\nSend me a link from YouTube, Instagram, or TikTok and I'll download it for you.\n\nChoose your language:",
    "welcome_admin": "👋 Welcome back boss!\n\nI'm ready to serve. Send me a link to download.\n\nChoose your language:",
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with admin detection."""
    db = Database()
    user = update.effective_user

    db.get_or_create_user(user.id, user.username, user.full_name)

    is_admin = user.id == Config.ADMIN_USER_ID or db.is_admin(user.id)

    if user.id == Config.ADMIN_USER_ID and not db.is_admin(user.id):
        db.set_admin(user.id, True)

    keyboard = [
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
        ]
    ]

    if is_admin:
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_admin:
        await update.message.reply_text(MESSAGES_START["welcome_admin"], reply_markup=reply_markup)
    else:
        await update.message.reply_text(MESSAGES_START["welcome"], reply_markup=reply_markup)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")

    db = Database()
    db.update_user_language(query.from_user.id, lang)

    user_id = query.from_user.id
    is_admin = user_id == Config.ADMIN_USER_ID or db.is_admin(user_id)

    if is_admin:
        await query.edit_message_text(get_message(lang, "language_selected"))
        await show_admin_panel(update, context, query.from_user.id)
    else:
        await query.edit_message_text(get_message(lang, "language_selected"))


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel button."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_admin = user_id == Config.ADMIN_USER_ID or Database().is_admin(user_id)

    if not is_admin:
        await query.edit_message_text("⛔ Access denied.")
        return

    await show_admin_panel(update, context, user_id, edit=True)


async def show_admin_panel(update_or_query, context, user_id: int, edit: bool = False):
    """Show admin management panel."""
    db = Database()
    stats = db.get_bot_stats()

    text = f"""🔧 Admin Panel
━━━━━━━━━━━━━━━━━━━

👥 Users: {stats['total_users']}
📥 Downloads: {stats['total_downloads']}
🔄 Queue: {stats['active_queue']}
📈 Success: {stats['success_rate']}%
🚫 4K Blocked: {stats.get('blocked_4k', 0)}"""

    keyboard = [
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("🎛️ Settings", callback_data="admin_settings_btn"),
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("🚫 Block User", callback_data="admin_block"),
        ],
        [
            InlineKeyboardButton("🔄 Restart Queue", callback_data="admin_restart"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update_or_query.message.reply_text(text, reply_markup=reply_markup)


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of recent users."""
    query = update.callback_query
    await query.answer()

    db = Database()
    with db._cursor() as cur:
        cur.execute(
            "SELECT user_id, username, full_name, total_downloads, is_admin, last_activity "
            "FROM users ORDER BY last_activity DESC LIMIT 10"
        )
        users = cur.fetchall()

    if not users:
        text = "No users yet."
    else:
        lines = ["👥 Recent Users\n"]
        for u in users:
            admin_badge = " 👑" if u["is_admin"] else ""
            name = u["full_name"] or u["username"] or str(u["user_id"])
            lines.append(f"• {name} ({u['user_id']}) - {u['total_downloads']} downloads{admin_badge}")
        text = "\n".join(lines)

    keyboard = [[InlineKeyboardButton("← Back", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup)


async def admin_restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show info about queue."""
    query = update.callback_query
    await query.answer("Queue restarted", show_alert=True)

    keyboard = [[InlineKeyboardButton("← Back", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("✅ Queue worker will pick up next item automatically.", reply_markup=reply_markup)


def get_handlers():
    """Return list of handlers for this module."""
    return [
        CommandHandler("start", start_command),
        CallbackQueryHandler(language_callback, pattern=r"^lang_"),
        CallbackQueryHandler(admin_panel_callback, pattern=r"^admin_panel$"),
        CallbackQueryHandler(admin_users_callback, pattern=r"^admin_users$"),
        CallbackQueryHandler(admin_restart_callback, pattern=r"^admin_restart$"),
    ]
