# User Manual - Portable Multi-Peer Dev Environment
> Condensed from USER_MANUAL.md. Full version archived in `_sys/docs/history/` (pre-docs-v2 SSOT).

---

## Quick Start

```
1. register.bat          # register on new PC (SUBST P: + context menu)
2. _sys\cli\claude.bat   # launch Claude Code peer
3. _sys\cli\gemini.bat   # launch Gemini CLI peer
```

---

## Command Wrappers

Use bare commands from any workspace: `hub`, `diag`, `msg`, `manage`, `git-draft`, `batch-review`, `set-collab-rate`, and the peer launchers (`claude`, `codex`, `agy`, `gemini`). `_sys\cli` is the single PATH entry for these operator commands. cmd/PowerShell resolve the `.bat` wrappers; Git Bash resolves the extensionless shims. Do not call `python _sys/core/hub.py ...` from arbitrary workspaces.


## Daily Workflow

### Session Start
```
hub init-session --agent cc     # (auto-called by claude.bat)
hub peer-status                 # all peers at a glance (canonical status)
```

### Check Peers
```
hub peer-status                 # all peers at a glance (canonical status)
hub health-precheck --peer ag   # before routing ask to a peer
hub health-check                # (Audit/Maintenance only) raw local health reads
diag                             # diagnostic dashboard (context, quotas, sessions, cost)
diag --watch 5                   # live refresh view; default 5s, rejects values below 2s
diag --json --watch 5            # NDJSON telemetry stream for automation
```

### Ask a Peer
```
hub ask --to gc --query-file <file.txt>
```
Query file format: TASK/CONTEXT/QUESTION in English.

### End of Session
```
ctx-save     # save session context (mid-session checkpoint)
ctx-end      # end-of-day: archive + cleanup
```

---

## Peer Reference & Topology

`_sys/ai/orchestration.json` is the canonical topology source. A peer is a provider-level participant. Its runtime nodes are generated from the profile tree in memory (e.g., standard, effort, deepthink).

| Peer | CLI | State | Standard | Effort | Deepthink |
|------|-----|-------|----------|--------|-----------|
| `cc` | Claude Code | Active | Haiku 4.5 / low | Sonnet 4.6 / high | Opus 4.8 / max |
| `ag` | Antigravity | Active | Gemini 3.5 Flash / low | Gemini 3.5 Flash / high | Gemini 3.1 Pro / high |
| `cx` | Codex | Active | GPT-5.4-mini / low | GPT-5.5 / high | GPT-5.5 / xhigh |
| `ca` | Claude alternate | Disabled | Inherited disabled | Inherited disabled | Inherited disabled |
| `gc` | Gemini CLI | Disabled | Inherited disabled | Inherited disabled | Inherited disabled |

The default profile is deliberately low cost. The hub analyzes each request and can promote or demote it among `standard`, `effort`, and `deepthink`.

---

## Collaboration Rate (collab_rate)

Current value: `_sys/ai/protocol.json["collab_rate"]["current"]`

| Rate | When to use |
|:----:|:-----------|
| 0 | Fully solo (read-only exploration) |
| 3 | Normal code work in workspace/ |
| 5 | Changing `_sys/` scripts |
| 8 | Multi-file `_sys/` changes |
| 10 | Protocol/hub.py changes (all peers must consent) |

---

## Common Commands

```
hub consensus-propose --subject "..." --voters cc,gc --from cc
hub consensus-vote --round-id r-XXXX --voter gc --vote agree
hub consensus-sweep                    # clean stalled rounds
hub directive-list                     # show active runtime directives
hub peer-quarantine --peer gc --reason quota
hub peer-recover --peer gc --reason quota_reset
hub elect-leader --needs code --effort mid
hub task-checkpoint --id <id> --peer cc --msg "..."
```

---

## New PC Setup

1. Clone/copy the portable folder to any drive
2. Run `register.bat` (creates SUBST P: + right-click "Open with Claude Code")
3. Run `_sys\cli\claude.bat` to launch

To move to a new drive: run `unregister.bat` on old PC, then `register.bat` on new PC.

---

## Maintenance

```
_sys\checks\check-health.bat      # verify peer health + deps
_sys\checks\check-portability.bat # verify no host-path leaks
_sys\tests\run-tests.bat --all    # full test suite
```
