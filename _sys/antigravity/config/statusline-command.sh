#!/usr/bin/env bash
# ============================================================
# Antigravity / agy (ag) — Statusline Adapter (Specific)
# Delegates to the unified formatter at:
#   _sys/ai/common/statusline/statusline-unified.sh
#
# stdin: JSON from Antigravity CLI TUI
# stdout: formatted statusline string
#
# agy's stdin JSON has fewer fields than Claude's, so this
# adapter enriches the data from health.json before forwarding.
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYS_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
UNIFIED="$SYS_DIR/ai/common/statusline/statusline-unified.sh"
HEALTH_FILE="$SYS_DIR/antigravity/health.json"

input=$(cat)

# Enrich with health.json data (context window, rate limit state)
if [ -f "$HEALTH_FILE" ]; then
  ctx_window=$(jq -r '.context_window // 0' "$HEALTH_FILE" 2>/dev/null || echo "0")
  session_tokens=$(jq -r '.session_token_count // 0' "$HEALTH_FILE" 2>/dev/null || echo "0")
  
  # Calculate percentage
  ctx_pct="0"
  if [ "$ctx_window" -gt 0 ] 2>/dev/null; then
    ctx_pct=$(echo "$session_tokens $ctx_window" | awk '{printf "%.1f", ($1/$2)*100}')
  fi
  
  # Merge health data into the input JSON
  input=$(echo "$input" | jq --arg ct "$session_tokens" --arg cw "$ctx_window" --arg cp "$ctx_pct" \
    '. + {context_used_tokens: ($ct | tonumber), context_total_tokens: ($cw | tonumber), context_used_pct: ($cp | tonumber)}')
fi

if [ -f "$UNIFIED" ]; then
  echo "$input" | bash "$UNIFIED" "ag"
else
  # Fallback: minimal inline output if unified script is missing
  model=$(echo "$input" | jq -r '.model // "Unknown"')
  printf "ag:%s (unified script missing)" "$model"
fi
