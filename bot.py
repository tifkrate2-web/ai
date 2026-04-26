#!/usr/bin/env python3
"""Telegram group management bot — commands only, no AI."""

import logging
from datetime import datetime, timezone

from telegram import (
    BotCommand,
    Chat,
    ChatPermissions,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database as db

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("groupbot")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_group(chat: Chat) -> bool:
    return chat.type in (Chat.GROUP, Chat.SUPERGROUP)


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    chat = update.effective_chat
    if not _is_group(chat):
        return True
    member = await context.bot.get_chat_member(chat.id, user_id)
    return member.status in ("administrator", "creator")


async def _resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return (user_id, username) from a reply or @mention argument."""
    message = update.message
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return u.id, u.full_name
    if context.args:
        arg = context.args[0].lstrip("@")
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, arg)
            return member.user.id, member.user.full_name
        except Exception:
            return None, None
    return None, None


def _escape(text: str) -> str:
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


# ---------------------------------------------------------------------------
# General commands
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hello! I'm a group management bot.\n\nType /help to see all commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Available Commands*\n\n"
        "*General*\n"
        "/help — show this message\n"
        "/ping — check if bot is alive\n"
        "/id — show your user ID and chat ID\n"
        "/time — current UTC date and time\n"
        "/rules — show group rules\n"
        "/admins — list group admins\n"
        "/report — report a message to admins\n"
        "/stats — show group stats\n\n"
        "*Admin only*\n"
        "/kick @user — kick a member\n"
        "/ban @user — ban a member\n"
        "/unban @user — unban a member\n"
        "/mute @user [minutes] — mute a member\n"
        "/unmute @user — unmute a member\n"
        "/warn @user [reason] — warn a member\n"
        "/warns @user — check warnings\n"
        "/clearwarns @user — clear all warnings\n"
        "/pin — pin replied message\n"
        "/unpin — unpin all messages\n"
        "/setrules <text> — set group rules\n"
        "/setwelcome <text> — set welcome message\n"
        "/delwelcome — remove welcome message\n"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Pong! Bot is online.")


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    await update.message.reply_text(
        f"Your user ID: `{user.id}`\nChat ID: `{chat.id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    await update.message.reply_text(f"Current time: `{now}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    rules = db.get_setting(chat.id, "rules")
    if rules:
        await update.message.reply_text(f"*Group Rules*\n\n{rules}", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No rules have been set yet. Use /setrules to add them.")


async def cmd_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not _is_group(chat):
        await update.message.reply_text("This command only works in groups.")
        return
    admins = await context.bot.get_chat_administrators(chat.id)
    lines = []
    for a in admins:
        name = a.user.full_name
        tag = " 👑" if a.status == "creator" else ""
        lines.append(f"• {name}{tag}")
    await update.message.reply_text(
        "*Group Admins*\n\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    stats = db.get_stats(chat.id)
    await update.message.reply_text(
        f"*Group Stats*\n\n"
        f"Total messages seen: `{stats['total_messages']}`\n"
        f"Total warnings issued: `{stats['total_warnings']}`\n"
        f"Members warned: `{stats['warned_members']}`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat = update.effective_chat
    reporter = update.effective_user

    if not message.reply_to_message:
        await message.reply_text("Reply to a message you want to report.")
        return

    reported_user = message.reply_to_message.from_user
    admins = await context.bot.get_chat_administrators(chat.id)

    await message.reply_text(
        f"Report sent to admins. Thank you, {reporter.first_name}."
    )

    report_text = (
        f"🚨 *Report*\n\n"
        f"Reported by: {reporter.mention_markdown()}\n"
        f"Reported user: {reported_user.mention_markdown()}\n"
        f"Message: {message.reply_to_message.text or '(non-text)'}"
    )
    for admin in admins:
        if not admin.user.is_bot:
            try:
                await context.bot.send_message(
                    admin.user.id, report_text, parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    await context.bot.ban_chat_member(chat.id, target_id)
    await context.bot.unban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"Kicked: {target_name}")
    db.log_action(chat.id, caller.id, target_id, "kick")


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    await context.bot.ban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"Banned: {target_name}")
    db.log_action(chat.id, caller.id, target_id, "ban")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    await context.bot.unban_chat_member(chat.id, target_id)
    await update.message.reply_text(f"Unbanned: {target_name}")


async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    # Optional duration (last arg if it's a number)
    duration = None
    until_date = None
    args = context.args or []
    for arg in reversed(args):
        if arg.isdigit():
            duration = int(arg)
            from datetime import timedelta
            until_date = datetime.now(timezone.utc) + timedelta(minutes=duration)
            break

    await context.bot.restrict_chat_member(
        chat.id,
        target_id,
        ChatPermissions(can_send_messages=False),
        until_date=until_date,
    )
    msg = f"Muted: {target_name}"
    if duration:
        msg += f" for {duration} minute(s)"
    await update.message.reply_text(msg)
    db.log_action(chat.id, caller.id, target_id, "mute")


async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    await context.bot.restrict_chat_member(
        chat.id,
        target_id,
        ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        ),
    )
    await update.message.reply_text(f"Unmuted: {target_name}")


async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    args = context.args or []
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason given"
    if update.message.reply_to_message and args:
        reason = " ".join(args)

    count = db.add_warning(chat.id, target_id, caller.id, reason)
    await update.message.reply_text(
        f"⚠️ {target_name} has been warned.\nReason: {reason}\nTotal warnings: {count}"
    )

    limit = config.WARN_LIMIT
    if count >= limit:
        await context.bot.ban_chat_member(chat.id, target_id)
        await update.message.reply_text(
            f"{target_name} has been auto-banned after reaching {limit} warnings."
        )


async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        target_id = update.effective_user.id
        target_name = update.effective_user.full_name

    warnings = db.get_warnings(chat.id, target_id)
    if not warnings:
        await update.message.reply_text(f"{target_name} has no warnings.")
        return

    lines = [f"*Warnings for {target_name}* ({len(warnings)} total)\n"]
    for i, w in enumerate(warnings, 1):
        ts = datetime.fromtimestamp(w["created_at"], tz=timezone.utc).strftime("%Y-%m-%d")
        lines.append(f"{i}. {w['reason']} — {ts}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_clearwarns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    target_id, target_name = await _resolve_target(update, context)
    if not target_id:
        await update.message.reply_text("Reply to a user or provide @username.")
        return

    db.clear_warnings(chat.id, target_id)
    await update.message.reply_text(f"Cleared all warnings for {target_name}.")


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to the message you want to pin.")
        return

    await context.bot.pin_chat_message(
        chat.id,
        update.message.reply_to_message.message_id,
        disable_notification=False,
    )
    await update.message.reply_text("Message pinned.")


async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    await context.bot.unpin_all_chat_messages(chat.id)
    await update.message.reply_text("All pinned messages unpinned.")


async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setrules <your rules text>")
        return

    rules = " ".join(context.args)
    db.set_setting(chat.id, "rules", rules)
    await update.message.reply_text("Group rules updated. Use /rules to view them.")


async def cmd_setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /setwelcome <message>\n\nUse {name} for the new member's name."
        )
        return

    welcome = " ".join(context.args)
    db.set_setting(chat.id, "welcome", welcome)
    await update.message.reply_text(f"Welcome message set:\n\n{welcome}")


async def cmd_delwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    caller = update.effective_user

    if not await _is_admin(update, context, caller.id):
        await update.message.reply_text("Only admins can use this command.")
        return

    db.delete_setting(chat.id, "welcome")
    await update.message.reply_text("Welcome message removed.")


# ---------------------------------------------------------------------------
# New member welcome
# ---------------------------------------------------------------------------

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    welcome_template = db.get_setting(chat.id, "welcome")
    if not welcome_template:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        text = welcome_template.replace("{name}", member.full_name)
        await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception: %s", context.error, exc_info=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config.validate()
    db.init_db()

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("time", cmd_time))
    app.add_handler(CommandHandler("rules", cmd_rules))
    app.add_handler(CommandHandler("admins", cmd_admins))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("unmute", cmd_unmute))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("warns", cmd_warns))
    app.add_handler(CommandHandler("clearwarns", cmd_clearwarns))
    app.add_handler(CommandHandler("pin", cmd_pin))
    app.add_handler(CommandHandler("unpin", cmd_unpin))
    app.add_handler(CommandHandler("setrules", cmd_setrules))
    app.add_handler(CommandHandler("setwelcome", cmd_setwelcome))
    app.add_handler(CommandHandler("delwelcome", cmd_delwelcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_error_handler(error_handler)

    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("help", "Show all commands"),
            BotCommand("ping", "Check if bot is alive"),
            BotCommand("id", "Show your user ID"),
            BotCommand("time", "Current UTC time"),
            BotCommand("rules", "Show group rules"),
            BotCommand("admins", "List group admins"),
            BotCommand("stats", "Group stats"),
            BotCommand("report", "Report a message to admins"),
            BotCommand("kick", "Kick a member (admin)"),
            BotCommand("ban", "Ban a member (admin)"),
            BotCommand("unban", "Unban a member (admin)"),
            BotCommand("mute", "Mute a member (admin)"),
            BotCommand("unmute", "Unmute a member (admin)"),
            BotCommand("warn", "Warn a member (admin)"),
            BotCommand("warns", "Check warnings"),
            BotCommand("clearwarns", "Clear warnings (admin)"),
            BotCommand("pin", "Pin a message (admin)"),
            BotCommand("unpin", "Unpin all messages (admin)"),
            BotCommand("setrules", "Set group rules (admin)"),
            BotCommand("setwelcome", "Set welcome message (admin)"),
            BotCommand("delwelcome", "Remove welcome message (admin)"),
        ])

    app.post_init = post_init

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
