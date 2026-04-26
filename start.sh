#!/data/data/com.termux/files/usr/bin/bash
# Start the Telegram group bot in a persistent tmux session with watchdog auto-restart
SESSION="groupbot"
BOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Validate .env exists and has tokens
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "ERROR: .env file not found. Run setup.sh first."
    exit 1
fi

if grep -q "your_telegram_bot_token_here" "$BOT_DIR/.env" 2>/dev/null; then
    echo "ERROR: Please edit .env and set your TELEGRAM_BOT_TOKEN."
    exit 1
fi

if grep -q "your_anthropic_api_key_here" "$BOT_DIR/.env" 2>/dev/null; then
    echo "ERROR: Please edit .env and set your ANTHROPIC_API_KEY."
    exit 1
fi

# Kill existing session if already running
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Stopping existing bot session..."
    tmux kill-session -t "$SESSION"
    sleep 1
fi

# Make scripts executable
chmod +x "$BOT_DIR/watchdog.sh" "$BOT_DIR/stop.sh"

# Start watchdog (which runs bot.py and restarts it on crash) inside tmux
tmux new-session -d -s "$SESSION" -c "$BOT_DIR" \
    "bash watchdog.sh; echo; echo 'Watchdog exited. Press Enter to close.'; read"

echo "Bot started with watchdog in tmux session '$SESSION'."
echo ""
echo "  tmux attach -t $SESSION   — view live logs (Ctrl+B then D to detach)"
echo "  ./stop.sh                 — stop the bot"
echo "  tail -f bot.log           — follow the log file"
echo ""
echo "The bot will auto-restart if it crashes and keep running"
echo "even when you close this Termux window."
