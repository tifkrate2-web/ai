#!/data/data/com.termux/files/usr/bin/bash
# Watchdog — keeps bot.py running forever, restarts it on any crash
# Run this instead of bot.py directly so the bot auto-recovers.

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$BOT_DIR/bot.log"
MAX_LOG_BYTES=5242880   # 5 MB — rotate log when it exceeds this
RESTART_DELAY=5         # seconds to wait before restarting after a crash
CRASH_COUNT=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

rotate_log() {
    if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt "$MAX_LOG_BYTES" ]; then
        mv "$LOG" "${LOG}.1"
        log "Log rotated."
    fi
}

acquire_wakelock() {
    # Keep CPU awake so Android doesn't suspend the process
    if command -v termux-wake-lock >/dev/null 2>&1; then
        termux-wake-lock
        log "Wake lock acquired."
    else
        log "termux-wake-lock not available (install Termux:API from F-Droid for better reliability)."
    fi
}

release_wakelock() {
    if command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock
    fi
}

cleanup() {
    log "Watchdog received shutdown signal. Exiting."
    release_wakelock
    exit 0
}

trap cleanup SIGTERM SIGINT

cd "$BOT_DIR" || { echo "Cannot cd to $BOT_DIR"; exit 1; }

log "=========================================="
log "Watchdog started. Bot directory: $BOT_DIR"
log "=========================================="

acquire_wakelock

while true; do
    rotate_log

    log "Starting bot.py (crash count so far: $CRASH_COUNT)..."
    python bot.py >> "$LOG" 2>&1
    EXIT_CODE=$?

    if [ "$EXIT_CODE" -eq 0 ]; then
        # Clean exit — probably a manual stop via stop.sh
        log "Bot exited cleanly (exit code 0). Watchdog stopping."
        break
    fi

    CRASH_COUNT=$((CRASH_COUNT + 1))
    log "Bot crashed with exit code $EXIT_CODE (total crashes: $CRASH_COUNT)."
    log "Restarting in ${RESTART_DELAY}s..."
    sleep "$RESTART_DELAY"
done

release_wakelock
log "Watchdog finished."
