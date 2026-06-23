"""PTY transport tests (ag-only path) — A2/A5/A7 + _PtyAskResult.

Uses a fake winpty child so no real `agy` is launched. Targets `_ask_with_pty`
directly: the A2 fix (a blocking read must NOT prevent the execution deadline),
exit-code capture (A5), spawn-failure transport error, cwd propagation (A7),
silent-zombie timeout, and the CONDITION-2 lease contract (open-here, the
caller closes).

NOTE: authored by the terminal as a verification artifact while worker peers
were quota/transport-blocked; the production PTY implementation was worker-
applied (cc.deepthink) and N=2 ratified. Asserts against the real applied API.
"""
import sys
import time
import types
import threading
import hashlib
from pathlib import Path

import pytest

sys.path.insert(0, __import__("os").path.join(
    __import__("os").path.dirname(__file__), "..", "..", "core"))
import hub  # noqa: E402


class _FakePty:
    """Minimal stand-in for winpty.PtyProcess."""
    spawn_calls: list = []
    instances: list = []
    _behavior: dict = {}

    def __init__(self, behavior):
        self.behavior = behavior
        self.pid = behavior.get("pid", 4242)
        self.exitstatus = behavior.get("exitstatus", 0)
        self._reads = list(behavior.get("reads", []))  # str chunks; then EOF
        self._alive = True
        self.terminated = False
        self.closed = False

    @classmethod
    def spawn(cls, cmd, cwd=None, env=None):
        cls.spawn_calls.append({"cmd": cmd, "cwd": cwd, "env": env})
        if cls._behavior.get("spawn_raises"):
            raise RuntimeError("spawn boom")
        inst = cls(cls._behavior)
        cls.instances.append(inst)
        return inst

    def read(self, n):
        if self.behavior.get("block"):
            # Simulate a blocking read that ends only when the main thread
            # terminates/closes us (the A2 scenario). Daemon reader → no hang.
            while self._alive and not self.terminated and not self.closed:
                time.sleep(0.01)
            raise EOFError()
        if self._reads:
            return self._reads.pop(0)
        self._alive = False
        raise EOFError()

    def isalive(self):
        return self._alive and not self.terminated and not self.closed

    def terminate(self, force=False):
        self.terminated = True
        self._alive = False

    def close(self, force=False):
        self.closed = True
        self._alive = False


@pytest.fixture
def fake_winpty(monkeypatch):
    """Install a fake `winpty` module; reset spawn log per test."""
    _FakePty.spawn_calls = []
    _FakePty.instances = []
    _FakePty._behavior = {}
    fake_mod = types.ModuleType("winpty")
    fake_mod.PtyProcess = _FakePty
    monkeypatch.setitem(sys.modules, "winpty", fake_mod)

    def _set(**behavior):
        _FakePty._behavior = behavior
    return _set


def test_ptyaskresult_fields():
    r = hub._PtyAskResult(
        text="x", elapsed=1, exit_code=0, timed_out=False,
        timeout_kind=None, pid=1,
    )
    assert (r.text, r.exit_code, r.timed_out, r.pid) == ("x", 0, False, 1)
    assert r.transport_error is None
    with pytest.raises(Exception):  # frozen dataclass
        r.text = "y"


def test_normal_eof_returns_output_and_exit_code(fake_winpty):
    fake_winpty(reads=["hello ", "world"], exitstatus=0)
    r = hub._ask_with_pty(["agy"], "ag", 30, {}, quiet=True, ai_root=None)
    assert "hello world" in r.text
    assert r.exit_code == 0
    assert r.timed_out is False
    assert r.transport_error is None
    assert r.pid == 4242


def test_nonzero_exit_is_captured(fake_winpty):
    fake_winpty(reads=["nope"], exitstatus=7)
    r = hub._ask_with_pty(["agy"], "ag", 30, {}, quiet=True, ai_root=None)
    assert r.exit_code == 7
    assert r.timed_out is False


