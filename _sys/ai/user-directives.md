# User Directives - Active Standing Rules

> Scope: all peers (`cc`, `gc`, `cx`, `ag`)
> Effective: immediately
> Expiry: none unless explicitly revoked
> Canonical path: `P:\_sys\ai\user-directives.md`
> Managed by: coordinator
> Injection: `hub.py` appends this file to every peer ask as a `[USER DIRECTIVES]` block.

## Active Directives

### DIR-001: ROI-Based Auto-Termination for Exhaustive Work Sessions

- Effective: 2026-06-14
- Status: ACTIVE
- Rule: During exhaustive improvement work sessions, the active coordinator must autonomously declare `EXHAUSTIVE_COMPLETE` when the ROI gate is met, without requiring additional user confirmation.
- ROI gate:
  1. All standard review lenses were applied.
  2. Two consecutive passes produced no HIGH findings.
  3. Remaining findings are cosmetic only.
- Reference: `DEBATE_PROTOCOL.md` section 16-3.

### DIR-002: Minimum Non-Interactive Permissions for All Peers

- Effective: 2026-06-13
- Status: ACTIVE
- Rule: All peers run with minimum non-interactive permissions and must not block on interactive approval prompts during `hub.py ask` or console wrapper invocations.
- Implementation:
  - `cc`: `--allowedTools Edit Write Read Glob Grep Bash MultiEdit --permission-mode acceptEdits`
  - `gc`: `--approval-mode auto_edit --skip-trust`
  - `cx`: `-s workspace-write`
  - `ag`: `--allowedTools Edit Write Read Glob Grep Bash MultiEdit --permission-mode acceptEdits`
- References:
  - `_sys/ai/orchestration.json`
  - `_sys/cli/peer_console.py`
  - `_sys/docs/protocol/protocol-permissions.md` (authoritative per-peer profiles)

### DIR-003: hub.py 공개 API 변경 시 test_contracts.py 동기화 필수

- Effective: 2026-06-16
- Status: ACTIVE
- Rule: `hub.py`의 공개 API (`_lease_cfg`, `_build_session_cmd`, `action_ask`, 및 모든 `action_*` 함수)의 시그니처(파라미터명, 기본값, 반환 타입 어노테이션)를 변경할 경우, 반드시 `_sys/tests/unit/test_contracts.py`를 같은 커밋에 업데이트해야 한다.
- Why: 과거 `_lease_cfg()` 2-tuple→3-tuple 변경 시 테스트 26개가 무음으로 깨진 사건에서 도출된 규칙.
- Scope: `cc`, `gc`, `cx` 모두 적용. API 변경 PR 리뷰 시 contract 업데이트 여부를 체크리스트에 포함.
- Source: LL-008 / gc self-evolution audit 2026-06-16.

## Revoked Directives

None.
