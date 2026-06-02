"""hub.py 10개 액션 단위 테스트."""
import json
import pytest
from pathlib import Path
import hub


# ─── init-session ───────────────────────────────────────────
class TestInitSession:
    def test_claude_creates_sid(self, ai_dir, capsys):
        hub.action_init_session(ai_dir, "claude", "")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        assert state["claude_sid"] is not None
        assert state["claude_sid"].startswith("c")

    def test_gemini_creates_sid(self, ai_dir, capsys):
        hub.action_init_session(ai_dir, "gemini", "")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        assert state["gemini_sid"] is not None
        assert state["gemini_sid"].startswith("g")

    def test_pair_format(self, ai_dir, capsys):
        hub.action_init_session(ai_dir, "claude", "")
        hub.action_init_session(ai_dir, "gemini", "")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        pair = state["pair"]
        assert pair.startswith("c")
        assert "-g" in pair

    def test_llm_format_output(self, ai_dir, capsys):
        hub.action_init_session(ai_dir, "claude", "llm")
        captured = capsys.readouterr()
        assert "[SESSION]" in captured.out

    def test_session_dir_created(self, ai_dir):
        hub.action_init_session(ai_dir, "claude", "")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        session_dir = ai_dir / "sessions" / state["pair"]
        assert session_dir.exists()


# ─── send + check ────────────────────────────────────────────
class TestSendCheck:
    def test_send_creates_message(self, ai_dir):
        hub.action_send(ai_dir, "claude", "gemini", "hello")
        mb = json.loads((ai_dir / "mailbox.json").read_text("utf-8"))
        assert len(mb["messages"]) == 1
        assert mb["messages"][0]["content"] == "hello"
        assert mb["messages"][0]["status"] == "unread"
        assert mb["unread_count"] == 1

    def test_check_llm_format(self, ai_dir, capsys):
        hub.action_send(ai_dir, "claude", "gemini", "test msg")
        hub.action_check(ai_dir, "gemini", "llm")
        captured = capsys.readouterr()
        assert "[UNREAD:1]" in captured.out
        assert "test msg" in captured.out

    def test_check_empty(self, ai_dir, capsys):
        hub.action_check(ai_dir, "claude", "llm")
        captured = capsys.readouterr()
        assert "[UNREAD:0]" in captured.out

    def test_multiple_messages(self, ai_dir):
        for i in range(5):
            hub.action_send(ai_dir, "claude", "gemini", f"msg-{i}")
        mb = json.loads((ai_dir / "mailbox.json").read_text("utf-8"))
        assert mb["unread_count"] == 5


# ─── mark-read ───────────────────────────────────────────────
class TestMarkRead:
    def test_mark_all(self, ai_dir):
        hub.action_send(ai_dir, "claude", "gemini", "m1")
        hub.action_send(ai_dir, "claude", "gemini", "m2")
        hub.action_mark_read(ai_dir, "gemini", all_=True, msg_id=None)
        mb = json.loads((ai_dir / "mailbox.json").read_text("utf-8"))
        assert mb["unread_count"] == 0

    def test_mark_by_id(self, ai_dir):
        hub.action_send(ai_dir, "claude", "gemini", "m1")
        hub.action_send(ai_dir, "claude", "gemini", "m2")
        hub.action_mark_read(ai_dir, "gemini", all_=False, msg_id=1)
        mb = json.loads((ai_dir / "mailbox.json").read_text("utf-8"))
        assert mb["unread_count"] == 1


# ─── update-status ───────────────────────────────────────────
class TestUpdateStatus:
    def test_mission(self, ai_dir):
        hub.action_update_status(ai_dir, "test task", None, None)
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        assert state["mission"] == "test task"

    def test_blocked(self, ai_dir):
        hub.action_update_status(ai_dir, "task", "auth bug", "3")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        assert state["blocked"] == "auth bug"
        assert state["phase"] == "3"


