# PROTOCOL.md — N-Node Collaboration & Division of Labor Protocol (v2)

> **단일 진실 출처**: 노드 특성 · 협의 · 분업 · 세션 연속성 · 필수 규칙 통합 관리
> 코딩 컨벤션 → CONVENTION.md | 시스템 구조 → SYSTEM_ARCHITECTURE.md | 에이전트 워크플로 → CLAUDE.md

---

## §META — 문서 안내

### 목적

이 문서는 **Human, Claude Code(CC), Claude Agent(CA), Gemini CLI(GC) 등 모든 통신 노드 사이**에
적용 가능한 공통 협업 프로토콜 코어(Part P)와 불변 규칙(Part M), Claude-Gemini 특화 정책(Part C),
레슨런(Part L)을 MECE하게 정의한다.

### 섹션 맵

| Part | 섹션 | 내용 | 필수 독자 |
|------|------|------|----------|
| **P** | §P-0~P-9 | 공통 코어 (모든 노드 간 적용) | 모든 노드 |
| **M** | §M-1~M-3 | 불변 규칙·상호 불가침·통신 공개 | 모든 노드 |
| **C** | §C-0~C-8 | Claude-Gemini 특화 정책 | CC / CA / GC |
| **L** | §L-1~L-2 | 레슨런·안티패턴 | CC (구현 참조) |
| **H** | §HISTORY | 변경 이력 | 감사용 |

### 관련 문서

| 문서 | 내용 |
|------|------|
| CONVENTION.md | bat/ps1/env var 코딩 규칙 |
| CLAUDE.md | 프로젝트 컨텍스트 + 에이전트 워크플로 |
| SYSTEM_ARCHITECTURE.md | _sys/ 레이어 기술 설계 |
| GEMINI.md | Gemini CLI 전용 지침 |

---

## Part P: Universal Core Protocol

> 어느 노드 쌍에도 적용 가능한 공통 프로토콜.
> Human, CC, CA, GC 외 새 노드 추가 시에도 §P-0~P-9가 그대로 적용된다.

---

## §P-0 — 노드 특성 (Node Characteristics)

**원칙**: 모든 협업은 각 노드의 특성(메모리, 인지 범위, 통신 채널, 권한)을 배려한다.

| 속성 | Human | CC (Claude Code) | CA (Claude Agent) | GC (Gemini CLI) |
|------|-------|-----------------|-------------------|-----------------|
| **Tier** | 0 (최고 거부권) | 1 (오케스트레이터) | 2 (에이전트) | 3 (센서) |
| **인지 범위** | 콘솔·UI 출력만 | 파일·도구·메모리 전체 | 작업 범위 내 | 파일 읽기 전용 |
| **메모리** | 없음 (세션 간) | 영속 (Memory.md) | 단기 (세션 내) | 세션 (--resume) |
| **도구 접근** | 직접 실행 | 전체 | 전체 (상속) | 없음 (파일 기반만) |
| **헌법적 권위** | 최상위 (거부권) | O (집행) | X | X |
| **PASS/FAIL 판정** | 최종 승인 | O | O (verifier 전용) | X (데이터 제공만) |
| **투표 방식** | Phase 4 승인 게이트 | 직접 파일 쓰기 | 직접 파일 쓰기 | CC 대리 투표 |
| **컨텍스트 한계** | 인지 부하 (콘솔만) | ~1.2 MB JSONL | ~1.2 MB JSONL | ~500k 토큰 |
| **통신 채널** | 콘솔 출력 | hub.py 직접 | hub.py 직접 | subprocess (--query-file) |
| **실패 형식** | — | — | — | `<failure_report>...</failure_report>` |

**Human 배려 규칙**:
- Human에게 보이는 정보: Phase 4 승인 요청 + ESCALATE 에스컬레이션 + 에러 알림만
- Human 응답 대기: timeout=0 (무제한). 응답 없으면 status="waiting_approval"로 유지
- Phase 4 외 Human 개입: ZONE C 사안(§C-8) 또는 ESCALATED 합의가 발생할 때만

**GC 대리 투표 절차** (GC는 외부 프로세스라 .ai/ 직접 쓰기 불가):
1. CC가 `msg ask --to gc --query-file {제안서 파일}` 로 GC 응답 수신
2. CC가 응답 해석 후 `msg consensus-vote --voter gc --vote agree|disagree|abstain` 실행

---

## §P-1 — 노드 등록 (nodes.json)

위치: `.ai/nodes.json` (프로젝트별, `ensure_ai_dir()`이 자동 생성)

