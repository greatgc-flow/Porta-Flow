# Specific — ag (AntiGravity)
> Delta from general/*. Status: ACTIVE (gc replacement, 2026-06-19).

---

## Status: ACTIVE

ag is an active consensus voter (cc/ag/cx). Replaces gc after IneligibleTierError (tier_suspended 2026-06-19).

Peer equality means equal governance rights and role eligibility. CLI permission
flags remain adapter-specific under DIR-002.

**Permission profile:**
```
agy --dangerously-skip-permissions -p {query}
```

**Critical Windows note:** agy writes to Windows Console API, not stdout pipes.
`requires_pty=true` is mandatory in orchestration.json. subprocess.PIPE capture hangs indefinitely.

## Runtime Profiles

The available model labels were verified locally through `agy models` using a
Windows PTY on 2026-06-20:

| Profile | Runtime model |
|---|---|
| `ag.standard` | `Gemini 3.5 Flash (Low)` |
| `ag.effort` | `Gemini 3.5 Flash (High)` |
| `ag.deepthink` | `Gemini 3.1 Pro (High)` |

The terminal and root default use `ag.standard`. Each profile passes its model
label through `agy --model`. The CLI's persistent `settings.json` model is not
modified by profile invocation.

`agy models` writes through the Windows Console API. Capturing it with ordinary
stdout returns an empty string; model discovery and validation require a PTY.

## Context and Collaboration

ag receives the common versioned room references. PTY output becomes shared state
only after the hub records or promotes it.

---

## Directory Layout

```
_sys/antigravity/
├── config/
│   ├── AGY.md              ← session instructions
│   ├── brain/              ← reasoning modules (now archived to _archive/reviews/agy/)
│   ├── builtin/            ← built-in commands
│   ├── settings.json       ← agy settings
│   └── log/                ← session logs
├── health.json             ← peer health (runtime-generated)
└── project/
```

---

## Gate & Entry (when active)

- Entry: `_sys/cli/agy.bat` → `agy_entry.py`
- Health: `_sys/antigravity/health.json`
- Config: `CODEX_HOME`-style env var pointing to `_sys/antigravity/config/`
