#!/usr/bin/env python3
"""Telegram group assistant bot powered by Claude AI."""

import asyncio
import logging
import time
from datetime import datetime

import anthropic
from telegram import (
    BotCommand,
    Chat,
    Message,
    Update,
)
from telegram.constants import ChatAction, ParseMode
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

claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_label(update: Update) -> str:
    user = update.effective_user
    if user is None:
        return "Unknown"
    return user.full_name or user.username or str(user.id)


def _is_group(chat: Chat) -> bool:
    return chat.type in (Chat.GROUP, Chat.SUPERGROUP)


async def _typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )


def _split_message(text: str, limit: int = 4000) -> list[str]:
    """Split long text into Telegram-safe chunks."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while text:
        parts.append(text[:limit])
        text = text[limit:]
    return parts


async def _ask_claude(chat_id: int, user_id: int, user_text: str) -> str:
    history = db.get_history(chat_id, limit=config.MAX_HISTORY)
    history.append({"role": "user", "content": user_text})

    response = await asyncio.to_thread(
        lambda: claude.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=1024,
            system=config.SYSTEM_PROMPT,
            messages=history,
        )
    )
    answer: str = response.content[0].text.strip()

    db.add_message(chat_id, user_id, "user", user_text)
    db.add_message(chat_id, 0, "assistant", answer)
    return answer


def _rate_limited(update: Update) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return True
    return not db.check_rate_limit(user.id, chat.id, config.RATE_LIMIT_PER_MIN)


def _is_admin(user_id: int) -> bool:
    return not config.ADMIN_IDS or user_id in config.ADMIN_IDS


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm your group AI assistant powered by Claude.\n\n"
        "How to use me:\n"
        "• `/ask <question>` — ask me anything\n"
        "• Mention me `@botname <question>` — in groups\n"
        "• Reply to my messages — to continue the conversation\n"
        "• `/clear` — clear this chat's history\n"
        "• `/stats` — show usage stats\n"
        "• `/help` — show this message\n\n"
        "Add me to a group and I'll help everyone!",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: `/ask <your question>`", parse_mode=ParseMode.MARKDOWN)
        return

    question = " ".join(context.args)
    await _handle_question(update, context, question)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return

    if _is_group(chat) and not _is_admin(user.id):
        await update.message.reply_text("Only group admins can clear the conversation history.")
        return

    count = db.clear_history(chat.id)
    await update.message.reply_text(
        f"Cleared {count} message(s) from memory for this chat."
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    stats = db.get_stats(chat.id)
    last = (
        datetime.fromtimestamp(stats["last_active"]).strftime("%Y-%m-%d %H:%M")
        if stats["last_active"]
        else "never"
    )
    await update.message.reply_text(
        f"📊 *Chat stats*\n"
        f"Total messages processed: `{stats['total_messages']}`\n"
        f"Last active: `{last}`",
        parse_mode=ParseMode.MARKDOWN,
    )


# ---------------------------------------------------------------------------
# Message handler (mention / reply)
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message = update.message
    chat = update.effective_chat
    user = update.effective_user

    if message is None or chat is None or user is None:
        return

    bot_username = (await context.bot.get_me()).username
    text: str = message.text or message.caption or ""

    # In groups: only respond when mentioned or replied to
    if _is_group(chat):
        is_reply_to_bot = (
            message.reply_to_message is not None
            and message.reply_to_message.from_user is not None
            and message.reply_to_message.from_user.username == bot_username
        )
        is_mention = bot_username and f"@{bot_username}" in text
        if not is_reply_to_bot and not is_mention:
            return
        # Strip the @mention from the text
        text = text.replace(f"@{bot_username}", "").strip()

    if not text:
        await message.reply_text("Please include a message or question.")
        return

    await _handle_question(update, context, text)


# ---------------------------------------------------------------------------
# Core Q&A flow
# ---------------------------------------------------------------------------

async def _handle_question(
    update: Update, context: ContextTypes.DEFAULT_TYPE, question: str
) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.message

    if chat is None or user is None or message is None:
        return

    if _rate_limited(update):
        await message.reply_text(
            f"You're sending messages too fast. Please wait a moment. "
            f"(Limit: {config.RATE_LIMIT_PER_MIN} messages/minute)"
        )
        return

    await _typing(update, context)

    try:
        answer = await _ask_claude(chat.id, user.id, question)
    except anthropic.APIStatusError as e:
        logger.error("Anthropic API error: %s", e)
        await message.reply_text("Claude API error. Please try again later.")
        return
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        await message.reply_text("Something went wrong. Please try again.")
        return

    parts = _split_message(answer, config.MAX_RESPONSE_CHARS)
    for i, part in enumerate(parts):
        if i == 0:
            await message.reply_text(part)
        else:
            await chat.send_message(part)


# ---------------------------------------------------------------------------
# Error handler
# ---------------------------------------------------------------------------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update: %s", context.error, exc_info=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    config.validate()
    db.init_db()

    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_error_handler(error_handler)

    # Register bot commands visible in Telegram UI
    async def post_init(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("ask", "Ask the AI assistant a question"),
            BotCommand("clear", "Clear conversation history for this chat"),
            BotCommand("stats", "Show usage statistics"),
            BotCommand("help", "Show help message"),
        ])

    app.post_init = post_init

    logger.info("Bot starting — model: %s", config.CLAUDE_MODEL)
    app.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
