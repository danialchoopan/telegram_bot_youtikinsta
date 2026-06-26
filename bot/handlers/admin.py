"""
==========================================
  Admin Handler Module
==========================================

Admin-only commands for bot management and statistics.
These commands are restricted to users with admin privileges.

Commands:
    /admin_stats - Show comprehensive bot statistics
    /addallow <user_id> - Add user to allowed list
    /ban <user_id> [hours] - Ban user for specified hours
    /setadmin <user_id> - Grant admin privileges

Access Control:
    Only users marked as admin in the database (or matching
    ADMIN_USERNAME from .env) can use these commands.
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

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
        CommandHandler("addallow", admin_add_user),
        CommandHandler("ban", admin_ban_user),
        CommandHandler("setadmin", admin_set_admin),
    ]