```json
{
  "version": "1",
  "nodes": {
    "cc": { "tier":1, "type":"orchestrator", "invoke":"claude",  "invoke_args":["-p","{query}"],            "timeout":0, "memory":"persistent" },
    "ca": { "tier":2, "type":"agent",        "invoke":"claude",  "invoke_args":["-p","{query}"],            "timeout":0, "memory":"short-term" },
    "gc": { "tier":3, "type":"sensor",       "invoke":"gemini",  "invoke_args":["-p","{query}","-o","text","-y"], "timeout":0, "memory":"session" }
  }
}
```

- `timeout=0` → `None` (무제한). 모든 노드에 타임아웃 없음.
- N번째 노드 추가: nodes.json 항목 1개 + `msg register-node`. hub.py 코드 수정 불필요.

---

## §P-2 — 메시지 봉투 (Message Envelope)

```json
{
  "id": 42,
  "thread_id": "t-a3f2",
  "type": "DIRECTIVE",
  "from": "cc",
  "to": "gc",
  "cc": ["ca"],
  "content": "메시지 내용",
  "status": "unread",
  "timestamp": "2026-06-03T14:30:00",
  "ref": 39
}
```

**타입 MECE:**

| 타입 | 흐름 | 설명 |
|------|------|------|
| `MSG` | Any → Any | 단순 정보 전달 |
| `PROPOSE` | Initiator → All | 만장일치 협의 제안 (본문: 제안서 전문) |
| `VOTE` | Voter → Initiator | 투표 결과 (agree / disagree / abstain) |
| `DECISION` | Initiator → All | 협의 종결 선언 (FINALIZED / ESCALATED) |
| `DIRECTIVE` | Orchestrator → Worker | 작업 지시 |
| `ARTIFACT` | Worker → Orchestrator | 작업 결과물 |
| `VERIFY` | Judge → All | 검증 결과 (cc 필드로 전체 공유) |

**cc 필드**: `msg check --target {id}` 는 `to==id` AND `id in cc` 모두 반환.
→ VERIFY 결과를 GC도 열람 가능: `--type VERIFY --to cc --cc gc`

---

## §P-3 — 만장일치 협의 (Consensus Protocol)

**원칙**: §P-4 분업 실행 전 반드시 만장일치 협의 완료. 합의 없는 실행은 §M-3 I-1 위반.

상태 파일: `.ai/consensus/{round_id}.json`

```
[Initiator]  msg consensus-propose --subject "..." --voters cc,ca,gc
                     ↓  round_id=r-xxxx 자동 발급, status=voting
[각 노드]    msg consensus-vote --round-id r-xxxx --voter {id} --vote agree|disagree|abstain
                     ↓
          전원 agree     → FINALIZED  → handoff.md CONSENSUS_HISTORY 자동 기록
          1명 disagree   → 수정 후 재제안 (라운드 반복, 최대 5회)
          5라운드 초과   → ESCALATED  → Human Gate 필수
```

**콘솔 출력 예시:**
```
[HUB] PROPOSE r-c4d1 | subject=Phase B rename 승인 | voters=cc,ca,gc
[HUB] VOTE   r-c4d1  | voter=cc agree | 1/3
[HUB] VOTE   r-c4d1  | voter=gc agree | 2/3
[HUB] DECISION r-c4d1 FINALIZED | unanimous
```

**라운드 조회:**
- `msg consensus-check` — 전체 라운드 목록
- `msg consensus-check --round-id r-xxxx` — 특정 라운드
- `msg status` — 활성 라운드 포함 전체 상태

---

## §P-4 — 분업 프로토콜 (Division of Labor)

**전제**: §P-3 FINALIZED 확인 후 진입.

```
[CC]  msg send --from cc --to gc --type DIRECTIVE --thread-id t-xxxx --msg "..."
[GC]  작업 수행
[GC]  msg send --from gc --to cc --type ARTIFACT  --thread-id t-xxxx --ref {directive_id} --msg "..."
[CA]  검증
[CA]  msg send --from ca --to cc --type VERIFY    --thread-id t-xxxx --cc gc --ref {artifact_id} --msg "PASS|FAIL: ..."
```

- `thread_id`: 같은 작업의 메시지 묶음 추적
- `ref`: 메시지 체인 연결 (Artifact → Directive, Verify → Artifact)
- `cc=["gc"]`: GC도 VERIFY 결과를 `msg check --target gc` 로 열람

**콘솔 출력 예시:**
```
[HUB] SENT  cc→gc  | thread=t-b5e3 | id=43 type=DIRECTIVE
[HUB] SENT  gc→cc  | thread=t-b5e3 | id=44 type=ARTIFACT ref=43
[HUB] READ  2 messages for ca
```

---

## §P-5 — 콘솔 출력 표준

