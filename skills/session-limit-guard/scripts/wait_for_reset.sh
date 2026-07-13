#!/bin/bash
# session-limit-guard: block until the 5-hour session window resets.
# Run this via the Bash tool with run_in_background: true — when it exits,
# Claude is re-invoked and can resume the task.
#
# Usage: wait_for_reset.sh <resets_at_epoch> [buffer_seconds]
#   resets_at_epoch  the resets_at value reported by check_usage.sh
#   buffer_seconds   extra wait after the reset time (default 120)
set -u

RESETS_AT="${1:?usage: wait_for_reset.sh <resets_at_epoch> [buffer_seconds]}"
BUFFER="${2:-120}"
TARGET=$(( RESETS_AT + BUFFER ))

fmt_time() {
  date -r "$1" '+%H:%M:%S %Z' 2>/dev/null || date -d "@$1" '+%H:%M:%S %Z' 2>/dev/null
}

now=$(date +%s)
total=$(( TARGET - now ))
if [ "$total" -le 0 ]; then
  echo "SESSION_WINDOW_RESET (reset time already passed) at $(fmt_time "$now")"
  exit 0
fi

echo "sleeping ${total}s; session window resets at $(fmt_time "$RESETS_AT"), will wake at $(fmt_time "$TARGET")"

i=0
while :; do
  now=$(date +%s)
  rem=$(( TARGET - now ))
  [ "$rem" -le 0 ] && break
  chunk=$(( rem < 300 ? rem : 300 ))
  sleep "$chunk"
  i=$(( i + 1 ))
  # progress line roughly every 30 minutes
  if [ $(( i % 6 )) -eq 0 ]; then
    now=$(date +%s)
    rem=$(( TARGET - now ))
    [ "$rem" -gt 0 ] && echo "still waiting: $(( rem / 60 ))m remaining"
  fi
done

echo "SESSION_WINDOW_RESET at $(fmt_time "$(date +%s)") — resume the task now"
exit 0
