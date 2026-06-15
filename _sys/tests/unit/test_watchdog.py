"""
GAP-4 Autonomy — Watchdog Tests (TDD Red Phase)

ctx_end.py must run check_contracts.py as a post-flight check.
On failure: create a hub thread with the failure log.
On success: silent, no thread created.
"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

SYS_DIR = Path(__file__).parent.parent.parent.resolve()
HOOKS_DIR = SYS_DIR / "hooks"

sys.path.insert(0, str(SYS_DIR))
sys.path.insert(0, str(HOOKS_DIR))


def _make_completed_process(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    cp = subprocess.CompletedProcess(args=[], returncode=returncode)
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


class TestWatchdogContractCheck:
    """ctx_end.py contract watchdog integration."""

    def test_run_watchdog_function_exists(self):
        """ctx_end.py must expose a run_contract_watchdog() function."""
        import ctx_end
        assert hasattr(ctx_end, "run_contract_watchdog"), (
            "ctx_end.py must expose run_contract_watchdog(ai_root, python_exe) function"
        )

    def test_watchdog_runs_check_contracts(self, tmp_path):
        """run_contract_watchdog must invoke check_contracts.py."""
        import ctx_end
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(0, "46 passed")
            ctx_end.run_contract_watchdog(ai_root=tmp_path, python_exe=sys.executable)
            # At least one call should be to check_contracts.py
            calls_str = str(mock_run.call_args_list)
            assert "check_contracts" in calls_str, (
                "run_contract_watchdog must call check_contracts.py"
            )

    def test_watchdog_silent_on_success(self, tmp_path, capsys):
        """On contract pass (rc=0), no thread is created and no error output."""
        import ctx_end
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = _make_completed_process(0, "46 passed")
            ctx_end.run_contract_watchdog(ai_root=tmp_path, python_exe=sys.executable)
            captured = capsys.readouterr()
            # Must not create a hub thread
            for c in mock_run.call_args_list:
                args = c.args[0] if c.args else []
                assert "thread-new" not in str(args), (
                    "On success, no hub thread should be created"
                )

    def test_watchdog_creates_thread_on_failure(self, tmp_path):
        """On contract failure (rc=1), must call hub.py thread-new with failure info."""
        import ctx_end

        call_args_list = []

        def fake_run(cmd, **kwargs):
            call_args_list.append(cmd)
            cmd_str = str(cmd)
            if "check_contracts" in cmd_str:
                return _make_completed_process(1, "", "FAIL: 2 contract violations")
            return _make_completed_process(0)

        with patch("subprocess.run", side_effect=fake_run):
            ctx_end.run_contract_watchdog(ai_root=tmp_path, python_exe=sys.executable)

        thread_calls = [c for c in call_args_list if "thread-new" in str(c)]
        assert len(thread_calls) >= 1, (
            "On contract failure, run_contract_watchdog must call hub.py thread-new"
        )

    def test_watchdog_thread_contains_failure_info(self, tmp_path):
        """Failure thread must contain '[SYSTEM_ALERT]' and failure details."""
        import ctx_end

        thread_topics = []

        def fake_run(cmd, **kwargs):
            cmd_str = str(cmd)
            if "thread-new" in cmd_str:
                thread_topics.append(cmd_str)
            if "check_contracts" in cmd_str:
                return _make_completed_process(1, "", "FAIL: contract violation")
            return _make_completed_process(0)

        with patch("subprocess.run", side_effect=fake_run):
            ctx_end.run_contract_watchdog(ai_root=tmp_path, python_exe=sys.executable)

        assert thread_topics, "No thread-new call made"
        combined = " ".join(thread_topics)
        assert "SYSTEM_ALERT" in combined or "contract" in combined.lower(), (
            "Thread must contain SYSTEM_ALERT or contract failure info"
        )

    def test_watchdog_no_recursion_guard(self, tmp_path):
        """Watchdog must not trigger ctx-end again (no recursion)."""
        import ctx_end

        call_count = {"n": 0}

        def fake_run(cmd, **kwargs):
            call_count["n"] += 1
            if call_count["n"] > 10:
                raise RuntimeError("Watchdog recursive loop detected!")
            if "check_contracts" in str(cmd):
                return _make_completed_process(0, "46 passed")
            return _make_completed_process(0)

        with patch("subprocess.run", side_effect=fake_run):
            ctx_end.run_contract_watchdog(ai_root=tmp_path, python_exe=sys.executable)

        assert call_count["n"] <= 10, "Watchdog triggered too many subprocess calls"


class TestWatchdogIntegration:
    """Watchdog is called from ctx_end main() flow."""

    def test_watchdog_called_at_session_end(self):
        """main() in ctx_end.py must call run_contract_watchdog."""
        import inspect
        import ctx_end
        src = inspect.getsource(ctx_end.main)
        assert "run_contract_watchdog" in src, (
            "ctx_end.main() must call run_contract_watchdog()"
        )
