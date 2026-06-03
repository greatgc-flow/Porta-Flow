"""
hub.py N-Node 합의(Consensus) 심화 테스트 — MECE 보완 (P1, P2, P3)
기권(Abstain), 에스컬레이션(Escalated), 동적 노드 확장 검증
"""
import json
import pytest
from pathlib import Path
import hub

class TestConsensusAdvanced:
    """N-Node 합의 프로토콜 심화 시나리오."""

    def test_p1_dynamic_node_consensus(self, ai_dir, capsys):
        """노드 동적 확장 후 합의 과정 포함 검증."""
        # 1. 새 노드 n1 등록
        hub.action_register_node(ai_dir, "n1", 4, "sensor", "custom-cli", "-p,{query}", "session", 0)
        
        # 2. n1을 포함한 합의 제안
        hub.action_consensus_propose(ai_dir, "Add n1 to team", ["cc", "ca", "gc", "n1"])
        
        out = capsys.readouterr().out
        assert "PROPOSE" in out
        
        # round_id 추출
        import re
        match = re.search(r"PROPOSE (r-\w+)", out)
        round_id = match.group(1)
        
        # 3. 모든 노드 투표 (n1 포함)
        hub.action_consensus_vote(ai_dir, round_id, "cc", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "ca", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "gc", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "n1", "agree")
        
        # 4. 결과 확인
        rpath = ai_dir / "consensus" / f"{round_id}.json"
        data = json.loads(rpath.read_text("utf-8"))
        assert data["status"] == "finalized"
        assert data["outcome"] == "unanimous"

    def test_p2_abstain_finalization(self, ai_dir, capsys):
        """기권(Abstain)이 포함된 합의 종결 검증."""
        hub.action_consensus_propose(ai_dir, "Minor change", ["cc", "ca", "gc"])
        out = capsys.readouterr().out
        round_id = re.search(r"PROPOSE (r-\w+)", out).group(1)
        
        # cc: agree, ca: abstain, gc: agree
        hub.action_consensus_vote(ai_dir, round_id, "cc", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "ca", "abstain")
        hub.action_consensus_vote(ai_dir, round_id, "gc", "agree")
        
        rpath = ai_dir / "consensus" / f"{round_id}.json"
        data = json.loads(rpath.read_text("utf-8"))
        # 반대가 없으면 finalized
        assert data["status"] == "finalized"
        assert data["outcome"] == "abstain" # agree + abstain = abstain (not unanimous)

    def test_p2_pure_abstain_finalization(self, ai_dir, capsys):
        """전원 기권 시의 결과 검증."""
        hub.action_consensus_propose(ai_dir, "No opinion", ["cc", "ca", "gc"])
        out = capsys.readouterr().out
        round_id = re.search(r"PROPOSE (r-\w+)", out).group(1)
        
        hub.action_consensus_vote(ai_dir, round_id, "cc", "abstain")
        hub.action_consensus_vote(ai_dir, round_id, "ca", "abstain")
        hub.action_consensus_vote(ai_dir, round_id, "gc", "abstain")
        
        rpath = ai_dir / "consensus" / f"{round_id}.json"
        data = json.loads(rpath.read_text("utf-8"))
        assert data["status"] == "finalized"
        assert data["outcome"] == "abstain"

    def test_p3_disagree_escalation(self, ai_dir, capsys):
        """단 1명이라도 반대 시 즉시 ESCALATED 전환 검증."""
        hub.action_consensus_propose(ai_dir, "Risky change", ["cc", "ca", "gc"])
        out = capsys.readouterr().out
        round_id = re.search(r"PROPOSE (r-\w+)", out).group(1)
        
        hub.action_consensus_vote(ai_dir, round_id, "cc", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "ca", "disagree", "Too risky")
        hub.action_consensus_vote(ai_dir, round_id, "gc", "agree")
        
        rpath = ai_dir / "consensus" / f"{round_id}.json"
        data = json.loads(rpath.read_text("utf-8"))
        assert data["status"] == "escalated"
        assert data["outcome"] == "human_gate"

    def test_consensus_history_auto_recording(self, ai_dir, capsys):
        """합의 종결 시 handoff.md에 자동 기록되는지 검증."""
        # 세션 초기화 필수 (pair 생성을 위해)
        hub.action_init_session(ai_dir, "claude")
        hub.action_init_session(ai_dir, "gemini")
        state = json.loads((ai_dir / "state.json").read_text("utf-8"))
        pair = state["pair"]
        
        hub.action_consensus_propose(ai_dir, "History test", ["cc", "ca", "gc"])
        out = capsys.readouterr().out
        round_id = re.search(r"PROPOSE (r-\w+)", out).group(1)
        
        hub.action_consensus_vote(ai_dir, round_id, "cc", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "ca", "agree")
        hub.action_consensus_vote(ai_dir, round_id, "gc", "agree")
        
        handoff_path = ai_dir / "sessions" / pair / "handoff.md"
        content = handoff_path.read_text("utf-8")
        assert "CONSENSUS_HISTORY" in content
        assert f"{round_id}: History test — FINALIZED" in content

import re
