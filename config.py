import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Auto-ban after this many warnings
WARN_LIMIT = int(os.getenv("WARN_LIMIT", "3"))


def validate() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN is not set. Edit your .env file."
        )
