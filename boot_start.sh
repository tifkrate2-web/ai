#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot script — runs automatically when the phone reboots.
#
# HOW TO INSTALL:
#   1. Install "Termux:Boot" from F-Droid
#   2. Open Termux:Boot once so it registers as a boot service
#   3. Run this command inside Termux:
#
#      mkdir -p ~/.termux/boot
#      cp ~/ai/boot_start.sh ~/.termux/boot/start-bot.sh
#      chmod +x ~/.termux/boot/start-bot.sh
#
#   4. Reboot your phone to test it.

# Wait for the system to fully boot before starting
sleep 15

BOT_DIR="$HOME/ai"

# Acquire wake lock early (requires Termux:API)
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
fi

# Start the bot via start.sh (which launches the watchdog in tmux)
if [ -f "$BOT_DIR/start.sh" ]; then
    bash "$BOT_DIR/start.sh"
else
    echo "$(date): ERROR — $BOT_DIR/start.sh not found" >> "$HOME/boot.log"
fi
