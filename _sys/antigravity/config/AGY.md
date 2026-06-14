# AGY.md — Antigravity (ag) Session Glue File
> Protocol v4.1 | Node ID: `ag` | Updated: 2026-06-12

## Role
agy is the Antigravity CLI peer. Capabilities: shell-scripts, quick-cli, file-ops,
system-orchestration, real-time-feedback-loop, image-generation.

## Session Start, IPC, Collaboration Rules

→ See `_sys/ai/common/peer-rules.md` for shared invariants (peer equality, IPC paths, hub commands, session start sequence, health self-reporting).

**ag-specific:** `agy_entry.py` runs the session start sequence automatically — steps 1-4 of the common checklist are pre-executed.
**ag output artifact:** `.ai/out/ag.last.md` — written by ag for other peers to consume.

## Shared IPC Paths (ag-specific additions)
| Path | Purpose |
|------|---------|
| `.ai/consensus/{round_id}.json` | Consensus votes — **direct JSON write only** (no hub.py ask, PTY deadlock risk) |
| `.ai/out/ag.last.md` | ag output artifact |

> Full IPC path table: `_sys/ai/common/peer-rules.md §2`

## Consensus Vote Policy (CRITICAL)
**Never use `hub.py ask` for consensus votes** — PTY deadlock risk.
- Preferred: write vote directly to `.ai/consensus/{round_id}.json`
- Fallback: `hub.py send --to cc` relay

```json
// .ai/consensus/{round_id}.json vote entry
{ "voter": "ag", "vote": "AGREE", "reason": "...", "voted_at": "..." }
```

## PTY Mode Rules
| Mode | When to use |
|------|-------------|
| async (send/check) | Default — non-blocking message delivery |
| sync/PTY (ask) | Only for self-contained queries needing immediate response |
| consensus votes | **Direct JSON write only** — never ask |

## Hub Commands (ag-specific)
```bash
hub.py check --target ag                          # read inbox
hub.py health-update --peer ag --status GREEN     # health report
hub.py send --to {peer} --msg "..."               # async message
hub.py checkpoint --agent ag --msg "..."          # mid-session handoff note
```
> Full command reference: `_sys/ai/common/peer-rules.md §3`

## Protocol Config
- Master config: `_sys/ai/protocol.json`
- Peer registry: `_sys/ai/peers.json`
- Health file: `_sys/antigravity/health.json`
- Common peer rules: `_sys/ai/common/peer-rules.md`
- Docs: `_sys/docs/protocol-antigravity.md`