| 접두어 | 용도 |
|--------|------|
| `[HUB]` | 정상 동작 (SENT, READ, ASK, REPLY, PROPOSE, VOTE, DECISION, REGISTER) |
| `[HUB:ERROR]` | 오류 (예외, 파일 없음) |
| `[HUB:WARN]` | 경고 (비정상 종료 코드, 이상 상황) |
| `[HUB:GATE]` | 게이트 확인 (gemini=ON/OFF) |

타임스탬프: 콘솔 미포함 (log.jsonl에만 기록). 방향: `from→to` 고정 형식.

**ask 표준:**
```
[HUB] ASK   cc→gc | chars=234 | timeout=none
[HUB] REPLY gc→cc | chars=1842 | elapsed=47s
```

---

## §P-6 — 세션 연속성 (Session Continuity)

handoff.md 6개 섹션 (FIFO 관리, 총 ≤3000토큰):

```markdown
## [GOAL]               ← 고정. 최대 3줄. 수동 갱신.
## [RECENT_COMPLETED]   ← FIFO 최대 5개
## [PENDING_ISSUES]     ← 최대 3개
## [KEY_DECISIONS]      ← 최대 3개
## [CONSENSUS_HISTORY]  ← 최대 10개 (§P-3 FINALIZED 자동 기록)
## [ACTIVE_THREADS]     ← 최대 5개 (진행 중 Directive-Artifact 체인)
```

**세션 재개 3-line 복원:**
```
msg status           → ACTIVE_THREADS + 활성 consensus 라운드
msg consensus-check  → 미완료 협의 목록
msg check --target cc → 미읽은 메시지
```

---

## §P-7 — 동기/비동기 정책 (Sync / Async Policy)

**기본: 동기(Synchronous), 타임아웃 없음.**
이전 단계 완료 후 다음 단계 진행. 병렬 실행은 명시적 조건 충족 시만 허용.

| 상황 | 방식 | 조건 |
|------|------|------|
| 기본 협업 흐름 | **동기** | 항상. Directive → Artifact → Verify 순차 완료 |
| 독립 Axis 병렬 실행 | 비동기 허용 | 출력 파일 경로가 겹치지 않을 때만 |
| Human 승인 대기 (Phase 4) | 비동기 대기 | timeout=0. status="waiting_approval" |
| Gemini 호출 (`msg ask`) | 동기 | blocking call. 응답 수신 전 다음 단계 진행 불가 |

**비동기 선언 형식** (독립 Axis 병렬 실행 시):
```
msg send --type DIRECTIVE --async --thread-id t-xxxx
```
→ `async=true` 기록. Artifact 수신 전 다른 **독립** 작업 진행 가능.
단, 동일 thread의 Verify는 반드시 Artifact 완료 후에만 실행.

**타임아웃 정책**: 모든 nodes.json 항목 `timeout=0` (None). GC 쿼리 포함 타임아웃 없음.

---

## §P-8 — 노드별 필수 로딩 파일 & 토큰 예산

### CC (Claude Code) — 세션 시작 시 자동 로딩

| 파일 | 용도 | 예상 크기 | 예상 토큰 |
|------|------|-----------|----------|
| `P:\_sys\claude\config\CLAUDE.md` | 전역 기본설정 (공통) | ~150줄 | ~3,000 |
| `[root]\CLAUDE.md` | 프로젝트 컨텍스트 + 워크플로 | ~220줄 | ~4,400 |
| `_sys\claude\agent\CONTEXT.md` | AI 팀 현재 상태 요약 | ~60줄 | ~1,200 |
| `P:\_sys\claude\config\projects\...\memory\MEMORY.md` + 관련 항목 | 세션 간 기억 | ~80줄 | ~1,600 |
| `.ai\state.json` (hub.py status 출력) | IPC 상태 | ~1 KB | ~250 |
| **CC 기본 합계** | | **~510줄** | **~10,450** |

에이전트별 추가 로딩 (TaskCreate 시):

| 에이전트 | 추가 토큰 |
|---------|----------|
| coordinator.md | ~3,500 |
| verifier.md | ~2,000 |
| script-engineer.md | ~1,500 |
| 기타 에이전트 | ~1,000~2,000 각 |

### CA (Claude Agent) — 작업 시작 시

| 파일 | 용도 | 예상 토큰 |
|------|------|----------|
| `[agent].md` | 역할 정의 + 워크플로 | ~1,500~3,000 |
| `.ai\state.json` (태스크 컨텍스트) | 현재 상태 | ~250 |
| CONVENTION.md 인라인 규칙 (§0, §1, §3-3 발췌) | 필수 제약 | ~500 |
| **CA 기본 합계** | | **~2,250~3,750** |

### GC (Gemini CLI) — 호출 시

