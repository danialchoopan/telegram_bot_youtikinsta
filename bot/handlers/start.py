"""
==========================================
  Start Handler + Admin Panel
==========================================

Admin uses REPLY KEYBOARD (regular buttons at bottom of chat).
Regular users use INLINE KEYBOARD (glass buttons attached to message).

Admin reply keyboard buttons send text commands:
    /stats, /users, /downloads, /settings
    /ban, /unban, /whitelist, /unwhitelist
    /setadmin, /clearqueue, /panel
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.config import Config
from bot.database import Database
from bot.utils.messages import get_message
from bot.utils.helpers import format_size

# Admin reply keyboard (regular buttons at bottom)
ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📊 Stats"), KeyboardButton("👥 Users"), KeyboardButton("📥 Downloads")],
        [KeyboardButton("🎛️ Settings"), KeyboardButton("📏 Resolution"), KeyboardButton("🎯 Format")],
        [KeyboardButton("🚫 4K Block"), KeyboardButton("⚡ Optimize"), KeyboardButton("🎚️ Bitrate")],
        [KeyboardButton("🚫 Ban"), KeyboardButton("✅ Unban"), KeyboardButton("📏 Daily Limit")],
        [KeyboardButton("➕ Whitelist"), KeyboardButton("➖ Unwhitelist"), KeyboardButton("👑 Set Admin")],
        [KeyboardButton("🗑️ Clear Queue"), KeyboardButton("🔙 Main Menu")],
    ],
    resize_keyboard=True,
)

# Normal user keyboard (just remove it)
NORMAL_KEYBOARD = ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)


def _is_admin(user_id: int) -> bool:
    return user_id == Config.ADMIN_USER_ID or Database().is_admin(user_id)


def _update_env(env_path, key, value):
    """Update a value in the .env file."""
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
# /help command
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if _is_admin(user_id):
        text = (
            "📖 Help - Admin\n━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Send any link to download\n\n"
            "⌨️ Admin Keyboard:\n"
            "📊 Stats - Bot statistics\n"
            "👥 Users - User list\n"
            "📥 Downloads - History with titles\n"
            "🎛️ Settings - Show all settings\n"
            "📏 Resolution - Toggle 720p/1080p\n"
            "🎯 Format - Toggle MP4/MKV/MP3\n"
            "🚫 4K Block - Toggle on/off\n"
            "⚡ Optimize - Toggle auto-optimize\n"
            "🎚️ Bitrate - Cycle 2/4/6/8 Mbps\n"
            "🚫 Ban / ✅ Unban\n"
            "➕ Whitelist / ➖ Unwhitelist\n"
            "👑 Set Admin\n"
            "🗑️ Clear Queue\n"
            "📏 Daily Limit\n"
            "🔙 Main Menu\n\n"
            "📋 Setting Commands:\n"
            "/setres 720 or 1080\n"
            "/setfmt mp4 or mkv or mp3\n"
            "/set4k on or off\n"
            "/setopt on or off\n"
            "/setbit 2 or 4 or 6 or 8\n"
            "/setabit 128 or 192 or 320\n"
            "/setlimit <number>\n\n"
            "⚡ Admins have NO download limits"
        )
    else:
        text = (
            "📖 Help\n━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Send a link from YouTube, Instagram, or TikTok\n"
            "🎯 I'll show you format options to choose from\n"
            "⚡ I'll download and optimize it for Telegram\n\n"
            "📋 Commands:\n"
            "/start - Main menu\n"
            "/settings - Your preferences\n"
            "/help - Show this message"
        )

    await update.message.reply_text(text)


# ==========================================
# /start command
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    user = update.effective_user
    user_data = db.get_or_create_user(user.id, user.username, user.full_name)

    if user.id == Config.ADMIN_USER_ID and not db.is_admin(user.id):
        db.set_admin(user.id, True)

    # Always show language selection first
    keyboard = [
        [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
         InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]
    await update.message.reply_text(
        "👋 Welcome!\n\nChoose your language:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    db = Database()
    db.update_user_language(query.from_user.id, lang)

    user_id = query.from_user.id

    if _is_admin(user_id):
        # Show admin welcome dashboard with stats
        await _show_admin_welcome(query, user_id)
    else:
        await query.edit_message_text(get_message(lang, "language_selected"))


async def _show_admin_welcome(query, user_id: int):
    """Show admin welcome dashboard with stats."""
    db = Database()
    stats = db.get_bot_stats()
    wl_on = db.is_whitelist_enabled()
    wl_count = len(db.get_whitelisted_users())

    text = (
        f"👋 Welcome back boss!\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Bot Status:\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"📥 Total Downloads: {stats['total_downloads']}\n"
        f"💾 Data Processed: {stats['total_size_gb']} GB\n"
        f"✅ Success Rate: {stats['success_rate']}%\n"
        f"🔄 Queue: {stats['active_queue']} items\n"
        f"🚫 4K Blocked: {stats.get('blocked_4k', 0)}\n"
        f"🔒 Whitelist: {'ON' if wl_on else 'OFF'} ({wl_count})\n\n"
        f"⚡ You have unlimited downloads\n"
        f"📋 Send a link to download or use the keyboard below"
    )

    await query.edit_message_text(text, reply_markup=ADMIN_KEYBOARD)


# ==========================================
# Admin Reply Keyboard Handler
# ==========================================

async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin reply keyboard button presses."""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    text = update.message.text.strip()

    # Stats
    if text == "📊 Stats":
        await _send_stats(update, user_id)

    # Users
    elif text == "👥 Users":
        await _send_users(update, user_id)

    # Downloads
    elif text == "📥 Downloads":
        await _send_downloads(update, user_id)

    # Settings overview — shows current values with instructions
    elif text == "🎛️ Settings":
        text = (
            f"🎛️ Settings\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"📏 Resolution: {Config.MAX_RESOLUTION}p\n"
            f"   → Type: /setres 720 or /setres 1080\n\n"
            f"🎯 Format: {Config.DEFAULT_FORMAT.upper()}\n"
            f"   → Type: /setfmt mp4 or mkv or mp3\n\n"
            f"🚫 4K Block: {'✅ ON' if Config.ENABLE_4K_BLOCKING else '❌ OFF'}\n"
            f"   → Type: /set4k on or /set4k off\n\n"
            f"⚡ Auto-Optimize: {'✅ ON' if Config.AUTO_OPTIMIZE else '❌ OFF'}\n"
            f"   → Type: /setopt on or /setopt off\n\n"
            f"🎚️ Video Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps\n"
            f"   → Type: /setbit 2 or 4 or 6 or 8\n\n"
            f"🎵 Audio Bitrate: {Config.AUDIO_BITRATE_KBPS} kbps\n"
            f"   → Type: /setabit 128 or 192 or 320\n\n"
            f"📊 Daily Limit: {Config.MAX_DAILY_DOWNLOADS_PER_USER}/user\n"
            f"   → Type: /setlimit <number>\n\n"
            f"⌨️ Or use buttons to toggle quickly"
        )
        await update.message.reply_text(text)

    # Resolution — show selection buttons
    elif text == "📏 Resolution":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("720p" + (" ✅" if Config.MAX_RESOLUTION == 720 else ""), callback_data="setres_720"),
             InlineKeyboardButton("1080p" + (" ✅" if Config.MAX_RESOLUTION == 1080 else ""), callback_data="setres_1080")],
        ])
        await update.message.reply_text(f"📏 Resolution (current: {Config.MAX_RESOLUTION}p)\n\nSelect:", reply_markup=kb)

    # Format — show selection buttons
    elif text == "🎯 Format":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("MP4" + (" ✅" if Config.DEFAULT_FORMAT == "mp4" else ""), callback_data="setfmt_mp4"),
             InlineKeyboardButton("MKV" + (" ✅" if Config.DEFAULT_FORMAT == "mkv" else ""), callback_data="setfmt_mkv")],
            [InlineKeyboardButton("MP3" + (" ✅" if Config.DEFAULT_FORMAT == "mp3" else ""), callback_data="setfmt_mp3")],
        ])
        await update.message.reply_text(f"🎯 Format (current: {Config.DEFAULT_FORMAT.upper()})\n\nSelect:", reply_markup=kb)

    # 4K Block — show on/off buttons
    elif text == "🚫 4K Block":
        state = "✅ ON" if Config.ENABLE_4K_BLOCKING else "❌ OFF"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("ON ✅" if Config.ENABLE_4K_BLOCKING else "ON", callback_data="set4k_on"),
             InlineKeyboardButton("OFF ✅" if not Config.ENABLE_4K_BLOCKING else "OFF", callback_data="set4k_off")],
        ])
        await update.message.reply_text(f"🚫 4K Block (current: {state})\n\nSelect:", reply_markup=kb)

    # Optimize — show on/off buttons
    elif text == "⚡ Optimize":
        state = "✅ ON" if Config.AUTO_OPTIMIZE else "❌ OFF"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("ON ✅" if Config.AUTO_OPTIMIZE else "ON", callback_data="setopt_on"),
             InlineKeyboardButton("OFF ✅" if not Config.AUTO_OPTIMIZE else "OFF", callback_data="setopt_off")],
        ])
        await update.message.reply_text(f"⚡ Auto-Optimize (current: {state})\n\nSelect:", reply_markup=kb)

    # Bitrate — show selection buttons
    elif text == "🎚️ Bitrate":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"2 Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS == 2 else ""), callback_data="setbit_2"),
             InlineKeyboardButton(f"4 Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS == 4 else ""), callback_data="setbit_4")],
            [InlineKeyboardButton(f"6 Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS == 6 else ""), callback_data="setbit_6"),
             InlineKeyboardButton(f"8 Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS == 8 else ""), callback_data="setbit_8")],
        ])
        await update.message.reply_text(f"🎚️ Video Bitrate (current: {Config.VIDEO_BITRATE_MBPS} Mbps)\n\nSelect:", reply_markup=kb)

    # Bitrate toggle
    elif text == "🎚️ Bitrate":
        rates = [2, 4, 6, 8]
        idx = rates.index(Config.VIDEO_BITRATE_MBPS) if Config.VIDEO_BITRATE_MBPS in rates else 1
        Config.VIDEO_BITRATE_MBPS = rates[(idx + 1) % len(rates)]
        _update_env(Config.BASE_DIR / ".env", "VIDEO_BITRATE_MBPS", str(Config.VIDEO_BITRATE_MBPS))
        await update.message.reply_text(f"🎚️ Video Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps")

    # Ban
    elif text == "🚫 Ban":
        await _send_ban_list(update, user_id)

    # Unban
    elif text == "✅ Unban":
        await _send_unban_list(update, user_id)

    # Whitelist
    elif text == "➕ Whitelist":
        await _send_whitelist_add(update, user_id)

    # Unwhitelist
    elif text == "➖ Unwhitelist":
        await _send_whitelist_remove(update, user_id)

    # Set Admin
    elif text == "👑 Set Admin":
        await _send_setadmin_list(update, user_id)

    # Daily Limit
    elif text == "📏 Daily Limit":
        await _send_daily_limit(update, user_id)

    # Clear Queue
    elif text == "🗑️ Clear Queue":
        db = Database()
        with db._cursor() as cur:
            cur.execute("UPDATE download_queue SET status = 'failed' WHERE status IN ('waiting', 'processing')")
            count = cur.rowcount
        await update.message.reply_text(f"🗑️ Cleared {count} items from queue.")

    # Main Menu
    elif text == "🔙 Main Menu":
        await update.message.reply_text("Main menu. Send a link to download.", reply_markup=ADMIN_KEYBOARD)


# ==========================================
# Admin Action Functions (send as messages)
# ==========================================

async def _send_stats(update: Update, user_id: int):
    db = Database()
    stats = db.get_bot_stats()
    wl_on = db.is_whitelist_enabled()
    wl_count = len(db.get_whitelisted_users())

    text = (
        f"📊 Bot Statistics\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {stats['total_users']}\n"
        f"📥 Downloads: {stats['total_downloads']}\n"
        f"💾 Data: {stats['total_size_gb']} GB\n"
        f"🔄 Queue: {stats['active_queue']} items\n"
        f"📈 Success: {stats['success_rate']}%\n"
        f"🚫 4K Blocked: {stats.get('blocked_4k', 0)}\n"
        f"🔒 Whitelist: {'ON' if wl_on else 'OFF'} ({wl_count} users)"
    )

    fmt = stats.get("format_stats", {})
    if fmt:
        text += "\n\n🎯 Formats:\n"
        for f, c in fmt.items():
            text += f"  • {f}: {c}\n"

    await update.message.reply_text(text)


async def _send_users(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute(
            "SELECT user_id, username, full_name, total_downloads, is_admin, banned_until "
            "FROM users ORDER BY last_activity DESC LIMIT 15"
        )
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No users yet.")
        return

    lines = ["👥 Users:\n"]
    for u in users:
        badges = []
        if u["is_admin"]:
            badges.append("👑")
        if u["banned_until"]:
            badges.append("🚫")
        badge = " ".join(badges)
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} | ID: {u['user_id']} | 📥 {u['total_downloads']} {badge}")

    await update.message.reply_text("\n".join(lines))


async def _send_downloads(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute(
            "SELECT d.title, d.selected_format, d.status, d.original_size_mb, d.optimized_size_mb, u.username "
            "FROM downloads d LEFT JOIN users u ON d.user_id = u.user_id "
            "ORDER BY d.request_time DESC LIMIT 10"
        )
        downloads = cur.fetchall()

    if not downloads:
        await update.message.reply_text("No downloads yet.")
        return

    lines = ["📥 Recent Downloads:\n"]
    for d in downloads:
        icon = {"completed": "✅", "failed": "❌", "downloading": "📥", "uploading": "📤"}.get(d["status"], "⏳")
        title = (d["title"] or "Unknown")[:25]
        user = d["username"] or "?"
        size = f"{d['original_size_mb'] or 0}→{d['optimized_size_mb'] or 0}MB" if d["optimized_size_mb"] else f"{d['original_size_mb'] or 0}MB"
        lines.append(f"{icon} {title} | {d['selected_format'].upper()} | {size}")

    await update.message.reply_text("\n".join(lines))


async def _send_settings(update: Update, user_id: int):
    text = (
        f"🎛️ Settings:\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"📏 Resolution: {Config.MAX_RESOLUTION}p\n"
        f"🎯 Format: {Config.DEFAULT_FORMAT.upper()}\n"
        f"🚫 4K Block: {'✅' if Config.ENABLE_4K_BLOCKING else '❌'}\n"
        f"⚡ Auto-Optimize: {'✅' if Config.AUTO_OPTIMIZE else '❌'}\n"
        f"📹 Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps\n"
        f"🎵 Audio: {Config.AUDIO_BITRATE_KBPS} kbps\n"
        f"📊 Daily Limit: {Config.MAX_DAILY_DOWNLOADS_PER_USER}/user"
    )
    await update.message.reply_text(text)


async def _send_daily_limit(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT AVG(download_limit_per_day) as avg_limit FROM users WHERE is_admin = 0")
        avg = cur.fetchone()["avg_limit"] or 10

    text = (
        f"📏 Daily Download Limit\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"Current average: {avg:.0f} downloads/user\n"
        f"Admins: Unlimited\n\n"
        f"Send a number to set limit for ALL users:\n"
        f"Example: /setlimit 20"
    )
    await update.message.reply_text(text)


async def _send_ban_list(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 0 ORDER BY last_activity DESC LIMIT 10")
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No users to ban.")
        return

    lines = ["🚫 Send /ban <user_id> to ban:\n"]
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} → /ban_{u['user_id']}")

    await update.message.reply_text("\n".join(lines))


async def _send_unban_list(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE banned_until IS NOT NULL")
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No banned users.")
        return

    lines = ["✅ Send /unban <user_id> to unban:\n"]
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} → /unban_{u['user_id']}")

    await update.message.reply_text("\n".join(lines))


async def _send_whitelist_add(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 0 ORDER BY last_activity DESC LIMIT 10")
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No users to whitelist.")
        return

    wl_on = db.is_whitelist_enabled()
    lines = [f"🔒 Whitelist: {'ON' if wl_on else 'OFF'}\n\nSend /wl_<user_id> to whitelist:\n"]
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        wl = " ✅" if db.is_user_whitelisted(u["user_id"]) else ""
        lines.append(f"• {name} → /wl_{u['user_id']}{wl}")

    await update.message.reply_text("\n".join(lines))


async def _send_whitelist_remove(update: Update, user_id: int):
    db = Database()
    wl_users = db.get_whitelisted_users()

    if not wl_users:
        await update.message.reply_text("No whitelisted users.")
        return

    lines = ["➖ Send /unwl_<user_id> to remove:\n"]
    for uid in wl_users:
        user = db.get_user(uid)
        name = (user.get("full_name") or user.get("username") or str(uid)) if user else str(uid)
        lines.append(f"• {name} → /unwl_{uid}")

    await update.message.reply_text("\n".join(lines))


async def _send_setadmin_list(update: Update, user_id: int):
    db = Database()
    with db._cursor() as cur:
        cur.execute("SELECT user_id, username, full_name FROM users WHERE is_admin = 0 ORDER BY last_activity DESC LIMIT 10")
        users = cur.fetchall()

    if not users:
        await update.message.reply_text("No users available.")
        return

    lines = ["👑 Send /setadmin_<user_id> to make admin:\n"]
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        lines.append(f"• {name} → /setadmin_{u['user_id']}")

    await update.message.reply_text("\n".join(lines))


# ==========================================
# Admin slash commands (from button taps)
# ==========================================

async def admin_ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban_<user_id>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        target_id = int(update.message.text.replace("/ban_", ""))
        Database().ban_user(target_id, hours=24)
        await update.message.reply_text(f"🚫 User {target_id} banned for 24h.")
    except Exception:
        await update.message.reply_text("Usage: /ban_<user_id>")


async def admin_unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unban_<user_id>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        target_id = int(update.message.text.replace("/unban_", ""))
        db = Database()
        with db._cursor() as cur:
            cur.execute("UPDATE users SET banned_until = NULL WHERE user_id = ?", (target_id,))
        await update.message.reply_text(f"✅ User {target_id} unbanned.")
    except Exception:
        await update.message.reply_text("Usage: /unban_<user_id>")


async def admin_wl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wl_<user_id>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        target_id = int(update.message.text.replace("/wl_", ""))
        Database().add_to_whitelist(target_id)
        await update.message.reply_text(f"✅ User {target_id} added to whitelist.")
    except Exception:
        await update.message.reply_text("Usage: /wl_<user_id>")


async def admin_unwl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unwl_<user_id>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        target_id = int(update.message.text.replace("/unwl_", ""))
        Database().remove_from_whitelist(target_id)
        await update.message.reply_text(f"❌ User {target_id} removed from whitelist.")
    except Exception:
        await update.message.reply_text("Usage: /unwl_<user_id>")


async def admin_setadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setadmin_<user_id>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        target_id = int(update.message.text.replace("/setadmin_", ""))
        Database().set_admin(target_id, True)
        await update.message.reply_text(f"👑 User {target_id} is now admin.")
    except Exception:
        await update.message.reply_text("Usage: /setadmin_<user_id>")


async def setlimit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setlimit <number>"""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return

    try:
        limit = int(update.message.text.split()[1])
        Database().set_daily_limit_all(limit)
        await update.message.reply_text(f"✅ Daily limit set to {limit} for all users.\nAdmins remain unlimited.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setlimit <number>\nExample: /setlimit 20")


async def setres_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setres <720|1080>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = int(update.message.text.split()[1])
        if val not in (720, 1080):
            raise ValueError
        Config.MAX_RESOLUTION = val
        _update_env(Config.BASE_DIR / ".env", "MAX_RESOLUTION", str(val))
        await update.message.reply_text(f"📏 Resolution set to {val}p")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setres <720|1080>\nExample: /setres 1080")


async def setfmt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setfmt <mp4|mkv|mp3>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = update.message.text.split()[1].lower()
        if val not in ("mp4", "mkv", "mp3"):
            raise ValueError
        Config.DEFAULT_FORMAT = val
        _update_env(Config.BASE_DIR / ".env", "DEFAULT_FORMAT", val)
        await update.message.reply_text(f"🎯 Format set to {val.upper()}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setfmt <mp4|mkv|mp3>\nExample: /setfmt mp4")


async def set4k_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /set4k <on|off>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = update.message.text.split()[1].lower()
        if val not in ("on", "off"):
            raise ValueError
        Config.ENABLE_4K_BLOCKING = val == "on"
        _update_env(Config.BASE_DIR / ".env", "ENABLE_4K_BLOCKING", val)
        await update.message.reply_text(f"🚫 4K Block: {'ON' if Config.ENABLE_4K_BLOCKING else 'OFF'}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set4k <on|off>\nExample: /set4k on")


async def setopt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setopt <on|off>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = update.message.text.split()[1].lower()
        if val not in ("on", "off"):
            raise ValueError
        Config.AUTO_OPTIMIZE = val == "on"
        _update_env(Config.BASE_DIR / ".env", "AUTO_OPTIMIZE", val)
        await update.message.reply_text(f"⚡ Auto-Optimize: {'ON' if Config.AUTO_OPTIMIZE else 'OFF'}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setopt <on|off>\nExample: /setopt on")


async def setbit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setbit <2|4|6|8>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = int(update.message.text.split()[1])
        if val not in (2, 4, 6, 8):
            raise ValueError
        Config.VIDEO_BITRATE_MBPS = val
        _update_env(Config.BASE_DIR / ".env", "VIDEO_BITRATE_MBPS", str(val))
        await update.message.reply_text(f"🎚️ Video Bitrate: {val} Mbps")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setbit <2|4|6|8>\nExample: /setbit 4")


async def setabit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setabit <128|192|320>"""
    if not _is_admin(update.effective_user.id):
        return
    try:
        val = int(update.message.text.split()[1])
        if val not in (128, 192, 320):
            raise ValueError
        Config.AUDIO_BITRATE_KBPS = val
        _update_env(Config.BASE_DIR / ".env", "AUDIO_BITRATE_KBPS", str(val))
        await update.message.reply_text(f"🎵 Audio Bitrate: {val} kbps")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setabit <128|192|320>\nExample: /setabit 192")


# ==========================================
# Settings Inline Keyboard Callbacks
# ==========================================

async def setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings inline keyboard button taps."""
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    data = query.data

    if data.startswith("setres_"):
        val = int(data.replace("setres_", ""))
        Config.MAX_RESOLUTION = val
        _update_env(Config.BASE_DIR / ".env", "MAX_RESOLUTION", str(val))
        await query.edit_message_text(f"✅ Resolution set to {val}p")

    elif data.startswith("setfmt_"):
        val = data.replace("setfmt_", "")
        Config.DEFAULT_FORMAT = val
        _update_env(Config.BASE_DIR / ".env", "DEFAULT_FORMAT", val)
        await query.edit_message_text(f"✅ Format set to {val.upper()}")

    elif data.startswith("set4k_"):
        val = data.replace("set4k_", "") == "on"
        Config.ENABLE_4K_BLOCKING = val
        _update_env(Config.BASE_DIR / ".env", "ENABLE_4K_BLOCKING", str(val).lower())
        state = "ON" if val else "OFF"
        await query.edit_message_text(f"✅ 4K Block: {state}")

    elif data.startswith("setopt_"):
        val = data.replace("setopt_", "") == "on"
        Config.AUTO_OPTIMIZE = val
        _update_env(Config.BASE_DIR / ".env", "AUTO_OPTIMIZE", str(val).lower())
        state = "ON" if val else "OFF"
        await query.edit_message_text(f"✅ Auto-Optimize: {state}")

    elif data.startswith("setbit_"):
        val = int(data.replace("setbit_", ""))
        Config.VIDEO_BITRATE_MBPS = val
        _update_env(Config.BASE_DIR / ".env", "VIDEO_BITRATE_MBPS", str(val))
        await query.edit_message_text(f"✅ Video Bitrate: {val} Mbps")


# ==========================================
# Register handlers
# ==========================================

def get_handlers():
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("setlimit", setlimit_command),
        CommandHandler("setres", setres_command),
        CommandHandler("setfmt", setfmt_command),
        CommandHandler("set4k", set4k_command),
        CommandHandler("setopt", setopt_command),
        CommandHandler("setbit", setbit_command),
        CommandHandler("setabit", setabit_command),
        CallbackQueryHandler(language_callback, pattern=r"^lang_"),
        CallbackQueryHandler(setting_callback, pattern=r"^set(res|fmt|4k|opt|bit)_"),
        # Admin text commands from reply keyboard
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(
            r"^📊 Stats|^👥 Users|^📥 Downloads|^🎛️ Settings|^📏 Resolution|^🎯 Format|"
            r"^🚫 4K Block|^⚡ Optimize|^🎚️ Bitrate|^🚫 Ban|^✅ Unban|^➕ Whitelist|"
            r"^➖ Unwhitelist|^👑 Set Admin|^🗑️ Clear Queue|^📏 Daily Limit|^🔙 Main Menu$"
        ), admin_message_handler),
        # Admin slash commands from button taps
        MessageHandler(filters.TEXT & filters.Regex(r"^/ban_\d+$"), admin_ban_command),
        MessageHandler(filters.TEXT & filters.Regex(r"^/unban_\d+$"), admin_unban_command),
        MessageHandler(filters.TEXT & filters.Regex(r"^/wl_\d+$"), admin_wl_command),
        MessageHandler(filters.TEXT & filters.Regex(r"^/unwl_\d+$"), admin_unwl_command),
        MessageHandler(filters.TEXT & filters.Regex(r"^/setadmin_\d+$"), admin_setadmin_command),
    ]
