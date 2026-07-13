#!/bin/bash
# session-limit-guard: report Claude 5-hour session usage from the statusline cache.
#
# Usage: check_usage.sh [threshold_pct]      (default 90)
# Exit codes:
#   0  under threshold, or the cached window has already reset
#   2  at/over threshold -> pause
#   3  no usage data available (run setup_statusline_cache.sh)
#
# Data source: ~/.claude/state/rate-limits.json, written by the user's
# statusline command on every statusline refresh (i.e. after every API
# response in any active Claude Code session). Override path with
# SLG_CACHE_FILE for testing.
set -u

THRESHOLD="${1:-90}"
CACHE="${SLG_CACHE_FILE:-$HOME/.claude/state/rate-limits.json}"

if [ ! -f "$CACHE" ]; then
  echo "status=NO_DATA reason=cache_missing hint='run setup_statusline_cache.sh (same directory) to install the statusline cache hook; data appears after the first API response in a session with a Pro/Max subscription'"
  exit 3
fi

now=$(date +%s)
cached_at=$(jq -r '.cached_at // 0' "$CACHE")
age=$(( now - cached_at ))

five_pct=$(jq -r '.rate_limits.five_hour.used_percentage // empty' "$CACHE")
five_reset=$(jq -r '.rate_limits.five_hour.resets_at // empty' "$CACHE")
seven_pct=$(jq -r '.rate_limits.seven_day.used_percentage // empty' "$CACHE")

if [ -z "$five_pct" ]; then
  echo "status=NO_DATA reason=no_five_hour_field age_s=$age"
  exit 3
fi

five_pct_int=$(printf '%.0f' "$five_pct")

out="source=statusline-cache age_s=$age five_hour_pct=$five_pct"
if [ -n "$five_reset" ]; then
  resets_in=$(( five_reset - now ))
  local_time=$(date -r "$five_reset" '+%Y-%m-%d %H:%M %Z' 2>/dev/null || date -d "@$five_reset" '+%Y-%m-%d %H:%M %Z' 2>/dev/null)
  out="$out resets_at=$five_reset resets_in_s=$resets_in resets_at_local=\"$local_time\""
fi
if [ -n "$seven_pct" ]; then
  out="$out seven_day_pct=$seven_pct"
  seven_pct_int=$(printf '%.0f' "$seven_pct")
  if [ "$seven_pct_int" -ge "$THRESHOLD" ]; then
    out="$out weekly_warning=1"
  fi
fi
echo "$out"

# If the cached window's reset time has passed, the cached percentage is
# stale-high: the window reset but no API response has refreshed the cache yet.
if [ -n "$five_reset" ] && [ "$now" -ge "$five_reset" ]; then
  echo "status=OK note=window_reset_since_cache threshold=$THRESHOLD"
  exit 0
fi

if [ "$five_pct_int" -ge "$THRESHOLD" ]; then
  echo "status=PAUSE threshold=$THRESHOLD"
  exit 2
fi

echo "status=OK threshold=$THRESHOLD"
exit 0
