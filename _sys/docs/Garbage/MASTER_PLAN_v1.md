# MASTER PLAN v1.0 — Full System Overhaul
> Leader: cc (Claude Code) | Peers: gc (Gemini), cx (Codex)
> collab_rate: 10 | Created: 2026-06-13
> Workspace root: P:\ | Codex workspace: P:\ (E: drive does not exist)

---

## 0. OVERVIEW

대규모 시스템 정비 작업. 모든 결정은 cc+gc+cx 만장일치 필요 (R:10).
작업 분업 후 교차검토 반복. 완결적으로 수행.

---

## 1. CODEX BUG FIX (선행 필수)

**문제**: `P:\_sys\codex\health.json` 내 `availability.authenticated=false`, `entrypoint_ok=false`
**원인 가설**:
- `hub.py health-update` 는 `context_health`/`session_health`만 갱신, `availability` 미갱신
- 초기화 시 false로 기록 후 성공 시에도 업데이트 안 됨
**담당**: cc (코드 분석), cx (픽스 구현)
**검증**: codex 실제 실행 후 health.json 확인

---

## 2. PHASE PLAN

### Phase 1: 현황 스캔 & 합의 (전원 병렬)
- cc: 전체 파일 구조 스캔, 정합성 이슈 목록 작성
- gc: TAXONOMY_v10.md 분석, v11 개선사항 초안
- cx: 소스/설정 버그 스캔 (`P:\_sys\core\`, `P:\_sys\checks\`, `P:\.ai\`)

### Phase 2: TAXONOMY v11 작성 (cc+gc 주도, cx 교차검토)
목표: `P:\_sys\docs\TAXONOMY_v11.md`
방향:
- No-Code / Composable / General-Specific MECE 구조 반영
- 모든 하드코딩 값 → JSON 설정화
- General-Specific 연결지점 JSON화
- Workspace 외 공통 공간 정의
- Base Template 구조 정의
- v10 구현 완성도 평가 → 개선사항 추가

### Phase 3: 전체 산출물 정합성 + 버그 픽스 (cx 주도, cc 검토)
범위:
- `P:\_sys\core\hub.py` — 버그 픽스
- `P:\_sys\checks\*.py` — 정합성
- `P:\.ai\` — 상태 파일 정합성
- `P:\PROTOCOL.md`, `P:\CONVENTION.md` — 내용 정합성
- `P:\_sys\ai\protocol.json` — 설정 정합성
- config.json 키 44개 맞추기 (현재 24개 → 44개)

### Phase 4: 사용자 설명서 (gc 주도, cc 검토)
목표: `P:\_sys\docs\USER_MANUAL.md`
내용 (MECE):
- 시스템 개요 (아키텍처 다이어그램)
- 설치 & 초기 구성
- 일상 사용 (ctx-save, ctx-end, ask, consensus 등)
- 피어별 사용법 (cc/gc/cx)
- 설정 파라미터 레퍼런스
- 트러블슈팅 가이드
- Workspace 신규 구성 가이드

### Phase 5: 구조 정리 (cc 주도, cx 실행)
- 불필요 파일 → `P:\Garbage\`
- 폴더 구조 정리
- 피어별 폴더/로그/설정 위치 표준화
- General-Specific 분리 적용

### Phase 6: 피어 관리 문서 (cc+gc 작성)
목표: `P:\_sys\docs\PEER_MANAGEMENT.md`
내용:
- 피어별: 폴더 위치, 로그 위치, 설정 위치, 관리방안
- General 설정 vs Specific 설정 분리
- JSON 연결 구조

### Phase 7: Git 현행화 (cc 실행)
- `git add -A` (민감 파일 제외)
- conventional commit 메시지
- push to main

---

## 3. TASK ASSIGNMENT

| Task | Primary | Support | Review |
|------|---------|---------|--------|
| Codex bug fix | cc분석/cx구현 | — | cc |
| TAXONOMY v11 | gc초안 | cc리뷰 | cx교차 |
| Hub.py 버그 | cx | cc | gc |
| 전체 정합성 | cx | cc | gc |
| 사용자 설명서 | gc | cc | cx |
| 구조 정리 | cc계획/cx실행 | — | gc |
| 피어 관리 문서 | cc | gc | cx |
| Git 커밋 | cc | — | — |

---

## 4. DECISION RULES (R:10)

- 모든 구조 변경: cc+gc+cx 만장일치 필요
- 파일 삭제/이동: 만장일치 후 실행
- 코드 수정: cx 구현 → cc 리뷰 → gc 교차검토
- 설정 변경: 전원 합의
- 버그 픽스: cx 구현 → cc 검증

---

## 5. FILE LOCATIONS TO AUDIT

```
P:\
├── _sys/
│   ├── ai/           ← protocol.json, orchestration.json
│   ├── checks/       ← check_*.py (버그 스캔 대상)
│   ├── claude/       ← cc 설정, memory
│   ├── codex/        ← cx 설정
│   ├── core/         ← hub.py (핵심, 버그 픽스 대상)
│   ├── cli/          ← msg.bat, codex.bat, etc.
│   ├── docs/         ← TAXONOMY, PROTOCOL, etc.
│   ├── gemini/       ← gc 설정, config.json
│   └── hooks/        ← ctx-save, ctx-end
├── .ai/              ← state.json, sessions, nodes.json
├── PROTOCOL.md       ← 정합성 검토
├── CONVENTION.md     ← 정합성 검토
└── Garbage/          ← 이동 대상 (생성 필요)
```

---

## 6. QUALITY GATES

각 Phase 완료 전:
1. cc가 체크리스트 작성
2. gc 교차검토
3. cx 기술적 검증
4. 만장일치 ACK → 다음 Phase 진행

---

## 7. CURRENT STATUS

- [ ] Codex bug 조사 완료
- [ ] 전체 파일 구조 스캔
- [ ] gc/cx 숙지 확인
- [ ] Phase 1 시작

---
*이 파일은 진행 중 업데이트됨. 최종본이 아님.*
