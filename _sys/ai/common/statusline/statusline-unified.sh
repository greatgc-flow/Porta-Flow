#!/usr/bin/env bash
# ============================================================
# statusline-unified.sh — General statusline formatter
# Location: _sys/ai/common/statusline/
#
# Usage:  echo "$json_input" | bash statusline-unified.sh <peer_id>
#
# This script receives peer-specific JSON on stdin and formats
# it into the unified statusline format:
#   {peer}:{model} | ctx:{used}k/{total}k ({pct}%) | {dir} ({branch}) | 5h:{X}% 7d:{Y}%
#
# Peer adapters (cc/ag) call this script with their own JSON.
# ============================================================
set -euo pipefail

PEER_ID="${1:-??}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYS_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

input=$(cat)

# ── 1. Model Name ─────────────────────────────────────────
model=$(echo "$input" | jq -r 'if .model_name then .model_name elif (.model | type) == "object" then .model.display_name elif (.model | type) == "string" then .model else "Unknown" end')

# ── 2. Context Usage ──────────────────────────────────────
used_tokens=$(echo "$input" | jq -r '.context_used_tokens // .context_window.total_input_tokens // 0')
total_tokens=$(echo "$input" | jq -r '.context_total_tokens // .context_window.context_window_size // 0')
used_pct=$(echo "$input" | jq -r '.context_used_pct // .context_window.used_percentage // empty')

if [ -n "$used_pct" ] && [ "$total_tokens" -gt 0 ] 2>/dev/null; then
  ctx_str=$(printf "%dk/%dk (%.0f%%)" "$((used_tokens/1000))" "$((total_tokens/1000))" "$used_pct")
else
  ctx_str="${used_tokens}/${total_tokens}"
fi

# ── 3. Directory & Git Branch ─────────────────────────────
cwd=$(echo "$input" | jq -r '.cwd // .workspace.current_dir // ""')
short_cwd=$(basename "$cwd" 2>/dev/null || echo "$cwd")

git_branch=""
if [ -n "$cwd" ] && [ -d "$cwd" ]; then
  git_branch=$(git -C "$cwd" --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null || true)
fi

location="$short_cwd"
[ -n "$git_branch" ] && location="$short_cwd ($git_branch)"

# ── 4. Rate Limits ────────────────────────────────────────
five_pct=$(echo "$input" | jq -r '.rate_5h_pct // .rate_limits.five_hour.used_percentage // empty')
week_pct=$(echo "$input" | jq -r '.rate_7d_pct // .rate_limits.seven_day.used_percentage // empty')
five_reset=$(echo "$input" | jq -r '.rate_5h_reset // .rate_limits.five_hour.reset_at // empty')

rate_parts=""
if [ -n "$five_pct" ]; then
  rate_parts=$(printf "5h:%.0f%%" "$five_pct")
  if [ -n "$five_reset" ]; then
    reset_hm=$(echo "$five_reset" | grep -oE '[0-9]{2}:[0-9]{2}' | head -1)
    [ -n "$reset_hm" ] && rate_parts="${rate_parts}[↻${reset_hm}]"
  fi
else
  rate_parts="5h:N/A"
fi
if [ -n "$week_pct" ]; then
  rate_parts="${rate_parts} $(printf "7d:%.0f%%" "$week_pct")"
else
  rate_parts="${rate_parts} 7d:N/A"
fi

# ── 5. Hub Status (optional) ─────────────────────────────
hub_str=""
hub_state_file="$SYS_DIR/../.ai/state.json"
if [ -f "$hub_state_file" ]; then
  hub_phase=$(jq -r '.phase // "idle"' "$hub_state_file" 2>/dev/null || echo "idle")
  hub_str=" | hub:${hub_phase}"
fi

# ── Output ────────────────────────────────────────────────
printf "%s:%s | ctx:%s | %s | %s%s" "$PEER_ID" "$model" "$ctx_str" "$location" "$rate_parts" "$hub_str"
