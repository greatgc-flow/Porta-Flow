"""
hub.py — Portable Dev Environment AI 협업 허브 (P2P v3.1)
액션: Write 7개 (filelock) + Read 2개 (Lock-Free) + ask 1개 (동기) + consensus 3개 + node 2개

P2P v3: N-Way Room 세션 기반 평등 권등 구조 구현.
기존 Pair(c-g) 구조 폐기 -> room-{uuid} 및 members 리스트 기반 동적 협업.
v3.1: 실시간 협업 가시성 로그 (_log_p2p) 추가.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Windows 콘솔 UTF-8 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────
# .ai/ 프로젝트 루트 탐색
# ─────────────────────────────────────────────────────────────

def find_ai_root() -> Path:
    cwd = Path.cwd().resolve()
    candidate = cwd
    while True:
        if (candidate / ".ai").exists():
            return candidate / ".ai"
        if (candidate / ".git").exists():
            return candidate / ".ai"
        parent = candidate.parent
        if parent == candidate:
            return cwd / ".ai"
        candidate = parent


def _load_orchestration() -> dict:
    """_sys/ai/orchestration.json 로드 (hub 전용 상수 포함)."""
    path = Path(__file__).parent.parent / "ai" / "orchestration.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _load_protocol_cfg() -> dict:
    """_sys/ai/protocol.json 로드 (협업 정책 마스터 설정)."""
    path = Path(__file__).parent.parent / "ai" / "protocol.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _peer_sys_dir(peer_id: str) -> Path:
    """peers.json의 sys_subdir로 _sys/{subdir}/ 해석 — 하드코딩 없음.

    node_id(cc, ca, gc, ag, cx) → peers.json key(claude, gemini, antigravity, codex) 매핑 포함.
    """
    # node_id → peers.json key 매핑 (orchestration.json 또는 기본값)
    _NODE_TO_PEER: dict[str, str] = {"cc": "claude", "ca": "claude", "gc": "gemini", "ag": "antigravity", "cx": "codex"}
    peers = _load_peers()
    peer_data = peers.get("peers", peers)
    peer_key = _NODE_TO_PEER.get(peer_id, peer_id)
    cfg = peer_data.get(peer_key, {})
    subdir = cfg.get("sys_subdir", peer_key)
    return Path(__file__).parent.parent / subdir


def _load_peers() -> dict:
    """_sys/ai/peers.json 로드."""
    path = Path(__file__).parent.parent / "ai" / "peers.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("peers", {}) if path.exists() else {}
    except Exception:
        return {}


def _default_nodes() -> dict:
    """orchestration.json hub_nodes 배열에서 기본 노드 목록을 읽어 반환."""
    orch = _load_orchestration()
    nodes = {}
    for entry in orch.get("hub_nodes", []):
        nid = entry.get("node_id")
        if nid:
            nodes[nid] = {k: v for k, v in entry.items() if k != "node_id"}
    if not nodes:
        # orchestration.json 없을 때 최소 fallback (claude만)
        nodes = {"cc": {"type": "peer", "invoke": "claude", "invoke_args": ["-p", "{query}"], "timeout": 0, "memory": "persistent"}}
    return {"version": "2", "nodes": nodes}


def ensure_ai_dir(ai_root: Path) -> Path:
    (ai_root / ".lock").mkdir(parents=True, exist_ok=True)
    (ai_root / "sessions").mkdir(parents=True, exist_ok=True)
    (ai_root / "consensus").mkdir(parents=True, exist_ok=True)
    if not (ai_root / "mailbox.json").exists():
        _write_json(ai_root / "mailbox.json", {"messages": [], "unread_count": 0})
    if not (ai_root / "state.json").exists():
        _write_json(ai_root / "state.json", {
            "room_id": None,
            "members": {}, # {node_id: sid}
            "mission": None, "blocked": None, "phase": None,
            "updated_at": None
        })
    if not (ai_root / "nodes.json").exists():
        _write_json(ai_root / "nodes.json", _default_nodes())
    return ai_root


# ─────────────────────────────────────────────────────────────
# JSON / 유틸리티
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
    return prefix + uuid.uuid4().hex[:4]


def _log_p2p(action: str, details: str, from_node: str | None = None, to_node: str | None = None) -> None:
    """실시간 협업 가시성을 위한 정형화된 로그 출력."""
    if os.environ.get("P2P_VERBOSE") != "1":
        # 루틴한 폴링/상태 조회는 기본적으로 숨김
        routine = action.lower() in ("check", "status", "check-gate", "mark-read", "list-nodes", "consensus-check")
        if routine: return
    
    n_from = from_node.upper() if from_node else "SYS"
    n_to = to_node.upper() if to_node else "ALL"
    
    # [P2P] 프리픽스로 가시성 확보
    print(f"  ━━ P2P [{n_from} → {n_to}] {action}: {details}", file=sys.stderr)


def _strip_ansi(text: str) -> str:
    return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)


def _extract_jsonl_text(raw: str, peer_id: str, ai_root: Path | None) -> str:
    """JSONL 스트림(--json 플래그)에서 텍스트만 추출, .ai/out/<peer>.last.md에 저장.

    지원 이벤트 형식:
    - codex: {"type":"item.completed","item":{"text":"..."}}
    - codex delta: {"type":"item.delta","item":{"type":"text","text":"..."}}
    - codex message: {"type":"message","role":"assistant","content":[{"type":"text","text":"..."}]}
    - 일반: {"text":"..."} / {"content":"..."} / {"message":"..."}
    """
    texts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = obj.get("type", "")
        # codex item.completed
        if t == "item.completed":
            item = obj.get("item", {})
            val = item.get("text") or item.get("content", "")
            if val:
                texts.append(val)
        # codex item.delta (streaming)
        elif t == "item.delta":
            delta = obj.get("item", {})
            if delta.get("type") == "text":
                val = delta.get("text", "")
                if val:
                    texts.append(val)
        # codex / openai message event
        elif t == "message":
            role = obj.get("role", "")
            if role in ("assistant", ""):
                content = obj.get("content", "")
                if isinstance(content, str) and content:
                    texts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            val = block.get("text", "")
                            if val:
                                texts.append(val)
        # 일반 플랫 필드
        elif "text" in obj and obj["text"]:
            texts.append(obj["text"])
        elif "content" in obj and isinstance(obj["content"], str) and obj["content"]:
            texts.append(obj["content"])
        elif "message" in obj and isinstance(obj["message"], str) and obj["message"]:
            texts.append(obj["message"])

    # delta 누적은 그대로, completed는 마지막 것만 의미 있으므로 중복 제거
    seen: set[str] = set()
    deduped = [t for t in texts if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
    result = "\n\n".join(deduped).strip() or raw.strip()

    # .ai/out/<peer>.last.md 에 저장
    if ai_root:
        out_dir = ai_root / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{peer_id}.last.md").write_text(result, encoding="utf-8")
    return result


# ─────────────────────────────────────────────────────────────
# filelock 헬퍼
# ─────────────────────────────────────────────────────────────

def _get_lock(ai_root: Path, resource: str):
    from filelock import FileLock
    lock_path = ai_root / ".lock" / f"{resource}.lock"
    os.makedirs(ai_root / ".lock", exist_ok=True)
    return FileLock(str(lock_path), timeout=10)


# ─────────────────────────────────────────────────────────────
# nodes.json 관리
# ─────────────────────────────────────────────────────────────

def _load_nodes(ai_root: Path) -> dict:
    """orchestration.json을 base로 로드. nodes.json은 custom 추가 노드만 병합."""
    base = _default_nodes()["nodes"]
    nodes_path = ai_root / "nodes.json"
    if nodes_path.exists():
        data = _read_json(nodes_path)
        custom = data.get("nodes", {})
        # orchestration 노드가 우선, custom은 신규 노드만 추가
        return {**custom, **base}
    return base


# ─────────────────────────────────────────────────────────────
# 설정 및 상수
# ─────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = Path(__file__).parent / "hub_config.json"
    defaults = {
        "limits": {
            "mailbox_max": 500,
            "handoff_max_chars": 12000,
            "handoff_max_completed": 5,
            "handoff_max_issues": 3,
            "handoff_max_decisions": 3,
            "handoff_max_consensus": 10,
            "handoff_max_threads": 5,
            "large_payload_threshold": 4000
        }
    }
    if not cfg_path.exists():
        return defaults
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        # Merge defaults
        for k, v in defaults["limits"].items():
            cfg.setdefault("limits", {})
            if k not in cfg["limits"]:
                cfg["limits"][k] = v
        return cfg
    except Exception:
        return defaults

_CFG = load_config()
_LIMITS = _CFG["limits"]

HANDOFF_MAX_CHARS = _LIMITS["handoff_max_chars"]
HANDOFF_MAX_COMPLETED = _LIMITS["handoff_max_completed"]
HANDOFF_MAX_ISSUES = _LIMITS["handoff_max_issues"]
HANDOFF_MAX_DECISIONS = _LIMITS["handoff_max_decisions"]
HANDOFF_MAX_CONSENSUS = _LIMITS["handoff_max_consensus"]
HANDOFF_MAX_THREADS = _LIMITS["handoff_max_threads"]

_MAILBOX_MAX = _LIMITS["mailbox_max"]
_LARGE_PAYLOAD_THRESHOLD = _LIMITS["large_payload_threshold"]

_HANDOFF_SECTIONS = [
    "GOAL", "RECENT_COMPLETED", "PENDING_ISSUES", "KEY_DECISIONS",
    "CONSENSUS_HISTORY", "ACTIVE_THREADS"
]


def _parse_handoff(text: str) -> dict:
    sections: dict[str, list[str]] = {s: [] for s in _HANDOFF_SECTIONS}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        for sec in _HANDOFF_SECTIONS:
            if stripped == f"## [{sec}]":
                current = sec
                break
        else:
            if current and stripped.startswith("- "):
                sections[current].append(stripped[2:])
    return sections


def _render_handoff(sections: dict) -> str:
    lines = []
    for sec in _HANDOFF_SECTIONS:
        lines.append(f"## [{sec}]")
        items = sections.get(sec, [])
        lines += [f"- {x}" for x in items] or ["- (없음)"]
        lines.append("")
    return "\n".join(lines)


def _read_handoff(session_dir: Path) -> dict:
    path = session_dir / "handoff.md"
    if not path.exists():
        return {s: [] for s in _HANDOFF_SECTIONS}
    return _parse_handoff(path.read_text(encoding="utf-8"))


def _write_handoff(session_dir: Path, sections: dict) -> None:
    sections["RECENT_COMPLETED"] = sections.get("RECENT_COMPLETED", [])[-HANDOFF_MAX_COMPLETED:]
    sections["PENDING_ISSUES"]   = sections.get("PENDING_ISSUES", [])[-HANDOFF_MAX_ISSUES:]
    sections["KEY_DECISIONS"]    = sections.get("KEY_DECISIONS", [])[-HANDOFF_MAX_DECISIONS:]
    sections["CONSENSUS_HISTORY"] = sections.get("CONSENSUS_HISTORY", [])[-HANDOFF_MAX_CONSENSUS:]
    sections["ACTIVE_THREADS"]    = sections.get("ACTIVE_THREADS", [])[-HANDOFF_MAX_THREADS:]
    text = _render_handoff(sections)
    while len(text) > HANDOFF_MAX_CHARS and sections["RECENT_COMPLETED"]:
        sections["RECENT_COMPLETED"].pop(0)
        text = _render_handoff(sections)
    (session_dir / "handoff.md").write_text(text, encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# Write 액션 (filelock)
# ─────────────────────────────────────────────────────────────

def action_init_session(ai_root: Path, agent: str, room_id: str | None = None) -> None:
    sid = _short_id(agent[:1])
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        if room_id: state["room_id"] = room_id
        elif not state.get("room_id"): state["room_id"] = _short_id("room-")
        members = state.get("members", {})
        members[agent] = sid
        state["members"] = members
        state["updated_at"] = _now()
        _write_json(ai_root / "state.json", state)
        _log_p2p("JOIN", f"Room={state['room_id']} SID={sid}", from_node=agent)
    session_dir = ai_root / "sessions" / state["room_id"]
    session_dir.mkdir(parents=True, exist_ok=True)
    print(sid)


def action_end_session(ai_root: Path, agent: str) -> None:
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        room_id = state.get("room_id")
        ts = _now()
        members = state.get("members", {})
        if agent in members: del members[agent]
        state["members"] = members
        state["updated_at"] = ts
        _write_json(ai_root / "state.json", state)
        _log_p2p("EXIT", "Session ended", from_node=agent)
    if room_id:
        session_dir = ai_root / "sessions" / room_id
        session_dir.mkdir(parents=True, exist_ok=True)
        handoff = _read_handoff(session_dir)
        handoff.setdefault("RECENT_COMPLETED", []).append(f"{ts[:10]} {agent}: 세션 종료")
        _write_handoff(session_dir, handoff)
    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = [m for m in mb.get("messages", []) if m.get("status") != "read"]
        mb["messages"] = msgs
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)
    print(f"[END] {agent} 세션 종료 완료")


def action_send(
    ai_root: Path, from_: str, to: str, msg: str,
    thread_id: str | None = None,
    msg_type: str = "MSG",
    cc_list: list[str] | None = None,
    ref_id: int | None = None,
) -> None:
    if cc_list is None: cc_list = []
    auto_thread = thread_id or _short_id("t-")

    # 대용량 페이로드 오프로드 (Threshold 초과 시)
    if len(msg) > _LARGE_PAYLOAD_THRESHOLD and msg_type == "MSG":
        payload_id = _short_id("p-")
        payload_dir = ai_root / "payloads"
        payload_dir.mkdir(parents=True, exist_ok=True)
        payload_path = payload_dir / f"{payload_id}.json"
        _write_json(payload_path, {"from": from_, "to": to, "content": msg, "timestamp": _now()})
        
        msg = f"payload://{payload_id}"
        msg_type = "PAYLOAD_REF"
        _log_p2p("OFFLOAD", f"Large msg saved to payloads/{payload_id}.json", from_node=from_)

    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = mb.get("messages", [])
        if len(msgs) >= _MAILBOX_MAX:
            msgs = [m for m in msgs if m.get("status") != "read"]
            if len(msgs) >= _MAILBOX_MAX:
                msgs = msgs[-(  _MAILBOX_MAX - 1):]
        new_id = (msgs[-1]["id"] + 1) if msgs else 1
        msgs.append({
            "id": new_id, "thread_id": auto_thread, "type": msg_type,
            "from": from_, "to": to, "cc": cc_list, "content": msg,
            "status": "unread", "timestamp": _now(), "ref": ref_id,
        })
        mb["messages"] = msgs
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)
        _log_p2p("SEND", f"({msg_type}) {msg[:60]}...", from_node=from_, to_node=to)
    cc_str = f" cc={','.join(cc_list)}" if cc_list else ""
    ref_str = f" ref={ref_id}" if ref_id else ""
    print(f"[HUB] SENT  {from_}→{to} | thread={auto_thread} | id={new_id} type={msg_type}{cc_str}{ref_str}")


def action_mark_read(ai_root: Path, target: str, all_: bool, msg_id: int | None) -> None:
    with _get_lock(ai_root, "mailbox"):
        mb = _read_json(ai_root / "mailbox.json")
        msgs = mb.get("messages", [])
        count = 0
        for m in msgs:
            if m.get("to") == target and m.get("status") == "unread":
                if all_ or m.get("id") == msg_id:
                    m["status"] = "read"; count += 1
        mb["unread_count"] = sum(1 for m in msgs if m.get("status") == "unread")
        _write_json(ai_root / "mailbox.json", mb)
    print(f"[READ] {count}개 메시지 읽음 처리")


def action_append_log(ai_root: Path, axis: str, script: str, status: str, detail: str) -> None:
    log_path = ai_root / "log.jsonl"
    entry = {"ts": _now(), "axis": axis, "script": script, "status": status, "detail": detail}
    with _get_lock(ai_root, "log"):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[LOG] {axis} {script} → {status}")


def action_archive_file(ai_root: Path, name: str, file_path: str) -> None:
    src = Path(file_path)
    if not src.exists(): sys.exit(1)
    archive_dir = ai_root.parent / "_archive"
    archive_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    shutil.copy2(src, archive_dir / f"{name}-{date_str}.json")
    shutil.copy2(src, archive_dir / f"{name}-latest.json")
    print(f"[ARCHIVE] {name} → {name}-latest.json")


def action_update_status(ai_root: Path, mission: str, blocked: str | None, phase: str | None) -> None:
    with _get_lock(ai_root, "state"):
        state = _read_json(ai_root / "state.json")
        state["mission"] = mission
        if blocked is not None: state["blocked"] = blocked if blocked else None
        if phase is not None: state["phase"] = phase
        state["updated_at"] = _now()
        _write_json(ai_root / "state.json", state)
        _log_p2p("STATUS", f"Mission={mission} Phase={phase}", from_node="SYSTEM")
    print(f"[STATUS] mission={mission}")


# ─────────────────────────────────────────────────────────────
# Read 액션 (Lock-Free)
# ─────────────────────────────────────────────────────────────

def action_check(ai_root: Path, target: str) -> None:
    mb = _read_json(ai_root / "mailbox.json")
    unread = [m for m in mb.get("messages", []) if (m.get("to") == target or target in m.get("cc", [])) and m.get("status") == "unread"]
    if not unread: print(f"[HUB] READ  0 messages for {target} (inbox empty)"); return
    print(f"[HUB] READ  {len(unread)} messages for {target}\n")
    for m in unread:
        ts = m.get("timestamp", "")[:16]
        content = m.get("content", "")
        
        # Payload dereference
        if content.startswith("payload://"):
            payload_id = content.replace("payload://", "")
            payload_path = ai_root / "payloads" / f"{payload_id}.json"
            if payload_path.exists():
                pdata = _read_json(payload_path)
                content = pdata.get("content", content) + f"\n\n(Payload loaded from {payload_id}.json)"
            else:
                content = f"[ERROR: Payload {payload_id} not found]"

        print(f"**[{m['id']}]** From: **{m['from']}** | {ts} | type={m.get('type','MSG')}\n{content}\n---")


def action_list_nodes(ai_root: Path) -> None:
    nodes = _load_nodes(ai_root)
    print(f"[HUB] NODES ({len(nodes)})")
    for nid, cfg in nodes.items():
        print(f"  {nid}: tier={cfg.get('tier', '-')} type={cfg.get('type', '-')} invoke={cfg.get('invoke', '-')}")


def action_register_node(
    ai_root: Path,
    node_id: str,
    tier: int,
    node_type: str,
    invoke: str,
    invoke_args_str: str,
    memory: str,
    timeout: int,
) -> None:
    invoke_args = [a.strip() for a in invoke_args_str.split(",") if a.strip()]
    with _get_lock(ai_root, "nodes"):
        data = _read_json(ai_root / "nodes.json") if (ai_root / "nodes.json").exists() else _default_nodes()
        data.setdefault("nodes", {})[node_id] = {
            "tier": tier, "type": node_type,
            "invoke": invoke, "invoke_args": invoke_args,
            "memory": memory, "timeout": timeout,
        }
        _write_json(ai_root / "nodes.json", data)
    print(f"[REGISTER] {node_id} (tier={tier}, invoke={invoke})")


def action_status(ai_root: Path) -> None:
    state = _read_json(ai_root / "state.json")
    mb = _read_json(ai_root / "mailbox.json")
    unread_count = mb.get("unread_count", 0)
    
    print("### [ROOM STATUS]")
    print(f"**Room ID**: {state.get('room_id') or '없음'}")
    print(f"**Members**: {', '.join(state.get('members', {}).keys()) or '없음'}")
    print(f"**Mission**: {state.get('mission') or '없음'}")
    print(f"**Blocked**: {state.get('blocked') or '없음'}")
    print(f"**Phase**: {state.get('phase') or '없음'}")
    print(f"**Updated**: {state.get('updated_at') or '없음'}")
    print(f"**Mailbox**: {unread_count} unread")
    
    consensus_dir = ai_root / "consensus"
    if consensus_dir.exists():
        active = []
        for f in sorted(consensus_dir.glob("*.json")):
            r = _read_json(f)
            if r.get("status") == "voting":
                active.append(f"  - {r['round_id']}: {r.get('subject','?')} [{sum(1 for v in r['votes'].values() if v is not None)}/{len(r['voters'])}]")
        if active:
            print("\n### [CONSENSUS — ACTIVE]")
            print("\n".join(active))

    room_id = state.get("room_id")
    if room_id:
        handoff_path = ai_root / "sessions" / room_id / "handoff.md"
        if handoff_path.exists():
            print("\n### [HANDOFF]")
            print(handoff_path.read_text(encoding="utf-8"))


def action_check_gate(ai_root: Path, agent: str) -> None:
    peers = _load_peers()
    gate = None
    # agent는 node_id(gc) 또는 peer_id(gemini) 둘 다 허용
    for peer_id, peer_cfg in peers.items():
        if peer_id == agent or peer_cfg.get("sys_subdir") == agent:
            gate = peer_cfg.get("gate")
            break
    if gate:
        sys_dir = Path(__file__).parent.parent
        status_path = sys_dir / gate["status_file"]
        if status_path.exists():
            data = _read_json(status_path)
            if data.get(gate["mode_key"]) == gate["mode_on_value"]:
                print(f"[GATE] {agent}=ON"); sys.exit(0)
        print(f"[GATE] {agent}=OFF"); sys.exit(1)
    print(f"[GATE] {agent}=ON"); sys.exit(0)


# ─────────────────────────────────────────────────────────────
# ask 액션
# ─────────────────────────────────────────────────────────────

def _decode_output(data: bytes) -> str:
    if not data:
        return ""
    
    # 1. BOM Check
    if data.startswith(b'\xff\xfe'): # UTF-16-LE BOM
        return data[2:].decode("utf-16-le", errors="replace").replace("\r\n", "\n")
    if data.startswith(b'\xfe\xff'): # UTF-16-BE BOM
        return data[2:].decode("utf-16-be", errors="replace").replace("\r\n", "\n")
    if data.startswith(b'\xef\xbb\xbf'): # UTF-8 BOM
        return data[3:].decode("utf-8", errors="replace").replace("\r\n", "\n")

    # 2. Heuristic for UTF-16 if null bytes are present (common in Windows pipes)
    if b'\x00' in data:
        try:
            # decode as utf-16-le and remove any residual nulls
            return data.decode("utf-16-le").replace("\x00", "").replace("\r\n", "\n")
        except UnicodeDecodeError:
            try:
                return data.decode("utf-16-be").replace("\x00", "").replace("\r\n", "\n")
            except UnicodeDecodeError:
                pass
            
    # 3. Standard encodings
    for enc in ["utf-8", "cp949"]:
        try:
            return data.decode(enc).replace("\r\n", "\n")
        except UnicodeDecodeError:
            continue
            
    # 4. Fallback
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n")


def _ask_with_pty(cmd: list[str], node_id: str, timeout_sec: int, process_env: dict) -> None:
    """pywinpty로 pseudo-TTY 실행 — WriteConsole() API 우회 (agy 등 TUI CLI 전용)."""
    try:
        import winpty as _winpty
    except ImportError:
        print(f"[HUB:ERROR] pywinpty not installed (required for {node_id})", file=sys.stderr)
        sys.exit(1)

    p = _winpty.PtyProcess.spawn(cmd, env=process_env)
    chunks: list[str] = []
    deadline = time.monotonic() + (timeout_sec if timeout_sec > 0 else 300)
    t0 = time.monotonic()

    while time.monotonic() < deadline:
        try:
            chunk = p.read(4096)
            if chunk:
                chunks.append(chunk)
        except EOFError:
            break

    try:
        p.close()
    except Exception:
        pass

    elapsed = int(time.monotonic() - t0)
    output = _strip_ansi("".join(chunks))
    print(f"[HUB] REPLY {node_id} | chars={len(output)} | elapsed={elapsed}s\n{output.strip()}")


def action_ask(to: str, query: str, query_file: str | None, timeout_sec: int, ai_root: Path | None) -> None:
    if query_file:
        qf = Path(query_file)
        if not qf.exists(): sys.exit(1)
        query = qf.read_text(encoding="utf-8")
        qf.unlink()

    # 쿼리 전달 전략:
    # {query} 치환 방식은 Windows cmd/bat 호출 시 줄바꿈(\n)에서 인자가 잘리는 치명적 결함이 있음.
    # 따라서 일반 노드는 stdin(-p -) 방식으로 강제 전환.
    # requires_pty 노드(agy 등)는 pywinpty 사용 + query 직접 인라인.
    # aliases는 orchestration.json 각 노드의 "aliases" 필드에서 동적 로드
    nodes = _load_nodes(ai_root) if ai_root else _default_nodes()["nodes"]
    if to not in nodes:
        for nid, ncfg in nodes.items():
            if to in ncfg.get("aliases", []):
                to = nid
                break
    node = nodes.get(to, {})
    exe_name = node.get("invoke", to)
    raw_args = node.get("invoke_args", ["-p", "{query}"])
    requires_pty = node.get("requires_pty", False)

    cmd_args = []
    use_stdin = False
    for arg in raw_args:
        if "{query}" in arg:
            if requires_pty:
                # PTY 모드: query를 직접 인라인 (stdin 치환 불필요)
                cmd_args.append(arg.replace("{query}", query))
            else:
                # {query}가 포함된 인자를 - (stdin) 지시자로 치환
                cmd_args.append(arg.replace("{query}", "-"))
                use_stdin = True
        else:
            cmd_args.append(arg)
    
    exe = shutil.which(exe_name)
    if not exe:
        print(f"[ERROR] {exe_name} CLI not found in PATH", file=sys.stderr)
        sys.exit(1)
    
    cmd = [exe] + cmd_args
    
    # ── Environment Variable Injection ─────────────────────────
    process_env = {**os.environ, "PYTHONUTF8": "1"}
    
    # Load peers to apply peer-specific env_vars (e.g. AGY_CONFIG_HOME)
    peers = _load_peers()
    target_peer_id = None
    target_peer_cfg = None

    # Heuristic to find the peer corresponding to the node or invoke name
    if to in peers:
        target_peer_id = to
        target_peer_cfg = peers[to]
    else:
        for pid, pcfg in peers.items():
            native = pcfg.get("native_binary")
            if native and native.get("bin_name") == exe_name:
                target_peer_id = pid
                target_peer_cfg = pcfg
                break
            if pcfg.get("npm_package") and (to in pid or pid in to):
                target_peer_id = pid
                target_peer_cfg = pcfg
                break

    if target_peer_cfg:
        sys_dir = Path(__file__).parent.parent
        peer_subdir = sys_dir / target_peer_cfg.get("sys_subdir", target_peer_id)
        for k, rel in target_peer_cfg.get("env_vars", {}).items():
            # Resolve relative path
            process_env[k] = str((peer_subdir / rel).resolve())

    # requires_pty: pywinpty로 pseudo-TTY 실행 (WriteConsole() 우회)
    if requires_pty and sys.platform == "win32":
        _ask_with_pty(cmd, to, timeout_sec, process_env)
        return

    try:
        t0 = time.monotonic()
        # env에 PYTHONUTF8=1 설정하여 대상 CLI가 Python인 경우 UTF-8 출력 유도
        # bytes로 캡처하여 인코딩 중의적 처리
        
        result = subprocess.run(
            cmd,
            input=query.encode("utf-8") if use_stdin else None,
            capture_output=True,
            timeout=timeout_sec if timeout_sec > 0 else None,
            env=process_env
        )
        
        elapsed = int(time.monotonic() - t0)
        output = _decode_output(result.stdout)
        output = _strip_ansi(output)

        # JSONL 응답(--json 플래그 사용 노드, 예: cx) → 텍스트만 추출 후 artifact 저장
        if node.get("invoke_args") and "--json" in node.get("invoke_args", []):
            output = _extract_jsonl_text(output, to, ai_root)

        if result.returncode != 0:
            err = _decode_output(result.stderr)
            print(f"[HUB:WARN] {to} exited {result.returncode}\n{_strip_ansi(err)}", file=sys.stderr)

        print(f"[HUB] REPLY {to} | chars={len(output)} | elapsed={elapsed}s\n{output.strip()}")
    except Exception as e:
        print(f"[HUB:ERROR] ask 실패: {e}", file=sys.stderr)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Consensus 프로토콜
# ─────────────────────────────────────────────────────────────

def action_consensus_propose(ai_root: Path, subject: str, voters: list[str], proposed_by: str) -> None:
    round_id = _short_id("r-")
    data = {"round_id": round_id, "subject": subject, "proposed_by": proposed_by, "proposed_at": _now(), 
            "status": "voting", "voters": voters, "votes": {v: None for v in voters}}
    _write_json(ai_root / "consensus" / f"{round_id}.json", data)
    _log_p2p("PROPOSE", f"ID={round_id} Subject='{subject}'", from_node=proposed_by)
    print(f"[HUB] PROPOSE {round_id} | subject={subject} | voters={','.join(voters)}")


def action_consensus_vote(ai_root: Path, round_id: str, voter: str, vote_val: str, reason: str) -> None:
    rpath = ai_root / "consensus" / f"{round_id}.json"
    if not rpath.exists(): sys.exit(1)
    with _get_lock(ai_root, f"consensus_{round_id}"):
        data = _read_json(rpath)
        if data.get("status") in ("finalized", "escalated"):
            print(f"[HUB:ERR] round {round_id} is already closed", file=sys.stderr)
            sys.exit(1)
        if voter not in data.get("voters", []):
            print(f"[HUB:ERR] {voter} is not a registered voter for {round_id}", file=sys.stderr)
            sys.exit(1)
        votes = data.get("votes", {})
        votes[voter] = {"vote": vote_val, "reason": reason, "ts": _now()}
        data["votes"] = votes
        total, cast = len(data["voters"]), sum(1 for v in votes.values() if v is not None)
        
        _log_p2p("VOTE", f"ID={round_id} Vote={vote_val} ({cast}/{total})", from_node=voter)
        print(f"[HUB] VOTE {round_id} | voter={voter} {vote_val} | {cast}/{total}")
        
        if cast == total:
            has_disagree = any(v["vote"] == "disagree" for v in votes.values())
            all_agree = all(v["vote"] == "agree" for v in votes.values())
            if has_disagree:
                data["status"] = "escalated"
                data["outcome"] = "human_gate"
            elif all_agree:
                data["status"] = "finalized"
                data["outcome"] = "unanimous"
            else:
                data["status"] = "finalized"
                data["outcome"] = "abstain"
            _write_json(rpath, data)
            _log_p2p("DECISION", f"ID={round_id} Status={data['status'].upper()} Outcome={data['outcome']}", from_node="SYSTEM")
            print(f"[HUB] DECISION {round_id} {data['status'].upper()} | {data['outcome']}")
            _append_consensus_history(ai_root, round_id, data["subject"], data["status"].upper())
        else: _write_json(rpath, data)


def _append_consensus_history(ai_root: Path, round_id: str, subject: str, outcome: str) -> None:
    state = _read_json(ai_root / "state.json")
    room_id = state.get("room_id")
    if not room_id: return
    session_dir = ai_root / "sessions" / room_id
    session_dir.mkdir(parents=True, exist_ok=True)
    handoff = _read_handoff(session_dir)
    handoff.setdefault("CONSENSUS_HISTORY", []).append(f"{round_id}: {subject} — {outcome} {_now()[:10]}")
    _write_handoff(session_dir, handoff)


def action_consensus_check(ai_root: Path, round_id: str | None) -> None:
    consensus_dir = ai_root / "consensus"
    if not consensus_dir.exists(): return
    files = [consensus_dir / f"{round_id}.json"] if round_id else sorted(consensus_dir.glob("*.json"))
    for f in files:
        if not f.exists(): continue
        r = _read_json(f)
        print(f"\n### [{r['round_id']}] {r['status'].upper()} - {r['subject']}")
        for v, d in r['votes'].items(): print(f"  - {v}: {d['vote'] if d else '(pending)'}")


def action_consensus_sweep(ai_root: Path, timeout_minutes: int = 30) -> None:
    """Auto-escalate stalled voting rounds older than timeout_minutes."""
    consensus_dir = ai_root / "consensus"
    if not consensus_dir.exists(): return
    now = datetime.now()
    swept = 0
    for f in sorted(consensus_dir.glob("*.json")):
        r = _read_json(f)
        if r.get("status") != "voting": continue
        proposed_at_str = r.get("proposed_at", "")
        try:
            proposed_at = datetime.fromisoformat(proposed_at_str)
            age_minutes = (now - proposed_at).total_seconds() / 60
        except Exception:
            age_minutes = 0
        if age_minutes >= timeout_minutes:
            with _get_lock(ai_root, f"consensus_{r['round_id']}"):
                r = _read_json(f)
                if r.get("status") != "voting": continue
                r["status"] = "escalated"
                r["outcome"] = "timeout"
                r["outcome_at"] = _now()
                _write_json(f, r)
            _log_p2p("DECISION", f"ID={r['round_id']} Status=ESCALATED Outcome=timeout (age={age_minutes:.0f}m)", from_node="SYSTEM")
            print(f"[HUB] SWEEP {r['round_id']} ESCALATED | timeout after {age_minutes:.0f}m | {r['subject'][:50]}")
            _append_consensus_history(ai_root, r["round_id"], r["subject"], "ESCALATED(timeout)")
            swept += 1
    if swept == 0:
        print(f"[HUB] SWEEP: no stalled rounds (timeout={timeout_minutes}m)")


# ─────────────────────────────────────────────────────────────
# 건강 관리 액션 (Protocol v4.0)
# ─────────────────────────────────────────────────────────────

def action_health_update(peer_id: str, status: str, jsonl_mb: float = 0.0, failures: int = 0, extra: dict | None = None) -> None:
    """피어 건강 파일 갱신 — 제로토큰, 로컬 파일만."""
    peer_dir = _peer_sys_dir(peer_id)
    health_path = peer_dir / "health.json"
    with _get_lock(peer_dir.parent.parent / ".ai", f"health_{peer_id}"):
        data: dict = {}
        if health_path.exists():
            try:
                data = json.loads(health_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        cfg = _load_protocol_cfg()
        thresholds = cfg.get("health", {}).get("thresholds", {})
        peer_name = peer_id.rstrip("ca")  # cc/ca → claude
        if peer_name not in thresholds:
            peer_name = peer_id
        th = thresholds.get(peer_name, {"green_mb": 0.6, "yellow_mb": 1.2})
        computed_status = status
        if status == "AUTO":
            if jsonl_mb >= th["yellow_mb"]:
                computed_status = "RED"
            elif jsonl_mb >= th["green_mb"]:
                computed_status = "YELLOW"
            else:
                computed_status = "GREEN"
        ctx = data.setdefault("context_health", {})
        ctx["status"] = computed_status
        ctx["jsonl_mb"] = jsonl_mb
        ctx["checked_at"] = datetime.now().strftime("%Y%m%dT%H%M%S")
        ctx["source"] = "self"
        sh = data.setdefault("session_health", {})
        sh["consecutive_failures"] = failures
        today = datetime.now().strftime("%Y%m%d")
        if sh.get("session_date") != today:
            sh["session_count_today"] = 0
            sh["session_date"] = today
        if extra:
            ctx.update(extra)
        health_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    _log_p2p("HEALTH", f"peer={peer_id} status={computed_status} jsonl={jsonl_mb:.2f}MB failures={failures}")
    print(f"[HUB] HEALTH-UPDATE {peer_id} | status={computed_status} jsonl={jsonl_mb:.2f}MB")


def _pid_alive(pid: int) -> bool:
    """PID가 현재 살아있는지 확인 (제로토큰)."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def action_health_check(peer_filter: str | None = None) -> None:
    """전체(또는 특정) 피어 건강 상태 출력. GREEN이지만 PID 종료 시 STALE로 표시."""
    peers_data = _load_peers()
    all_peers_cfg = peers_data.get("peers", peers_data)
    results = []
    targets = [peer_filter] if peer_filter else list(all_peers_cfg.keys())
    for peer_name in targets:
        peer_dir = Path(__file__).parent.parent / all_peers_cfg.get(peer_name, {}).get("sys_subdir", peer_name)
        health_path = peer_dir / "health.json"
        if not health_path.exists():
            results.append(f"{peer_name}=UNKNOWN")
            continue
        try:
            h = json.loads(health_path.read_text(encoding="utf-8"))
            ctx = h.get("context_health", {})
            st = ctx.get("status", "UNKNOWN")
            mb = ctx.get("jsonl_mb", 0.0)
            # lazy PID 검증: GREEN인데 active_pid가 죽어있으면 STALE로 표시 후 갱신
            active_pid = h.get("availability", {}).get("active_pid")
            if st == "GREEN" and active_pid and not _pid_alive(active_pid):
                st = "STALE"
                h.setdefault("context_health", {})["status"] = "STALE"
                h.setdefault("availability", {}).pop("active_pid", None)
                health_path.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
            results.append(f"{peer_name}={st}({mb:.1f}MB)")
        except Exception:
            results.append(f"{peer_name}=ERROR")
    print(f"[HUB:GATE] HEALTH | {' '.join(results)}")


