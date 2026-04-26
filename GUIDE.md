# Telegram Group Management Bot — Full Guide

A Telegram group management bot with commands for admins and members, hosted on your Android phone via **Termux**. No AI, no external APIs — just your bot token.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Create a Telegram Bot](#2-create-a-telegram-bot)
3. [Install Termux on Android](#3-install-termux-on-android)
4. [Install the Bot](#4-install-the-bot)
5. [Configure .env](#5-configure-env)
6. [Start the Bot](#6-start-the-bot)
7. [Add the Bot to a Group](#7-add-the-bot-to-a-group)
8. [Commands Reference](#8-commands-reference)
9. [Run 24/7 Automatically](#9-run-247-automatically)
10. [Monitoring & Logs](#10-monitoring--logs)
11. [Troubleshooting](#11-troubleshooting)
12. [Project Files](#12-project-files)

---

## 1. Prerequisites

| Item | Details |
|------|---------|
| Android phone | Android 7.0+ |
| Internet connection | Mobile data or Wi-Fi |
| Telegram account | To create and control the bot |

No paid services, no API keys beyond your free Telegram bot token.

---

## 2. Create a Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Enter a display name (e.g. `My Group Manager`)
4. Enter a username ending in `bot` (e.g. `mygroupmanager_bot`)
5. BotFather sends your token:
   ```
   123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   ```
6. Copy and save it

**Allow the bot to read all group messages:**
- Send `/setprivacy` to BotFather
- Select your bot → choose **Disable**

**Make the bot an admin in your group** so it can kick/ban/mute:
- Group settings → Administrators → Add Administrator → select your bot
- Enable: Delete messages, Ban users, Pin messages

---

## 3. Install Termux on Android

> Install from **F-Droid only** — the Play Store version is outdated.

1. Open your browser → go to **f-droid.org**
2. Download and install F-Droid
3. Open F-Droid → search **Termux** → Install
4. Open Termux

---

## 4. Install the Bot

In the Termux terminal, run these commands:

```bash
# Install git
pkg install -y git

# Clone the bot
git clone https://github.com/tifkrate2-web/ai.git
cd ai

# Run setup (installs Python, tmux, dependencies)
bash setup.sh
```

---

## 5. Configure .env

```bash
nano .env
```

Add your bot token:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ

# Optional: auto-ban after this many warnings (default 3)
WARN_LIMIT=3
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 6. Start the Bot

```bash
./start.sh
```

Output:
```
Bot started with watchdog in tmux session 'groupbot'.
  tmux attach -t groupbot   — view live logs
  ./stop.sh                 — stop the bot
  tail -f bot.log           — follow the log file
```

---

## 7. Add the Bot to a Group

1. Open your Telegram group
2. Group info → Add Member → search your bot username
3. Add it
4. Make it **admin**: Group info → Administrators → Add Administrator → your bot
   - Enable: Delete messages, Restrict members, Pin messages

Test it — send `/ping` in the group.

---

## 8. Commands Reference

### General (everyone)

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/ping` | Check if bot is online |
| `/id` | Show your user ID and the chat ID |
| `/time` | Current UTC date and time |
| `/rules` | Show group rules |
| `/admins` | List all group admins |
| `/stats` | Show warning and action stats |
| `/report` | Reply to a message to report it to all admins |

### Admin only

| Command | Description |
|---------|-------------|
| `/kick @user` | Remove user (they can rejoin) |
| `/ban @user` | Permanently ban user |
| `/unban @user` | Unban a user |
| `/mute @user [minutes]` | Silence a user (optional duration) |
| `/unmute @user` | Restore a user's ability to send messages |
| `/warn @user [reason]` | Issue a warning (auto-bans at warn limit) |
| `/warns @user` | View a user's warning history |
| `/clearwarns @user` | Clear all warnings for a user |
| `/pin` | Pin the replied-to message |
| `/unpin` | Unpin all pinned messages |
| `/setrules <text>` | Set the group rules (shown with /rules) |
| `/setwelcome <text>` | Set a welcome message for new members (use `{name}`) |
| `/delwelcome` | Remove the welcome message |

### Welcome message example

```
/setwelcome Welcome to the group, {name}! Please read /rules before posting.
```

### Warn limit

By default, a user is **automatically banned** after **3 warnings**. Change this in `.env`:

```env
WARN_LIMIT=5
```

---

## 9. Run 24/7 Automatically

Four layers keep the bot running around the clock:

```
Phone boots
  └── Termux:Boot → boot_start.sh (waits 15s)
        └── start.sh
              └── tmux session "groupbot"
                    └── watchdog.sh (infinite loop)
                          └── python bot.py
                                ↑ auto-restarted on crash
```

### Step A — Disable battery optimization (required)

Android kills background apps without this.

- **Settings → Apps → Termux → Battery → Unrestricted**
- Samsung: Settings → Device Care → Battery → Background usage limits → Never sleeping apps → Add Termux
- Xiaomi: Settings → Apps → Manage apps → Termux → Battery saver → No restrictions

### Step B — Wake lock (recommended)

Prevents CPU from sleeping. Requires **Termux:API**.

1. F-Droid → search **Termux:API** → Install
2. Open Termux:API once
3. In Termux:
   ```bash
   pkg install -y termux-api
   ```

The watchdog acquires the wake lock automatically.

### Step C — Auto-start on reboot

1. F-Droid → search **Termux:Boot** → Install
2. Open Termux:Boot once (registers it as a boot service)
3. In Termux:
   ```bash
   mkdir -p ~/.termux/boot
   cp ~/ai/boot_start.sh ~/.termux/boot/start-bot.sh
   chmod +x ~/.termux/boot/start-bot.sh
   ```
4. Reboot your phone to test — after ~30 seconds:
   ```bash
   tmux ls   # should show: groupbot
   ```

---

## 10. Monitoring & Logs

```bash
# View live logs
tmux attach -t groupbot
# Press Ctrl+B then D to detach (bot keeps running)

# Follow the log file
tail -f ~/ai/bot.log

# Check if the session is alive
tmux ls

# See crash/restart history
grep "crash\|Restarting\|Starting" ~/ai/bot.log

# Stop the bot
./stop.sh

# Restart the bot
./start.sh
```

---

## 11. Troubleshooting

**Bot doesn't respond in the group**
- Send `/setprivacy` to BotFather → Disable
- Make sure the bot is an admin in the group
- Check `tmux attach -t groupbot` for errors

**`TELEGRAM_BOT_TOKEN is not set`**
- Run `cat .env` to verify the token is there

**Bot stops after closing Termux**
- Disable battery optimization (Step A above)
- Use `./start.sh` — it runs inside tmux so it persists

**Kick/ban/mute not working**
- The bot must be an admin with the right permissions (Delete messages, Restrict members)

**`pip install` fails**
```bash
pkg install -y python python-pip
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 12. Project Files

```
ai/
├── bot.py           # All command handlers
├── config.py        # Reads .env, validates token
├── database.py      # SQLite: warnings, settings, action log
├── watchdog.sh      # Runs bot.py, auto-restarts on crash
├── start.sh         # Starts watchdog inside tmux
├── stop.sh          # Kills the tmux session
├── boot_start.sh    # Termux:Boot — auto-starts on phone reboot
├── setup.sh         # One-time install script
├── requirements.txt # Python dependencies
├── .env             # Your bot token (not committed to git)
└── bot_data.db      # Auto-created SQLite database
```

**Local data:**
- `bot_data.db` — warnings, group settings, action log
- `bot.log` — runtime log (rotated at 5 MB)
- `.env` — your token (never share or commit this)
