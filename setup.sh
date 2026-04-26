#!/data/data/com.termux/files/usr/bin/bash
# Termux setup script for the Telegram group bot
set -e

echo "=== Telegram Group Bot — Termux Setup ==="

# 1. Update packages
echo "[1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install Python
echo "[2/6] Installing Python..."
pkg install -y python python-pip

# 3. Install git (optional but useful)
pkg install -y git 2>/dev/null || true

# 4. Install tmux for background sessions
echo "[3/6] Installing tmux..."
pkg install -y tmux

# 5. Install Python dependencies
echo "[4/6] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "[5/6] Creating .env file..."
    cat > .env <<'EOF'
# === Required ===
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# === Optional ===
CLAUDE_MODEL=claude-sonnet-4-6
MAX_HISTORY=20
RATE_LIMIT_PER_MIN=5
# Comma-separated Telegram user IDs who can use admin commands (empty = all admins)
ADMIN_IDS=

# Custom system prompt (optional)
# SYSTEM_PROMPT=You are a helpful group assistant.
EOF
    echo "  -> .env created. Fill in your tokens before running."
else
    echo "[5/6] .env already exists, skipping."
fi

# 7. Make scripts executable
chmod +x start.sh stop.sh 2>/dev/null || true

echo "[6/6] Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY"
echo "  2. Run:  ./start.sh"
echo "  3. To keep the bot running after closing Termux, use tmux (./start.sh handles this)"