def action_peer_status() -> None:
    """모든 피어 건강 + 게이트 통합 테이블 출력 — check-gate 대체."""
    peers_data = _load_peers()
    all_peers_cfg = peers_data.get("peers", peers_data)
    print("┌─────────────────────────────────────────────────────┐")
    print("│  PEER STATUS (Protocol v4.0)                        │")
    print("├──────────┬──────────┬──────────┬────────────────────┤")
    print("│ Peer     │ Gate     │ Health   │ Details            │")
    print("├──────────┼──────────┼──────────┼────────────────────┤")
    for peer_name, pcfg in all_peers_cfg.items():
        if not pcfg.get("enabled", True):
            continue
        sys_subdir = pcfg.get("sys_subdir", peer_name)
        peer_dir = Path(__file__).parent.parent / sys_subdir
        # 게이트 확인
        gate_cfg = pcfg.get("gate")
        if gate_cfg:
            gate_file = Path(__file__).parent.parent / gate_cfg["status_file"]
            try:
                gd = json.loads(gate_file.read_text(encoding="utf-8"))
                gate = "ON" if gd.get(gate_cfg["mode_key"]) == gate_cfg["mode_on_value"] else "OFF"
            except Exception:
                gate = "?"
        else:
            gate = "OPEN"
        # 건강 확인
        health_path = peer_dir / "health.json"
        if health_path.exists():
            try:
                h = json.loads(health_path.read_text(encoding="utf-8"))
                ctx = h.get("context_health", {})
                health = ctx.get("status", "?")
                mb = ctx.get("jsonl_mb", 0.0)
                details = f"{mb:.1f}MB"
            except Exception:
                health, details = "ERR", ""
        else:
            health, details = "NO FILE", ""
        print(f"│ {peer_name:<8} │ {gate:<8} │ {health:<8} │ {details:<18} │")
    print("└──────────┴──────────┴──────────┴────────────────────┘")


