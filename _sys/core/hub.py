"""
hub.py — Portable Dev Environment AI 협업 허브 (Facade 패턴)
10개 액션: Write 7개 (filelock) + Read 3개 (Lock-Free)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Windows 콘솔 UTF-8 강제 (CP949 가로막기)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import uuid
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# .ai/ 프로젝트 루트 탐색 (CWD → .git 상향, 없으면 CWD에 생성)
# ─────────────────────────────────────────────────────────────

def find_ai_root() -> Path:
    """CWD에서 시작해 .git/.ai를 찾아 상향 탐색. 없으면 CWD."""
    cwd = Path.cwd().resolve()
    candidate = cwd
    while True:
        if (candidate / ".ai").exists():
            return candidate / ".ai"
        if (candidate / ".git").exists():
            return candidate / ".ai"
        parent = candidate.parent
        if parent == candidate:  # 드라이브 루트
            return cwd / ".ai"
        candidate = parent


def ensure_ai_dir(ai_root: Path) -> Path:
    """필요한 하위 폴더 생성 및 초기 파일 생성."""
    (ai_root / ".lock").mkdir(parents=True, exist_ok=True)
    (ai_root / "sessions").mkdir(parents=True, exist_ok=True)
    if not (ai_root / "mailbox.json").exists():
        _write_json(ai_root / "mailbox.json", {"messages": [], "unread_count": 0})
    if not (ai_root / "state.json").exists():
        _write_json(ai_root / "state.json", {
            "pair": None, "claude_sid": None, "gemini_sid": None,
            "mission": None, "blocked": None, "phase": None,
            "updated_at": None
        })
    return ai_root


# ─────────────────────────────────────────────────────────────
# JSON 유틸리티 (UTF-8 강제)
# ─────────────────────────────────────────────────────────────

def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _short_id(prefix: str = "") -> str:
    """prefix + 4자리 hex. 예: claude→'c2b5', gemini→'g4707'"""
    return prefix + uuid.uuid4().hex[:4]


# ─────────────────────────────────────────────────────────────
# filelock 헬퍼
# ─────────────────────────────────────────────────────────────

def _get_lock(ai_root: Path, resource: str):
    from filelock import FileLock
    lock_path = ai_root / ".lock" / f"{resource}.lock"
    os.makedirs(ai_root / ".lock", exist_ok=True)  # FileLock 전 필수
    return FileLock(str(lock_path), timeout=10)


# ─────────────────────────────────────────────────────────────
# handoff.md FIFO 관리 (≤3000토큰 ≈ 12000자)
# ─────────────────────────────────────────────────────────────

HANDOFF_MAX_CHARS = 12000
HANDOFF_MAX_COMPLETED = 5
HANDOFF_MAX_ISSUES = 3
HANDOFF_MAX_DECISIONS = 3


def _parse_handoff(text: str) -> dict:
    """섹션 파싱: [GOAL], [RECENT_COMPLETED], [PENDING_ISSUES], [KEY_DECISIONS]"""
    sections: dict[str, list[str]] = {
        "GOAL": [], "RECENT_COMPLETED": [], "PENDING_ISSUES": [], "KEY_DECISIONS": []
    }
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("## [GOAL]", "## [RECENT_COMPLETED]", "## [PENDING_ISSUES]", "## [KEY_DECISIONS]"):
            current = stripped[4:-1]
        elif current and stripped.startswith("- "):
            sections[current].append(stripped[2:])
    return sections


def _render_handoff(sections: dict) -> str:
    lines = ["## [GOAL]"]
    lines += [f"- {x}" for x in sections["GOAL"]] or ["- (목표 미설정)"]
    lines += ["\n## [RECENT_COMPLETED]"]
    lines += [f"- {x}" for x in sections["RECENT_COMPLETED"]] or ["- (없음)"]
    lines += ["\n## [PENDING_ISSUES]"]
    lines += [f"- {x}" for x in sections["PENDING_ISSUES"]] or ["- (없음)"]
    lines += ["\n## [KEY_DECISIONS]"]
    lines += [f"- {x}" for x in sections["KEY_DECISIONS"]] or ["- (없음)"]
    return "\n".join(lines) + "\n"


def _read_handoff(session_dir: Path) -> dict:
    path = session_dir / "handoff.md"
    if not path.exists():
        return {"GOAL": [], "RECENT_COMPLETED": [], "PENDING_ISSUES": [], "KEY_DECISIONS": []}
    return _parse_handoff(path.read_text(encoding="utf-8"))


def _write_handoff(session_dir: Path, sections: dict) -> None:
    # FIFO: 초과 항목 제거
    sections["RECENT_COMPLETED"] = sections["RECENT_COMPLETED"][-HANDOFF_MAX_COMPLETED:]
    sections["PENDING_ISSUES"] = sections["PENDING_ISSUES"][-HANDOFF_MAX_ISSUES:]
    sections["KEY_DECISIONS"] = sections["KEY_DECISIONS"][-HANDOFF_MAX_DECISIONS:]
    text = _render_handoff(sections)
    # 3000토큰 방어 (12000자 초과 시 RECENT_COMPLETED 추가 축소)
    while len(text) > HANDOFF_MAX_CHARS and sections["RECENT_COMPLETED"]:
        sections["RECENT_COMPLETED"].pop(0)
        text = _render_handoff(sections)
    (session_dir / "handoff.md").write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# Token-Zero 포맷터
# ─────────────────────────────────────────────────────────────

def _format_llm_check(messages: list, target: str) -> str:
    unread = [m for m in messages if m.get("to") == target and m.get("status") == "unread"]
    if not unread:
        return f"[UNREAD:0] {target}에게 새 메시지 없음"
    lines = [f"[UNREAD:{len(unread)}]"]
    for m in unread[-5:]:  # 최대 5개
        lines.append(f"  From:{m['from']} | ID:{m['id']} | '{m['content'][:60]}'")
    return "\n".join(lines)


def _format_llm_status(state: dict, messages: list) -> str:
    pair = state.get("pair") or "미설정"
    mission = state.get("mission") or "없음"
    blocked = state.get("blocked")
    phase = state.get("phase")
    unread_c = sum(1 for m in messages if m.get("to") == "claude" and m.get("status") == "unread")
    unread_g = sum(1 for m in messages if m.get("to") == "gemini" and m.get("status") == "unread")
    lines = [
        f"[PAIR] {pair} | mission={mission}" + (f" | blocked={blocked}" if blocked else ""),
    ]
    if phase:
        lines[0] += f" | phase={phase}"
    lines.append(f"[MAILBOX] claude={unread_c}unread / gemini={unread_g}unread")
    return "\n".join(lines)


def _format_llm_handoff(sections: dict) -> str:
    lines = []
    if sections["PENDING_ISSUES"]:
        lines.append("[HANDOFF] ⚠ " + " | ".join(sections["PENDING_ISSUES"][:2]))
    if sections["RECENT_COMPLETED"]:
        lines.append("[RECENT] " + sections["RECENT_COMPLETED"][-1])
    return "\n".join(lines) if lines else "[HANDOFF] 이전 세션 정보 없음"


# ─────────────────────────────────────────────────────────────
# Write 액션 (filelock 적용)
# ─────────────────────────────────────────────────────────────

def action_init_session(ai_root: Path, agent: str, fmt: str) -> None:
    """세션 초기화: SID 발급, pair 생성 또는 합류."""
    # SID에 prefix 포함: claude→"c2b5", gemini→"g4707"
    prefix = "c" if agent == "claude" else "g"
    sid = _short_id(prefix)
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        ts = _now()
        if agent == "claude":
            state["claude_sid"] = sid
        else:
            state["gemini_sid"] = sid

        # pair 갱신: "c2b5-g4707" 형식
        c = state.get("claude_sid") or "c---"
        g = state.get("gemini_sid") or "g---"
        state["pair"] = f"{c}-{g}"
        state["updated_at"] = ts
        _write_json(ai_root / "state.json", state)

    # 세션 폴더 생성
    session_dir = ai_root / "sessions" / state["pair"]
    session_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "llm":
        handoff = _read_handoff(session_dir)
        print(f"[SESSION] {agent}={sid} | pair={state['pair']}")
        print(_format_llm_handoff(handoff))
    else:
        print(sid)


def action_end_session(ai_root: Path, agent: str) -> None:
    """세션 종료: handoff.md 갱신 (COMPLETED 추가), mailbox 정리."""
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        pair = state.get("pair")
        ts = _now()

        if agent == "claude":
            completed_entry = f"{ts[:10]} {agent}: 세션 종료"
            state["claude_sid"] = None
        else:
            completed_entry = f"{ts[:10]} {agent}: 세션 종료"
            state["gemini_sid"] = None
        state["updated_at"] = ts
        _write_json(ai_root / "state.json", state)

    if pair:
        session_dir = ai_root / "sessions" / pair
        session_dir.mkdir(parents=True, exist_ok=True)
        handoff = _read_handoff(session_dir)
        handoff["RECENT_COMPLETED"].append(completed_entry)
        _write_handoff(session_dir, handoff)

    # 읽은 메시지 정리 (read 상태 → 제거)
    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = mb.get("messages", [])
        msgs = [m for m in msgs if m.get("status") != "read"]
        mb["messages"] = msgs
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)

    print(f"[END] {agent} 세션 종료 완료")


def action_send(ai_root: Path, from_: str, to: str, msg: str) -> None:
    """메시지 발송."""
    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = mb.get("messages", [])
        new_id = len(msgs) + 1
        msgs.append({
            "id": new_id,
            "from": from_,
            "to": to,
            "content": msg,
            "status": "unread",
            "timestamp": _now()
        })
        mb["messages"] = msgs
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)
    print(f"[SENT] {from_}→{to} | id={new_id}")


def action_mark_read(ai_root: Path, target: str, all_: bool, msg_id: int | None) -> None:
    """메시지 읽음 처리."""
    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = mb.get("messages", [])
        count = 0
        for m in msgs:
            if m.get("to") == target and m.get("status") == "unread":
                if all_ or m.get("id") == msg_id:
                    m["status"] = "read"
                    count += 1
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)
    print(f"[READ] {count}개 메시지 읽음 처리")


def action_append_log(ai_root: Path, axis: str, script: str, status: str, detail: str) -> None:
    """Axis 실행 로그 기록."""
    log_path = ai_root / "log.jsonl"
    entry = {
        "ts": _now(), "axis": axis, "script": script,
        "status": status, "detail": detail
    }
    with _get_lock(ai_root, "log"):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[LOG] {axis} {script} → {status}")


def action_archive_file(ai_root: Path, name: str, file_path: str) -> None:
    """파일을 _archive/{name}-YYYYMMDD.json + latest 로 아카이빙."""
    src = Path(file_path)
    if not src.exists():
        print(f"[ERROR] 파일 없음: {file_path}", file=sys.stderr)
        sys.exit(1)

    # _archive 위치: ai_root 부모의 _archive/
    archive_dir = ai_root.parent / "_archive"
    archive_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    dst_dated = archive_dir / f"{name}-{date_str}.json"
    dst_latest = archive_dir / f"{name}-latest.json"

    import shutil
    shutil.copy2(src, dst_dated)
    shutil.copy2(src, dst_latest)
    print(f"[ARCHIVE] {name} → {dst_dated.name} + {name}-latest.json")


def action_update_status(ai_root: Path, mission: str, blocked: str | None, phase: str | None) -> None:
    """미션·블로커·페이즈 상태 업데이트."""
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        state["mission"] = mission
        if blocked is not None:
            state["blocked"] = blocked if blocked else None
        if phase is not None:
            state["phase"] = phase
        state["updated_at"] = _now()
        _write_json(ai_root / "state.json", state)
    print(f"[STATUS] mission={mission}")


# ─────────────────────────────────────────────────────────────
# Read 액션 (Lock-Free)
# ─────────────────────────────────────────────────────────────

def action_check(ai_root: Path, target: str, fmt: str) -> None:
    """받은 메시지 확인."""
    mb = _read_json(ai_root / "mailbox.json")
    msgs = mb.get("messages", [])
    if fmt == "llm":
        print(_format_llm_check(msgs, target))
    else:
        unread = [m for m in msgs if m.get("to") == target and m.get("status") == "unread"]
        print(json.dumps(unread, ensure_ascii=False, indent=2))


def action_status(ai_root: Path, fmt: str) -> None:
    """전체 상태 조회."""
    state = _read_json(ai_root / "state.json")
    mb = _read_json(ai_root / "mailbox.json")
    msgs = mb.get("messages", [])

    if fmt == "llm":
        print(_format_llm_status(state, msgs))
        # handoff 추가
        pair = state.get("pair")
        if pair:
            session_dir = ai_root / "sessions" / pair
            handoff = _read_handoff(session_dir)
            print(_format_llm_handoff(handoff))
    else:
        print(json.dumps({
            "state": state,
            "unread_claude": sum(1 for m in msgs if m.get("to") == "claude" and m.get("status") == "unread"),
            "unread_gemini": sum(1 for m in msgs if m.get("to") == "gemini" and m.get("status") == "unread"),
        }, ensure_ascii=False, indent=2))


def action_check_gate(ai_root: Path, agent: str) -> None:
    """게이트 확인: Gemini/Claude 가용 여부."""
    if agent == "gemini":
        # _sys/gemini/status.json 참조
        status_path = Path(__file__).parent.parent / "gemini" / "status.json"
        if status_path.exists():
            data = _read_json(status_path)
            if data.get("mode") == "ON":
                print("[GATE] gemini=ON")
                sys.exit(0)
        print("[GATE] gemini=OFF")
        sys.exit(1)
    else:
        print(f"[GATE] {agent}=ON")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog="hub", description="AI 협업 허브")
    parser.add_argument("action", choices=[
        "init-session", "end-session", "send", "mark-read",
        "append-log", "archive-file", "update-status",
        "check", "status", "check-gate"
    ])
    parser.add_argument("--agent", choices=["claude", "gemini"])
    parser.add_argument("--from", dest="from_", metavar="AGENT")
    parser.add_argument("--to", dest="to_")
    parser.add_argument("--msg", dest="msg")
    parser.add_argument("--target", dest="target")
    parser.add_argument("--all", dest="all_", action="store_true")
    parser.add_argument("--id", dest="msg_id", type=int)
    parser.add_argument("--axis", dest="axis")
    parser.add_argument("--script", dest="script")
    parser.add_argument("--status", dest="status_val")
    parser.add_argument("--detail", dest="detail", default="")
    parser.add_argument("--name", dest="name")
    parser.add_argument("--file", dest="file_path")
    parser.add_argument("--mission", dest="mission")
    parser.add_argument("--blocked", dest="blocked", default=None)
    parser.add_argument("--phase", dest="phase", default=None)
    parser.add_argument("--format", dest="fmt", default="", choices=["", "llm"])
    args = parser.parse_args()

    ai_root = find_ai_root()
    ensure_ai_dir(ai_root)

    act = args.action
    try:
        if act == "init-session":
            action_init_session(ai_root, args.agent or "claude", args.fmt)
        elif act == "end-session":
            action_end_session(ai_root, args.agent or "claude")
        elif act == "send":
            if not args.from_ or not args.to_ or not args.msg:
                print("[ERROR] --from, --to, --msg 필수", file=sys.stderr); sys.exit(1)
            action_send(ai_root, args.from_, args.to_, args.msg)
        elif act == "mark-read":
            if not args.target:
                print("[ERROR] --target 필수", file=sys.stderr); sys.exit(1)
            action_mark_read(ai_root, args.target, args.all_, args.msg_id)
        elif act == "append-log":
            action_append_log(ai_root, args.axis or "", args.script or "", args.status_val or "", args.detail)
        elif act == "archive-file":
            if not args.name or not args.file_path:
                print("[ERROR] --name, --file 필수", file=sys.stderr); sys.exit(1)
            action_archive_file(ai_root, args.name, args.file_path)
        elif act == "update-status":
            if not args.mission:
                print("[ERROR] --mission 필수", file=sys.stderr); sys.exit(1)
            action_update_status(ai_root, args.mission, args.blocked, args.phase)
        elif act == "check":
            if not args.target:
                print("[ERROR] --target 필수", file=sys.stderr); sys.exit(1)
            action_check(ai_root, args.target, args.fmt)
        elif act == "status":
            action_status(ai_root, args.fmt)
        elif act == "check-gate":
            action_check_gate(ai_root, args.agent or "gemini")
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