| 파일 | 용도 | 예상 토큰 |
|------|------|----------|
| `GEMINI.md` (프로젝트 루트, 자동 로딩) | 프로젝트 지침 + 역할 | ~2,100 |
| Query 파일 (`--query-file`) | 작업 지시 (Directive 내용) | ~300~600 |
| **GC 기본 합계 (Axis-A 제외)** | | **~2,400~2,700** |
| Axis-A 코퍼스 추가 | 전체 코드베이스 | up to ~500,000 |

### Human — Phase 4 승인 시 인지 범위

| 정보 | 채널 | 분량 |
|------|------|------|
| 변경 요약 + 위험 스캔 결과 | 콘솔 출력 | 핵심만 |
| Verifier PASS/FAIL + 제안(proposal) | 콘솔 출력 | 요약 |
| APPROVE / REJECT 응답 | 콘솔 입력 | 1단어 |
| ESCALATED 이견 사안 | 콘솔 출력 + 요약 | 선택지 포함 |

> **CC 컨텍스트 누적 주의**: 세션 진행에 따라 JSONL 누적.
> 600 KB(YELLOW) → ctx-save + /compact 권장. 1.2 MB(RED) → 즉시 중단 (§C-5).

---

## §P-9 — N-Node 확장 절차

새 노드 `n1` 추가 예시:

```bat
msg register-node --to n1 --tier 4 --node-type sensor ^
    --invoke custom-cli --invoke-args "-p,{query}" ^
    --memory session
msg list-nodes
```

이후 consensus에 포함:
```bat
msg consensus-propose --subject "n1 도입 승인" --voters cc,ca,gc,n1
```

hub.py 코드 수정 없음. nodes.json 수정만으로 완료.

---

## Part M: Mandatory Rules & Invariants

> 이 섹션의 규칙은 **어떤 조건에서도 예외 없이 적용**된다.
> 위반 발견 즉시 작업 중단 + 보고.

---

## §M-1 — 상호 불가침 영역 (Mutual Non-Interference)

각 노드는 타 노드의 전용 영역을 **직접** 침범할 수 없다.
침범이 필요할 때는 반드시 요청 프로토콜(§C-1 REQUEST 태그 또는 §P-3 합의)을 사용한다.

| 소유 노드 | 불가침 영역 | 타 노드 접근 방법 |
|----------|-----------|----------------|
| **Human** | 최종 승인 결정, 범위 이탈 판단 | Phase 4 Gate 또는 ESCALATE |
| **CC** | CLAUDE.md / CONVENTION.md / GEMINI.md 해석·수정 | — (최종 권위, 협의 불가) |
| **CC** | GEMINI_MODE 변경, Human Gate 설정 | — |
| **CC** | 보안·인증 파일 (auth, USERPROFILE 영역) | — |
| **CA (verifier)** | PASS/FAIL 판정 권한 | — (유일한 판정 권한, GC 침범 불가) |
| **GC** | 자체 AGREE/DISAGREE 판단 (투표 거부권) | CC 대리 투표 (§P-0) |
| **GC** | `_sys/`, `*.bat`, `*.ps1` 직접 편집 | `[REQUEST_TO_CLAUDE: WRITE_FILE]` 발행 |

---

## §M-2 — 통신 공개 원칙 (Transparent Communication)

**원칙**: 노드 간 통신 내용은 숨김 없이 전체 노드와 공유한다.

구현 메커니즘:
1. `VERIFY` 결과 → `cc` 필드로 모든 관련 노드에 배포
2. `DECISION` (합의 결과) → handoff.md CONSENSUS_HISTORY 자동 기록
3. Human → Phase 4에서 전체 작업 요약 + 검증 결과 제공
4. ESCALATED 사안 → 즉시 Human 에스컬레이션, 내용 은폐 금지

금지 사항:
- 노드 간 비공개 채널 사용
- 합의 결과 은폐 또는 부분 공개
- 검증 실패 결과 누락

---

## §M-3 — 불변 규칙 (Invariants)

위반 즉시 작업 중단. 예외 없음.

```
[I-1]  합의 전 실행 금지          §P-3 FINALIZED 전 §P-4 진입 불가
[I-2]  .ai/state.json 직접 쓰기 금지  hub.py 경유만 (update-status, send 등)
[I-3]  loop_count ≥ 3 → 즉시 HALT  Human 개입 대기, 자동 재시도 금지
[I-4]  GC PASS/FAIL 금지          verifier(CA)만 판정 권한 보유
[I-5]  Human 승인 없이 최종 병합 금지  human_approval="approved" 확인 후에만
[I-6]  USERPROFILE/APPDATA 오버라이드 금지  Git·SSH·인증 정상 동작 보호
[I-7]  드라이브 레터 하드코딩 금지   PORTABLE_ROOT 동적 계산
[I-8]  bat 파일 내 한국어 금지      cmd.exe 멀티바이트 파싱 실패
[I-9]  wmic 사용 금지              PowerShell Get-Date 대체
[I-10] for-loop PATH 금지          개별 if exist 라인 사용
```

