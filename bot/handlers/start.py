"""
==========================================
  Start Handler + Admin Panel
==========================================

Admin uses REPLY KEYBOARD (regular buttons at bottom).
User actions tracked via context.user_data for proper flow.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from bot.config import Config
from bot.database import Database
from bot.utils.messages import get_message


# ==========================================
# Keyboards
# ==========================================

ADMIN_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📊 Stats"), KeyboardButton("👥 Users"), KeyboardButton("📥 Downloads")],
        [KeyboardButton("🎛️ Settings"), KeyboardButton("📏 Resolution"), KeyboardButton("🎯 Format")],
        [KeyboardButton("🚫 4K Block"), KeyboardButton("⚡ Optimize"), KeyboardButton("🎚️ Bitrate")],
        [KeyboardButton("🚫 Ban"), KeyboardButton("✅ Unban"), KeyboardButton("📏 Daily Limit")],
        [KeyboardButton("➕ Whitelist"), KeyboardButton("➖ Unwhitelist"), KeyboardButton("👑 Set Admin")],
        [KeyboardButton("🗑️ Clear Queue"), KeyboardButton("🏠 Menu")],
    ],
    resize_keyboard=True,
)


def _is_admin(uid: int) -> bool:
    return uid == Config.ADMIN_USER_ID or Database().is_admin(uid)


def _env(key, val):
    """Write value to .env file."""
    p = Config.BASE_DIR / ".env"
    if not p.exists():
        return
    lines = p.read_text().splitlines(keepends=True)
    with open(p, "w") as f:
        found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={val}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={val}\n")


# ==========================================
# /start
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = Database()
    u = update.effective_user
    db.get_or_create_user(u.id, u.username, u.full_name)
    if u.id == Config.ADMIN_USER_ID and not db.is_admin(u.id):
        db.set_admin(u.id, True)

    # Clear any pending state
    context.user_data.pop("awaiting", None)

    # Always ask language first
    kb = [[InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa"),
           InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]]
    await update.message.reply_text("👋 Welcome!\n\nChoose your language:", reply_markup=InlineKeyboardMarkup(kb))


async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = q.data.replace("lang_", "")
    Database().update_user_language(q.from_user.id, lang)

    if _is_admin(q.from_user.id):
        await _show_dashboard(q)
    else:
        await q.edit_message_text(get_message(lang, "language_selected"))


async def _show_dashboard(query):
    db = Database()
    s = db.get_bot_stats()
    wl = db.is_whitelist_enabled()
    wl_n = len(db.get_whitelisted_users())

    text = (
        f"👋 Welcome back boss!\n━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: {s['total_users']}  |  📥 Downloads: {s['total_downloads']}\n"
        f"💾 Data: {s['total_size_gb']} GB  |  📈 Success: {s['success_rate']}%\n"
        f"🔄 Queue: {s['active_queue']}  |  🚫 4K Blocked: {s.get('blocked_4k', 0)}\n"
        f"🔒 Whitelist: {'ON' if wl else 'OFF'} ({wl_n})\n\n"
        f"⚡ Unlimited downloads • Use keyboard below"
    )
    await query.edit_message_text(text, reply_markup=ADMIN_KB)


# ==========================================
# /help
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_admin(update.effective_user.id):
        t = (
            "📖 Help — Admin\n━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Send any link to download\n\n"
            "Buttons: tap to see options\n"
            "📊 Stats • 👥 Users • 📥 Downloads\n"
            "🎛️ Settings • 📏 Resolution • 🎯 Format\n"
            "🚫 4K Block • ⚡ Optimize • 🎚️ Bitrate\n"
            "🚫 Ban • ✅ Unban • 📏 Daily Limit\n"
            "➕ Whitelist • ➖ Unwhitelist • 👑 Set Admin\n"
            "🗑️ Clear Queue • 🏠 Menu\n\n"
            "⚡ Admins have NO download limits"
        )
    else:
        t = (
            "📖 Help\n━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Send a YouTube, Instagram, or TikTok link\n"
            "🎯 Choose format → bot downloads → sends file\n\n"
            "/start • /settings • /help"
        )
    await update.message.reply_text(t)


# ==========================================
# Admin Reply Keyboard Handler
# ==========================================

async def admin_kb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _is_admin(uid):
        return

    txt = update.message.text.strip()
    db = Database()

    # --- Info panels ---
    if txt == "📊 Stats":
        s = db.get_bot_stats()
        wl = db.is_whitelist_enabled()
        wl_n = len(db.get_whitelisted_users())
        fmt = "\n".join(f"  • {f}: {c}" for f, c in s.get("format_stats", {}).items()) or "  —"
        qual = "\n".join(f"  • {q}: {c}" for q, c in s.get("quality_stats", {}).items()) or "  —"
        await update.message.reply_text(
            f"📊 Stats\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 {s['total_users']} users • 📥 {s['total_downloads']} downloads\n"
            f"💾 {s['total_size_gb']} GB • 📈 {s['success_rate']}% success\n"
            f"🔄 {s['active_queue']} queued • 🚫 {s.get('blocked_4k',0)} 4K blocked\n"
            f"🔒 Whitelist: {'ON' if wl else 'OFF'} ({wl_n})\n\n"
            f"🎯 Formats:\n{fmt}\n\n📐 Quality:\n{qual}"
        )

    elif txt == "👥 Users":
        with db._cursor() as cur:
            cur.execute("SELECT user_id,username,full_name,total_downloads,is_admin,banned_until FROM users ORDER BY last_activity DESC LIMIT 15")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No users.")
        lines = ["👥 Users:\n"]
        for r in rows:
            b = []
            if r["is_admin"]: b.append("👑")
            if r["banned_until"]: b.append("🚫")
            nm = r["full_name"] or r["username"] or str(r["user_id"])
            lines.append(f"• {nm} | ID:{r['user_id']} | 📥{r['total_downloads']} {' '.join(b)}")
        await update.message.reply_text("\n".join(lines))

    elif txt == "📥 Downloads":
        with db._cursor() as cur:
            cur.execute("SELECT title,selected_format,status,original_size_mb,optimized_size_mb FROM downloads ORDER BY request_time DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No downloads yet.")
        icons = {"completed":"✅","failed":"❌","downloading":"📥","uploading":"📤"}
        lines = ["📥 Downloads:\n"]
        for r in rows:
            ic = icons.get(r["status"],"⏳")
            t = (r["title"] or "?")[:25]
            sz = f"{r['original_size_mb'] or 0}→{r['optimized_size_mb'] or 0}MB" if r["optimized_size_mb"] else f"{r['original_size_mb'] or 0}MB"
            lines.append(f"{ic} {t} | {r['selected_format'].upper()} | {sz}")
        await update.message.reply_text("\n".join(lines))

    # --- Settings with selection buttons ---
    elif txt == "🎛️ Settings":
        txt2 = (
            f"🎛️ Settings\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"📏 Resolution: {Config.MAX_RESOLUTION}p\n"
            f"🎯 Format: {Config.DEFAULT_FORMAT.upper()}\n"
            f"🚫 4K Block: {'✅ ON' if Config.ENABLE_4K_BLOCKING else '❌ OFF'}\n"
            f"⚡ Optimize: {'✅ ON' if Config.AUTO_OPTIMIZE else '❌ OFF'}\n"
            f"🎚️ Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps\n"
            f"🎵 Audio: {Config.AUDIO_BITRATE_KBPS} kbps\n"
            f"📊 Daily: {Config.MAX_DAILY_DOWNLOADS_PER_USER}/user\n\n"
            f"Tap a setting button below to change it."
        )
        await update.message.reply_text(txt2)

    elif txt == "📏 Resolution":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("720p" + (" ✅" if Config.MAX_RESOLUTION==720 else ""), callback_data="adm_res_720"),
            InlineKeyboardButton("1080p" + (" ✅" if Config.MAX_RESOLUTION==1080 else ""), callback_data="adm_res_1080"),
        ]])
        await update.message.reply_text(f"📏 Resolution: {Config.MAX_RESOLUTION}p\n\nTap to change:", reply_markup=kb)

    elif txt == "🎯 Format":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("MP4" + (" ✅" if Config.DEFAULT_FORMAT=="mp4" else ""), callback_data="adm_fmt_mp4"),
             InlineKeyboardButton("MKV" + (" ✅" if Config.DEFAULT_FORMAT=="mkv" else ""), callback_data="adm_fmt_mkv")],
            [InlineKeyboardButton("MP3" + (" ✅" if Config.DEFAULT_FORMAT=="mp3" else ""), callback_data="adm_fmt_mp3")],
        ])
        await update.message.reply_text(f"🎯 Format: {Config.DEFAULT_FORMAT.upper()}\n\nTap to change:", reply_markup=kb)

    elif txt == "🚫 4K Block":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("ON" + (" ✅" if Config.ENABLE_4K_BLOCKING else ""), callback_data="adm_4k_on"),
            InlineKeyboardButton("OFF" + (" ✅" if not Config.ENABLE_4K_BLOCKING else ""), callback_data="adm_4k_off"),
        ]])
        s = "ON" if Config.ENABLE_4K_BLOCKING else "OFF"
        await update.message.reply_text(f"🚫 4K Block: {s}\n\nTap to change:", reply_markup=kb)

    elif txt == "⚡ Optimize":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("ON" + (" ✅" if Config.AUTO_OPTIMIZE else ""), callback_data="adm_opt_on"),
            InlineKeyboardButton("OFF" + (" ✅" if not Config.AUTO_OPTIMIZE else ""), callback_data="adm_opt_off"),
        ]])
        s = "ON" if Config.AUTO_OPTIMIZE else "OFF"
        await update.message.reply_text(f"⚡ Auto-Optimize: {s}\n\nTap to change:", reply_markup=kb)

    elif txt == "🎚️ Bitrate":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{r} Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS==r else ""), callback_data=f"adm_bit_{r}") for r in [2,4]],
            [InlineKeyboardButton(f"{r} Mbps" + (" ✅" if Config.VIDEO_BITRATE_MBPS==r else ""), callback_data=f"adm_bit_{r}") for r in [6,8]],
        ])
        await update.message.reply_text(f"🎚️ Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps\n\nTap to change:", reply_markup=kb)

    # --- User management ---
    elif txt == "🚫 Ban":
        with db._cursor() as cur:
            cur.execute("SELECT user_id,username,full_name FROM users WHERE is_admin=0 ORDER BY last_activity DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No users.")
        lines = ["🚫 Tap to ban:\n"]
        kb = []
        for r in rows:
            nm = r["full_name"] or r["username"] or str(r["user_id"])
            lines.append(f"• {nm} ({r['user_id']})")
            kb.append([InlineKeyboardButton(f"🚫 Ban {nm[:15]}", callback_data=f"adm_ban_{r['user_id']}")])
        await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))

    elif txt == "✅ Unban":
        with db._cursor() as cur:
            cur.execute("SELECT user_id,username,full_name FROM users WHERE banned_until IS NOT NULL")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No banned users.")
        kb = []
        for r in rows:
            nm = r["full_name"] or r["username"] or str(r["user_id"])
            kb.append([InlineKeyboardButton(f"✅ Unban {nm[:15]}", callback_data=f"adm_unban_{r['user_id']}")])
        await update.message.reply_text("✅ Tap to unban:", reply_markup=InlineKeyboardMarkup(kb))

    elif txt == "➕ Whitelist":
        with db._cursor() as cur:
            cur.execute("SELECT user_id,username,full_name FROM users WHERE is_admin=0 ORDER BY last_activity DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No users.")
        lines = [f"🔒 Whitelist: {'ON' if db.is_whitelist_enabled() else 'OFF'}\n\nTap to whitelist:"]
        kb = []
        for r in rows:
            nm = r["full_name"] or r["username"] or str(r["user_id"])
            wl = " ✅" if db.is_user_whitelisted(r["user_id"]) else ""
            lines.append(f"• {nm} ({r['user_id']}){wl}")
            kb.append([InlineKeyboardButton(f"➕ {nm[:15]}", callback_data=f"adm_wladd_{r['user_id']}")])
        await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(kb))

    elif txt == "➖ Unwhitelist":
        wl_users = db.get_whitelisted_users()
        if not wl_users:
            return await update.message.reply_text("No whitelisted users.")
        kb = []
        for uid in wl_users:
            u = db.get_user(uid)
            nm = (u.get("full_name") or u.get("username") or str(uid)) if u else str(uid)
            kb.append([InlineKeyboardButton(f"❌ {nm[:15]}", callback_data=f"adm_wlrm_{uid}")])
        await update.message.reply_text("➖ Tap to remove:", reply_markup=InlineKeyboardMarkup(kb))

    elif txt == "👑 Set Admin":
        with db._cursor() as cur:
            cur.execute("SELECT user_id,username,full_name FROM users WHERE is_admin=0 ORDER BY last_activity DESC LIMIT 10")
            rows = cur.fetchall()
        if not rows:
            return await update.message.reply_text("No users.")
        kb = []
        for r in rows:
            nm = r["full_name"] or r["username"] or str(r["user_id"])
            kb.append([InlineKeyboardButton(f"👑 {nm[:15]}", callback_data=f"adm_setadm_{r['user_id']}")])
        await update.message.reply_text("👑 Tap to make admin:", reply_markup=InlineKeyboardMarkup(kb))

    elif txt == "📏 Daily Limit":
        with db._cursor() as cur:
            cur.execute("SELECT AVG(download_limit_per_day) as avg FROM users WHERE is_admin=0")
            avg = cur.fetchone()["avg"] or 10
        await update.message.reply_text(
            f"📏 Daily Limit\n━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current: {avg:.0f} per user\nAdmins: Unlimited\n\n"
            f"Send /setlimit <number> to change\nExample: /setlimit 20"
        )

    elif txt == "🗑️ Clear Queue":
        with db._cursor() as cur:
            cur.execute("UPDATE download_queue SET status='failed' WHERE status IN ('waiting','processing')")
            n = cur.rowcount
        await update.message.reply_text(f"🗑️ Cleared {n} items from queue.")

    elif txt == "🏠 Menu":
        await update.message.reply_text("🏠 Main menu", reply_markup=ADMIN_KB)


# ==========================================
# Settings Callbacks (inline keyboard taps)
# ==========================================

async def adm_setting_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _is_admin(q.from_user.id):
        return

    d = q.data

    if d.startswith("adm_res_"):
        v = int(d.replace("adm_res_", ""))
        Config.MAX_RESOLUTION = v
        _env("MAX_RESOLUTION", str(v))
        await q.edit_message_text(f"✅ Resolution: {v}p")

    elif d.startswith("adm_fmt_"):
        v = d.replace("adm_fmt_", "")
        Config.DEFAULT_FORMAT = v
        _env("DEFAULT_FORMAT", v)
        await q.edit_message_text(f"✅ Format: {v.upper()}")

    elif d.startswith("adm_4k_"):
        v = d.replace("adm_4k_", "") == "on"
        Config.ENABLE_4K_BLOCKING = v
        _env("ENABLE_4K_BLOCKING", str(v).lower())
        await q.edit_message_text(f"✅ 4K Block: {'ON' if v else 'OFF'}")

    elif d.startswith("adm_opt_"):
        v = d.replace("adm_opt_", "") == "on"
        Config.AUTO_OPTIMIZE = v
        _env("AUTO_OPTIMIZE", str(v).lower())
        await q.edit_message_text(f"✅ Auto-Optimize: {'ON' if v else 'OFF'}")

    elif d.startswith("adm_bit_"):
        v = int(d.replace("adm_bit_", ""))
        Config.VIDEO_BITRATE_MBPS = v
        _env("VIDEO_BITRATE_MBPS", str(v))
        await q.edit_message_text(f"✅ Bitrate: {v} Mbps")

    elif d.startswith("adm_ban_"):
        tid = int(d.replace("adm_ban_", ""))
        Database().ban_user(tid, 24)
        await q.edit_message_text(f"🚫 User {tid} banned for 24h")

    elif d.startswith("adm_unban_"):
        tid = int(d.replace("adm_unban_", ""))
        with Database()._cursor() as cur:
            cur.execute("UPDATE users SET banned_until=NULL WHERE user_id=?", (tid,))
        await q.edit_message_text(f"✅ User {tid} unbanned")

    elif d.startswith("adm_wladd_"):
        tid = int(d.replace("adm_wladd_", ""))
        Database().add_to_whitelist(tid)
        await q.edit_message_text(f"✅ User {tid} whitelisted")

    elif d.startswith("adm_wlrm_"):
        tid = int(d.replace("adm_wlrm_", ""))
        Database().remove_from_whitelist(tid)
        await q.edit_message_text(f"❌ User {tid} removed from whitelist")

    elif d.startswith("adm_setadm_"):
        tid = int(d.replace("adm_setadm_", ""))
        Database().set_admin(tid, True)
        await q.edit_message_text(f"👑 User {tid} is now admin")


# ==========================================
# /setlimit
# ==========================================

async def setlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    try:
        n = int(update.message.text.split()[1])
        Database().set_daily_limit_all(n)
        await update.message.reply_text(f"✅ Daily limit: {n} for all users")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setlimit <number>")


# ==========================================
# Register
# ==========================================

def get_handlers():
    return [
        CommandHandler("start", start_command),
        CommandHandler("help", help_command),
        CommandHandler("setlimit", setlimit_cmd),
        CallbackQueryHandler(lang_callback, pattern=r"^lang_"),
        CallbackQueryHandler(adm_setting_cb, pattern=r"^adm_"),
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(
            r"^📊 Stats|^👥 Users|^📥 Downloads|^🎛️ Settings|^📏 Resolution|^🎯 Format|"
            r"^🚫 4K Block|^⚡ Optimize|^🎚️ Bitrate|^🚫 Ban|^✅ Unban|^➕ Whitelist|"
            r"^➖ Unwhitelist|^👑 Set Admin|^🗑️ Clear Queue|^📏 Daily Limit|^🏠 Menu$"
        ), admin_kb_handler),
    ]
