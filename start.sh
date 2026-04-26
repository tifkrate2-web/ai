#!/data/data/com.termux/files/usr/bin/bash
# Start the Telegram group bot in a persistent tmux session
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

# Kill existing session if running
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Stopping existing bot session..."
    tmux kill-session -t "$SESSION"
    sleep 1
fi

# Start new tmux session running the bot
tmux new-session -d -s "$SESSION" -c "$BOT_DIR" \
    "python bot.py 2>&1 | tee -a bot.log; echo 'Bot exited. Press Enter to close.'; read"

echo "Bot started in tmux session '$SESSION'."
echo ""
echo "Useful commands:"
echo "  tmux attach -t $SESSION   — view live logs"
echo "  ./stop.sh                 — stop the bot"
echo "  tail -f bot.log           — tail the log file"
echo ""
echo "The bot will keep running even if you close this Termux window."
echo "To prevent Termux from sleeping, go to Android Settings > Battery and"
echo "disable battery optimization for Termux."