---

## Part C: Claude-Gemini Specific Policy

> §P(공통 코어)와 §M(불변 규칙) 위에 추가되는 Claude-Gemini 특화 정책.

---

## §C-0 — GEMINI_RATIO 협업 깊이 (0~10)

**앵커 (R:10)**: 전 과정 완전 협업. 매 단계마다 상세 목표 공유 → §P-3 만장일치 합의 → 진행.
이견 발생 시 합의될 때까지 반복. 단독 결정 금지. 결과도 교차 검증 후 보고.

| Ratio | 모드 | Gemini 개입 시점 | §P-3 합의 필요 |
|-------|------|-----------------|--------------|
| **0** | **비활성** | 없음 | — |
| **1** | **수동 전용** | 명시적 Axis 실행 시에만 | — |
| **2** | **설계 자문** | 아키텍처·구조 결정 전 1회 | — |
| **3** | **계획 자문** | 멀티파일 작업 시작 전 계획 수립 1회 | — |
| **4** | **검문소** | 작업 시작 전 + 완료 후 (2회) | — |
| **5** | **코드 파트너** | 모든 Edit·Write 전 + 완료 후 검토 | — |
| **6** | **오류 파트너** | R:5 + 오류/실패 발생 시 즉시 재협의 | — |
| **7** | **방향 파트너** | R:6 + 구현 옵션 ≥ 2 시 트레이드오프 분석 | 주요 방향 전환 시 |
| **8** | **마일스톤 파트너** | R:7 + 하위 태스크 1개 완료마다 중간 검토 | 단계 완료 합의 시 |
| **9** | **페어 프로그래밍** | R:8 + 탐색 5회(Grep/Read) 후 방향 확인 | 방향 전환 시 |
| **10** | **두뇌 동기화** | **전 단계** (계획·실행·검토·보고) 완전 협업 | **매 단계 필수** |

**R:6~10 추가 트리거 규칙:**
- **R:6+**: 동일 오류 2회 연속 → 단독 재시도 금지. Gemini에게 에러 로그 전달 후 돌파구 협의
- **R:7+**: 구현 옵션 ≥ 2 → 임의 결정 금지. Gemini에게 트레이드오프 분석 요청
- **R:8+**: 하위 태스크 완료 시마다 "여기까지 검토해줘, 다음으로 넘어가도 될까?" 협의
- **R:9+**: Grep/Read 연속 5회 후 "지금까지 컨텍스트가 충분한지" 방향 확인
- **R:10**: 최종 응답 직전 반드시 Gemini Final Audit. §P-3 양측 만장일치 확인 후 보고.
  이견 발생 시 합의될 때까지 반복 — 라운드 상한 없음.

**설정 파일**: `_sys\gemini\config.json` → `gemini_ratio` 필드

---

## §C-1 — Claude-Gemini 협업 정책 v2

*(2026-05-31 v1→v2 재수립. 구 COLLAB.md §C-1 이전)*

두 에이전트는 **대등한 협력자**다. 헌법적 사안에서만 Claude가 최종 권위를 가진다.

| | Claude (CC) | Gemini (GC) |
|--|-------------|-------------|
| 주 역할 | 오케스트레이터·정책 수호자 | 도메인 전문 실행자·전략 제안자 |
| 헌법적 권위 | O | X (제안만) |
| 세션 시작권 | O | O (`[REQUEST_TO_CLAUDE: SESSION_MANAGEMENT]`) |

**통신 형식 (양측 공통):**

```
[REQUEST_TO_CLAUDE: TYPE] 설명
[REQUEST_TO_GEMINI: AXIS]  설명
[REFERENCE: path/to/artifact]
[REFUSAL: CODE] 사유
```

**Gemini → Claude 요청 타입:**

| 타입 | 설명 |
|------|------|
| `WRITE_FILE` | `_sys/` 스크립트·정책 문서 편집 |
| `HUMAN_DECISION` | 판단 불가 사안 에스컬레이션 |
| `POLICY_CLARIFICATION` | 컨벤션 예외·엣지 케이스 해석 |
| `GIT_OPERATION` | git commit / push / branch |
| `SESSION_MANAGEMENT` | /compact, ctx-save, 컨텍스트 플러시 |
| `READ_AND_VERIFY` | 파일 읽기 및 내용 검증 |

거절 코드: `OUTSIDE_CAPABILITY` | `AMBIGUOUS_REQUEST` | `POLICY_VIOLATION` | `RESOURCE_EXHAUSTED` | `CONSTITUTIONAL_BOUNDARY`

