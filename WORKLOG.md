# WORKLOG — Portable Dev Environment

> 1인 개발 환경의 주요 아키텍처 결정 및 변경 이력.
> 상세 커밋 이력은 `git log`; 이전 세션 요약은 `_archive/sessions/` 참조.

---

## 2026-06-04 — Batch Parenthesis Parsing Bug Remediation

**목표**: 경로명에 `(`, `)`, `-` 등이 포함될 때 발생하는 배치파일 구문 오류(Unexpected -) 해결 및 전수 수정.

### Lesson Learned (Lesson-Run)
- **Root Cause**: CMD 파서가 `if (...)` 또는 `for (...)` 블록 내에서 따옴표로 묶인 경로일지라도 `)`를 만나면 블록의 끝으로 오인하는 고질적 버그가 있음. 특히 `D:\Path (2) - Copy`와 같이 괄호 뒤에 공백과 대시가 올 경우 `- was unexpected` 에러로 나타남.
- **Rule of Thumb**: 경로 확장이 포함된 로직은 가급적 `(...)` 블록 내부에서 수행하지 않거나, 단일 행 명령(`if cond cmd`)을 사용해야 함. 복잡한 로직이 필요한 경우 `setlocal EnableDelayedExpansion`을 사용하고 `!VAR!`로 확장하여 파싱 단계의 간섭을 피해야 함.