def test_blocking_read_honors_execution_deadline(fake_winpty):
    """THE A2 fix: a child whose read() blocks indefinitely must still be cut
    at the execution deadline (not run unbounded), and reported timed_out."""
    fake_winpty(block=True)
    t0 = time.monotonic()
    r = hub._ask_with_pty(["agy"], "ag", 1, {}, quiet=True, ai_root=None)
    wall = time.monotonic() - t0
    assert r.timed_out is True
    assert r.timeout_kind == "deadline"
    assert wall < 4, f"deadline not honored during blocking read (wall={wall:.1f}s)"
    assert _FakePty.instances[0].terminated is True
    assert _FakePty.instances[0].closed is True


def test_lease_renewal_happens_while_read_blocked(fake_winpty, monkeypatch):
    monkeypatch.setattr(hub, "_lease_cfg", lambda: (0.1, 10, 10))
    renews = []
    monkeypatch.setattr(hub, "_lease_renew", lambda *a: renews.append(a))
    monkeypatch.setattr(hub, "_lease_open", lambda *a, **k: None)
    fake_winpty(block=True)
    hub._ask_with_pty(["agy"], "ag", 1, {}, quiet=True, ai_root=Path("/tmp/root"))
    assert len(renews) > 0, "Lease renewal must happen while read is blocked"


def test_silent_zombie_timeout(fake_winpty, monkeypatch):
    """Alive but silent child is killed by the zombie guard."""
    # heartbeat, lease_timeout, zombie  → tiny zombie so the test is fast.
    monkeypatch.setattr(hub, "_lease_cfg", lambda: (30, 300, 1))
    fake_winpty(block=True)
    r = hub._ask_with_pty(["agy"], "ag", 60, {}, quiet=True, ai_root=None)
    assert r.timed_out is True
    assert r.timeout_kind == "zombie"
    assert _FakePty.instances[0].terminated is True
    assert _FakePty.instances[0].closed is True


def test_spawn_failure_returns_transport_error(fake_winpty):
    fake_winpty(spawn_raises=True)
    r = hub._ask_with_pty(["agy"], "ag", 30, {}, quiet=True, ai_root=None)
    assert r.transport_error is not None
    assert "pty_spawn_failed" in r.transport_error
    assert r.pid == -1
    assert r.timed_out is False


def test_cwd_is_propagated_to_spawn(fake_winpty):
    fake_winpty(reads=["ok"], exitstatus=0)
    hub._ask_with_pty(["agy"], "ag", 30, {}, quiet=True, ai_root=None,
                      cwd=r"D:\proj root")
    assert _FakePty.spawn_calls[-1]["cwd"] == r"D:\proj root"


def test_ask_with_pty_opens_lease_but_does_not_close(fake_winpty, monkeypatch):
    """CONDITION-2: the lease is OPENED here, never CLOSED here (the caller's
    PTY `finally` closes it exactly once)."""
    opened, closed = [], []
    monkeypatch.setattr(hub, "_lease_open",
                        lambda *a, **k: opened.append((a, k)))
    monkeypatch.setattr(hub, "_lease_close",
                        lambda *a, **k: closed.append((a, k)))
    monkeypatch.setattr(hub, "_lease_renew", lambda *a, **k: None)
    fake_winpty(reads=["ok"], exitstatus=0)
    r = hub._ask_with_pty(["agy"], "ag", 30, {}, quiet=True, ai_root="/tmp/x",
                          ask_id="ask-abcd")
    assert opened, "_ask_with_pty must open the lease"
    assert not closed, "_ask_with_pty must NOT close the lease (caller does)"
    assert r.exit_code == 0


def test_staged_prompt_filename_is_not_ephemeral():
    """A1 staged file {ask_id}-ag-prompt.txt must NOT match the ephemeral
    auto-name regex (so it is governed only by the explicit finally delete,
    never the single-use unlink path)."""
    from pathlib import Path
    p = Path("/repo/ipc/ask-ab12-ag-prompt.txt")
    assert hub._is_ephemeral_query_file(p) is False


