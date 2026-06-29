"""
==========================================
  Start Handler Module
==========================================

/start command, language selection, and admin panel.

Admin panel features (all inline keyboard):
    - Dashboard with live stats
    - User list with ban/unban
    - Download history
    - Quality settings
    - Queue management
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.config import Config
from bot.database import Database
from bot.utils.messages import get_message
from bot.utils.helpers import format_size


def _is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id == Config.ADMIN_USER_ID or Database().is_admin(user_id)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    db = Database()
    user = update.effective_user
    db.get_or_create_user(user.id, user.username, user.full_name)

    if user.id == Config.ADMIN_USER_ID and not db.is_admin(user.id):
        db.set_admin(user.id, True)

    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]
    if _is_admin(user.id):
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])

    msg = "👋 Welcome back boss!\n\nSend me a link to download." if _is_admin(user.id) else \
          "👋 Welcome to Media Downloader Bot!\n\nSend me a link to download.\n\nChoose your language:"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    if _is_admin(query.from_user.id):
        await query.edit_message_text(get_message(lang, "language_selected"))
        await _show_panel(query, query.from_user.id)
    else:
        await query.edit_message_text(get_message(lang, "language_selected"))


# ==========================================
# Admin Panel
# ==========================================

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel entry point."""
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return await query.edit_message_text("⛔ Access denied.")
    await _show_panel(query, query.from_user.id)


async def _show_panel(query, user_id: int, edit: bool = True):
    """Show main admin dashboard."""
    db = Database()
    stats = db.get_bot_stats()

    text = (
        f"🔧 Admin Panel\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {stats['total_users']}\n"
        f"📥 Downloads: {stats['total_downloads']}\n"
        f"💾 Data: {stats['total_size_gb']} GB\n"
        f"🔄 Queue: {stats['active_queue']} items\n"
        f"📈 Success: {stats['success_rate']}%\n"
        f"🚫 4K Blocked: {stats.get('blocked_4k', 0)}"
    )

    kb = [
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats"),
         InlineKeyboardButton("👥 Users", callback_data="adm_users")],
        [InlineKeyboardButton("📥 Downloads", callback_data="adm_downloads"),
         InlineKeyboardButton("🎛️ Settings", callback_data="adm_settings")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"),
         InlineKeyboardButton("✅ Unban User", callback_data="adm_unban")],
        [InlineKeyboardButton("👑 Set Admin", callback_data="adm_setadmin"),
         InlineKeyboardButton("🗑️ Clear Queue", callback_data="adm_clearqueue")],
    ]

    if edit:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ==========================================
