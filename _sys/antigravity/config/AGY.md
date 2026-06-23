# Antigravity Peer Configuration

> Protocol 4.2 | Node ID: `ag` | Updated: 2026-06-24

`ag` is the active Antigravity CLI peer. Runtime topology, lifecycle, profiles,
models, permissions, and roles are defined in `_sys/ai/orchestration.json`.

## Session Contract

- Shared rules: `_sys/ai/common/peer-rules.md`
- Runtime policy: `_sys/ai/protocol.json`
- Health state: `_sys/antigravity/health.json`
- IPC entry point: `_sys/cli/msg.bat`

## Execution & Stateless IPC

- **Launch:** Hub `ask --to ag` invokes the native `_sys\tools\agy\agy.exe` DIRECTLY via `AgyAdapter`. This bypasses `agy.bat` to avoid context-fill contamination. (`agy_entry.py` / `agy.bat` are used for INTERACTIVE launch only).
- **Arguments:** `ag` is PTY-only, inline `-p {query}` (agy ignores stdin); `--print-timeout 60m`.
- **Session Mode:** `session_mode: none` — no hub-managed session reuse; hub never sends `-c`/`--continue`/`--conversation`.
- **Environment:** IPC `ag` calls run against a conversation/implicit-CLEAN stateless home (`ipc-config`, seeded from `config/`) so each ask is stateless. The interactive `config/` home (durable conversations/implicit) remains untouched.

## Profile Defaults

| Profile | Runtime model | Effort |
|---------|---------------|--------|
| `standard` | Gemini 3.5 Flash | Low |
| `effort` | Gemini 3.5 Flash | High |
| `deepthink` | Gemini 3.1 Pro | High |

The standard profile is the terminal default. Hub requests may be promoted or
demoted automatically.

## IPC Rules

- Use asynchronous `send` and `check` for normal peer communication.
- Use synchronous `ask` only for self-contained requests requiring a response.
- Do not recursively invoke `ag` from an active `ag` PTY session.
- Use hub consensus actions rather than editing consensus state directly.

```bat
_sys\cli\msg.bat check --target ag
_sys\cli\msg.bat send --from ag --to cx --msg "Review requested"
_sys\cli\msg.bat health-update --peer ag --status GREEN
_sys\cli\msg.bat checkpoint --agent ag --msg "Checkpoint recorded"
```