def action_checkpoint(ai_root: Path, agent: str, note: str) -> None:
    """세션 중간에 handoff.md에 체크포인트 항목 추가 — 다른 피어가 즉시 확인 가능."""
    state = _read_json(ai_root / "state.json")
    room_id = state.get("room_id")
    if not room_id:
        print("[HUB] CHECKPOINT: no active room", file=sys.stderr)
        sys.exit(1)
    handoff_path = ai_root / "sessions" / room_id / "handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    entry = f"\n- [{ts}] ({agent}) {note}"
    with _get_lock(ai_root, "handoff"):
        existing = handoff_path.read_text(encoding="utf-8") if handoff_path.exists() else ""
        # ACTIVE_THREADS 섹션에 추가, 없으면 파일 끝에 추가
        if "## ACTIVE_THREADS" in existing:
            updated = existing.replace(
                "## ACTIVE_THREADS",
                f"## ACTIVE_THREADS{entry}",
                1
            )
        else:
            updated = existing + f"\n## ACTIVE_THREADS{entry}\n"
        handoff_path.write_text(updated, encoding="utf-8")
    _log_p2p("CHECKPOINT", f"agent={agent} room={room_id} note={note[:60]}")
    print(f"[HUB] CHECKPOINT {agent} | room={room_id} | {note[:80]}")


