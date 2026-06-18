import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure _sys/core is in path
sys.path.append(str(Path(__file__).parent.parent / "core"))
import hub

@pytest.fixture
def mock_context_gate():
    with patch("hub._ContextGate") as mock:
        gate_instance = MagicMock()
        mock.return_value = gate_instance
        yield gate_instance

def test_action_ask_recursion_limit(mock_context_gate, tmp_path):
    # Setup ContextGate to failover in a chain: cc -> gc -> cx -> cc
    def side_effect(query, model_id):
        if model_id == "claude-sonnet-4-6": # cc
            return {"action": "failover", "failover_model": "gc", "ratio": 1.0}
        if model_id == "gemini-2.5-pro": # gc
            return {"action": "failover", "failover_model": "cx", "ratio": 1.0}
        if model_id == "gpt-5.5": # cx
            return {"action": "failover", "failover_model": "cc", "ratio": 1.0}
        return {"action": "pass"}
    
    mock_context_gate.check.side_effect = side_effect
    
    # Mock nodes
    mock_nodes = {
        "cc": {"node_id": "cc", "peer": "claude-sonnet-4-6", "invoke": "claude", "aliases": []},
        "gc": {"node_id": "gc", "peer": "gemini-2.5-pro", "invoke": "gemini", "aliases": []},
        "cx": {"node_id": "cx", "peer": "gpt-5.5", "invoke": "codex", "aliases": []}
    }
    
    with patch("hub._load_nodes", return_value=mock_nodes), \
         patch("hub._load_orchestration", return_value={"hub_nodes": []}), \
         patch("hub._ask_health_precheck"), \
         patch("hub._lease_sweep"), \
         patch("sys.exit") as mock_exit:
        
        # This should trigger recursion: depth 0 (cc) -> 1 (gc) -> 2 (cx) -> 3 (cc) -> EXIT
        hub.action_ask(
            to="cc", 
            query="test", 
            query_file=None, 
            timeout_sec=0, 
            ai_root=None
        )
        
        assert mock_exit.called
        # It should exit at depth 3
        mock_exit.assert_called_with(1)

def test_action_ask_prevents_immediate_loop(mock_context_gate):
    # Setup ContextGate to failover to the same model
    mock_context_gate.check.return_value = {
        "action": "failover",
        "failover_model": "cc",
        "ratio": 1.0
    }
    
    mock_nodes = {
        "cc": {"node_id": "cc", "peer": "claude-sonnet-4-6", "invoke": "claude", "aliases": []}
    }
    
    with patch("hub._load_nodes", return_value=mock_nodes), \
         patch("hub._load_orchestration", return_value={"hub_nodes": []}), \
         patch("hub._ask_health_precheck"), \
         patch("hub._lease_sweep"), \
         patch("sys.exit") as mock_exit:
        
        # This should NOT recurse because failover_model == to
        # Instead it will try to proceed and likely hit more errors since we didn't mock everything,
        # but we can check if action_ask was called recursively.
        
        with patch("hub.action_ask", side_effect=hub.action_ask) as mock_recursive_ask:
            try:
                hub.action_ask(
                    to="cc", 
                    query="test", 
                    query_file=None, 
                    timeout_sec=0, 
                    ai_root=None
                )
            except SystemExit:
                pass
            
            # Should only be called once (the initial call)
            assert mock_recursive_ask.call_count == 1
