#!/bin/bash
# session-limit-guard: idempotently install the statusline cache hook.
#
# Claude Code sends `rate_limits` (5-hour + 7-day usage) to the configured
# statusline command after every API response. This script makes sure that
# payload gets cached to ~/.claude/state/rate-limits.json, which
# check_usage.sh reads. No credentials, no network calls.
#
# Exit codes:
#   0  installed (or already installed)
#   2  could not install automatically — manual snippet printed
set -u

MARKER="session-limit-guard cache"
SETTINGS="$HOME/.claude/settings.json"

cache_block() {
  cat <<'EOF'
# --- session-limit-guard cache ---
# Cache rate-limit data for the session-limit-guard skill
# (reads ~/.claude/state/rate-limits.json)
if echo "$input" | jq -e '.rate_limits.five_hour' >/dev/null 2>&1; then
  mkdir -p "$HOME/.claude/state"
  echo "$input" | jq -c '{cached_at: (now | floor), rate_limits: .rate_limits}' \
    > "$HOME/.claude/state/rate-limits.json.$$.tmp" 2>/dev/null \
    && mv -f "$HOME/.claude/state/rate-limits.json.$$.tmp" "$HOME/.claude/state/rate-limits.json"
fi
# --- end session-limit-guard cache ---
EOF
}

manual_instructions() {
  echo "MANUAL_SETUP_REQUIRED: add this block to your statusline script, right after it reads stdin into \$input (e.g. after 'input=\$(cat)'):"
  echo
  cache_block
}

statusline_cmd=$(jq -r '.statusLine.command // empty' "$SETTINGS" 2>/dev/null)

if [ -n "$statusline_cmd" ]; then
  # Find the script file inside the configured command (last *.sh token that exists).
  script_file=""
  for tok in $statusline_cmd; do
    tok_expanded="${tok/#\~/$HOME}"
    case "$tok_expanded" in
      *.sh) [ -f "$tok_expanded" ] && script_file="$tok_expanded" ;;
    esac
  done

  if [ -z "$script_file" ]; then
    echo "statusLine is configured but its command ('$statusline_cmd') is not a plain .sh script I can edit."
    manual_instructions
    exit 2
  fi

  if grep -q "$MARKER" "$script_file"; then
    echo "already_installed: $script_file"
    exit 0
  fi

  if ! grep -qE '^\s*input=\$\(cat\)' "$script_file"; then
    echo "statusline script $script_file doesn't read stdin as 'input=\$(cat)' — not editing it automatically."
    manual_instructions
    exit 2
  fi

  cp "$script_file" "$script_file.bak"
  block_file=$(mktemp)
  cache_block > "$block_file"
  awk -v blockfile="$block_file" '
    { print }
    !done && /^[[:space:]]*input=\$\(cat\)/ {
      while ((getline line < blockfile) > 0) print line
      close(blockfile)
      done = 1
    }
  ' "$script_file.bak" > "$script_file"
  rm -f "$block_file"
  echo "installed: cache block added to $script_file (backup at $script_file.bak)"
  exit 0
fi

# No statusline configured: install a minimal one that caches and shows usage.
target="$HOME/.claude/statusline-command.sh"
if [ -e "$target" ]; then
  echo "no statusLine in settings.json, but $target already exists — not overwriting it."
  manual_instructions
  echo
  echo "Then set it as your statusline in $SETTINGS:"
  echo '  "statusLine": { "type": "command", "command": "sh ~/.claude/statusline-command.sh" }'
  exit 2
fi

{
  echo '#!/bin/sh'
  echo '# Minimal Claude Code statusline (installed by session-limit-guard)'
  echo 'input=$(cat)'
  cache_block
  cat <<'EOF'
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "~"')
case "$cwd" in
  "$HOME"*) cwd="~${cwd#$HOME}" ;;
esac
five=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
printf '%s' "$cwd"
[ -n "$five" ] && printf ' | 5h: %.0f%%' "$five"
EOF
} > "$target"
chmod +x "$target"

cp "$SETTINGS" "$SETTINGS.bak" 2>/dev/null
tmp_settings=$(mktemp)
if jq '.statusLine = {"type": "command", "command": "sh ~/.claude/statusline-command.sh"}' "$SETTINGS" > "$tmp_settings" 2>/dev/null; then
  mv "$tmp_settings" "$SETTINGS"
  echo "installed: wrote $target and set statusLine in $SETTINGS (backup at $SETTINGS.bak)"
  exit 0
else
  rm -f "$tmp_settings"
  echo "wrote $target but could not update $SETTINGS — add this yourself:"
  echo '  "statusLine": { "type": "command", "command": "sh ~/.claude/statusline-command.sh" }'
  exit 2
fi
