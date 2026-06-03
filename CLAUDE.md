# Portable Sandbox Dev Environment
> Last updated: 2026-06-03
> This file lets Claude Code resume from where the setup conversation left off.

## What This Project Is

A fully portable Windows development environment that lives in a single folder
(USB drive or cloud). Right-click any folder -> open VS Code + Claude Desktop
with all tools (Python, Node.js, FFmpeg, Git, etc.) pre-configured.

## Final Folder Structure

```
[PortableDev]/
├── install.bat / register.bat / unregister.bat
├── README.md / CLAUDE.md / CONVENTION.md / PROTOCOL.md
├── workspace/     ← default project folder
├── .claude/       ← agents/ + skills/
├── _state/        ← agent session workspace (auto-managed)
├── .ai/           ← IPC state (hub.py managed — never write directly)
├── _archive/      ← logs, sessions, collab-log, workspace backups
└── _sys/          ← cli/ hooks/ checks/ core/ templates/ env/ tools/ tests/ data/
                     SYSTEM_ARCHITECTURE.md  git-config/  claude/  gemini/
```
Full annotated tree: `README.md`

## Architecture Decisions

| Decision | Reason |
|----------|--------|
| Everything under `_sys/` (except docs + workspace) | Root clean: 3 docs + workspace + .claude + _sys only |
| Workspace at root or external | Multiple workspaces, nested or outside BASE_DIR |
| Registry key = `SandboxRun_[FolderName]` | Multiple envs on same PC without conflict |
| HKCU for context menu (not HKCR) | No admin required; register.bat handles initial and re-registration |
| register.bat for explicit PC registration | Assigns fixed SUBST drive; calls manage.ps1 to store state and register menu |
| unregister.bat for permanent removal | Calls manage.ps1 for global cleanup (SUBST + Registry + State) |
| Unified manage.ps1 manager | Single Source of Truth for naming, SUBST mapping, and Registry state |
| State-aware Cleanup | Registration auto-cleans orphaned keys from previous folder names/paths |
| No USERPROFILE/APPDATA override | Preserves Git, SSH, host credentials |
| Tool-specific env vars (NPM_CONFIG_*, etc.) | Precise isolation without broad side effects |
| `CLAUDE_CONFIG_DIR = _sys\claude\config\` | Claude Code CLI auth/config travels with USB |
| Gemini CLI via npm-global (nodejs/npm-global) | `gemini.cmd` auto-in-PATH via existing npm-global PATH entry; no separate PATH line needed |
| Gemini auth in `%USERPROFILE%\.gemini\` (host) | Gemini CLI v1.x does not support `GEMINI_CONFIG_DIR` override; re-auth required per PC |
| `_archive/` for all rolling data | logs + sessions + workspace backups in one place for easy cleanup |
| `LOG_DIR = BASE_DIR\_archive\logs` | Logs beside workspace backups, not buried under _sys |
| `SESSION_DIR = BASE_DIR\_archive\sessions` | Session files beside logs; ctx-save/end fallback-derives from script location if SESSION_DIR unset |
| `ENV_DIR`, `TOOLS_DIR`, `CLAUDE_DIR`, `DATA_DIR` in start.bat | All paths relative to SYS_DIR |
| Individual `if exist` lines (not for-loop) | for-loop expands %PATH% once -> bug |
| `-LiteralPath` in all registry PS1 ops | `HKCU:\Software\Classes\*\shell\...` wildcard hang prevention |
| `launch.ps1` as registry intermediary | Direct bat execution from registry breaks on space/Korean paths |
| `.bat` files: English only, no Korean | chcp 65001 doesn't fix cmd.exe parser for multi-byte chars |
| No Rust toolchain | Removed; not used |
| `local.config.bat` for per-PC overrides | start.bat auto-loads it before CONFIG defaults; not tracked in Git |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` auto-set | Harness (agent teams) requires this env var; start.bat sets it on every launch |
| `setup.ps1` component-level try/catch (Run-Component) | One component failing does not abort the whole bootstrap; failures listed in summary |
| `install.bat` at root | Single double-click entry for first-time setup; relays to `_sys\setup.ps1` |
| `code.cmd` in `npm-global/` | VS Code portable wrapper; Claude Code IDE integration requires `code.cmd` in PATH |
| `start.bat` syncs `statusline-command.sh` to `~/.claude/` | statusline script must be at `~/.claude/` on every host PC; start.bat copies it on each launch |
| WSB (`launch-wsbtest.ps1`) as default test env | True OS isolation; sandbox-test.bat runs unmodified inside WSB; local fallback for CI |
| `_archive/CHANGELOG.md` for change history | Keeps CLAUDE.md stable (better prompt-cache hits); history accessible but not loaded every session |
| `pwsh/` in `env/` | Portable PowerShell 7; optional component via `setup.ps1 -Pwsh` |

