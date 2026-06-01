# Global Claude Preferences
<!-- Copy this file to: [PortableDev]\_sys\claude\config\CLAUDE.md  -->
<!-- CLAUDE_CONFIG_DIR in start.bat points claude here automatically -->
<!-- Update with ctx-end --global                                    -->

---

## Communication
- Respond in Korean
- Explain the plan before making changes
- Ask before large refactors or file deletions
- Keep answers concise; expand only when asked

## Development Environment
- OS: Windows 11, portable sandbox dev env (USB / cloud drive)
- Editor: VS Code (portable) + Claude Code CLI (portable via npm-global)
- Claude Desktop on host PC

## Code Preferences
- Python: type hints, docstrings on public functions
- Commit messages: English, conventional commits format
- Variable names: English; inline comments: Korean OK
- Prefer explicit over clever

## Workflow Rules
- Create a branch before large changes
- Write tests before implementation when practical
- Run ctx-save at natural pause points during a session
- Run ctx-end when done for the day

## Gemini Delegation Protocol

Claude의 역할: **위임(delegate) → 검증(verify) → 보고(report)**
Gemini가 실작업을 수행하고, Claude는 방향 설정과 결과 점검을 담당한다.

### GEMINI_RATIO 레벨 (P:\_sys\gemini\config.json)

| ratio | Claude 행동 기준 |
|-------|----------------|
| 0     | Gemini OFF — 모든 작업을 Claude가 독립 수행 |
| 1–4   | Claude 독립 — 수동 요청 시에만 Gemini 참여 |
| 5–6   | 복잡한 분석·설계 결정에만 consult 필수 |
| 7–9   | 멀티파일·리팩토링·버그분석 등 비trivial 작업 전 반드시 consult |
| 10    | **전면 위임** — 모든 읽기·쓰기·분석 행동 전에 Gemini 먼저 |

### ratio 10: 전면 위임 규칙
아래 각 행동을 하기 **전에** 반드시 Gemini를 호출한다:

- **파일 읽기(Read) 전**: 해당 파일에서 찾을 내용·관련 섹션을 Gemini에게 먼저 분석 요청
- **파일 편집/쓰기(Edit·Write) 전**: 변경 내용의 완전한 초안을 Gemini에게 생성 요청 → 결과를 그대로 적용
- **Bash 명령 전**: 명령의 정확성·위험성·대안을 Gemini에게 확인
- **코드 분석·리뷰**: Gemini가 주도하고 Claude는 결과 검증

### 호출 방법 (2단계, Bash 도구 timeout 180000)
Step 1 — 쿼리 파일 작성 (Write 도구):
  파일: `P:\_sys\gemini\consult-query.txt`
  내용: TASK/CONTEXT/QUESTION 형식으로 작성

Step 2 — Gemini 호출 (PowerShell 도구, timeout 180000):
```
$env:PATH += ";P:\_sys\env\nodejs\npm-global"
cmd /c "P:\_sys\context\gemini-consult.bat" 2>&1
```

### 위임 모드 (파일 내용 생성을 Gemini에게)
쿼리에 "파일의 완전한 새 내용을 작성해줘" 포함 → Gemini가 전체 파일 내용을 텍스트로 출력
→ Claude가 Write 도구로 해당 파일에 그대로 적용 → `git diff HEAD`로 확인 후 보고

### Claude의 역할 순서
1. 사용자 의도 파악 → Gemini에 명확한 지시 전달
2. Gemini 응답 대기 (30~120초 정상 범위)
3. Gemini 결과 검증 (git diff, 로직 확인)
4. 미완성/오류 부분만 Claude가 보완

## Context Files
- Project context : [project root]\CLAUDE.md  (auto-read at session start)
- Global context  : [this file]               (applies to all projects)
- Session archive : _sys\data\sessions\YYYY-MM-DD_ProjectName.md  (auto-saved by ctx-save / ctx-end)
