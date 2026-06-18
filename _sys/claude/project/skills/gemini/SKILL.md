---
name: gemini
description: "Gemini-specific monitoring — usage stats (zero token), collab log view, Axis execution. For STATUS/TOGGLE/RATIO (common to all peers) use /peer skill. Use for: gemini usage, axis run, collab-log view, gemini status, 제미나이 상태, 사용량, 협업 로그, axis 실행."
---

# Gemini Integration Skill

Gemini-specific actions: STATUS (CLI gate check), USAGE, COLLAB, AXIS.
For common peer management (TOGGLE, RATIO across all peers) → use `/peer` skill.

## Trigger Mapping

| User Request | Action |
|-------------|--------|
| "gemini status", "is gemini on", "gemini 상태" | → STATUS |
| "gemini usage", "how many today", "axis count", "gemini 사용량" | → USAGE |
| "collab log", "today's axis history", "협업 로그" | → COLLAB |
| "gemini on/off", "enable/disable gemini", "gemini 켜기/끄기" | → TOGGLE (delegates to /peer) |
| "run axis A", "axis-H", "axis 실행" | → AXIS |

> **RATIO** (`collab_rate` 변경) → `/peer` skill로 이동. `collab_rate`는 모든 피어에 공통.

---

## ACTION: STATUS

Check current Gemini CLI gate (install + auth check).

1. PowerShell: `cmd /c "P:\_sys\gemini\gemini-status.bat"`
2. Read `_sys\gemini\status.json`
3. Report:
   - **ON**: "Gemini ready. Axis calls today: {calls_today}."
   - **OFF**: "Gemini OFF — reason: {reason}"
     - `not_installed` → Gemini CLI not installed (`npm i -g @google/gemini-cli`)
     - `not_authenticated` → Auth required (`gemini auth`)
     - `api_error` / `manual_override` → Manual or API error

For full peer health (all peers): use `/peer status`.

---

## ACTION: USAGE

Zero token — local file parsing only.

1. PowerShell: `cmd /c "P:\_sys\gemini\gemini-usage.bat"`
2. Read `_sys\gemini\usage.json`
3. Dashboard output:

```
[Gemini Usage] {date}
Direct CLI : {sessions_today} sessions, {messages_today} messages
Axis calls : {calls_today} (consecutive failures: {consecutive_failures})
  A={by_axis.A}  B={by_axis.B}  C={by_axis.C}  D={by_axis.D}  D+={by_axis.D+}
  E={by_axis.E}  F={by_axis.F}  G={by_axis.G}  H={by_axis.H}
Last call  : {axis_calls.last_axis} @ {last_call_ts}
Total today: {total_interactions_today}
```

---

## ACTION: COLLAB

View today's collaboration log.

1. Get today's date: `Get-Date -Format yyyy-MM-dd`
2. Read `_archive\collab-log\{YYYY-MM-DD}.md`
   - If file missing: "No collab log for today ({date}) — no Axis calls made."
3. Summarize by section header (`## [HH:MM:SS] Axis-X`)

---

## ACTION: TOGGLE

Delegates to `/peer` skill for hub.py gate control.

Quick reference:
- **OFF**: `python P:\_sys\core\hub.py peer-quarantine --peer gc --reason "manual"`
- **ON**: `python P:\_sys\core\hub.py peer-recover --peer gc`

Verify after: run STATUS to confirm gate state.

---

## ACTION: AXIS

**Always** check STATUS first (`GEMINI_MODE=ON` required).

| Axis | Script | Limit | Description |
|------|--------|-------|-------------|
| A | portability-auditor agent | **Max 3/day** | Full-corpus portability scan |
| B | `_sys\checks\check-versions.bat` | Unlimited | Tool version verification |
| C | `_sys\hooks\ctx-end.bat` | Session end | Session summary |
| D | Manual Gemini call | Unlimited | Syntax/policy check |
| D+ | `_sys\hooks\ctx-save.bat` | Unlimited | Mid-session checkpoint |
| E | `_sys\checks\check-agents.bat` | Unlimited | Agent audit |
| F | `_sys\checks\check-deps.bat` | Unlimited | Script dependency map |
| G | `_sys\cli\git-draft.bat` | Unlimited | Commit message draft |
| H | `_sys\checks\check-health.bat` | Unlimited | Context health check |
| Q | `_sys\cli\msg.bat ask --to gemini` | Unlimited | Sync consult — Gemini first (ratio 5+) |
| R | `_sys\cli\batch-review.bat` | Manual | Uncommitted diff batch review |

**Axis-A daily limit exceeded**: "Axis-A already used 3 times today. Recommend running tomorrow."

After execution, `collab-log.bat` automatically records to `_archive\collab-log\{date}.md`.
