#!/data/data/com.termux/files/usr/bin/bash
# Termux setup script for the Telegram group bot
set -e

echo "=== Telegram Group Bot — Termux Setup ==="

echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "[2/5] Installing Python and tmux..."
pkg install -y python python-pip tmux

echo "[3/5] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "[4/5] Creating .env file..."
    cat > .env <<'EOF'
# === Required ===
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# === Optional ===
WARN_LIMIT=3
EOF
    echo "  -> .env created. Add your TELEGRAM_BOT_TOKEN before running."
else
    echo "[4/5] .env already exists, skipping."
fi

chmod +x start.sh stop.sh watchdog.sh boot_start.sh 2>/dev/null || true

echo "[5/5] Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env:    nano .env"
echo "  2. Start bot:    ./start.sh"
