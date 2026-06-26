"""
==========================================
  Admin Handler Module
==========================================

Admin-only commands for bot management and statistics.
These commands are restricted to users with admin privileges.

Commands:
    /admin_stats - Show comprehensive bot statistics
    /admin_quality_settings - Quality control panel
    /addallow <user_id> - Add user to allowed list
    /ban <user_id> [hours] - Ban user for specified hours
    /setadmin <user_id> - Grant admin privileges

Access Control:
    Only users marked as admin in the database (or matching
    ADMIN_USERNAME from .env) can use these commands.
"""

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from bot.config import Config
from bot.database import Database
from bot.utils.messages import get_message


def admin_only(handler):
    """
    Decorator to restrict handler access to admin users only.

    Checks if user is admin in database or matches ADMIN_USERNAME.
    Non-admin users see an "access denied" message.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        db = Database()
        user_id = update.effective_user.id
        username = update.effective_user.username or ""

        # Check if user is already marked as admin in database
        if db.is_admin(user_id):
            return await handler(update, context)

        # Check if username matches admin username from config
        # Auto-promote to admin if match
        if username.lower() == Config.ADMIN_USERNAME.lower():
            db.set_admin(user_id, True)
            return await handler(update, context)

        # User is not admin - send access denied message
        user_data = db.get_user(user_id)
        lang = user_data.get("language", "en") if user_data else "en"
        await update.message.reply_text(get_message(lang, "not_available"))
    return wrapper


@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show comprehensive bot statistics.

    Displays:
    - Total users and downloads
    - Total data downloaded
    - Success rate
    - Queue status
    - Format distribution
    - Quality distribution
    - 4K blocked count
    """
    db = Database()
    stats = db.get_bot_stats()

    # Build format distribution lines
    format_lines = []
    for fmt, count in stats.get("format_stats", {}).items():
        pct = round(count / stats["total_downloads"] * 100, 1) if stats["total_downloads"] > 0 else 0
        format_lines.append(f"• {fmt}: {count} ({pct}%)")

    # Build quality distribution lines
    quality_lines = []
    for qual, count in stats.get("quality_stats", {}).items():
        pct = round(count / stats["total_downloads"] * 100, 1) if stats["total_downloads"] > 0 else 0
        quality_lines.append(f"• {qual}: {count} ({pct}%)")

    # Build main stats message
    text = get_message("en", "admin_stats",
        users=stats["total_users"],
        downloads=stats["total_downloads"],
        data=stats["total_size_gb"],
        success=stats["success_rate"],
        queue=stats["active_queue"],
    )

    # Add format and quality sections if data exists
    if format_lines:
        text += "\n\n🎯 Format Distribution:\n" + "\n".join(format_lines)
    if quality_lines:
        text += "\n\n📐 Quality Distribution:\n" + "\n".join(quality_lines)

    text += f"\n\n🚫 4K Blocked: {stats.get('blocked_4k', 0)}"

    await update.message.reply_text(text)


@admin_only
async def admin_quality_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show quality settings control panel.

    Allows admin to view and modify quality optimization settings.
    """
    # Get current settings from environment
    settings_text = f"""🎛️ QUALITY SETTINGS
━━━━━━━━━━━━━━━━━━━

[1] Max Resolution: {Config.MAX_RESOLUTION}p {'✅' if Config.MAX_RESOLUTION == 1080 else '⚠️'}
[2] Default Format: {Config.DEFAULT_FORMAT.upper()}
[3] Video Bitrate: {Config.VIDEO_BITRATE_MBPS} Mbps
[4] Audio Bitrate: {Config.AUDIO_BITRATE_KBPS} kbps
[5] Enable 4K Blocking: {'✅' if Config.ENABLE_4K_BLOCKING else '❌'}
[6] Auto-Optimize: {'✅' if Config.AUTO_OPTIMIZE else '❌'}
[7] Force H.264: {'✅' if Config.FORCE_H264 else '❌'}
[8] Optimization Preset: {Config.OPTIMIZATION_PRESET}

