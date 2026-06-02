# WORKLOG — Portable Dev Environment

> 1인 개발 환경의 주요 아키텍처 결정 및 변경 이력.
> 상세 커밋 이력은 `git log`; 이전 세션 요약은 `_archive/sessions/` 참조.

---

## 2026-06-03 — Phase 0~9 전면 재편 (Baseline v2)

**목표**: 파일명 혼재, 종횡 경쟁 상태, AI↔AI IPC 부재를 해결하는 전면 재설계.

### 핵심 아키텍처 결정

| 결정 | 이유 |
|------|------|
| `hub.py` — Python Facade 10 액션 | 모든 IPC 로직을 단일 진입점으로 통합. Batch ≤5줄 원칙 |
| `filelock` 라이브러리 (venv) | os.mkdir 뮤텍스는 고아 락 위험. venv 가용으로 안전한 OS-레벨 락 사용 |
| `.ai/` 프로젝트 로컬 상태 폴더 | .git/.vscode 패턴 따름. CWD→.git 상향 탐색, 프로젝트별 격리 |
| `c{4}-g{4}` 세션 pair ID | 1:1 매핑. prefix 포함 UUID 앞 4자리 (예: c2b5-g4707) |
| `handoff.md` FIFO ≤3000토큰 | 세션 간 컨텍스트 연속성. 초과 시 가장 오래된 항목 자동 삭제 |
| `--format llm` Token-Zero | LLM에 raw JSON 절대 금지. 마크다운 요약만 출력 |
| `PYTHONUTF8=1` 전역 | Windows CP949 인코딩 충돌 방지. 모든 배치 파일에 포함 |
| `PORTABLE_ROOT` 동적 계산 | `P:\` 하드코딩 금지. `%~dp0..\..` 기반 상대 경로 |

### 폴더 구조 변경

| 이전 | 이후 | 내용 |
|------|------|------|
| `_sys/context/*.bat` (20개) | `_sys/cli/` + `_sys/hooks/` + `_sys/scans/` + `_sys/tools/` | MECE 역할 분리 |
| `_workspace/*.json` (직접 쓰기) | `.ai/state.json` (hub.py 경유만) | 동시성 안전 |
| `session-master.json` `collab-bridge.json` | hub.py `send/check` 액션 | IPC 표준화 |
| `session-primer.md` | `.ai/sessions/*/handoff.md` (FIFO) | Token-Zero 연속성 |

### 스크립트 통폐합 (22 → 13)

| 삭제/통합 | 대체 |
|----------|------|
| `msg.bat` + `claude-task.bat` + `gemini-task.bat` | `cli/msg.bat` |
| `collab-log-append.bat` + `raw-log.bat` | `hooks/collab-log-append.bat` + `hooks/raw-log.bat` |
| `gemini-gate.bat` + `gemini-mode-check.bat` | `hooks/check-gate.bat` |
| `version-check.bat` + `gemini-usage.bat` + `gemini-set-ratio.bat` | `scans/scan-env.bat` |

### 테스트 결과

- **Unit (pytest)**: 22/22 PASS — hub.py 10 액션, FIFO, Token-Zero
- **Integration (PS1)**: 22/22 PASS — IPC, 세션 흐름, 경로/venv 검증

### 잔여 작업 (다음 세션)

1. `.claude/settings.json` 권한 업데이트 (자동 차단으로 수동 필요)
2. 전역 `P:\_sys\claude\config\CLAUDE.md`의 `context/gemini-consult.bat` → `tools/consult-ai.bat` 경로 수정
3. `setup.ps1` — venv 생성 + filelock 설치 항목 추가
4. WSB(`launch-wsbtest.ps1`) 환경에서 integration 테스트 검증
