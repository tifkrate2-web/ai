#!/data/data/com.termux/files/usr/bin/bash
# Stop the bot tmux session
SESSION="groupbot"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
    echo "Bot stopped (tmux session '$SESSION' killed)."
else
    echo "No running bot session found."
fi
