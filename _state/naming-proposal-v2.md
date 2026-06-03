# Naming & Structure Change Proposal v2
> Round 3 feedback incorporated. Sent for final confirmation (Round 4).

Changes from v1:
- §2-4: `_state/` → `_workspace/` DROPPED (Gemini DISAGREE + Round 1 5/5). Keep `_state/`.
- §2-2: `templates/` retained over scaffold/boilerplate (more universal under _sys/ context).
- §4: GEMINI_RATIO unchanged (acceptable as technical setting).

---

## §1. MECE Structure Fixes (Confirmed, no change from v1)

- `git-draft.bat`, `batch-review.bat` → `_sys/cli/`
- `archive-data.bat` → `_sys/hooks/`
- Delete `_state/collab/` (empty)
- `agent-audit.json`, `script-deps.json` → `_archive/scans/`
- Delete 6 `workspace-*-legacy-*.json` files from `_archive/`

---

## §2. Folder Renames (v2 — consensus)

| Folder | Change | Status |
|--------|--------|--------|
| `_sys/scans/` | → `_sys/checks/` | AGREED |
| `_sys/docs/` | → `_sys/templates/` + SYSTEM_ARCHITECTURE.md → `_sys/` root | AGREED (minor modify noted, templates retained) |
| `_sys/git_config/` | → `_sys/git-config/` | AGREED |
| `_state/` | **KEEP AS `_state/`** | AGREED (workspace rename DROPPED) |
| `_sys/test/` | → `_sys/tests/` | AGREED |

---

## §3. File Renames (v2 — consensus)

| File | Change | Status |
|------|--------|--------|
| `cli/cla.bat` | → `claude.bat` | AGREED (PATH priority check needed) |
| `cli/gem.bat` | → `gemini.bat` | AGREED |
| `cli/msg.bat` | keep | AGREED |
| `hooks/append-log.bat` | → `log-write.bat` | AGREED |
| `hooks/check-gate.bat` | → `ai-check.bat` | AGREED |
| `hooks/collab-log-append.bat` | → `collab-log.bat` | AGREED |
| `checks/scan-env.bat` | → `check-versions.bat` | AGREED |
| `checks/scan-audit.bat` | → `check-agents.bat` | AGREED |
| `checks/scan-health.bat` | → `check-health.bat` | AGREED |
| `checks/scan-risk.bat` | → `check-risk.bat` | AGREED |
| `checks/scan-deps.bat` | → `check-deps.bat` | AGREED |
| ROOT `INSTALL.bat` | → `install.bat` | AGREED |
| ROOT `CLEANUP.bat` | → `cleanup.bat` | AGREED |

---

## §4. Concept Review (v2)

- `GEMINI_RATIO`: **KEEP** (technical setting; acceptable per Gemini Round 3)
- Everything else (hub.py, .ai/, PROTOCOL.md, Axis-A~I, collab-log/): no change

---

**Question for Round 4:** Any remaining objections to v2? Specifically:
1. §2-2: `templates/` instead of scaffold/boilerplate — acceptable?
2. §3-1: `claude.bat`/`gemini.bat` — any PATH conflict concerns beyond what was noted?
3. Any other issues not addressed?
