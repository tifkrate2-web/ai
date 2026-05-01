import os
import logging
from collections import defaultdict, deque
from typing import Dict, Deque

import anthropic
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

client = anthropic.Anthropic()

# Per-chat rolling conversation history
chat_histories: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=MAX_HISTORY))

SYSTEM_PROMPT = (
    "You are a helpful group assistant powered by Claude AI. "
    "You assist users in both group chats and private conversations. "
    "In group chats, messages include the sender's first name in brackets, e.g. [Alice]: hello. "
    "Address users naturally and keep responses concise and on-topic. "
    "If asked about your capabilities, explain that you can answer questions, "
    "help with tasks, and maintain context across the conversation."
)

HELP_TEXT = (
    "👋 I'm your group assistant powered by Claude AI.\n\n"
    "*In private chats:* I respond to every message.\n"
    "*In groups:* mention me with @{username} or reply to one of my messages.\n\n"
    "*Commands:*\n"
    "/help — Show this message\n"
    "/clear — Clear this chat's conversation history\n"
    "/model — Show the active Claude model"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = await context.bot.get_me()
    await update.message.reply_text(
        HELP_TEXT.format(username=bot.username),
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_histories[update.effective_chat.id].clear()
    await update.message.reply_text("✅ Conversation history cleared.")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Active model: `{MODEL}`", parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    bot = await context.bot.get_me()

    is_private = chat.type == "private"
    is_mentioned = bool(
        message.entities
        and any(
            e.type == "mention"
            and message.text[e.offset : e.offset + e.length].lstrip("@") == bot.username
            for e in message.entities
        )
    )
    is_reply_to_bot = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    )

    if not (is_private or is_mentioned or is_reply_to_bot):
        return

    # Strip bot mention from text so Claude doesn't see it
    text = message.text
    if bot.username:
        text = text.replace(f"@{bot.username}", "").strip()
    if not text:
        text = "Hello!"

    # Prefix with sender name in group chats for context
    sender = user.first_name if user else "User"
    user_content = f"[{sender}]: {text}" if not is_private else text

    history = chat_histories[chat.id]
    history.append({"role": "user", "content": user_content})

    await context.bot.send_chat_action(chat_id=chat.id, action="typing")

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=list(history),
            thinking={"type": "adaptive"},
        ) as stream:
            response = stream.get_final_message()

        reply_text = next(
            (block.text for block in response.content if block.type == "text"),
            "I couldn't generate a response.",
        )

        history.append({"role": "assistant", "content": reply_text})

        # Split long messages to respect Telegram's 4096-char limit
        for chunk in _split_message(reply_text):
            await message.reply_text(chunk)

    except anthropic.RateLimitError:
        await message.reply_text("⚠️ Rate limit reached. Please try again shortly.")
    except anthropic.APIStatusError as e:
        logger.error("Claude API error %s: %s", e.status_code, e.message)
        await message.reply_text("⚠️ API error. Please try again.")
    except Exception:
        logger.exception("Unexpected error handling message")
        await message.reply_text("⚠️ Something went wrong. Please try again.")


def _split_message(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


def main() -> None:
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting with model %s, history limit %d", MODEL, MAX_HISTORY)
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