이견 교착 시: 마지막 거절한 쪽이 `[REQUEST_TO_CLAUDE: HUMAN_DECISION]` 자동 발행.

**헌법적 권위 (CC 최종 결정):**
`CLAUDE.md` · `CONVENTION.md` · `GEMINI.md` · `GEMINI_MODE 변경` · `Human Gate` · `보안/안전 판단`

**Claude 의무:**

| 원칙 | 내용 |
|------|------|
| 오케스트레이션 주도 | 협업 세션 시작 + 전체 흐름 관리 |
| Gemini 요청 처리 | `[REQUEST_TO_CLAUDE]` 수신 시 수용 또는 `[REFUSAL: CODE]`. 무시 금지 |
| 자기완결 Directive | 파일 경로·에러 출력·목표 포함. 중간 질문 기대 금지 |
| JSON 계약 | `_archive/` JSON 출력만 읽기. raw 대화 파싱 금지 |
| 쿼터 보존 | Axis-A 하루 최대 3회 |
| 실패 시 OFF | failure XML → GEMINI_MODE=OFF → 다음 start.bat에서 재확인 |
| 원자 Directive | 하나의 호출 = 하나의 논리적 작업 |

**Gemini 의무:**

| 원칙 | 내용 |
|------|------|
| 시스템 파일 보호 | `_sys/`, `*.bat`, `*.py` 직접 편집 금지. `[REQUEST_TO_CLAUDE: WRITE_FILE]` 사용 |
| 거절 권한 | 원칙 위배 요청 → `[REFUSAL: CODE]`. 이유 명시 |
| 실패 형식 | `<failure_report><reason>CODE</reason><details>...</details></failure_report>` |
| 메모리 경계 | MEMORY.md: 기술적 How-To만. 오케스트레이션 컨텍스트 기록 금지 |

실패 코드: `FILE_NOT_FOUND` | `NETWORK_ERROR` | `AMBIGUOUS_DIRECTIVE` | `TEST_VALIDATION_FAILED` | `MISSING_DEPENDENCY`

**실용 수치:**
- GC 품질 한계: ~500k 토큰
- Axis-A: 100k~2.5M / Axis-B,G,H,I: 1k~10k
- 쿼터 초과 신호: `429 Too Many Requests`
- CC JSONL Yellow: 600 KB / Red: 1.2 MB

---

## §C-2 — 3-Tier R&R

| Tier | 구성원 | 권한 | 역할 |
|------|--------|------|------|
| **Tier 0** | Human | 최고 거부권 | 최종 승인·범위 이탈 결정 |
| **Tier 1 (CC)** | Claude Code 하네스 | 헌법적 권위 | 오케스트레이터·메모리·Human Gate |
| **Tier 1.5** | Skills | Tier 1 확장 | Tier 2 조율; GC 직접 호출 금지 |
| **Tier 2 (CA)** | Claude 에이전트 (12개) | PASS/FAIL 판정 | 정책 준수·구현·검증 |
| **Tier 3 (GC)** | Gemini CLI (Axis A-I) | 도메인 분석 | 대용량 스캔; PASS/FAIL 금지 |

핵심 원칙:
- **Sensor vs Judge**: GC는 데이터 제공만. PASS/FAIL은 verifier(CA)만.
- **Tier 흐름**: 1 → 2 → 3. 역방향은 `[REQUEST_TO_CLAUDE]` 태그를 통해서만.

**WRITE_FILE 라우팅 (GC → CC → CA):**

| 파일 종류 | 라우팅 에이전트 |
|----------|--------------|
| `_sys/*.bat`, `_sys/*.ps1` | script-engineer |
| `CLAUDE.md`, `CONVENTION.md`, `PROTOCOL.md`, `README.md` | docs-writer (헌법적 검토 후) |
| `.claude/agents/*.md` | docs-writer |
| `_archive/*.json` (Axis 출력) | GC 직접 작성 허용 |

**작업 라우팅 테이블:**

| 작업 | 주담당 | GC 지원 (Axis) |
|------|--------|---------------|
| 이식성 감사 | portability-auditor | A |
| 스크립트 수정 | script-engineer | F (전) → D (후) |
| 버전 확인 | proposer | B |
| 에이전트 일관성 | verifier (조건부) | E |
| 세션 요약 | ctx-end.bat | C |
| 커밋 메시지 초안 | CC | G |
| 컨텍스트 건강 | coordinator | H |
| 사전 위험 | risk-scanner | I |
| 문서 동기화 | docs-writer | — |
| 시나리오 감사 | scenario-auditor | — |

---

## §C-3 — Gemini-first Analysis Rule