## Key Bugs Fixed (for reference)

1. **HKCR wildcard hang**: `Test-Path` / `Set-ItemProperty` on `HKCR:\*\shell\...`
   treats `*` as wildcard -> enumerated all HKCR keys. Fixed: `-LiteralPath`.
   Same applies to `HKCU:\Software\Classes\*\shell\...`.

2. **for-loop PATH accumulation**: `for %%T in (...) do (set "PATH=...;%PATH%")`
   expands `%PATH%` once before loop. Fixed: individual `if exist` lines.

3. **Korean in .bat call args**: `call :LOG "???..."` - cmd.exe parser splits
   multi-byte UTF-8 chars into tokens. Fixed: English only in all .bat files.

4. **Registry command quoting**: `cmd.exe /c ""path"" "arg""` -> empty command error.
   Fixed: `launch.ps1` as relay, uses `cmd /c call "bat" "arg"` pattern.

5. **FZF_HISTORY_DIR**: invented env var that fzf doesn't recognize. Removed.

6. **BAT_CONFIG_DIR**: wrong name. Fixed: `BAT_CACHE_PATH`.

7. **`for /f` wmic in for-loop block with `!VAR!`**: needed `setlocal EnableDelayedExpansion`.

## CRITICAL: Windows Shell Rules

- **Bash tool = /usr/bin/bash** → PowerShell 문법 절대 금지 (backslash path, `$env:`, `-ErrorAction` 등)
- PowerShell 명령 → PowerShell tool 사용
- 시스템 작업 → `.bat` 파일 직접 호출
- 경로 구분자: `\` (backslash)
- 모든 `.bat` 호출 시 `PYTHONUTF8=1` 환경변수 설정 또는 내부에 포함

## CRITICAL: State Management

- `.ai/state.json` 직접 쓰기 절대 금지
- 상태 변경: `python _sys/core/hub.py update-status --mission "..." ` 호출
- 메시지 발송: `python _sys/core/hub.py send --from X --to Y --msg "..."`
- 세션 조회: `python _sys/core/hub.py status --format llm`
- 배치 진입점: `_sys/cli/claude.bat`, `_sys/cli/gemini.bat`, `_sys/cli/msg.bat`

## Gemini Consultation (Axis-Q)

이 프로젝트에서 Gemini consult 스크립트 위치: `_sys\cli\msg.bat ask --to gemini`
복잡한 작업 전 Gemini를 먼저 호출하고 응답을 기다린 후 진행할 것. (전역 CLAUDE.md 참조)

## Current State
Last updated: 2026-06-03 (MECE 구조·명칭 정리 완료)
2026-06-03 MECE + 일반성 기준 전면 정리 (Gemini Round 1~4 협의):
- Phase A: tools/ bat 파일 → cli/hooks/, _state/collab/ 삭제, _archive/scans/ 분리
- Phase B: scans→checks, docs→templates, git_config→git-config, test→tests
         cla→claude, gem→gemini, append-log→log-write, check-gate→ai-check
         collab-log-append→collab-log, INSTALL/CLEANUP → install/cleanup (소문자)
- Phase C: start.bat, check-*.bat, test/*.bat 내부 경로 현행화
- Phase D: GEMINI.md, CLAUDE.md, CONVENTION.md, agents/*.md, skills/*.md 문서 현행화
2026-06-03 3TCP v1 완료:
- _sys/core/hub.py (16 액션, filelock, 3TCP v1), PROTOCOL.md 신규 생성

## Next Steps

1. **Fresh PC setup**: install.bat (double-click) → _sys\setup.ps1 (사용자 직접 수행)

---

## Portable Dev Environment

**Summary:** `_sys/` system files are centralized; architecture supports multi-instance parallel execution; test coverage is 4 layers + 7 agents with full audit/task tracking (89 tests total).
**Tag:** Portable Dev Environment work is tagged `portable-env`.
See `_archive/CHANGELOG.md` for full change history (last updated: 2026-06-03).