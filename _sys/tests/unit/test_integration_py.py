"""
통합 테스트 개정 (P2P v3)
N-Way Room 세션, P2P 무제한 합의, 분업(Division of Labor), 교차 검증 시나리오 구현
"""
import json
import subprocess
import os
import shutil
import re
import pytest
from pathlib import Path

class TestIntegrationP2P:
    """N-Tier Peer-to-Peer 협업 시스템 고도화 검증."""

    @pytest.fixture
    def test_env(self, tmp_path):
        """테스트용 격리 환경 생성."""
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir(exist_ok=True)
        (tmp_path / ".git").mkdir(exist_ok=True)
        
        root_dir = Path(__file__).parent.parent.parent.parent
        venv_py = root_dir / "_sys" / "env" / "venv" / "Scripts" / "python.exe"
        hub_py = root_dir / "_sys" / "core" / "hub.py"
        
        return {
            "root": tmp_path,
            "ai_dir": ai_dir,
            "venv_py": venv_py,
            "hub_py": hub_py
        }

    def test_scenario_nway_lifecycle(self, test_env):
        """[세션/상태] N-Way 단일 룸 생명주기 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        
        # 3개 노드 조인 (동일 룸)
        room_id = "test-room-123"
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "cc", "--room", room_id], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "ca", "--room", room_id], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "gc", "--room", room_id], cwd=root, check=True)
        
        state = json.loads((root / ".ai/state.json").read_text("utf-8"))
        assert state["room_id"] == room_id
        assert "cc" in state["members"]
        assert "ca" in state["members"]
        assert "gc" in state["members"]
        
        # 브로드캐스트 모의 (하나의 노드가 보내고 다른 노드가 확인)
        subprocess.run([str(vpy), str(hub), "send", "--from", "cc", "--to", "ca", "--msg", "p2p-hi"], cwd=root, check=True)
        out = subprocess.check_output([str(vpy), str(hub), "check", "--target", "ca"], cwd=root, text=True, encoding="utf-8")
        assert "p2p-hi" in out

    def test_scenario_p2p_consensus(self, test_env):
        """[권한/의사결정] P2P 무제한 합의 및 교차 발의 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        
        # GC가 먼저 합의 발의 (P2P 권한 동등성)
        subprocess.run([str(vpy), str(hub), "consensus-propose", "--subject", "p2p-test", "--voters", "cc,ca,gc", "--from", "gc"], cwd=root, check=True)
        
        rounds = list((root / ".ai/consensus").glob("*.json"))
        assert len(rounds) == 1
        round_data = json.loads(rounds[0].read_text("utf-8"))
        rid = round_data["round_id"]
        
        # 1. cc votes disagree -> status remains 'voting' until all cast, then becomes 'escalated'
        subprocess.run([str(vpy), str(hub), "consensus-vote", "--round-id", rid, "--voter", "cc", "--vote", "disagree", "--reason", "more info req"], cwd=root, check=True)
        
        # 2. ca votes agree -> still 'voting' (2/3)
        subprocess.run([str(vpy), str(hub), "consensus-vote", "--round-id", rid, "--voter", "ca", "--vote", "agree"], cwd=root, check=True)
        
        # 3. gc votes agree -> all cast (3/3), has_disagree=True -> status becomes 'escalated'
        subprocess.run([str(vpy), str(hub), "consensus-vote", "--round-id", rid, "--voter", "gc", "--vote", "agree"], cwd=root, check=True)
        
        round_data = json.loads(rounds[0].read_text("utf-8"))
        assert round_data["status"] == "escalated"
        assert round_data["outcome"] == "human_gate"

    def test_scenario_division_of_labor(self, test_env):
        """[분업/실행] 다중 노드 태스크 분할 및 병렬 실행 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        
        # Room 초기화
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "cc"], cwd=root, check=True)
        
        # 병렬 태스크 할당 (Node A: Doc, Node B: Code)
        subprocess.run([str(vpy), str(hub), "send", "--from", "cc", "--to", "gc", "--msg", "write-doc", "--type", "DIRECTIVE"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "send", "--from", "cc", "--to", "ca", "--msg", "write-code", "--type", "DIRECTIVE"], cwd=root, check=True)
        
        # 각 노드가 Artifact 제출
        subprocess.run([str(vpy), str(hub), "send", "--from", "gc", "--to", "cc", "--msg", "doc-done", "--type", "ARTIFACT"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "send", "--from", "ca", "--to", "cc", "--msg", "code-done", "--type", "ARTIFACT"], cwd=root, check=True)
        
        # CC가 Inbox에서 두 아티팩트 모두 확인 (수합 가능성 확인)
        inbox = subprocess.check_output([str(vpy), str(hub), "check", "--target", "cc"], cwd=root, text=True, encoding="utf-8")
        assert "doc-done" in inbox
        assert "code-done" in inbox

    def test_scenario_cross_validation(self, test_env):
        """[검증] 전원 교차 검토(Cross-check) 흐름 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        
        # 3개 노드 룸 참여
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "cc"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "ca"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "gc"], cwd=root, check=True)
        
        # 작업물 제출
        subprocess.run([str(vpy), str(hub), "send", "--from", "ca", "--to", "cc", "--msg", "feat-x", "--type", "ARTIFACT"], cwd=root, check=True)
        
        # 전원 교차 검증 (GC와 CC 모두 검증 메시지 발신)
        subprocess.run([str(vpy), str(hub), "send", "--from", "gc", "--to", "ca", "--msg", "PASS: doc aligns", "--type", "VERIFY"], cwd=root, check=True)
        subprocess.run([str(vpy), str(hub), "send", "--from", "cc", "--to", "ca", "--msg", "PASS: code logic ok", "--type", "VERIFY"], cwd=root, check=True)
        
        # Verifier(CA) 입장에서 모든 검증 결과 확인
        ca_inbox = subprocess.check_output([str(vpy), str(hub), "check", "--target", "ca"], cwd=root, text=True, encoding="utf-8")
        assert "doc aligns" in ca_inbox
        assert "code logic ok" in ca_inbox

    def test_scenario_collab_rate(self, test_env):
        """[정책] COLLAB_RATE=10 에 따른 합의 필수성 로직(모의) 검증."""
        root, vpy, hub = test_env["root"], test_env["venv_py"], test_env["hub_py"]
        
        # COLLAB_RATE=10 설정 시나리오
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "cc"], cwd=root, check=True)
        
        # 합의 라운드 생성 (모든 작업 전 필수)
        subprocess.run([str(vpy), str(hub), "consensus-propose", "--subject", "high-rate-task", "--voters", "cc,ca,gc"], cwd=root, check=True)
        
        # 합의 확인 전까지는 '실행' 상태로 전이하지 않음을 상태창으로 확인
        status = subprocess.check_output([str(vpy), str(hub), "status"], cwd=root, text=True, encoding="utf-8")
        assert "high-rate-task" in status
        assert "CONSENSUS — ACTIVE" in status

    def test_external_portability(self, test_env, tmp_path_factory):
        """[포터빌리티] 워크스페이스 외부 폴더에서 N-Tier 협업 도구 사용 및 컨텍스트 격리 검증."""
        # 1. 워크스페이스와 완전히 떨어진 외부 임시 프로젝트 생성
        ext_project = tmp_path_factory.mktemp("external_proj")
        (ext_project / ".git").mkdir() # 프로젝트 루트 인식용
        
        vpy, hub = test_env["venv_py"], test_env["hub_py"]
        
        # 2. 외부 폴더에서 세션 초기화 (시스템 내 도구 호출)
        subprocess.run([str(vpy), str(hub), "init-session", "--agent", "cc", "--room", "ext-room-1"], cwd=ext_project, check=True)
        
        # 3. .ai/ 폴더가 외부 프로젝트 루트에 생성되었는지 확인 (워크스페이스가 아닌)
        assert (ext_project / ".ai").exists()
        assert (ext_project / ".ai" / "state.json").exists()
        
        # 4. 외부 프로젝트 내에서 메시지 송수신 테스트
        subprocess.run([str(vpy), str(hub), "send", "--from", "cc", "--to", "gc", "--msg", "ext-msg-test"], cwd=ext_project, check=True)
        inbox = subprocess.check_output([str(vpy), str(hub), "check", "--target", "gc"], cwd=ext_project, text=True, encoding="utf-8")
        assert "ext-msg-test" in inbox
        
        # 5. 기존 워크스페이스 상태에 영향을 주지 않았는지 확인
        ws_root = test_env["root"]
        if (ws_root / ".ai" / "state.json").exists():
            ws_state = json.loads((ws_root / ".ai" / "state.json").read_text("utf-8"))
            assert ws_state.get("room_id") != "ext-room-1"