def test_pty_inline_command_limit_constant():
    assert hub._PTY_INLINE_COMMAND_LIMIT == 24_000


def test_action_ask_exit_7_records_failure(monkeypatch):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    failures = []
    successes = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: successes.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    res = hub._PtyAskResult(
        text="failed output", elapsed=3, exit_code=7, timed_out=False,
        timeout_kind=None, pid=123
    )
    monkeypatch.setattr(hub, "_ask_with_pty", lambda *a, **k: res)
    
    with pytest.raises(SystemExit) as exc:
        hub.action_ask("ag", "test query", None, 300, None)
    
    assert exc.value.code == 1
    assert len(failures) == 1
    assert len(successes) == 0


def test_action_ask_partial_output_timeout_is_failure(monkeypatch):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    failures = []
    successes = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: successes.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    res = hub._PtyAskResult(
        text="partial progress", elapsed=5, exit_code=None, timed_out=True,
        timeout_kind="deadline", pid=123
    )
    monkeypatch.setattr(hub, "_ask_with_pty", lambda *a, **k: res)
    
    with pytest.raises(SystemExit) as exc:
        hub.action_ask("ag", "test query", None, 300, None)
        
    assert exc.value.code == 1
    assert len(failures) == 1
    assert len(successes) == 0


def test_action_ask_exit_0_with_output_is_success(monkeypatch, capsys):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    failures = []
    successes = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: successes.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    res = hub._PtyAskResult(
        text="successful output", elapsed=2, exit_code=0, timed_out=False,
        timeout_kind=None, pid=123
    )
    monkeypatch.setattr(hub, "_ask_with_pty", lambda *a, **k: res)
    
    hub.action_ask("ag", "test query", None, 300, None)
    
    assert len(failures) == 0
    assert len(successes) == 1


def test_action_ask_lease_closed_exactly_once(monkeypatch):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    closed_calls = []
    monkeypatch.setattr(hub, "_lease_close", lambda *a: closed_calls.append(a))
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    # Test success path -> lease_status "closed"
    res_success = hub._PtyAskResult(
        text="ok", elapsed=1, exit_code=0, timed_out=False,
        timeout_kind=None, pid=123
    )
    monkeypatch.setattr(hub, "_ask_with_pty", lambda *a, **k: res_success)
    hub.action_ask("ag", "test query", None, 300, Path("/tmp/root"))
    
    assert len(closed_calls) == 1
    # _lease_close signature: (ai_root, node_id, pid, status)
    assert closed_calls[0] == (Path("/tmp/root"), "ag", 123, "closed")
    
    # Test timeout path -> lease_status "timeout"
    closed_calls.clear()
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: None)
    res_timeout = hub._PtyAskResult(
        text="partial", elapsed=1, exit_code=None, timed_out=True,
        timeout_kind="deadline", pid=123
    )
    monkeypatch.setattr(hub, "_ask_with_pty", lambda *a, **k: res_timeout)
    with pytest.raises(SystemExit):
        hub.action_ask("ag", "test query", None, 300, Path("/tmp/root"))
    assert len(closed_calls) == 1
    assert closed_calls[0] == (Path("/tmp/root"), "ag", 123, "timeout")


def test_action_ask_propagates_parent_cwd(monkeypatch):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    passed_cwd = []
    def mock_ask_with_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        passed_cwd.append(cwd)
        return hub._PtyAskResult(text="ok", elapsed=1, exit_code=0, timed_out=False, timeout_kind=None, pid=123)
        
    monkeypatch.setattr(hub, "_ask_with_pty", mock_ask_with_pty)
    
    ai_root = Path("/foo/bar/.ai")
    hub.action_ask("ag", "test query", None, 300, ai_root)
    
    assert passed_cwd == [str(ai_root.parent)]


