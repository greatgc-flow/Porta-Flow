"""Governance tests for hub.py leadership claims."""
import json
import shutil
import uuid
from pathlib import Path

import pytest

import hub


@pytest.fixture
def governance_ai_dir(monkeypatch):
    root = Path.cwd().resolve()
    test_root = root / "pytest_local" / "hub_governance" / uuid.uuid4().hex
    ai = test_root / "ai"
    (ai / ".lock").mkdir(parents=True)
    (ai / "sessions").mkdir()
    (ai / "consensus").mkdir()
    (ai / "mailbox").mkdir()
    (ai / "mailbox.json").write_text(
        json.dumps({"messages": [], "unread_count": 0}), encoding="utf-8"
    )
    (ai / "state.json").write_text(
        json.dumps({
            "room_id": None,
            "members": {},
            "mission": None,
            "blocked": None,
            "phase": None,
            "updated_at": None,
        }),
        encoding="utf-8",
    )
    (ai / "nodes.json").write_text(json.dumps({"version": "1", "nodes": {}}), encoding="utf-8")
    (ai / "leases.json").write_text(json.dumps({}), encoding="utf-8")

    def write_json_for_test(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    monkeypatch.setattr(hub, "_write_json_atomic", write_json_for_test)
    try:
        yield ai
    finally:
        resolved = test_root.resolve()
        allowed = root / "pytest_local"
        if resolved == allowed or allowed not in resolved.parents:
            raise RuntimeError(f"refusing to remove unexpected test path: {resolved}")
        shutil.rmtree(resolved, ignore_errors=True)


def _read_state(ai_dir):
    return json.loads((ai_dir / "state.json").read_text(encoding="utf-8"))


def _write_state(ai_dir, state):
    (ai_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")


def _patch_leader_claim_policy(monkeypatch, minutes=5):
    monkeypatch.setattr(
        hub,
        "_load_protocol_cfg",
        lambda: {"leader_election": {"challenge_window_minutes": minutes}},
    )


def test_leader_claim_records_pending_challenge_window(governance_ai_dir, monkeypatch, capsys):
    ai_dir = governance_ai_dir
    _patch_leader_claim_policy(monkeypatch)

    hub.action_leader_claim(ai_dir, "cc", reason="stabilize", domain="general")

    state = _read_state(ai_dir)
    leadership = state["leadership"]
    assert state["leader"] == "cc"
    assert state["active_coordinator"] == "cc"
    assert leadership["peer"] == "cc"
    assert leadership["status"] == "PENDING"
    assert leadership["domain"] == "general"
    assert leadership["reason"] == "stabilize"
    assert leadership["challenge_until"]
    assert state["coordinator_history"][-1]["peer"] == "cc"
    assert "status=PENDING" in capsys.readouterr().out


def test_ap20_blocks_fourth_consecutive_leader_claim(governance_ai_dir, monkeypatch, capsys):
    ai_dir = governance_ai_dir
    _patch_leader_claim_policy(monkeypatch)
    state = _read_state(ai_dir)
    state["coordinator_history"] = [
        {"peer": "gc", "at": "2026-06-16T00:00:00", "room": "room-1"},
        {"peer": "gc", "at": "2026-06-16T00:01:00", "room": "room-1"},
        {"peer": "gc", "at": "2026-06-16T00:02:00", "room": "room-1"},
    ]
    _write_state(ai_dir, state)

    with pytest.raises(SystemExit) as excinfo:
        hub.action_leader_claim(ai_dir, "gc", reason="fourth", domain="general")

    assert excinfo.value.code == 1
    state = _read_state(ai_dir)
    assert "leadership" not in state
    assert [item["peer"] for item in state["coordinator_history"]] == ["gc", "gc", "gc"]
    assert "AP-20 Violation" in capsys.readouterr().err


def test_counter_claim_during_challenge_window_replaces_pending_claim(governance_ai_dir, monkeypatch, capsys):
    ai_dir = governance_ai_dir
    _patch_leader_claim_policy(monkeypatch)
    monkeypatch.setattr(hub, "_peer_effective_health", lambda peer: ("GREEN", {}))

    hub.action_leader_claim(ai_dir, "cc", reason="initial", domain="general")
    capsys.readouterr()

    hub.action_leader_claim(ai_dir, "gc", reason="counter", domain="review")

    state = _read_state(ai_dir)
    leadership = state["leadership"]
    assert state["leader"] == "gc"
    assert state["active_coordinator"] == "gc"
    assert leadership["peer"] == "gc"
    assert leadership["status"] == "PENDING"
    assert leadership["domain"] == "review"
    assert leadership["reason"] == "counter"
    assert [item["peer"] for item in state["coordinator_history"][-2:]] == ["cc", "gc"]
    out = capsys.readouterr().out
    assert "CHALLENGE: gc is challenging cc's pending claim" in out
    assert "LEADER-CLAIM gc | status=PENDING" in out


def test_alert_raise_sets_active_alert_and_blocks(governance_ai_dir, capsys):
    ai_dir = governance_ai_dir
    hub.action_alert_raise(ai_dir, "gc", "P0", "Database corrupted")
    
    state = _read_state(ai_dir)
    alert = state.get("alert_active")
    assert alert is not None
    assert alert["severity"] == "P0"
    assert alert["msg"] == "Database corrupted"
    assert "P0 Alert" in state["blocked"]
    
    out = capsys.readouterr().out
    assert "ALERT RAISED by gc" in out


def test_thread_promote_copies_mailbox_to_thread(tmp_path, capsys):
    ai_dir = tmp_path / ".ai"
    hub.ensure_ai_dir(ai_dir)
    
    # 1. Create a mailbox message
    msg_id = "msg-123"
    mbox = {"messages": [{"id": msg_id, "from": "cc", "msg": "Key insight", "ts": "2026-06-16T12:00:00"}], "unread_count": 1}
    hub._write_json(ai_dir / "mailbox.json", mbox)
    
    # 2. Promote to thread
    hub.action_thread_promote(ai_dir, msg_id, "design-thread", "gc")
    
    # 3. Verify thread log
    # hub.py _threads_dir defaults to "default" if room_id is missing
    state = hub._read_json(ai_dir / "state.json")
    room_id = state.get("room_id") or "default"
    thread_path = ai_dir / "sessions" / room_id / "threads" / "design-thread.jsonl"
    
    assert thread_path.exists()
    content = thread_path.read_text("utf-8")
    assert "PROMOTED from msg-123" in content
    assert "Key insight" in content
    
    # 4. Verify mailbox marking
    updated_mbox = hub._read_json(ai_dir / "mailbox.json")
    assert updated_mbox["messages"][0]["promoted_to"] == "design-thread"