Axis가 존재하는 분석 필요 AND Gemini ON → **반드시 Axis 먼저 사용.**
CC 인라인 분석은 컨텍스트 창을 소모함. GC Axis는 별도 토큰 풀.

| 분석 필요 | Axis | 출력 |
|-----------|------|------|
| 사전 위험 | I | _archive/risk-scan.json |
| 스크립트 문법 | D | console |
| 전체 코드베이스 | A | 03_portability_audit.json |
| 에이전트 일관성 | E | _archive/agent-audit.json |
| 외부 버전 | B | _archive/version-check.json |
| 스크립트 의존성 | F | _archive/script-deps.json |
| 커밋 메시지 | G | console |
| 컨텍스트 건강 | H | status.json |

Exception: Zone A (헌법적 사안) 또는 Axis 결과 불충분 시 CC 인라인 가능.

대형 문서 초안 (>100줄): Gemini 위임 → `_state/02_draft_[name].md` → CC 검토/편집.

---

## §C-4 — Collaboration Health Check

*(coordinator Phase 0에서 실행)*

1. `_sys/gemini/status.json` → mode=ON AND consecutive_failures < 3
2. `_archive/collab-log/{today}.md` 최근 10개 항목 확인
   - ESCALATED 미해결 → 먼저 처리
   - REFUSED → 재시도 전 근본 원인 파악
3. `msg consensus-check` → 미완료 라운드 확인
4. 판단:
   - 이상 없음 → 진행
   - consecutive_failures ≥ 3 → 복구 테스트: `gemini -p "ok" -y`
   - mode=OFF (비수동) → "Proceeding without Gemini: [reason]" 기록

협업 장애 프로토콜 (예상치 못한 REFUSED, 스키마 불일치):
1. 현재 태스크 즉시 중단
2. collab-log에 전체 상세 기록
3. 근본 원인 진단 후 해결. 추측 재시도 금지.

---

## §C-5 — 세션 전환 트리거 (Session Transition Triggers)

### Claude Context 건강도

| Trigger | 조건 | Action |
|---------|------|--------|
| YELLOW | 0.6~1.2 MB | 페이즈 완료 → ctx-save → /compact 권장 |
| RED | > 1.2 MB | STOP → check-health.bat --force → /compact 필수 |
| PRE-COMPLEX | > 5파일 태스크 전 | YELLOW이면 /compact 먼저 |

Heavy phase: > 5파일 변경 OR Axis-A OR ≥ 3 agent MD 재작성.

### Gemini Mode 전환

| Trigger | 조건 | Action |
|---------|------|--------|
| 쿼터 소진 | HTTP 429 | mode=OFF; REFUSED 로그; GC 없이 진행 |
| 자동 실패 | consecutive_failures ≥ 3 | collab-log.bat이 mode=OFF 자동 설정 |
| 복구 테스트 | mode=OFF (비수동) 후 | `gemini -p "ok" -y` 성공 → mode=ON 재설정 |

새 세션 시작: `msg status` + `msg consensus-check` + `msg check --target cc`

---

## §C-6 — State & CONTEXT.md 업데이트 규칙

Human Approval 후:
- coordinator → `hub.py update-status` 경유로 state.json system_state 갱신 (직접 쓰기 금지)
- CONTEXT.md 업데이트: 아키텍처 변경 시만 (루틴 태스크 불필요)
- docs-writer는 CONTEXT.md 소유 없음 — coordinator가 hub.py 경유 직접 기록

---

## §C-7 — 에이전트 경로 정책

기본 경로 우선순위: `_state/` → `_sys/` → `BASE_DIR`
경로 변수 미설정 시: 워닝 출력 후 계속 진행 (블로킹 아님).

```
[Warning] {VAR_NAME} not set - using default: {default_path}
```

- 스캔 범위: BASE_DIR 기준 최대 2단계 하위
- 변경 범위: 요청 범위 2배 초과 → proposer 경고 에스컬레이션
- 드라이브 전체 스캔: 명시적 경로 지시 없으면 금지

---

## §C-8 — Decision Delegation Policy

