"""
OS-level File Locking Stress Test
Verifies that hub.py correctly handles concurrent access from multiple OS processes.
"""
import subprocess
import time
import json
import concurrent.futures
import pytest
from pathlib import Path

class TestLockingStress:
    """Stress test for file-based IPC and state locking."""

    @pytest.fixture
    def test_env(self, tmp_path):
        """Setup isolated .ai directory."""
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir(exist_ok=True)
        
        root_dir = Path(__file__).parent.parent.parent.parent
        venv_py = root_dir / "_sys" / "env" / "venv" / "Scripts" / "python.exe"
        hub_py = root_dir / "_sys" / "core" / "hub.py"
        
        return {
            "root": tmp_path,
            "venv_py": venv_py,
            "hub_py": hub_py
        }

    def run_hub_cmd(self, env, args):
        """Helper to run hub command in a separate process."""
        return subprocess.run(
            [str(env["venv_py"]), str(env["hub_py"])] + args,
            cwd=env["root"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

    def test_parallel_init_session(self, test_env):
        """Launch 10 parallel processes trying to init-session. 
        Only one should succeed in creating the room or they should all synchronize correctly.
        """
        agents = [f"agent_{i}" for i in range(4)]

        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.run_hub_cmd, test_env, ["init-session", "--agent", a, "--room", "stress-room"]) 
                for a in agents
            ]
            results = [f.result() for f in futures]

        # All should return 0 (success) because hub.py should handle retries/locking
        for i, res in enumerate(results):
            assert res.returncode == 0, f"Agent {i} failed: {res.stderr}"

        # Verify state.json contains all members
        state_path = test_env["root"] / ".ai" / "state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text("utf-8"))
        
        for a in agents:
            assert a in state["members"], f"Agent {a} missing from members list"

    def test_concurrent_consensus_votes(self, test_env):
        """Verify that multiple processes can vote on the same consensus round without corruption."""
        # 1. Initialize session and propose consensus
        self.run_hub_cmd(test_env, ["init-session", "--agent", "admin"])
        self.run_hub_cmd(test_env, ["consensus-propose", "--subject", "parallel-vote", "--voters", ",".join([f"v_{i}" for i in range(8)])])

        round_files = list((test_env["root"] / ".ai" / "consensus").glob("*.json"))
        assert len(round_files) == 1
        round_id = json.loads(round_files[0].read_text("utf-8"))["round_id"]

        # 2. 8 agents vote simultaneously from separate processes
        voters = [f"v_{i}" for i in range(8)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.run_hub_cmd, test_env, ["consensus-vote", "--round-id", round_id, "--voter", v, "--vote", "agree"]) 
                for v in voters
            ]
            results = [f.result() for f in futures]

        for i, res in enumerate(results):
            assert res.returncode == 0, f"Voter {i} failed: {res.stderr}"

        # 3. Final verification
        updated_round = json.loads(round_files[0].read_text("utf-8"))
        assert len(updated_round["votes"]) == 8
        assert updated_round["status"] == "finalized"
