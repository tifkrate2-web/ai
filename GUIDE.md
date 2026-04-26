# Telegram Group Assistant Bot — Full Mobile Hosting Guide

AI-powered Telegram group bot (Claude) running on your Android phone via **Termux**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Get a Telegram Bot Token](#2-get-a-telegram-bot-token)
3. [Get an Anthropic API Key](#3-get-an-anthropic-api-key)
4. [Install Termux on Android](#4-install-termux-on-android)
5. [Clone & Install the Bot](#5-clone--install-the-bot)
6. [Configure .env](#6-configure-env)
7. [Start the Bot](#7-start-the-bot)
8. [Add the Bot to a Telegram Group](#8-add-the-bot-to-a-telegram-group)
9. [Using the Bot](#9-using-the-bot)
10. [Keep the Bot Running 24/7](#10-keep-the-bot-running-247)
11. [Configuration Reference](#11-configuration-reference)
12. [Troubleshooting](#12-troubleshooting)
13. [Project File Overview](#13-project-file-overview)

---

## 1. Prerequisites

| Item | Details |
|------|---------|
| Android phone | Android 7.0+ |
| Internet connection | Mobile data or Wi-Fi |
| Telegram account | To create and use the bot |
| Anthropic account | For Claude API access |

---

## 2. Get a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Enter a **display name** (e.g. `My Group Assistant`)
4. Enter a **username** — must end in `bot` (e.g. `mygroupassist_bot`)
5. BotFather replies with your token:
   ```
   123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```
6. Copy and save this token — you'll need it in step 6.

**Optional — allow the bot to read all group messages:**
- Send `/setprivacy` to BotFather
- Select your bot
- Choose **Disable** — this lets the bot see every message in the group
  (needed for the `@mention` feature to work in all cases)

---

## 3. Get an Anthropic API Key

1. Go to **console.anthropic.com** and sign in
2. Click **API Keys** in the left sidebar
3. Click **Create Key**, give it a name
4. Copy the key (starts with `sk-ant-...`)
5. Save it — you'll need it in step 6

> Free tier gives you enough credits to test. Paid usage is billed per token.

---

## 4. Install Termux on Android

> **Important:** Install Termux from **F-Droid**, NOT the Google Play Store.  
> The Play Store version is outdated and unmaintained.

1. Download **F-Droid** from `f-droid.org`
2. Install F-Droid (you'll need to allow "Install from unknown sources")
3. Open F-Droid → search **Termux** → Install
4. Open Termux — you'll see a terminal prompt

---

## 5. Clone & Install the Bot

In the Termux terminal:

```bash
# Update Termux packages
pkg update -y && pkg upgrade -y

# Install git
pkg install -y git

# Clone the bot repository
git clone https://github.com/tifkrate2-web/ai.git
cd ai

# Run the setup script
bash setup.sh
```

The setup script will:
- Install Python 3 and pip
- Install tmux (for background running)
- Install all Python dependencies
- Create a template `.env` file

---

## 6. Configure .env

Edit the `.env` file with your credentials:

```bash
nano .env
```

Fill in:

```env
# === Required ===
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
ANTHROPIC_API_KEY=sk-ant-api03-...

# === Optional ===
CLAUDE_MODEL=claude-sonnet-4-6
MAX_HISTORY=20
RATE_LIMIT_PER_MIN=5
ADMIN_IDS=123456789,987654321
```

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`.

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *(required)* | Token from BotFather |
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `MAX_HISTORY` | `20` | Messages kept in memory per chat |
| `RATE_LIMIT_PER_MIN` | `5` | Max requests per user per minute |
| `ADMIN_IDS` | *(empty = all)* | Comma-separated Telegram user IDs for `/clear` |
| `SYSTEM_PROMPT` | *(built-in)* | Custom personality/instructions for the bot |

> **Tip:** To find your Telegram user ID, message @userinfobot on Telegram.

---

## 7. Start the Bot

```bash
./start.sh
```

You'll see:
```
Bot started in tmux session 'groupbot'.
Useful commands:
  tmux attach -t groupbot   — view live logs
  ./stop.sh                 — stop the bot
  tail -f bot.log           — tail the log file
```

To view live logs:
```bash
tmux attach -t groupbot
# Press Ctrl+B then D to detach (bot keeps running)
```

To stop the bot:
```bash
./stop.sh
```

---

## 8. Add the Bot to a Telegram Group

1. Open Telegram → your group → **Add Members**
2. Search for your bot's username (e.g. `@mygroupassist_bot`)
3. Add it to the group
4. **Promote the bot as admin** (optional but recommended):
   - Go to group info → Administrators → Add Administrator
   - Add the bot — enable "Read Messages" at minimum
   - This is required only if you disabled privacy mode in step 2

---

## 9. Using the Bot

### In a Group Chat

| Action | Example |
|--------|---------|
| Mention the bot | `@mygroupassist_bot what is the capital of France?` |
| Reply to a bot message | Just reply to any of its messages |
| Use `/ask` command | `/ask explain recursion simply` |

### Commands (work in groups and private chats)

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask the AI anything |
| `/clear` | Clear conversation history (admins only in groups) |
| `/stats` | Show total messages processed for this chat |
| `/help` | Show usage instructions |

### In Private Chat

You can also message the bot directly — it responds to all messages.

---

## 10. Keep the Bot Running 24/7

This section covers three layers of reliability:

| Layer | What it does |
|-------|-------------|
| **tmux** | Keeps the bot alive after you close Termux |
| **watchdog.sh** | Auto-restarts the bot if it crashes |
| **Termux:Boot** | Auto-starts everything when the phone reboots |
| **Wake lock** | Prevents Android from suspending the process |

---

### Step A — Disable Battery Optimization (required)

Without this, Android will kill Termux after a few minutes in the background.

1. Open **Android Settings**
2. Go to **Apps** → **Termux** → **Battery**
3. Select **Unrestricted** (exact wording varies by phone brand)

> On Samsung: Settings → Device Care → Battery → Background usage limits → Never sleeping apps → Add Termux
> On Xiaomi/MIUI: Settings → Apps → Manage apps → Termux → Battery saver → No restrictions

---

### Step B — Acquire Wake Lock (recommended)

Prevents the CPU from sleeping while the bot runs. Requires **Termux:API**.

**Install Termux:API:**
1. Open F-Droid → search **Termux:API** → Install
2. Inside Termux, run:
   ```bash
   pkg install -y termux-api
   ```

The watchdog script (`watchdog.sh`) calls `termux-wake-lock` automatically on startup.

To acquire it manually:
```bash
termux-wake-lock    # acquire
termux-wake-unlock  # release
```

---

### Step C — Auto-Restart on Crash (built-in)

The updated `start.sh` already uses `watchdog.sh` instead of running `bot.py` directly.

**How it works:**
```
start.sh
  └── tmux session "groupbot"
        └── watchdog.sh  (infinite loop)
              └── python bot.py
                    ↑ restarted here on crash (5s delay)
```

When the bot crashes for any reason (network drop, API error, exception), the watchdog restarts it automatically and logs the event to `bot.log`.

---

### Step D — Auto-Start on Phone Reboot

**Install Termux:Boot:**
1. Open F-Droid → search **Termux:Boot** → Install
2. Open the Termux:Boot app once — this registers it as a boot service

**Install the boot script:**
```bash
# Inside Termux:
mkdir -p ~/.termux/boot
cp ~/ai/boot_start.sh ~/.termux/boot/start-bot.sh
chmod +x ~/.termux/boot/start-bot.sh
```

**Test it:**
```bash
# Reboot your phone, then check after ~30 seconds:
tmux attach -t groupbot
```

The bot will now start automatically every time the phone boots.

---

### How to monitor the bot

```bash
# View live logs (Ctrl+B then D to detach without stopping)
tmux attach -t groupbot

# Tail the log file from a separate terminal
tail -f ~/ai/bot.log

# Check if the bot session is running
tmux ls

# See crash count and restart history
grep "crash\|Restarting\|Starting bot" ~/ai/bot.log
```

### Stop and restart

```bash
./stop.sh     # stop completely
./start.sh    # start again with watchdog
```

---

## 11. Configuration Reference

### Custom System Prompt

Change the bot's personality by editing `.env`:

```env
SYSTEM_PROMPT=You are a sarcastic but helpful assistant for a tech group. Keep answers short and witty.
```

### Multiple Admin IDs

```env
ADMIN_IDS=111111111,222222222,333333333
```

### Use a Different Claude Model

```env
# Fastest / cheapest
CLAUDE_MODEL=claude-haiku-4-5-20251001

# Most capable
CLAUDE_MODEL=claude-opus-4-7
```

---

## 12. Troubleshooting

### Bot doesn't respond in the group

- Make sure you @mentioned it or replied to one of its messages
- Check that privacy mode is disabled in BotFather (`/setprivacy` → Disable)
- Verify the bot was added to the group

### `TELEGRAM_BOT_TOKEN is not set` error

- Make sure `.env` exists and has the correct token
- Run `cat .env` to verify

### `anthropic` import error

```bash
pip install anthropic
```

### Rate limit hit

The default is 5 messages/minute per user. Increase in `.env`:
```env
RATE_LIMIT_PER_MIN=10
```

### Bot stops after closing Termux

- Make sure you used `./start.sh` (which uses tmux)
- Disable battery optimization for Termux in Android settings
- Use `tmux attach -t groupbot` to verify the session is alive

### View logs

```bash
tail -f bot.log
# or
tmux attach -t groupbot
```

---

## 13. Project File Overview

```
ai/
├── bot.py           # Main bot — handlers, Claude calls, message routing
├── config.py        # Reads .env, validates required values
├── database.py      # SQLite: conversation history, rate limits, stats
├── watchdog.sh      # Infinite loop: runs bot.py, restarts on crash, rotates logs
├── start.sh         # Start watchdog inside a background tmux session
├── stop.sh          # Stop the bot (kills tmux session)
├── boot_start.sh    # Termux:Boot script — auto-starts on phone reboot
├── setup.sh         # One-time Termux installation script
├── requirements.txt # Python package dependencies
├── GUIDE.md         # This guide
├── .env             # Your secrets (not committed to git)
└── bot_data.db      # Auto-created SQLite database
```

### Data stored locally

- **`bot_data.db`** — conversation history, rate limit counters, stats
- **`bot.log`** — runtime log (rotates on each start)
- **`.env`** — your API keys (never commit this file)

---

*Built with [python-telegram-bot](https://python-telegram-bot.org/) v21 and [Anthropic Claude](https://anthropic.com).*