def test_action_ask_staging_oversized_prompt(monkeypatch, tmp_path):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_close", lambda *a, **k: None)
    
    # Create a very long query (>24,000 chars)
    query = "A" * 25000
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()
    
    staged_file_path = None
    
    def mock_ask_with_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        nonlocal staged_file_path
        # The staged file should be in ai_root/ipc/{ask_id}-ag-prompt.txt
        staged_files = list((ai_root / "ipc").glob("*-ag-prompt.txt"))
        assert len(staged_files) == 1
        staged_file_path = staged_files[0]
        assert staged_file_path.read_text(encoding="utf-8") == query
        
        # The cmd should have been replaced with the pointer_prompt command
        assert any("[IPC PAYLOAD FILE]" in arg for arg in cmd)
        assert any(digest in arg for arg in cmd)
        
        return hub._PtyAskResult(text="ok", elapsed=1, exit_code=0, timed_out=False, timeout_kind=None, pid=123)
        
    monkeypatch.setattr(hub, "_ask_with_pty", mock_ask_with_pty)
    
    # ask_id is generated internally by action_ask (not a parameter); the mock
    # locates the staged file by glob, so it does not need a fixed value.
    hub.action_ask("ag", query, None, 300, ai_root)
    
    # The staged file should be cleaned up (deleted) in finally
    assert staged_file_path is not None
    assert not staged_file_path.exists(), "Staged file must be unlinked in finally"


def test_action_ask_staging_cleanup_on_timeout(monkeypatch, tmp_path):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_close", lambda *a, **k: None)
    
    query = "A" * 25000
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()
    
    staged_file_path = None
    
    def mock_ask_with_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        nonlocal staged_file_path
        staged_files = list((ai_root / "ipc").glob("*-ag-prompt.txt"))
        assert len(staged_files) == 1
        staged_file_path = staged_files[0]
        return hub._PtyAskResult(text="partial", elapsed=1, exit_code=None, timed_out=True, timeout_kind="deadline", pid=123)
        
    monkeypatch.setattr(hub, "_ask_with_pty", mock_ask_with_pty)
    
    with pytest.raises(SystemExit):
        hub.action_ask("ag", query, None, 300, ai_root)
        
    assert staged_file_path is not None
    assert not staged_file_path.exists(), "Staged file must be unlinked even on timeout"


def test_action_ask_staging_failure(monkeypatch, tmp_path):
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True,
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    failures = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    # Mock Path.write_text to fail
    original_write_text = Path.write_text
    def mock_write_text(self, data, *args, **kwargs):
        if "ag-prompt.txt" in self.name:
            raise IOError("disk full")
        return original_write_text(self, data, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", mock_write_text)
    
    query = "A" * 25000
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()
    
    with pytest.raises(SystemExit) as exc:
        hub.action_ask("ag", query, None, 300, ai_root)
        
    assert exc.value.code == 1
    assert len(failures) == 1
    assert failures[0][0] == "ag"  # health_peer
    assert failures[0][1] == "prompt_staging_failed"


def test_cc_cx_regression_never_calls_ask_with_pty(monkeypatch):
    cc_node = {
        "node_id": "cc", "invoke": "claude", "type": "peer",
        "adapter_class": "ClaudeAdapter",
    }
    cx_node = {
        "node_id": "cx", "invoke": "codex", "type": "peer",
        "adapter_class": "CodexAdapter",
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [cc_node, cx_node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/mock")
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.returncode = 0
            self.pid = 999
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def communicate(self, input=None, timeout=None):
            return b"standard response\n", b""
            
    monkeypatch.setattr(hub.subprocess, "Popen", MockPopen)
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    def pty_boom(*args, **kwargs):
        raise AssertionError("_ask_with_pty should never be called for cc or cx")
    monkeypatch.setattr(hub, "_ask_with_pty", pty_boom)
    
    hub.action_ask("cc", "hello cc", None, 300, None)
    hub.action_ask("cx", "hello cx", None, 300, None)