📁 File Paths:
• Downloads: {Config.DOWNLOAD_PATH}
• Optimized: {Config.OPTIMIZED_PATH}
• Database: {Config.DB_PATH}
• Logs: {Config.LOG_PATH}"""

    keyboard = [
        [
            InlineKeyboardButton("📏 Resolution", callback_data="admin_res"),
            InlineKeyboardButton("🎯 Format", callback_data="admin_fmt"),
        ],
        [
            InlineKeyboardButton("🚫 4K Block", callback_data="admin_4k"),
            InlineKeyboardButton("⚡ Optimize", callback_data="admin_opt"),
        ],
        [
            InlineKeyboardButton("🔄 Reset Defaults", callback_data="admin_reset"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(settings_text, reply_markup=reply_markup)


@admin_only
async def admin_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin settings button callbacks."""
    query = update.callback_query
    await query.answer()

    action = query.data
    env_file = Config.BASE_DIR / ".env"

    if action == "admin_res":
        # Toggle between 720 and 1080
        new_val = "720" if Config.MAX_RESOLUTION == 1080 else "1080"
        _update_env(env_file, "MAX_RESOLUTION", new_val)
        Config.MAX_RESOLUTION = int(new_val)
        await query.edit_message_text(f"✅ Max resolution set to {new_val}p")

    elif action == "admin_fmt":
        # Cycle through mp4, mkv, mp3
        formats = ["mp4", "mkv", "mp3"]
        idx = formats.index(Config.DEFAULT_FORMAT) if Config.DEFAULT_FORMAT in formats else 0
        new_fmt = formats[(idx + 1) % len(formats)]
        _update_env(env_file, "DEFAULT_FORMAT", new_fmt)
        Config.DEFAULT_FORMAT = new_fmt
        await query.edit_message_text(f"✅ Default format set to {new_fmt.upper()}")

    elif action == "admin_4k":
        # Toggle 4K blocking
        new_val = "false" if Config.ENABLE_4K_BLOCKING else "true"
        _update_env(env_file, "ENABLE_4K_BLOCKING", new_val)
        Config.ENABLE_4K_BLOCKING = new_val == "true"
        status = "enabled" if Config.ENABLE_4K_BLOCKING else "disabled"
        await query.edit_message_text(f"✅ 4K blocking {status}")

    elif action == "admin_opt":
        # Toggle auto-optimization
        new_val = "false" if Config.AUTO_OPTIMIZE else "true"
        _update_env(env_file, "AUTO_OPTIMIZE", new_val)
        Config.AUTO_OPTIMIZE = new_val == "true"
        status = "enabled" if Config.AUTO_OPTIMIZE else "disabled"
        await query.edit_message_text(f"✅ Auto-optimization {status}")

    elif action == "admin_reset":
        # Reset to defaults
        defaults = {
            "MAX_RESOLUTION": "1080",
            "DEFAULT_FORMAT": "mp4",
            "ENABLE_4K_BLOCKING": "true",
            "AUTO_OPTIMIZE": "true",
            "FORCE_H264": "true",
            "VIDEO_BITRATE_MBPS": "4",
            "AUDIO_BITRATE_KBPS": "128",
            "OPTIMIZATION_PRESET": "medium",
        }
        for key, val in defaults.items():
            _update_env(env_file, key, val)
            setattr(Config, key, int(val) if val.isdigit() else (val == "true" if val in ("true", "false") else val))
        await query.edit_message_text("✅ Settings reset to defaults")


def _update_env(env_path: Path, key: str, value: str):
    """Update a value in the .env file."""
    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

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


@admin_only
async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add a user to the allowed list.

    Usage: /addallow <user_id>
    """
    db = Database()
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("Usage: /addallow <user_id>")
            return

        target_user_id = int(parts[1])
        # Create user record (if doesn't exist)
        db.get_or_create_user(target_user_id)
        await update.message.reply_text(get_message("en", "admin_added", user_id=target_user_id))
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addallow <user_id>")


@admin_only
async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ban a user for specified number of hours.

    Usage: /ban <user_id> [hours]
    Default ban duration: 24 hours
    """
    db = Database()
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("Usage: /ban <user_id> [hours]")
            return

        target_user_id = int(parts[1])
        hours = int(parts[2]) if len(parts) > 2 else 24
        db.ban_user(target_user_id, hours)
        await update.message.reply_text(get_message("en", "admin_banned", user_id=target_user_id, hours=hours))
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /ban <user_id> [hours]")


@admin_only
async def admin_set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Grant admin privileges to a user.

    Usage: /setadmin <user_id>
    """
    db = Database()
    try:
        parts = update.message.text.split()
        if len(parts) < 2:
            await update.message.reply_text("Usage: /setadmin <user_id>")
            return

        target_user_id = int(parts[1])
        db.set_admin(target_user_id, True)
        await update.message.reply_text(f"✅ User {target_user_id} is now an admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /setadmin <user_id>")


def get_handlers():
    """Return list of admin command handlers."""
    return [
        CommandHandler("admin_stats", admin_stats),
        CommandHandler("admin_quality_settings", admin_quality_settings),
        CommandHandler("addallow", admin_add_user),
        CommandHandler("ban", admin_ban_user),
        CommandHandler("setadmin", admin_set_admin),
        CallbackQueryHandler(admin_settings_callback, pattern=r"^admin_"),
    ]
