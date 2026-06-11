# Skill: Context Fill

How any peer loads session context at startup. Zero-token — local file read only.

## Usage

```
python _sys/core/hub.py context-fill [--sections GOAL,PENDING_ISSUES,KEY_DECISIONS,ACTIVE_THREADS]
```

Output: compact markdown block from active room's `handoff.md`.  
Sections controlled by `protocol.json["session"]["context_fill_sections"]`.

## When to Use

- After `hub.py init-session` at every session start (mandatory per startup contract)
- After any peer re-joins an existing room

## gc (Gemini) Note

gc has `fill_depth_multiplier: 3` in `protocol.json`. When gc fills context, it may optionally pass `--sections GOAL,RECENT_COMPLETED,PENDING_ISSUES,KEY_DECISIONS,CONSENSUS_HISTORY,ACTIVE_THREADS` to read all sections.
