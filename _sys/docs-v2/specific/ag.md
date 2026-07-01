# Specific — ag (AntiGravity)
> Delta-only from general/*. Status: ACTIVE (gc replacement).

---

## Permission Profile & Flags
```
agy --dangerously-skip-permissions -p {query} --print-timeout 60m
```
- **Inline prompt:** Uses inline `-p {query}`. `agy` ignores `-p -` (stdin).
- **`--print-timeout 60m`:** Child-process output ceiling so `agy` does not self-terminate before the hub's liveness guard fires. There is **no hard wall-clock deadline** (orchestration `timeout: 0`); liveness is governed by `zombie_timeout_sec` (silence-based; `ag.deepthink` up to 7200s). The 300s `pty_lease_sec` is a lease-renew / orphan-cleanup window, **not** an execution deadline.
- **Windows PTY:** `agy` writes to Windows Console API. `requires_pty=true` is mandatory in `orchestration.json` (subprocess.PIPE hangs).

## Session & State (`session_mode: reuse`)
- **Durable home (verified 2026-07-01):** ag uses the durable config home
  (`AGY_CONFIG_HOME=config`). There is **no clean/stateless IPC home** —
  `ipc_stateless_home` is **not** configured in `peers.json` (an earlier design,
  now inactive; the `_prepare_ipc_stateless_home` code remains but is unused for ag).
- **A6 isolation via scoped id, not home-wipe:** `agy -p` auto-continues ambient
  state, so IPC asks are isolated by an explicit scoped `--conversation
  <room:ag.profile>` id (`AgyAdapter`), which pins the conversation instead of
  wiping the home. (Empirically a fresh scope does not inherit prior context.)
- **Reuse lifecycle (unified):** the hub persists + reuses that id via the general
  path-agnostic `_store_session_from_result` — same lifecycle as cc/cx.
- **Continuity caveat:** the id is reused, but `agy -p` one-shot mode does **not**
  currently restore prior conversation history (verified) — effective continuity is
  limited pending an agy resume/continue mode; collaboration context should still
  travel in the ask envelope.

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
│   ├── conversations/      ← durable session .db store (used by IPC too)
│   └── implicit/           ← durable implicit context
└── health.json             ← peer health (runtime-generated)
```
- **Entry:** `_sys/cli/agy.bat` → `agy_entry.py`
- **Config Env:** `AGY_CONFIG_HOME`/`GEMINI_DIR` → `_sys/antigravity/config/` (durable; IPC uses the same home — no separate `ipc-config`).

## Context and Collaboration
*(Delta from general/protocol.md + general/lifecycle.md.)*
- **PTY transport:** ag is the only PTY peer — liveness is heartbeat-based (zombie timeout), not a hard process deadline; `ag.deepthink` may think silently for long stretches without being a hang.
- **IPC isolation via scoped id:** hub asks reuse the durable home but pin a scoped `--conversation <room:ag.profile>` id, so ag does NOT inherit prior interactive room context; collaboration context must travel in the ask envelope. (Actual history restore in `-p` mode is a pending CLI limitation — see Session & State.)
