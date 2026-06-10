# Gemini Agent Context
> Last updated: 2026-06-05
> Static topology only. Dynamic state → `.ai/state.json` (hub.py status).

## Active Room
Room ID: `room-7fb9` (ACTIVE)
Blackboard: `.ai/sessions/room-7fb9/handoff.md`
State file: `.ai/state.json`

## Key Policy Files
- P2P protocol + consensus: `PROTOCOL.md v3.3` (§P-0~P-10, §C-0)
- Coding conventions: `CONVENTION.md`
- Claude-facing rules: `CLAUDE.md` (project) + `_sys\claude\config\CLAUDE.md` (global)
- Agent topology: `_sys\claude\agent\CONTEXT.md`

## Collaboration Policy
- Full policy: `PROTOCOL.md §C-0` (COLLAB_RATE)
- Adaptive rate: R:0=read-only, R:3=workspace/, R:5=_sys/, R:10=constitutional docs
- IPC compact syntax: ACK/NACK/FC/PROC (LLM-level convention — not yet enforced in hub.py)

## Gemini Axis Map
- A: portability-auditor full-corpus (≤500k tok, max 3/day)
- B: check-versions.bat | C: ctx-end session summary | D: inline syntax check
- D+: ctx-save mid-summary (opt-in) | E: check-agents.bat | F: check-deps.bat
- G: git-draft.bat | H: check-health.bat | I: check-risk.bat (Phase 1.5)
→ Token budgets: `CONVENTION.md §3-4-D`

## Context Health Thresholds (Axis-H)
GREEN <600KB | YELLOW 600KB–1.2MB | RED >1.2MB

## Practical Figures
- Gemini quality limit: ~500k tokens | Quota signal: `429` (not failure XML)
- NumericalClassifierStrategy non-zero on success → use file-exist check, not errorlevel
