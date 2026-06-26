# Specific — ag (AntiGravity)
> Delta-only from general/*. Status: ACTIVE (gc replacement).

---

## Permission Profile & Flags
```
agy --dangerously-skip-permissions -p {query} --print-timeout 60m
```
- **Inline prompt:** Uses inline `-p {query}`. `agy` ignores `-p -` (stdin).
- **`--print-timeout 60m`:** Child-process output ceiling to prevent self-termination before the hub's authoritative 300s deadline.
- **Windows PTY:** `agy` writes to Windows Console API. `requires_pty=true` is mandatory in `orchestration.json` (subprocess.PIPE hangs).

## Session & State (`session_mode: reuse`)
- **Durable Store:** `AGY_CONFIG_HOME/conversations/*.db` and `implicit/` are durable. `agy -p` natively auto-continues this ambient state even without a `--conversation` flag.
- **IPC Stateless Home:** To prevent A6 contamination (hub inheriting prior interactive sessions), `peers.json` declares an `ipc_stateless_home` (`_sys/antigravity/ipc-config/`).
  - Before IPC asks, hub seeds auth/models (`settings.json`, `installation_id`, `AGY.md`, `keybindings.json`, `status.json`, `usage.json`) from `config/`.
  - Hub recreates `conversations/` and `implicit/` EMPTY so the ask is stateless.
  - Temporarily repoints `AGY_CONFIG_HOME` and `GEMINI_DIR` to this directory.

## Runtime Profiles
| Profile | Runtime model |
|---|---|
| `ag.standard` | `Gemini 3.5 Flash (Low)` |
| `ag.effort` | `Gemini 3.5 Flash (High)` |
| `ag.deepthink` | `Gemini 3.1 Pro (High)` |

*(Note: `agy models` writes via Windows Console API. Model discovery requires a PTY).*

## Directory Layout & Entry
```
_sys/antigravity/
├── config/                 ← INTERACTIVE home (durable; never mutated by hub IPC)
│   ├── AGY.md              ← session instructions
│   ├── conversations/      ← durable session .db store
│   └── implicit/           ← durable implicit context
├── ipc-config/             ← STATELESS IPC home (A6; gitignored, runtime-generated)
└── health.json             ← peer health (runtime-generated)
```
- **Entry:** `_sys/cli/agy.bat` → `agy_entry.py`
- **Config Env:** `CODEX_HOME`-style env var points to `_sys/antigravity/config/`

## Context and Collaboration
*(Delta from general/protocol.md + general/lifecycle.md.)*
- **PTY transport:** ag is the only PTY peer — liveness is heartbeat-based (zombie timeout), not a hard process deadline; `ag.deepthink` may think silently for long stretches without being a hang.
- **Stateless IPC:** hub asks run in the stateless `ipc-config/` home, so ag does NOT inherit prior interactive room context unless explicitly seeded; collaboration context must travel in the ask envelope.