# Stats
# ==========================================

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    stats = db.get_bot_stats()

    fmt_lines = "\n".join(
        f"  • {f}: {c} ({round(c/stats['total_downloads']*100,1) if stats['total_downloads'] else 0}%)"
        for f, c in stats.get("format_stats", {}).items()
    ) or "  No data"

    qual_lines = "\n".join(
        f"  • {q}: {c}" for q, c in stats.get("quality_stats", {}).items()
    ) or "  No data"

    text = (
        f"📊 Detailed Stats\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"📥 Total Downloads: {stats['total_downloads']}\n"
        f"💾 Total Data: {stats['total_size_gb']} GB\n"
        f"📈 Success Rate: {stats['success_rate']}%\n\n"
        f"🎯 Format Distribution:\n{fmt_lines}\n\n"
        f"📐 Quality Distribution:\n{qual_lines}"
    )

    kb = [[InlineKeyboardButton("← Back", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ==========================================
# Users
# ==========================================

async def users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute(
            "SELECT user_id, username, full_name, total_downloads, is_admin, banned_until "
            "FROM users ORDER BY last_activity DESC LIMIT 15"
        )
        users = cur.fetchall()

    lines = ["👥 Users\n"]
    for u in users:
        badges = []
        if u["is_admin"]:
            badges.append("👑")
        if u["banned_until"]:
            badges.append("🚫")
        badge = " ".join(badges)
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} | ID: {u['user_id']} | 📥 {u['total_downloads']} {badge}")

    kb = [[InlineKeyboardButton("← Back", callback_data="admin_panel")]]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


# ==========================================
# Downloads
# ==========================================

async def downloads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute(
            "SELECT d.url, d.selected_format, d.status, d.original_size_mb, d.optimized_size_mb, u.username "
            "FROM downloads d LEFT JOIN users u ON d.user_id = u.user_id "
            "ORDER BY d.request_time DESC LIMIT 10"
        )
        downloads = cur.fetchall()

    if not downloads:
        text = "📥 No downloads yet."
    else:
        lines = ["📥 Recent Downloads\n"]
        for d in downloads:
            status_icon = {"completed": "✅", "failed": "❌", "downloading": "📥", "uploading": "📤"}.get(d["status"], "⏳")
            user = d["username"] or "unknown"
            url_short = d["url"][:35] + "..." if len(d["url"]) > 35 else d["url"]
            size_info = f"{d['original_size_mb']}MB→{d['optimized_size_mb']}MB" if d["optimized_size_mb"] else f"{d['original_size_mb'] or 0}MB"
            lines.append(f"{status_icon} {d['selected_format'].upper()} | {size_info} | @{user}")
        text = "\n".join(lines)

    kb = [[InlineKeyboardButton("← Back", callback_data="admin_panel")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ==========================================
# Settings
# ==========================================

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    text = (
        f"🎛️ Settings\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 Max Resolution: {Config.MAX_RESOLUTION}p\n"
        f"🎯 Default Format: {Config.DEFAULT_FORMAT.upper()}\n"
        f"🚫 4K Blocking: {'✅' if Config.ENABLE_4K_BLOCKING else '❌'}\n"
        f"⚡ Auto-Optimize: {'✅' if Config.AUTO_OPTIMIZE else '❌'}\n"
        f"📹 Video Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps\n"
        f"🎵 Audio Bitrate: {Config.AUDIO_BITRATE_KBPS} kbps\n"
        f"📦 Max File: {Config.MAX_FILE_SIZE_GB} GB\n"
        f"📊 Daily Limit: {Config.MAX_DAILY_DOWNLOADS_PER_USER}/user"
    )

    kb = [
        [InlineKeyboardButton("📏 Resolution", callback_data="adm_res"),
         InlineKeyboardButton("🚫 4K Block", callback_data="adm_4k")],
        [InlineKeyboardButton("⚡ Optimize", callback_data="adm_opt"),
         InlineKeyboardButton("🎯 Format", callback_data="adm_fmt")],
        [InlineKeyboardButton("← Back", callback_data="admin_panel")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


async def setting_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    action = query.data
    env_file = Config.BASE_DIR / ".env"

    if action == "adm_res":
        new = "720" if Config.MAX_RESOLUTION == 1080 else "1080"
        _update_env(env_file, "MAX_RESOLUTION", new)
        Config.MAX_RESOLUTION = int(new)
    elif action == "adm_4k":
        Config.ENABLE_4K_BLOCKING = not Config.ENABLE_4K_BLOCKING
        _update_env(env_file, "ENABLE_4K_BLOCKING", str(Config.ENABLE_4K_BLOCKING).lower())
    elif action == "adm_opt":
        Config.AUTO_OPTIMIZE = not Config.AUTO_OPTIMIZE
        _update_env(env_file, "AUTO_OPTIMIZE", str(Config.AUTO_OPTIMIZE).lower())
    elif action == "adm_fmt":
        fmts = ["mp4", "mkv", "mp3"]
        idx = fmts.index(Config.DEFAULT_FORMAT) if Config.DEFAULT_FORMAT in fmts else 0
        Config.DEFAULT_FORMAT = fmts[(idx + 1) % len(fmts)]
        _update_env(env_file, "DEFAULT_FORMAT", Config.DEFAULT_FORMAT)

    await settings_callback(update, context)


def _update_env(env_path, key, value):
    if not env_path.exists():
        return
    lines = env_path.read_text().splitlines(keepends=True)
    with open(env_path, "w") as f:
        found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")


# ==========================================
# Ban / Unban
# ==========================================

async def ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 0 ORDER BY last_activity DESC LIMIT 10")
        users = cur.fetchall()

    if not users:
        return await query.edit_message_text("No users to ban.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))

    lines = ["🚫 Select user to ban:\n"]
    kb = []
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} ({u['user_id']})")
        kb.append([InlineKeyboardButton(f"🚫 Ban {name[:15]}", callback_data=f"adm_doban_{u['user_id']}")])
    kb.append([InlineKeyboardButton("← Back", callback_data="admin_panel")])

    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))


async def do_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    target_id = int(query.data.replace("adm_doban_", ""))
    db = Database()
    db.ban_user(target_id, hours=24)
    await query.edit_message_text(f"🚫 User {target_id} banned for 24h.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))


async def unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE banned_until IS NOT NULL")
        users = cur.fetchall()

    if not users:
        return await query.edit_message_text("No banned users.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))

    kb = []
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        kb.append([InlineKeyboardButton(f"✅ Unban {name[:15]}", callback_data=f"adm_dounban_{u['user_id']}")])
    kb.append([InlineKeyboardButton("← Back", callback_data="admin_panel")])

    await query.edit_message_text("✅ Select user to unban:", reply_markup=InlineKeyboardMarkup(kb))


async def do_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    target_id = int(query.data.replace("adm_dounban_", ""))
    db = Database()
    with db._cursor() as cur:
        cur.execute("UPDATE users SET banned_until = NULL WHERE user_id = ?", (target_id,))
    await query.edit_message_text(f"✅ User {target_id} unbanned.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))


# ==========================================
# Set Admin / Clear Queue
# ==========================================

async def setadmin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 0 ORDER BY last_activity DESC LIMIT 10")
        users = cur.fetchall()

    if not users:
        return await query.edit_message_text("No users available.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))

    kb = []
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        kb.append([InlineKeyboardButton(f"👑 {name[:15]}", callback_data=f"adm_dosetadmin_{u['user_id']}")])
    kb.append([InlineKeyboardButton("← Back", callback_data="admin_panel")])

    await query.edit_message_text("👑 Select user to make admin:", reply_markup=InlineKeyboardMarkup(kb))


async def do_setadmin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    target_id = int(query.data.replace("adm_dosetadmin_", ""))
    Database().set_admin(target_id, True)
    await query.edit_message_text(f"👑 User {target_id} is now admin.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))


async def clearqueue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    db = Database()
    with db._cursor() as cur:
        cur.execute("UPDATE download_queue SET status = 'failed' WHERE status IN ('waiting', 'processing')")
        count = cur.rowcount

    await query.edit_message_text(f"🗑️ Cleared {count} items from queue.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="admin_panel")]]))


# ==========================================
# Register handlers
# ==========================================

def get_handlers():
    return [
        CommandHandler("start", start_command),
        CallbackQueryHandler(language_callback, pattern=r"^lang_"),
        # Admin panel
        CallbackQueryHandler(admin_panel_callback, pattern=r"^admin_panel$"),
        CallbackQueryHandler(stats_callback, pattern=r"^adm_stats$"),
        CallbackQueryHandler(users_callback, pattern=r"^adm_users$"),
        CallbackQueryHandler(downloads_callback, pattern=r"^adm_downloads$"),
        CallbackQueryHandler(settings_callback, pattern=r"^adm_settings$"),
        CallbackQueryHandler(setting_toggle_callback, pattern=r"^adm_(res|4k|opt|fmt)$"),
        # Ban/Unban
        CallbackQueryHandler(ban_callback, pattern=r"^adm_ban$"),
        CallbackQueryHandler(do_ban_callback, pattern=r"^adm_doban_"),
        CallbackQueryHandler(unban_callback, pattern=r"^adm_unban$"),
        CallbackQueryHandler(do_unban_callback, pattern=r"^adm_dounban_"),
        # Admin management
        CallbackQueryHandler(setadmin_callback, pattern=r"^adm_setadmin$"),
        CallbackQueryHandler(do_setadmin_callback, pattern=r"^adm_dosetadmin_"),
        CallbackQueryHandler(clearqueue_callback, pattern=r"^adm_clearqueue$"),
    ]
