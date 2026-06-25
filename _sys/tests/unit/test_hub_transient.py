import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

from hub import (
    _classify_ask_failure,
    _record_ask_failure,
    _ask_health_precheck,
    _parse_reset_time,
    _read_peer_health,
    _write_peer_health,
    _peer_effective_health,
    _TRANSIENT_REASONS
)

class TestHubTransient:
    def test_parse_reset_time(self):
        # Format 1: Absolute date
        t1 = "You've hit your usage limit. Try again at Jun 26th, 2026 9:34 AM"
        res1 = _parse_reset_time(t1)
        assert res1 == "2026-06-26T09:34:00"
        
        # Format 2: Time only
        t2 = "try again at 9:09 PM"
        res2 = _parse_reset_time(t2)
        assert res2 is not None
        # Should be today or tomorrow at 21:09:00
        dt2 = datetime.fromisoformat(res2)
        assert dt2.hour == 21
        assert dt2.minute == 9
        
    def test_classify_ask_failure(self):
        # Plain text codex usage limit
        txt1 = "You've hit your usage limit. Try again at Jun 26th, 2026 9:34 AM"
        r1, extra1 = _classify_ask_failure(txt1)
        assert r1 == "rate_or_session_limit"
        assert extra1["rate_limit_state"]["limited"] is True
        assert extra1["rate_limit_state"]["reset_at"] == "2026-06-26T09:34:00"
        
        # JSON codex error shape
        txt2 = '{"type":"error","message":"you exceeded your quota, please try again later."}'
        r2, extra2 = _classify_ask_failure(txt2)
        assert r2 == "rate_or_session_limit"
        
        # 503 Service Unavailable
        txt3 = "HTTP 503 temporarily unavailable"
        r3, extra3 = _classify_ask_failure(txt3)
        assert r3 == "rate_or_session_limit"

        # Transient tests
        r_t1, _ = _classify_ask_failure("HTTP 503 Service Unavailable")
        assert r_t1 == "rate_or_session_limit"
        r_t2, _ = _classify_ask_failure("429 Too Many Requests")
        assert r_t2 == "rate_or_session_limit"
        
        # Regression tests for false positives
        r4, _ = _classify_ask_failure("segfault at 0x503f88 core dumped")
        assert r4 != "rate_or_session_limit"
        
        r5, _ = _classify_ask_failure("panic: index 429 out of range")
        assert r5 != "rate_or_session_limit"
        
        r6, _ = _classify_ask_failure("Error: ENOENT config not found at line 503")
        assert r6 == "cli_not_found"
        
        # Regression test for critical shadowed by transient
        r7, _ = _classify_ask_failure("spawn EPERM: connection refused by sandbox")
        assert r7 == "sandbox_spawn_eperm"
        
    def test_record_ask_failure_transient(self, tmp_path):
        # Create dummy ai_root
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        (ai_root / "state.json").write_text('{"room_id": "r1"}')
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        peer_id = "testpeer"
        
        # Record a transient failure
        _record_ask_failure(peer_id, "rate_or_session_limit", "quota exceeded", 1, ai_root, health_dir=health_dir)
        
        _, data = _read_peer_health(peer_id, health_dir)
        # Should NOT bump consecutive_failures because it's transient
        assert data.get("session_health", {}).get("consecutive_failures", 0) == 0
        assert data.get("session_health", {}).get("transient_failures", 0) == 1
        
        avail = data.get("availability", {})
        assert avail.get("gate_open") is False
        assert avail.get("quarantined") is not True
        rls = avail.get("rate_limit_state", {})
        assert rls.get("limited") is True
        assert rls.get("reset_at") is not None
        
    def test_record_ask_failure_non_transient(self, tmp_path):
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        (ai_root / "state.json").write_text('{"room_id": "r1"}')
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        peer_id = "testpeer"
        
        # Record a non-transient error (e.g. CLI crash repeatedly to hit critical)
        _record_ask_failure(peer_id, "nonzero_exit", "fatal crash", 1, ai_root, health_dir=health_dir)
        
        _, data = _read_peer_health(peer_id, health_dir)
        assert data.get("session_health", {}).get("consecutive_failures", 0) == 1
        
        # For critical_reasons e.g. cli_not_found
        with pytest.raises(SystemExit):
            _record_ask_failure(peer_id, "cli_not_found", "no cli", 1, ai_root, health_dir=health_dir)
        _, data2 = _read_peer_health(peer_id, health_dir)
        assert data2.get("context_health", {}).get("status") == "RED"
        assert data2.get("availability", {}).get("gate_open") is False
        
    def test_auto_reopen_gate(self, tmp_path):
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        peer_id = "testpeer"
        
        # Mock peer sys dir so _ask_health_precheck uses it
        import hub
        original_peer_sys_dir = hub._peer_sys_dir
        hub._peer_sys_dir = lambda p: health_dir
        
        try:
            # Set up health file with past reset_at
            past_dt = datetime.now() - timedelta(minutes=5)
            data = {
                "availability": {
                    "gate_open": False,
                    "rate_limit_state": {
                        "limited": True,
                        "reset_at": past_dt.isoformat(),
                        "source_msg": "rate limit"
                    }
                }
            }
            _write_peer_health(peer_id, data, ai_root, health_dir)
            
            # _ask_health_precheck should auto reopen and NOT exit
            try:
                _ask_health_precheck(peer_id, ai_root)
                did_exit = False
            except SystemExit:
                did_exit = True
            
            assert did_exit is False, "_ask_health_precheck should not exit because gate was reopened"
            
            _, data2 = _read_peer_health(peer_id, health_dir)
            assert data2["availability"]["gate_open"] is True
            assert data2["availability"]["rate_limit_state"] == "ok"
            
        finally:
            hub._peer_sys_dir = original_peer_sys_dir

    def test_soft_skip_returns_distinct_exit_code(self, tmp_path, capsys):
        import hub
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = ai_root / ".health"
        health_dir.mkdir()
        
        original_peer_sys_dir = getattr(hub, "_peer_sys_dir", None)
        try:
            if original_peer_sys_dir:
                hub._peer_sys_dir = lambda *a, **k: health_dir
                
            peer_id = "rl_peer"
            from hub import _write_peer_health, _ask_health_precheck
            
            _write_peer_health(peer_id, {
                "availability": {
                    "gate_open": False,
                    "rate_limit_state": {
                        "limited": True,
                        "reset_at": "9999-12-31T23:59:59"
                    }
                }
            }, ai_root, health_dir)
            
            with pytest.raises(SystemExit) as exc:
                _ask_health_precheck(peer_id, ai_root)
                
            assert exc.value.code == hub.SOFT_SKIP_EXIT
            out, err = capsys.readouterr()
            assert "[HUB:SOFT-SKIP]" in out
        finally:
            if original_peer_sys_dir:
                hub._peer_sys_dir = original_peer_sys_dir