# ─── end-session ─────────────────────────────────────────────
class TestEndSession:
    def test_end_session_cleans_read_messages(self, ai_dir):
        hub.action_init_session(ai_dir, "claude", "")
        hub.action_send(ai_dir, "gemini", "claude", "done")
        hub.action_mark_read(ai_dir, "claude", all_=True, msg_id=None)
        hub.action_end_session(ai_dir, "claude")
        mb = json.loads((ai_dir / "mailbox.json").read_text("utf-8"))
        # read 상태 메시지는 제거됨
        assert len(mb["messages"]) == 0

    def test_end_session_updates_handoff(self, ai_dir):
        hub.action_init_session(ai_dir, "claude", "")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        hub.action_end_session(ai_dir, "claude")
        session_dir = ai_dir / "sessions" / state["pair"]
        handoff = (session_dir / "handoff.md").read_text("utf-8")
        assert "claude: 세션 종료" in handoff


# ─── status ──────────────────────────────────────────────────
class TestStatus:
    def test_status_llm(self, ai_dir, capsys):
        hub.action_init_session(ai_dir, "claude", "")
        hub.action_update_status(ai_dir, "test mission", None, "1")
        hub.action_status(ai_dir, "llm")
        captured = capsys.readouterr()
        assert "[PAIR]" in captured.out
        assert "test mission" in captured.out


# ─── check-gate ──────────────────────────────────────────────
class TestCheckGate:
    def test_gate_gemini_on(self, ai_dir, tmp_path, monkeypatch):
        gemini_dir = tmp_path / "gemini"
        gemini_dir.mkdir()
        status = gemini_dir / "status.json"
        status.write_text(json.dumps({"mode": "ON"}), encoding="utf-8")

        # Path(__file__).parent.parent.parent / "gemini" / "status.json" 모킹
        import hub as hub_mod
        monkeypatch.setattr(
            hub_mod.Path, "__truediv__",
            lambda self, other: status if str(other) == "status.json" else Path.__truediv__(self, other)
        )

    def test_claude_always_on(self, ai_dir, capsys):
        with pytest.raises(SystemExit) as exc:
            hub.action_check_gate(ai_dir, "claude")
        assert exc.value.code == 0


# ─── handoff FIFO ────────────────────────────────────────────
class TestHandoffFIFO:
    def test_fifo_max_completed(self, ai_dir):
        session_dir = ai_dir / "sessions" / "c1234-g5678"
        session_dir.mkdir(parents=True)
        sections = {
            "GOAL": ["목표"],
            "RECENT_COMPLETED": [f"task-{i}" for i in range(10)],
            "PENDING_ISSUES": [],
            "KEY_DECISIONS": []
        }
        hub._write_handoff(session_dir, sections)
        result = hub._read_handoff(session_dir)
        assert len(result["RECENT_COMPLETED"]) <= hub.HANDOFF_MAX_COMPLETED

    def test_fifo_char_limit(self, ai_dir):
        session_dir = ai_dir / "sessions" / "c1234-g5678"
        session_dir.mkdir(parents=True)
        # 매우 긴 항목들
        sections = {
            "GOAL": ["목표"],
            "RECENT_COMPLETED": ["x" * 2000] * 10,
            "PENDING_ISSUES": [],
            "KEY_DECISIONS": []
        }
        hub._write_handoff(session_dir, sections)
        content = (session_dir / "handoff.md").read_text("utf-8")
        assert len(content) <= hub.HANDOFF_MAX_CHARS


# ─── Token-Zero 포맷터 ────────────────────────────────────────
class TestTokenZero:
    def test_format_unread_messages(self):
        messages = [
            {"id": 1, "from": "claude", "to": "gemini", "content": "hello", "status": "unread"},
            {"id": 2, "from": "claude", "to": "gemini", "content": "world", "status": "read"},
        ]
        output = hub._format_llm_check(messages, "gemini")
        assert "[UNREAD:1]" in output
        assert "hello" in output

    def test_format_no_messages(self):
        output = hub._format_llm_check([], "gemini")
        assert "[UNREAD:0]" in output
