# Naming & Structure Change Proposal v1
> For Gemini review — respond with AGREE / DISAGREE / MODIFY per section

Evaluation criterion: Can a developer seeing this project for the first time understand the purpose from the name alone?
Changes must be justified by GENERALITY (industry-standard terms). Internal consistency is NOT a valid reason.

---

## §2. Folder Renames

### §2-1. `_sys/scans/` → `_sys/checks/`
Content: 5 health/quality check scripts (version check, dependency map, risk assessment, context health, agent audit).
Problem: "scans" primarily suggests security scanning (SAST, vulnerability scans) to most developers.
Proposal: rename to `checks/`

### §2-2. `_sys/docs/` → `_sys/templates/`
Content: 2 copy-paste template files (CLAUDE_project.md, CLAUDE_global.md) + 1 architecture doc.
Problem: "docs" implies read-only documentation; primary use is "files to copy and customize".
Proposal: rename to `templates/` + move SYSTEM_ARCHITECTURE.md to `_sys/` root.

### §2-3. `_sys/git_config/` → `_sys/git-config/`
Reason: directory naming convention uses hyphens; underscores are for filenames.

### §2-4. `_state/` → `_workspace/` (KEY QUESTION)
Content: AI agent session artifacts (02_*.md, 03_*.md produced per session by AI agent team)
Problem: "state" overlaps with `.ai/state.json` (IPC state file). Two different "states" in same project.
Proposal: rename to `_workspace/` (VS Code, JetBrains standard term for working area)
Counter: Round 1 gave `_state` 5/5 — clearly conveys "current state" vs `_archive/` (past). Also, `_workspace/` might be confused with the actual project source code workspace.

### §2-5. `_sys/test/` → `_sys/tests/`
Reason: plural is industry convention (pytest, jest, go test).

---

## §3. File Renames

### §3-1. CLI launcher names in `_sys/cli/`
- `cla.bat` → `claude.bat` (problem: "cla" is project-specific abbreviation, meaningless to outsiders)
- `gem.bat` → `gemini.bat` (problem: "gem" = Ruby gem to most developers — wrong association)
- `msg.bat` → keep (clear: message/message bus)
Note: `claude.cmd` and `gemini.cmd` already exist in npm-global (different extension .bat vs .cmd).

### §3-2. Hook script renames in `_sys/hooks/`
- `append-log.bat` → `log-write.bat` ("what does it log?" unclear; generic log writer via hub.py)
- `check-gate.bat` → `ai-check.bat` ("gate" unclear; purpose is checking Gemini service availability)
- `collab-log-append.bat` → `collab-log.bat` (drop redundant "append")

### §3-3. Scan file renames (depends on §2-1)
- `scan-env.bat` → `check-versions.bat` ("env" ambiguous: env settings or version check?)
- `scan-audit.bat` → `check-agents.bat` (audit of what? "agents" is clearer)
- `scan-health.bat` → `check-health.bat` (prefix only)
- `scan-risk.bat` → `check-risk.bat` (prefix only)
- `scan-deps.bat` → `check-deps.bat` (prefix only)

### §3-4. ROOT bat file casing
Current: `INSTALL.bat`, `CLEANUP.bat` (uppercase) mixed with `register.bat`, `unregister.bat` (lowercase).
Proposal: all lowercase — modern dev standard (Linux/cross-platform/GitHub convention).

---

## §4. Concept Review

- `GEMINI_RATIO` env var → `COLLAB_LEVEL`? (is `COLLAB_LEVEL` more universally understood?)

---

Please evaluate each section §2-1 through §4 with: **AGREE / DISAGREE / MODIFY** + short reason.
Focus especially on §2-4 (`_state` vs `_workspace`) and §3-1 (`cla`/`gem` rename).
