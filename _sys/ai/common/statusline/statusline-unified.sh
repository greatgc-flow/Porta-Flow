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
effort=$(echo "$input" | jq -r '
  if (.model_reasoning_effort | type) == "object" then .model_reasoning_effort.level // .model_reasoning_effort
  elif (.effort | type) == "object" then .effort.level // .effort
  else (.model_reasoning_effort // .effort) end | select(.!=null)
' 2>/dev/null | tr -d '\n\r' | sed 's/[{}]//g' | sed 's/"//g')

if [ -n "$effort" ] && [ "$effort" != "null" ]; then
  if ! echo "$model" | grep -qi "$effort"; then
    model="${model} (${effort})"
  fi
fi

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
five_pct=$(echo "$input" | jq -r '.rate_5h_pct // .rate_limits.five_hour.used_percentage // (if .quota."gemini-5h".remaining_fraction != null then (1 - .quota."gemini-5h".remaining_fraction) * 100 else empty end) // empty')
week_pct=$(echo "$input" | jq -r '.rate_7d_pct // .rate_limits.seven_day.used_percentage // (if .quota."gemini-weekly".remaining_fraction != null then (1 - .quota."gemini-weekly".remaining_fraction) * 100 else empty end) // empty')
five_reset=$(echo "$input" | jq -r '.rate_5h_reset // .rate_limits.five_hour.reset_at // .rate_limits.five_hour.resets_at // .quota."gemini-5h".reset_time // empty')
week_reset=$(echo "$input" | jq -r '.rate_7d_reset // .rate_limits.seven_day.reset_at // .rate_limits.seven_day.resets_at // .quota."gemini-weekly".reset_time // empty')

rate_parts=""
if [ -n "$five_pct" ]; then
  rate_parts=$(printf "5h:%.0f%%" "$five_pct")
  if [ -n "$five_reset" ]; then
    if [[ "$five_reset" =~ ^[0-9]+$ ]]; then
      reset_hm=$(date -d "@$five_reset" +"%H:%M" 2>/dev/null)
    else
      reset_hm=$(date -d "$five_reset" +"%H:%M" 2>/dev/null || echo "$five_reset" | grep -oE '[0-9]{2}:[0-9]{2}' | head -1)
    fi
    [ -n "$reset_hm" ] && rate_parts="${rate_parts}[↻${reset_hm}]"
  fi
else
  rate_parts="5h:N/A"
fi
if [ -n "$week_pct" ]; then
  week_str=$(printf "7d:%.0f%%" "$week_pct")
  if [ -n "$week_reset" ]; then
    if [[ "$week_reset" =~ ^[0-9]+$ ]]; then
      reset_md=$(date -d "@$week_reset" +"%m/%d" 2>/dev/null)
    else
      reset_md=$(date -d "$week_reset" +"%m/%d" 2>/dev/null || echo "$week_reset" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | awk -F'-' '{print $2"/"$3}' | head -1)
    fi
    [ -n "$reset_md" ] && week_str="${week_str}[↻${reset_md}]"
  fi
  rate_parts="${rate_parts} ${week_str}"
else
  rate_parts="${rate_parts} 7d:N/A"
fi

# ── 5. Hub Status (optional) ─────────────────────────────
hub_str=""
hub_state_file="$SYS_DIR/../.ai/state.json"
if [ -f "$hub_state_file" ]; then
  hub_phase=$(jq -r '.phase // "idle"' "$hub_state_file" 2>/dev/null || echo "idle")
  hub_room=$(jq -r '.room_id // empty' "$hub_state_file" 2>/dev/null)
  
  if [ -n "$hub_room" ]; then
    hub_str=" | hub:${hub_phase} [${hub_room}]"
  else
    hub_str=" | hub:${hub_phase}"
  fi
fi

# ── Output ────────────────────────────────────────────────
printf "%s:%s | ctx:%s | %s | %s%s" "$PEER_ID" "$model" "$ctx_str" "$location" "$rate_parts" "$hub_str"