def action_context_fill(ai_root: Path, sections: list[str] | None = None) -> None:
    """handoff.md에서 지정 섹션만 읽어 컨텍스트 채우기용 블록 출력 — 제로토큰."""
    cfg = _load_protocol_cfg()
    default_sections = cfg.get("session", {}).get("context_fill_sections", ["GOAL", "PENDING_ISSUES", "KEY_DECISIONS", "ACTIVE_THREADS"])
    wanted = set(sections or default_sections)
    state = _read_json(ai_root / "state.json")
    room_id = state.get("room_id")
    if not room_id:
        print("[HUB] CONTEXT-FILL: no active room")
        return
    handoff_path = ai_root / "sessions" / room_id / "handoff.md"
    if not handoff_path.exists():
        print("[HUB] CONTEXT-FILL: no handoff.md found")
        return
    parsed = _parse_handoff(handoff_path.read_text(encoding="utf-8"))
    print(f"<!-- context-fill | room={room_id} | sections={','.join(wanted)} -->")
    for section, content in parsed.items():
        if section in wanted and content.strip():
            print(f"\n## [{section}]\n{content.strip()}")
    print("<!-- /context-fill -->")


# ─────────────────────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog="hub", description="AI 협업 허브 — P2P v3.1")
    parser.add_argument("action", choices=["init-session", "end-session", "send", "mark-read", "append-log", "archive-file", "update-status", "check", "status", "check-gate", "ask", "consensus-propose", "consensus-vote", "consensus-check", "consensus-sweep", "register-node", "list-nodes", "health-update", "health-check", "peer-status", "context-fill", "checkpoint"])
    parser.add_argument("--agent")
    parser.add_argument("--room")
    parser.add_argument("--from", dest="from_")
    parser.add_argument("--to", dest="to_")
    parser.add_argument("--msg")
    parser.add_argument("--thread-id")
    parser.add_argument("--type", default="MSG")
    parser.add_argument("--cc")
    parser.add_argument("--ref", type=int)
    parser.add_argument("--query", default="")
    parser.add_argument("--query-file")
    parser.add_argument("--target")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--id", type=int)
    parser.add_argument("--axis")
    parser.add_argument("--script")
    parser.add_argument("--status", dest="status_val")
    parser.add_argument("--detail", default="")
    parser.add_argument("--name")
    parser.add_argument("--file", dest="file_path")
    parser.add_argument("--mission")
    parser.add_argument("--blocked")
    parser.add_argument("--phase")
    parser.add_argument("--round-id")
    parser.add_argument("--subject")
    parser.add_argument("--voters")
    parser.add_argument("--voter")
    parser.add_argument("--vote", dest="vote_val")
    parser.add_argument("--reason", default="")
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--tier", type=int, default=4)
    parser.add_argument("--node-type", dest="node_type", default="agent")
    parser.add_argument("--invoke", default="")
    parser.add_argument("--invoke-args", dest="invoke_args_str", default="-p,{query}")
    parser.add_argument("--memory", default="short-term")
    parser.add_argument("--peer")
    parser.add_argument("--jsonl-mb", dest="jsonl_mb", type=float, default=0.0)
    parser.add_argument("--failures", type=int, default=0)
    parser.add_argument("--sections")

    args = parser.parse_args()
    if args.action == "ask":
        ai_root_opt = None
        try: ai_root_opt = find_ai_root()
        except: pass
        action_ask(args.to_, args.query, args.query_file, args.timeout, ai_root_opt)
        return

    ai_root = find_ai_root()
    ensure_ai_dir(ai_root)
    act = args.action
    if act == "init-session": action_init_session(ai_root, args.agent or "cc", args.room)
    elif act == "end-session": action_end_session(ai_root, args.agent or "cc")
    elif act == "send": 
        cc_list = [x.strip() for x in args.cc.split(",") if x.strip()] if args.cc else []
        action_send(ai_root, args.from_, args.to_, args.msg, args.thread_id, args.type, cc_list, args.ref)
    elif act == "mark-read": action_mark_read(ai_root, args.target, args.all, args.id)
    elif act == "append-log": action_append_log(ai_root, args.axis, args.script, args.status_val, args.detail)
    elif act == "archive-file": action_archive_file(ai_root, args.name, args.file_path)
    elif act == "update-status": action_update_status(ai_root, args.mission, args.blocked, args.phase)
    elif act == "check": action_check(ai_root, args.target)
    elif act == "status": action_status(ai_root)
    elif act == "check-gate":
        orch = _load_orchestration()
        default_gate_agent = orch.get("check_gate", {}).get("default_agent", "gc")
        action_check_gate(ai_root, args.agent or default_gate_agent)
    elif act == "consensus-propose":
        orch = _load_orchestration()
        consensus_cfg = orch.get("consensus", {})
        default_voters_list = consensus_cfg.get("default_voters", ["cc", "ca", "gc"])
        default_proposer = consensus_cfg.get("default_proposer", "cc")
        if args.voters:
            voters = [v.strip() for v in args.voters.split(",") if v.strip()]
        else:
            voters = default_voters_list
        action_consensus_propose(ai_root, args.subject, voters, args.from_ or default_proposer)
    elif act == "consensus-vote": action_consensus_vote(ai_root, args.round_id, args.voter, args.vote_val, args.reason)
    elif act == "consensus-check": action_consensus_check(ai_root, args.round_id)
    elif act == "consensus-sweep": action_consensus_sweep(ai_root, args.timeout or 30)
    elif act == "list-nodes": action_list_nodes(ai_root)
    elif act == "register-node":
        action_register_node(
            ai_root, args.name or "", int(getattr(args, "tier", 4) or 4),
            getattr(args, "node_type", "agent") or "agent",
            args.invoke or "", args.invoke_args_str or "-p,{query}",
            args.memory or "short-term", int(args.timeout or 0),
        )
    elif act == "health-update":
        action_health_update(args.peer or "cc", args.status_val or "GREEN", args.jsonl_mb, args.failures)
    elif act == "health-check":
        action_health_check(args.peer)
    elif act == "peer-status":
        action_peer_status()
    elif act == "context-fill":
        sections = [s.strip() for s in args.sections.split(",")] if args.sections else None
        action_context_fill(ai_root, sections)
    elif act == "checkpoint":
        note = args.msg or ""
        if not note:
            print("[HUB] checkpoint requires --msg", file=sys.stderr); sys.exit(1)
        action_checkpoint(ai_root, args.agent or "unknown", note)

if __name__ == "__main__":
    main()
