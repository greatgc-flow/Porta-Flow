# Statusline & Diagnostic (diag) System Architecture
> **Date**: 2026-06-25
> **Topic**: CLI Statusline JSON Pipeline & `diag` command

## 1. Overview
This document serves as a recovery and architecture reference for the peer statusline format and the global `diag` diagnostic command.

## 2. Statusline Pipeline (JSON)
- **Problem Resolved**: The CLI wrappers originally relied on `health.json` to extract `session_token_count`. However, because native binaries (`agy`, `cc`, `cx`) stream tokens, they do NOT update `health.json` in real-time (to avoid SSD wear). This caused the context in the status bar to show `0/0`.
- **Current Pipeline**:
  - `agy` and `cc` Native Binaries → Output Live Status JSON to `stdout` / `stdin`.
  - Python Wrappers (`ag_statusline.py`, `claude_entry.py`) intercept this.
  - Bash adapters (`_sys/antigravity/config/statusline-command.sh` & `_sys/claude/config/statusline-command.sh`) **intercept the JSON using `tee` or direct file writing** to create a live dump (`status_input.log` or `ag_stdin.log`).
  - The JSON is piped to `_sys/ai/common/statusline/statusline-unified.sh`.
- **statusline-unified.sh Modifications**:
  - Handles `jq` extraction of `.context_window`, `.rate_limits`, and `.quota`.
  - Natively parses UNIX timestamps (`resets_at`: e.g., `1782315600`) and UTC strings (`reset_time`: e.g., `"2026-06-24T15:54:26Z"`).
  - Converts all reset times to **Local OS Time** dynamically using `date -d`.
  - Appends `effort` (e.g., `model_reasoning_effort`) to the model string (e.g., `Opus 4.8 (high)`).

## 3. Diagnostic Command (`diag`)
- **Path**: `_sys/cli/diag.bat` (and `_sys/cli/diag.py`)
- **Purpose**: Provides a unified dashboard for all peer states, bypassing the stale `health.json` by directly reading the live JSON intercepts.
- **Data Sources**:
  - **AG (Antigravity)**: Reads `_sys/cli/ag_stdin.log`. Extracts Gemini 5H/7D quotas + Claude(3P) 5H/7D quotas.
  - **CC (Claude)**: Reads `_sys/claude/config/status_input.log`. Extracts cost, 5H/7D quotas, context.
  - **CX (Codex)**: Reads the local SQLite DB (`_sys/codex/config/state_5.sqlite`) natively (Read-Only mode) to query `tokens_used` and `reasoning_effort` from the `threads` table, as Codex does not output JSON statuslines.
  - **Health Backup**: Falls back to `health.json` for quarantine and gate status.

## 4. Recovery / Rollback Instructions
- If the status bar breaks due to upstream JSON schema changes (e.g., Anthropic changing `resets_at` to another key):
  - Check the intercepted logs: `_sys/cli/ag_stdin.log` or `_sys/claude/config/status_input.log`.
  - Update the `jq` fallback queries in `_sys/ai/common/statusline/statusline-unified.sh`.
- If `diag` crashes:
  - Verify that `_sys/codex/config/state_5.sqlite` is not strictly locked (we use `?mode=ro`).
  - Verify that the intercepted JSON logs are valid JSON format.
