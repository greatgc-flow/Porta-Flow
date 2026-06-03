"""
통합 테스트의 Python화 (Refactored from PS1)
병렬 안전성, 장애 복구, 세션 라이프사이클, 도구 경로, 사용자 시나리오 검증
"""
import json
import subprocess
import os
import shutil
import re
import pytest
from pathlib import Path

class TestIntegrationRefactored:
    """기존 PS1 통합 테스트 및 사용자 시나리오를 Python pytest 스타일로 통합 관리."""

    @pytest.fixture
    def test_env(self, tmp_path):
        """테스트용 격리 환경 생성 및 필수 경로 제공."""
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir(exist_ok=True)
        (tmp_path / ".git").mkdir(exist_ok=True)
        
        root_dir = Path(__file__).parent.parent.parent.parent
        msg_bat = root_dir / "_sys" / "cli" / "msg.bat"
        venv_py = root_dir / "_sys" / "env" / "venv" / "Scripts" / "python.exe"
        hub_py = root_dir / "_sys" / "core" / "hub.py"
        
        return {
            "root": tmp_path,
            "ai_dir": ai_dir,
            "msg_bat": msg_bat,
            "venv_py": venv_py,
            "hub_py": hub_py,
            "root_dir": root_dir
        }

    def test_tools_availability(self, test_env):
        """test_tools_path.ps1: 필수 도구 및 경로 유효성 검증."""
        root_dir = test_env["root_dir"]
        assert test_env["venv_py"].exists()
        subprocess.run([str(test_env["venv_py"]), "-c", "import filelock"], check=True)
        assert (root_dir / "_sys/tools/ripgrep/rg.exe").exists()
        assert (root_dir / "_sys/tools/fd/fd.exe").exists()
        
        cli_dir = root_dir / "_sys/cli"
        for bat in cli_dir.glob("*.bat"):
            content = bat.read_text(encoding="utf-8", errors="ignore")
            lines = [line for line in content.splitlines() if not line.strip().startswith("::")]
            assert "P:\\\\" not in "\n".join(lines), f"Hardcoded P:\\ found in {bat.name}"

    def test_session_lifecycle(self, test_env):
        """test_session_flow.ps1: 세션 시작, 업데이트, 종료 흐름 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "claude"], cwd=root, check=True)
        state = json.loads((root / ".ai/state.json").read_text("utf-8"))
        assert state["claude_sid"] is not None
        
        subprocess.run([str(vpy), str(hub), "update-status", "--mission", "test mission"], cwd=root, check=True)
        assert json.loads((root / ".ai/state.json").read_text("utf-8"))["mission"] == "test mission"
        
        subprocess.run([str(vpy), str(hub), "end-session", "--agent", "claude"], cwd=root, check=True)
        assert json.loads((root / ".ai/state.json").read_text("utf-8"))["claude_sid"] is None

    def test_ipc_and_msg_bat(self, test_env):
        """test_ipc.ps1: msg.bat을 통한 IPC 및 메시지 송수신 검증."""
        root, msg = test_env["root"], test_env["msg_bat"]
        subprocess.run([str(msg), "init-session", "--agent", "claude"], cwd=root, check=True, capture_output=True)
        out = subprocess.check_output([str(msg), "send", "--from", "claude", "--to", "gemini", "--msg", "hello"], cwd=root, text=True)
        assert "[HUB] SENT" in out
        out = subprocess.check_output([str(msg), "check", "--target", "gemini"], cwd=root, text=True)
        assert "hello" in out
        subprocess.run([str(msg), "mark-read", "--target", "gemini", "--all"], cwd=root, check=True)
        assert "inbox empty" in subprocess.check_output([str(msg), "check", "--target", "gemini"], cwd=root, text=True)

    def test_scenario_collaboration(self, test_env):
        """test_scenarios.ps1 Scenario A: Claude <-> Gemini 협업 흐름."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        # 1. Claude 시작
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "claude"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "update-status", "--mission", "task1"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "send", "--from", "claude", "--to", "gemini", "--msg", "review req"], cwd=root, check=True)
        
        # 2. Gemini 확인 및 응답
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "gemini"], cwd=root, check=True)
        inbox = subprocess.check_output([str(vpy), str(hub), "check", "--target", "gemini"], cwd=root, text=True)
        assert "review req" in inbox
        subprocess.run([str(vpy), str(hub), "send", "--from", "gemini", "--to", "claude", "--msg", "ok"], cwd=root, check=True)
        
        # 3. Claude 확인
        reply = subprocess.check_output([str(vpy), str(hub), "check", "--target", "claude"], cwd=root, text=True)
        assert "ok" in reply

    def test_scenario_project_isolation(self, tmp_path, test_env):
        """test_scenarios.ps1 Scenario C: 프로젝트 간 격리 검증."""
        vpy, hub = test_env["venv_py"], test_env["hub_py"]
        projA, projB = tmp_path / "projA", tmp_path / "projB"
        for p in [projA, projB]:
            p.mkdir()
            (p / ".git").mkdir()
            
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "claude"], cwd=projA, check=True)
        subprocess.run([str(vpy), str(hub), "update-status", "--mission", "A work"], cwd=projA, check=True)
        
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "claude"], cwd=projB, check=True)
        subprocess.run([str(vpy), str(hub), "update-status", "--mission", "B work"], cwd=projB, check=True)
        
        assert json.loads((projA / ".ai/state.json").read_text("utf-8"))["mission"] == "A work"
        assert json.loads((projB / ".ai/state.json").read_text("utf-8"))["mission"] == "B work"

    def test_scenario_large_message(self, test_env):
        """test_scenarios.ps1 Scenario G: 대용량 메시지 처리."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        long_msg = "test content\n" * 100 + "END_OF_MSG"
        subprocess.run([str(vpy), str(hub), "send", "--from", "claude", "--to", "gemini", "--msg", long_msg], cwd=root, check=True)
        out = subprocess.check_output([str(vpy), str(hub), "check", "--target", "gemini"], cwd=root, text=True)
        assert "END_OF_MSG" in out

    def test_parallel_safety_horizontal(self, test_env):
        """L1: Horizontal Parallel - 세션 UUID 기반 격리."""
        root, msg = test_env["root"], test_env["msg_bat"]
        envs = [os.environ.copy() for _ in range(2)]
        pairs = []
        for i, env in enumerate(envs):
            env["SESSION_UUID"] = f"sess{i}"
            subprocess.run([str(msg), "init-session", "--agent", "claude"], cwd=root, env=env, check=True, capture_output=True)
            status = subprocess.check_output([str(msg), "status"], cwd=root, env=env, text=True)
            # Robust regex to capture full pair ID (e.g., c1234-g--- or c1234-g5678)
            match = re.search(r"Pair\**:\s+(\S+)", status)
            if not match:
                raise ValueError(f"Could not find Pair in status output: {status}")
            pairs.append(match.group(1))
        
        assert pairs[0] != pairs[1]
        assert (root / ".ai" / "sessions" / pairs[0]).exists()
        assert (root / ".ai" / "sessions" / pairs[1]).exists()

    def test_external_directory_isolation(self, test_env, tmp_path_factory):
        """External Dir: 워크스페이스 외부(타 드라이브/폴더)에서 N-Tier 협업 시 컨텍스트 독립 유지 검증."""
        ext_dir = tmp_path_factory.mktemp("external_project")
        (ext_dir / ".git").mkdir()
        msg = test_env["msg_bat"]
        
        subprocess.run([str(msg), "init-session", "--agent", "claude"], cwd=ext_dir, check=True, capture_output=True)
        subprocess.run([str(msg), "init-session", "--agent", "gemini"], cwd=ext_dir, check=True, capture_output=True)
        subprocess.run([str(msg), "update-status", "--mission", "Ext Task"], cwd=ext_dir, check=True)
        
        state_file = ext_dir / ".ai" / "state.json"
        assert state_file.exists()
        assert json.loads(state_file.read_text("utf-8"))["mission"] == "Ext Task"
        
        subprocess.run([str(msg), "send", "--from", "claude", "--to", "gemini", "--msg", "ext-ping"], cwd=ext_dir, check=True)
        out = subprocess.check_output([str(msg), "check", "--target", "gemini"], cwd=ext_dir, text=True)
        assert "ext-ping" in out

    def test_recovery_flow_mode_off(self, test_env):
        """R2: 장애 발생 시 Gemini Mode OFF 전환."""
        root_dir = test_env["root_dir"]
        status_json = root_dir / "_sys/gemini/status.json"
        collab_log_bat = root_dir / "_sys/hooks/collab-log.bat"
        backup = status_json.with_suffix(".json.bak")
        if status_json.exists(): shutil.copy(status_json, backup)
        try:
            with open(status_json, "w", encoding="utf-8") as f:
                json.dump({"mode": "ON", "gemini_metrics": {"consecutive_failures": 0}}, f)
            env = os.environ.copy()
            env["GEMINI_DIR"] = str(root_dir / "_sys/gemini")
            for i in range(3):
                subprocess.run([str(collab_log_bat), "Axis-X", "test.bat", "FAILURE", "error"], env=env, check=True)
            with open(status_json, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                assert data["gemini_metrics"]["consecutive_failures"] >= 3
                assert data["mode"] == "OFF"
        finally:
            if backup.exists(): shutil.move(backup, status_json)
