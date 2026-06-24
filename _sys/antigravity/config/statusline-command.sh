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

# Health data enrichment removed. agy natively provides context_window and quota in stdin.

if [ -f "$UNIFIED" ]; then
  echo "$input" | bash "$UNIFIED" "ag"
else
  # Fallback: minimal inline output if unified script is missing
  model=$(echo "$input" | jq -r '.model // "Unknown"')
  printf "ag:%s (unified script missing)" "$model"
fi