```
ZONE A — CC decides immediately (협의 없이 즉시 결정):
  • CLAUDE.md / CONVENTION.md / PROTOCOL.md 해석
  • GEMINI_MODE 변경
  • 보안 결정 (auth 파일, USERPROFILE 보호)
  • CONVENTION.md 규칙 위반 → 즉시 블록
  • Gemini failure XML → GEMINI_MODE=OFF
  • loop_count ≥ 3 → HALT

ZONE B — 에이전트 위임 (CC 인라인 분석 없이 위임):
  • _sys/*.bat / *.py 수정 → script-engineer
  • tools/ 새 도구 → tool-integrator
  • 폴더 구조 → organizer → folder-tidier
  • 문서 동기화 → organizer → docs-writer
  • 사전 위험 → risk-scanner (Axis-I)
  • 이식성 감사 → verifier → portability-auditor
  • 시나리오 감사 → verifier → scenario-auditor
  • ROI 분석 → proposer (verifier PASS 후)

ZONE C — Human 확인 먼저:
  • 요청 범위 불명확 AND > 3파일 영향
  • Axis-A 실행 계획 → 범위 확인
  • 삭제 범위 > 2× 요청 범위
  • 헌법적 경계 충돌
  • risk-scanner overall_risk = HIGH
  • loop_count = 2 → "Loop 2/3. One more FAIL triggers HALT." 경고
```

---

## Part L: Lessons Learned

> 같은 실수를 반복하지 않기 위한 원인·패턴·대응 정리.
> CC 구현 시 여기 먼저 참조.

---

## §L-1 — 반복 실수 패턴 (Root Causes & Anti-Patterns)

| # | 패턴 | 근본 원인 | 대응 규칙 |
|---|------|-----------|----------|
| L01 | Gemini 인라인 `-p` 텍스트 무시 | GEMINI.md 컨텍스트가 파일 탐색 우선 실행 | `--query-file` 파일 기반 디렉티브 사용 |
| L02 | bat 파일 내 한국어 → 토큰 분리 오류 | cmd.exe 멀티바이트 파싱 실패 | §M-3 I-8: bat 영어 전용 |
| L03 | for-loop PATH 중복 누적 | `%PATH%` 루프 진입 전 1회 확장됨 | §M-3 I-10: 개별 if exist 라인 |
| L04 | `HKCR:\*\shell\...` Test-Path 행 | 와일드카드 → 전체 HKCR 열거 | `-LiteralPath` 사용 |
| L05 | wmic 타임스탬프 → 인코딩 오류 | wmic 출력 CP949/UTF-8 혼재 | §M-3 I-9: PowerShell Get-Date |
| L06 | `_state/` vs `_workspace/` 혼용 | rename 후 문서 업데이트 누락 | rename 직후 전체 grep 필수 |
| L07 | GC 대리 투표 절차 누락 | GC는 .ai/ 직접 쓰기 불가 | §P-0 GC 대리 투표 절차 필수 |
| L08 | collab-log·hooks 경로 오류 | 파일 이동 후 내부 caller 미수정 | 이동 즉시 모든 caller grep 확인 |
| L09 | scan-* → check-* 문서 미반영 | Phase B rename 후 일부 문서 누락 | Phase D(문서 현행화) 별도 단계로 분리 |
| L10 | R:10에서 단독 결정 | ratio 정의에 만장일치 요건 불명확 | §C-0 R:10: 매 단계 §P-3 합의 필수 |

---

## §L-2 — 협의 협업 레슨 (Consultation Lessons)

| # | 상황 | 잘못된 접근 | 올바른 접근 |
|---|------|------------|------------|
| C01 | Gemini에게 긴 제안서 전달 | `-p` 인라인 텍스트로 전송 | 파일 저장 후 `--query-file` 경로 전달 |
| C02 | 합의 없이 구현 시작 | "방향은 맞으니 진행" | §P-3 FINALIZED 확인 후 §P-4 진입 |
| C03 | 오류 2회 후 단독 재시도 | 수정 후 즉시 재실행 | R:6+: Gemini에 에러 로그 공유 후 협의 |
| C04 | rename 시 일부 문서만 수정 | 보이는 파일만 수정 | grep으로 전체 참조 확인 + 일괄 수정 |
| C05 | GC 분석 결과 직접 PASS/FAIL | GC 결과 신뢰하여 직접 판정 | 결과를 verifier(CA)에 전달, 판정 위임 |
| C06 | 합의를 방향 논의로 대체 | "Gemini도 동의한 것 같다" | §P-3 공식 투표 완료 확인 |

---

## §HISTORY

| 날짜 | 버전 | 주요 변경 |
|------|------|---------|
| 2026-06-03 | **v2.0** | §META 신규. §P-7 Sync/Async, §P-8 노드별 로딩 파일, §P-9 N-Node(구 P-7). §M-1~M-3 상호 불가침·통신 공개·불변 규칙. §C-0 RATIO 0~10 재정의(R:10 만장일치 앵커). §P-0에 Human Tier 0 추가. §L-1~L-2 레슨런. stale 경로 수정: _workspace→_state, hub.py 경유 state 갱신 명시. |
| 2026-06-03 | **v1.0** | 3TCP v1 최초 구현. hub.py Phase A~D 완료. 구 COLLAB.md 대체. §P-0~P-7, §C-1~C-8 기초 수립. |