### 변경 요약
- **manage.bat**: `if not exist "%PY%"` 블록을 단일 행으로 변경하여 `register.bat` 실행 시 에러 해결.
- **start.bat**: `gemini-status.bat` 호출 및 Git 경로 설정 블록을 단일 행으로 리팩토링.
- **check-*.bat / hooks/*.bat**: `if ... (...) else (for ...)` 패턴을 `if not defined ... for ...` 단일 행 패턴으로 전수 수정 (10개 파일).
- **CONVENTION.md**: §1-6 "경로 및 특수문자 처리" 규칙 신규 추가.

---

## 2026-06-04 — Batch Path & Encoding Issues Remediation

**목표**: 한글 경로 및 인코딩으로 인한 배치파일 오작동 해결 및 재발 방지.

### Lesson Learned (Lesson-Run)
- **Root Cause**: `local.config.bat` 생성 시 한글 포함 물리 경로(`BASE_DIR_PHYS`)를 UTF-8로 저장 -> `cmd.exe`가 이를 ANSI로 오인하여 경로 깨짐 발생 -> `subst` 및 환경변수 로딩 실패.
- **Rule of Thumb**: 배치파일용 설정 파일은 **동적 경로 추출(%~dp0)**을 우선하고, 절대 경로 저장이 불가피할 경우 비-ASCII 문자 포함을 철저히 배제해야 함.

### 변경 요약
- **manage.py**: `local.config.bat` 생성 시 `BASE_DIR_PHYS`, `MENU_REG_KEY` 등 비-ASCII 가능성이 높은 중복 변수 제거.
- **Batch Cleanup**: `claude.bat`, `gemini.bat`, `run-tests.bat` 등 시스템 배치파일 내 모든 한글 주석 및 특수 기호(─, —)를 영어/ASCII로 교체 (CONVENTION.md §1-1 준수).
- **Resilience**: `start.bat`이 실행 시점에 `%~dp0`를 통해 경로를 재계산하도록 하여 USB 드라이브 문자나 폴더명 변경에 강인하게 수정.

---

## 2026-06-03 — .md 문서 MECE + 제로토큰 통폐합 (Gemini 3-round 협의)

**목표**: 각 개념이 정확히 한 파일에만 정의되도록 하고, 세션 자동 로딩 토큰을 최소화.

### 변경 요약 (Phase A~F)

| Phase | 대상 | 변경 내용 |
|-------|------|----------|
| A | GEMINI.md (105→70줄) | §2-1 삭제 → CONVENTION.md 포인터; §4/§4-1 축약 → PROTOCOL.md 포인터 |
| B | 프로젝트 CLAUDE.md (238→126줄) | ASCII 폴더 트리 10줄 요약 → README.md 위임; Gemini Collaboration 섹션 제거 |
| C | 전역 CLAUDE.md (111→65줄) | GEMINI_RATIO 테이블 + R:6~10 트리거 + 협업 사이클 → PROTOCOL.md §C-0/§C-1 포인터 |
| D | CONTEXT.md | Axis Map 스크립트명 현행화; 건강도 임계값 → PROTOCOL.md §C-5 포인터 |
| E | SYSTEM_ARCHITECTURE.md | §9 Gemini Axis 기술 명세 SSoT 신규 추가; §7 latest 패턴 오류 수정 |
| F | agents/*.md | coordinator/verifier/portability-auditor에 PROTOCOL.md §C-8/§P-3/§M-1/§C-3 포인터 추가 |

**세션 토큰 절감**: ~3,460 토큰/세션 (~35%) — 전역 CLAUDE.md 1,360 + 프로젝트 CLAUDE.md 700 + CONTEXT.md 일부

**SSoT 재편 결과**:
- PROTOCOL.md = 협업 정책 권위 문서 (중복 인라인 → 포인터)
- CONVENTION.md = 코드 품질 기준 단독 소유
- SYSTEM_ARCHITECTURE.md §9 = Axis A-I 기술 명세 SSoT (신규)

---

## 2026-06-03 — PROTOCOL.md v2 전면 재작성

**목표**: N-tier 합의체 + 분업 협업 프로토콜을 모든 통신 노드에 적용 가능한 공통 코어로 재설계.

### 핵심 변경 (v1 → v2)

| 섹션 | 변경 내용 |
|------|---------|
| §P-0 | Human을 Tier 0 노드로 추가 (인지 범위: 콘솔만, 권한: 최고 거부권) |
| §P-7 (신규) | 명시적 동기/비동기 정책 — 기본 동기, timeout=0, 비동기 허용 조건 정의 |
| §P-8 (신규) | 노드별 필수 로딩 파일 & 토큰 예산 (CC ~10k, CA ~3k, GC ~2.7k) |
| §P-9 | N-Node 확장 절차 (구 §P-7에서 이동) |
| §M-1~M-3 | 상호 불가침 영역, 통신 공개 원칙, 불변 규칙 10개 (신규) |
| §C-0 | GEMINI_RATIO 0~10 재정의 — R:10을 만장일치 앵커로 지정; R:7~10에 §P-3 합의 요건 연결 |
| §L-1~L-2 | 레슨런·안티패턴 (루트 원인 10개, 협의 레슨 6개) 신규 |
| §HISTORY | 버전 이력 신규 |

### 설계 원칙
- 동기화 기본(Sync-default): Directive → Artifact → Verify 순차 완료 후 다음 진행
- timeout=0 전체: GC 쿼리 포함 타임아웃 없음 (복잡한 분석 실패 방지)
- Human Tier 0: Phase 4 승인 게이트로만 개입; 응답 없으면 status="waiting_approval" 유지
- Stale 경로 수정: `_workspace/` → `_state/`, state 변경은 hub.py update-status 경유 명시

---

## 2026-06-03 — MECE + 명칭 일반화 (Gemini 4-round 협의 완료)

**목표**: 전체 파일/폴더 구조 MECE 정리 + 처음 보는 개발자가 이름만으로 목적 파악 가능한 수준으로 일반화.  
Gemini Round 1~4 협의 완료 후 구현.

### Phase A — 구조 정리
| 변경 | 내용 |
|------|------|
| `_sys/tools/git-draft.bat`, `batch-review.bat` | → `_sys/cli/` (사용자 직접 실행 CLI) |
| `_sys/tools/archive-data.bat` | → `_sys/hooks/` (Axis 스크립트 내부 헬퍼) |
| `_state/collab/` | 빈 폴더 삭제 |
| `_archive/scans/` | 신규 생성 + agent-audit.json, script-deps.json 이동 |
| `_archive/workspace-*-legacy-*.json` (6개) | 삭제 |

### Phase B — 폴더/파일명 rename
| 구 이름 | 신 이름 | 기준 |
|---------|---------|------|
| `_sys/scans/` | `_sys/checks/` | "scans"는 보안 스캔 연상; "checks"가 점검 스크립트 의미 명확 |
| `scan-env.bat` | `check-versions.bat` | "env" 모호; "versions" 목적 명확 |
| `scan-audit.bat` | `check-agents.bat` | 무엇을 audit? "agents" 대상 명확 |
| `scan-health/risk/deps.bat` | `check-health/risk/deps.bat` | prefix 일관성 |
| `_sys/docs/` | `_sys/templates/` | 읽는 docs가 아닌 복사용 템플릿 |
| `_sys/git_config/` | `_sys/git-config/` | 디렉토리 관례 (언더스코어 → 하이픈) |
| `_sys/test/` | `_sys/tests/` | 복수형이 업계 관례 |
| `_state/` | **유지** | Gemini Round1 5/5 + Round3 DISAGREE 신호 |
| `cli/cla.bat` | `claude.bat` | "cla"는 프로젝트 전용 약어 |
| `cli/gem.bat` | `gemini.bat` | "gem"은 Ruby gem 연상 |
| `hooks/append-log.bat` | `log-write.bat` | 동사-목적어 패턴 |
| `hooks/check-gate.bat` | `ai-check.bat` | "gate" 불명확; AI 서비스 체크임이 명확 |
| `hooks/collab-log-append.bat` | `collab-log.bat` | "append" 생략해도 맥락 유지 |
| `INSTALL.bat`, `CLEANUP.bat` | `install.bat`, `cleanup.bat` | 소문자가 현대 cross-platform 표준 |

### Phase C/D — 배치파일 + 문서 현행화
- `start.bat` PATH 블록: scans→checks, git_config→git-config 반영
- `check-*.bat` 5개: 새 경로(ai-check, collab-log, archive-data) 반영
- `git-draft.bat`, `batch-review.bat`: 이동 후 훅 경로 수정
- 문서: GEMINI.md, CLAUDE.md, CONVENTION.md, PROTOCOL.md, CONTEXT.md, coordinator.md
- Skills: gemini, portable-env, context-health, risk-scan, propose-improvements
- Agents: risk-scanner, proposer, verifier

---

## 2026-06-03 — 테스트 클린업 (stale refs 제거)

**목표**: `_sys/context/` 삭제 이후 남겨진 stale 테스트 참조 정리.

### 변경 요약

| 파일 | 변경 내용 |
|------|----------|
| `sandbox-test.bat` | xcopy: `context/` → `hooks/+scans/+cli/+tools/`; 스캔 파일 레거시 alias; gemini-consult 8개 `:SK` 대체; ephemeral-session 루프 `scan-*.bat` 경로 수정; `_GEMINI_SESSION_FLAG` → `check-gate` 체크; gemini-session-read 4개 `:SK` 대체 |
| `local-test.bat` | GROUP 16: gemini-consult 7개 `:SK` 대체; ctx-end 경로 `context/→hooks/`; ephemeral/interactive/session-read 동일 정리 |
| `hub.py` | empty-inbox 출력 Korean → English (`inbox empty`) — PS 5.1 CP949/UTF-8 충돌 방지 |
| `test_ipc.ps1`, `test_scenarios.ps1` | `새 메시지 없음` → `inbox empty` |
| `test_hub.py`, `test_hub_edge.py` | 동일 |
| `CONVENTION.md §10-1` | `session-master.json` → `.ai/mailbox.json` (hub.py 경유) |

### 테스트 결과

- **Unit (pytest)**: 74/74 PASS
- **Integration (PS1, pwsh)**: 31/31 PASS (test_ipc×10 + test_scenarios×7 + test_tools_path×8 + test_session_flow×6)
- **총합**: 105 tests ALL PASS

---

## 2026-06-03 — 3TCP v1 프로토콜 (hub.py Phase A-D)

**목표**: N-node 만장일치 협의체 + 분업 협업 프로토콜 설계 및 구현.

### 핵심 아키텍처 결정

| 결정 | 이유 |
|------|------|
| `timeout=None` (무제한) | Gemini 쿼리 120초 타임아웃으로 복잡한 분석 실패 방지 |
| 메시지 봉투 확장 (thread_id/type/cc/ref) | 분업 체인 추적 + 타 노드 메시지 열람(cc) 지원 |
| `nodes.json` N-node 등록 | hub.py 코드 수정 없이 새 노드 추가. `msg register-node` |
| 만장일치 consensus (Propose→Vote→Decision) | 3노드 합의 없이는 진행 불가. GC 대리 투표(CC 경유) |
| PROTOCOL.md 단일 진실 출처 | COLLAB.md 흡수 삭제. §P-0~P-7(3TCP) + §C-1~C-8(정책) 통합 |

### 주요 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `_sys/core/hub.py` | Phase A~D 완전 재작성. 16개 액션 |
| `PROTOCOL.md` | 신규 (COLLAB.md 흡수). 3TCP v1 §P-0~P-7 |
| `COLLAB.md` | 삭제 |
| `_sys/cli/msg.bat` | 한국어 주석 → 영어 (CONVENTION §1-1) |
| `_sys/hooks/ctx-save.bat` | session-master.json 제거 + gemini-mode-check → check-gate |
| `_sys/hooks/ctx-end.bat` | 동일 + context/ → docs/ 경로 수정 |
| `_sys/bridge/` | 삭제 (hub.py로 대체) |

### 테스트 결과

- **Unit (pytest)**: 74/74 PASS — 신규: §P-2 봉투 5개, §P-3 consensus 8개, §P-7 node 3개
- **Integration (PS1)**: 31/31 PASS
- **총합**: 105 tests ALL PASS

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
