import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# How many past messages to send as context per conversation
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

# Max characters per Claude response (Telegram limit is 4096)
MAX_RESPONSE_CHARS = 4000

# System prompt for the group assistant
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful, friendly, and concise group assistant. "
    "You help members of a Telegram group with questions, summaries, and tasks. "
    "Keep answers clear and to the point. When code is needed, format it properly.",
)

# Rate limit: max messages per user per minute
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "5"))

# Admins (Telegram user IDs) who can use admin commands
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = (
    [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip()]
    if ADMIN_IDS_RAW
    else []
)

def validate() -> None:
    errors = []
    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set")
    if errors:
        raise EnvironmentError("Missing configuration:\n" + "\n".join(f"  - {e}" for e in errors))
