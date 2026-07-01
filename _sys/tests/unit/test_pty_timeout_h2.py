import pytest
import sys
from pathlib import Path
import subprocess

sys.path.insert(0, __import__("os").path.join(
    __import__("os").path.dirname(__file__), "..", "..", "core"))
import hub

def test_pty_unbounded_timeout_when_node_timeout_zero(monkeypatch):
    """PTY node.timeout=0 + no --timeout: deadline unbounded (not 300s)"""
    node = {
        "node_id": "ag", "invoke": "agy", "type": "peer",
        "adapter_class": "AgyAdapter", "requires_pty": True, "timeout": 0
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/agy")
    
    passed_timeout = None
    
    def mock_ask_with_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        nonlocal passed_timeout
        passed_timeout = timeout_sec
        return hub._PtyAskResult(text="ok", elapsed=1, exit_code=0, timed_out=False, timeout_kind=None, pid=123, transport_error=None)
        
    monkeypatch.setattr(hub, "_ask_with_pty", mock_ask_with_pty)
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_sweep", lambda *a: None)
    
    hub.action_ask("ag", "hello", None, 0, None)
    
    assert passed_timeout == 0, "When node.timeout<=0, PTY must be unbounded (0) like non-PTY"

def test_profile_aware_zombie(monkeypatch):
    """profile-aware zombie: ag.deepthink resolves ~7200s, ag.standard short"""
    def mock_resolve_profile_id(node_id):
        return node_id # "ag.deepthink" or "ag.standard"
        
    monkeypatch.setattr(hub, "_resolve_profile_id", mock_resolve_profile_id)
    monkeypatch.setattr(hub, "_load_protocol_cfg", lambda: {
        "communication_policy": {
            "heartbeat_sec": 30,
            "lease_timeout_sec": 300,
            "zombie_timeout_sec": 600,
            "zombie_profile_map": {
                "deepthink": 7200,
                "standard": 300
            }
        }
    })
    
    _, _, z_deep = hub._lease_cfg("ag.deepthink")
    assert z_deep == 7200, "deepthink profile must resolve to 7200s zombie timeout"
    
    _, _, z_std = hub._lease_cfg("ag.standard")
    assert z_std == 300, "standard profile must resolve to 300s zombie timeout"
    
    _, _, z_fallback = hub._lease_cfg("ag")
    assert z_fallback == 600, "unmapped profile must fallback to global zombie_timeout_sec"

def test_a1_silent_zombie_exception_reports_zombie_threshold(monkeypatch):
    """A1: silent-zombie exception/log reports the zombie threshold, not lease_timeout_sec."""
    node = {
        "node_id": "cc", "invoke": "claude", "type": "peer",
        "adapter_class": "ClaudeAdapter", "requires_pty": False
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/claude")
    monkeypatch.setattr(hub, "_lease_cfg", lambda x=None: (5, 1800, 600))
    monkeypatch.setattr(hub, "_lease_open", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_renew", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_kill_process_tree", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_short_id", lambda *a, **k: "id")
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.pid = 999
            self.stdout = None
            self.stderr = None
            self.returncode = None
        def poll(self):
            return None # still running
        def communicate(self, input=None, timeout=None):
            # Emit output once (flips staged timeout to the zombie phase), then
            # stay silent so the ZOMBIE threshold (not startup, not lease) is hit.
            raise subprocess.TimeoutExpired(["cmd"], timeout, output=b"partial")
            
    monkeypatch.setattr(hub.subprocess, "Popen", MockPopen)
    
    failures = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    with pytest.raises(SystemExit):
        hub.action_ask("cc", "mock", None, 3000, None)
        
    assert len(failures) == 1
    detail = failures[0][2]
    assert "ask timeout after 600" in detail, "ZOMBIE threshold must be reported in exception, not lease timeout"

def test_explicit_timeout_enforced_non_pty_unchanged(monkeypatch):
    """explicit --timeout still enforced; non-PTY (cc/cx) unchanged."""
    node = {
        "node_id": "cc", "invoke": "claude", "type": "peer",
        "adapter_class": "ClaudeAdapter", "requires_pty": False
    }
    monkeypatch.setattr(hub, "_load_orchestration", lambda: {"hub_nodes": [node]})
    monkeypatch.setattr(hub.shutil, "which", lambda x: "/bin/claude")
    monkeypatch.setattr(hub, "_lease_cfg", lambda x=None: (5, 1800, 600))
    monkeypatch.setattr(hub, "_lease_open", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_renew", lambda *a, **k: None)
    
    import time
    time_val = 100.0
    monkeypatch.setattr(time, "monotonic", lambda: time_val)
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.pid = 999
            self.stdout = None
            self.stderr = None
            self.returncode = None
        def poll(self):
            return None
        def communicate(self, input=None, timeout=None):
            nonlocal time_val
            time_val += 60.0  # pass deadline
            raise subprocess.TimeoutExpired(["cmd"], timeout, output=b"")
            
    monkeypatch.setattr(hub.subprocess, "Popen", MockPopen)
    monkeypatch.setattr(hub, "_kill_process_tree", lambda *a, **k: None)
    
    failures = []
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: failures.append(a))
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    
    with pytest.raises(SystemExit):
        hub.action_ask("cc", "hello", None, 50, None)
    
    assert len(failures) == 1
    detail = failures[-1][2]
    assert "ask timeout after 50" in detail, "Explicit timeout must be enforced"

    # test 0 timeout (unbounded)
    time_val = 100.0
    passed_timeout = None
    
    class MockPopen0:
        def __init__(self, *args, **kwargs):
            self.pid = 999
            self.stdout = None
            self.stderr = None
            self.returncode = 0
        def poll(self):
            return 0
        def communicate(self, input=None, timeout=None):
            nonlocal passed_timeout
            passed_timeout = timeout
            return b"ok", b""
            
    monkeypatch.setattr(hub.subprocess, "Popen", MockPopen0)
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    
    hub.action_ask("cc", "hello", None, 0, None)
    assert passed_timeout == 5, "non-PTY with 0 timeout must stay bounded by heartbeat for loop logic"

