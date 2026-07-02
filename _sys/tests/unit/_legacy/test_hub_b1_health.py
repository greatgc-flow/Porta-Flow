import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

from hub import (
    _record_ask_failure,
    _record_ask_success,
    _ask_health_precheck,
    _healthy_peer,
    _read_peer_health,
)
from hub_profile_router import _eligible_profile, ProfileRoutingError


class TestHubB1Health:
    def test_b1_profile_fallback(self, tmp_path):
        """rate-limit cc.deepthink -> an ask routed to cc.deepthink serves via cc.effort"""
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        peer_id = "cc"
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": peer_id,
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {"gate_open": True, "consecutive_failures": 0},
                    "effort": {"gate_open": True, "consecutive_failures": 0},
                    "standard": {"gate_open": True, "consecutive_failures": 0}
                }
            }
        }))
        
        # 1. Failure on deepthink rate-limit
        _record_ask_failure(
            peer_id=peer_id,
            reason="rate_or_session_limit",
            detail="HTTP 429",
            elapsed=100,
            ai_root=ai_root,
            health_dir=health_dir,
            profile_key="deepthink"
        )
        
        # Assert deepthink closed, but root and others open
        health = json.loads(health_dir.joinpath("health.json").read_text())
        assert health["availability"]["profiles"]["deepthink"]["gate_open"] is False
        assert health["availability"]["gate_open"] is True
        assert health["availability"]["profiles"]["effort"]["gate_open"] is True
        
        # 2. _eligible_profile check
        root_node = {
            "node_id": peer_id,
            "profiles": {
                "deepthink": {"enabled": True},
                "effort": {"enabled": True},
                "standard": {"enabled": True}
            }
        }
        profile_order = ["standard", "effort", "deepthink"]
        eligible, fallback_from = _eligible_profile(root_node, "deepthink", profile_order, health)
        assert eligible == "effort"
        assert fallback_from == "deepthink"

    def test_b1_peer_wide_drop(self, tmp_path):
        """auth failure -> ALL profiles closed (no fallback within peer)."""
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        peer_id = "ag"
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": peer_id,
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {"gate_open": True},
                    "effort": {"gate_open": True},
                }
            }
        }))
        
        _record_ask_failure(
            peer_id=peer_id,
            reason="cli_not_found",
            detail="HTTP 401",
            elapsed=100,
            ai_root=ai_root,
            health_dir=health_dir,
            profile_key="deepthink"
        )
        
        health = json.loads(health_dir.joinpath("health.json").read_text())
        assert health["availability"]["gate_open"] is False
        
        root_node = {
            "node_id": peer_id,
            "profiles": {
                "deepthink": {"enabled": True},
                "effort": {"enabled": True},
            }
        }
        profile_order = ["standard", "effort", "deepthink"]
        selected, _ = _eligible_profile(root_node, "deepthink", profile_order, health)
        assert selected is None

    def test_b1_profile_rate_limit_recovers(self, tmp_path):
        """profile deepthink rate-limited with reset_at in the PAST -> eligibility check treats deepthink as OPEN."""
        from hub import _ask_health_precheck
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        # Write state with a past reset_at for profile deepthink
        from datetime import datetime, timedelta
        past_dt = datetime.now() - timedelta(minutes=5)
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": "ag",
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {
                        "gate_open": False,
                        "rate_limit_state": {
                            "limited": True,
                            "reset_at": past_dt.isoformat()
                        }
                    }
                }
            }
        }))
        
        from unittest.mock import patch
        with patch("hub._peer_effective_health", return_value=("YELLOW", json.loads(health_dir.joinpath("health.json").read_text()))), \
             patch("hub._write_peer_health") as mock_write, \
             patch("hub._load_orchestration", return_value={"hub_nodes": [{"node_id": "ag", "profiles": {"deepthink": {"enabled": True}}}]}):
            _ask_health_precheck("ag", ai_root)
            
            # The precheck should have opened the profile's gate
            assert mock_write.called
            written_data = mock_write.call_args[0][1]
            assert written_data["availability"]["profiles"]["deepthink"]["gate_open"] is True
            assert written_data["availability"]["profiles"]["deepthink"]["rate_limit_state"] == "ok"

    def test_b1_model_error_closes_profile(self, tmp_path):
        """_record_ask_failure(reason='model_error', profile_key='deepthink') closes profiles.deepthink.gate_open=False while root gate_open stays True."""
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        peer_id = "ag"
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": peer_id,
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {"gate_open": True}
                }
            }
        }))
        
        _record_ask_failure(
            peer_id=peer_id,
            reason="model_error",
            detail="some context window error",
            elapsed=10,
            ai_root=ai_root,
            health_dir=health_dir,
            profile_key="deepthink"
        )
        
        health = json.loads(health_dir.joinpath("health.json").read_text())
        assert health["availability"]["gate_open"] is True
        assert health["availability"]["profiles"]["deepthink"]["gate_open"] is False

    def test_b1_peer_recover_clears_profiles(self, tmp_path):
        """after peer-recover, all profile gates are open again."""
        from hub import action_peer_recover
        ai_root = tmp_path / ".ai"
        ai_root.mkdir()
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        peer_id = "ag"
        
        # setup blocked profile and blocked root
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": peer_id,
            "availability": {
                "gate_open": False,
                "profiles": {
                    "deepthink": {
                        "gate_open": False,
                        "rate_limit_state": {"limited": True, "reset_at": "2099"}
                    }
                }
            }
        }))
        
        from unittest.mock import patch
        with patch("hub._read_peer_health", return_value=(health_dir.joinpath("health.json"), json.loads(health_dir.joinpath("health.json").read_text()))), \
             patch("hub._write_peer_health") as mock_write, \
             patch("hub._append_handoff_item"), patch("builtins.print"):
            action_peer_recover(ai_root, peer_id, "test_recover")
            
            written_data = mock_write.call_args[0][1]
            assert written_data["availability"]["gate_open"] is True
            assert written_data["availability"]["profiles"]["deepthink"]["gate_open"] is True
            assert "rate_limit_state" not in written_data["availability"]["profiles"]["deepthink"] or written_data["availability"]["profiles"]["deepthink"]["rate_limit_state"] == "ok"

    def test_b1_healthy_peer_aggregation(self, tmp_path):
        """_healthy_peer("cc") is True when deepthink closed but effort open."""
        # _healthy_peer normally resolves path via peers.json. We can mock _read_peer_health
        health = {
            "peer_id": "cc",
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {"gate_open": False},
                    "effort": {"gate_open": True},
                    "standard": {"gate_open": True}
                }
            }
        }
        from unittest.mock import patch
        with patch("hub._read_peer_health", return_value=(Path("dummy"), health)):
            with patch("hub._load_orchestration", return_value={
                "hub_nodes": [{"node_id": "cc", "type": "peer", "enabled": True, "profiles": {"deepthink": {"enabled": True}, "effort": {"enabled": True}}}]
            }):
                assert _healthy_peer("cc") is True
                
        # What if root is closed?
        health2 = {
            "peer_id": "cc",
            "availability": {
                "gate_open": False,
                "profiles": {
                    "effort": {"gate_open": True}
                }
            }
        }
        with patch("hub._read_peer_health", return_value=(Path("dummy"), health2)):
            with patch("hub._load_orchestration", return_value={
                "hub_nodes": [{"node_id": "cc", "type": "peer", "enabled": True, "profiles": {"effort": {"enabled": True}}}]
            }):
                assert _healthy_peer("cc") is False

    def test_b1_read_is_pure(self, tmp_path):
        """reading per-profile health does not mutate it (E1 preserved)."""
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        
        original_json = json.dumps({
            "peer_id": "cc",
            "availability": {
                "gate_open": True,
                "profiles": {
                    "deepthink": {"gate_open": True}
                }
            }
        })
        health_file = health_dir / "health.json"
        health_file.write_text(original_json)
        
        _, data = _read_peer_health("cc", health_dir=health_dir)
        # Should not have modified the file
        assert health_file.read_text() == original_json
        
        root_node = {
            "node_id": "cc",
            "profiles": {"deepthink": {"enabled": True}}
        }
        profile_order = ["standard", "effort", "deepthink"]
        _eligible_profile(root_node, "deepthink", profile_order, data)
        assert health_file.read_text() == original_json

    def test_b1_backward_compat(self, tmp_path):
        """a health.json with no profiles key still works (defaults to root health)."""
        health_dir = tmp_path / "health"
        health_dir.mkdir()
        health_dir.joinpath("health.json").write_text(json.dumps({
            "peer_id": "cc",
            "availability": {
                "gate_open": True
            }
        }))
        
        _, data = _read_peer_health("cc", health_dir=health_dir)
        root_node = {
            "node_id": "cc",
            "profiles": {"deepthink": {"enabled": True}}
        }
        profile_order = ["standard", "effort", "deepthink"]
        eligible, fallback = _eligible_profile(root_node, "deepthink", profile_order, data)
        assert eligible == "deepthink"
        assert fallback is None
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from hub import action_ask

def test_b1_live_end_to_end_rate_limit_and_fallback(tmp_path, capfd):
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()
    health_dir = tmp_path / "health"
    health_dir.mkdir()
    
    nodes = {
        "cc": {
            "node_id": "cc",
            "type": "peer",
            "enabled": True,
            "invoke": "mock_cc",
            "profiles": {
                "deepthink": {"enabled": True},
                "effort": {"enabled": True},
                "standard": {"enabled": True}
            }
        },
        "cc.deepthink": {
            "node_id": "cc.deepthink",
            "type": "profile",
            "parent_node": "cc",
            "enabled": True,
            "invoke": "mock_cc"
        },
        "cc.effort": {
            "node_id": "cc.effort",
            "type": "profile",
            "parent_node": "cc",
            "enabled": True,
            "invoke": "mock_cc"
        }
    }
    
    health_file = health_dir / "health.json"
    health_file.write_text(json.dumps({
        "peer_id": "cc",
        "availability": {
            "gate_open": True,
            "profiles": {
                "deepthink": {"gate_open": True},
                "effort": {"gate_open": True},
                "standard": {"gate_open": True}
            }
        }
    }))
    
    def mock_read_peer_health(pid, hd=None):
        return health_file, json.loads(health_file.read_text())
    
    def mock_write_peer_health(pid, data, root=None, hd=None):
        health_file.write_text(json.dumps(data))
    
    class MockPopen:
        def __init__(self, ec, out, err):
            self.returncode = ec
            self.stdout = out
            self.stderr = err
            self.pid = 123
        def communicate(self, input=None, timeout=None):
            return self.stdout.encode('utf-8'), self.stderr.encode('utf-8')
        def poll(self):
            return self.returncode
            
    import hub
    original_record = hub._record_ask_failure
    def spy_record_ask_failure(*args, **kwargs):
        print(f"SPY ARGS: {args} KWARGS: {kwargs}")
        return original_record(*args, **kwargs)
    
    with patch("hub._load_nodes", return_value=nodes), \
         patch("hub._load_orchestration", return_value={"hub_nodes": list(nodes.values())}), \
         patch("hub._peer_sys_dir", return_value=health_dir), \
         patch("hub._read_peer_health", side_effect=mock_read_peer_health), \
         patch("hub._write_peer_health", side_effect=mock_write_peer_health), \
         patch("hub.shutil.which", return_value="/bin/mock_cc"), \
         patch("hub_peer.get_adapter", return_value=None), \
         patch("hub_profile_router._resolve_root", return_value=("cc", False, None)), \
         patch("hub_profile_router._score_query", return_value=(95, ["mock_deepthink"], "deepthink")), \
         patch("hub_profile_router._explicit_tag", return_value=None), \
         patch("hub.is_routable", return_value=True), \
         patch("hub._record_ask_failure", side_effect=spy_record_ask_failure):
    
        with patch("hub.subprocess.Popen", return_value=MockPopen(1, "", "HTTP 429 Rate Limit Exceeded")) as mock_popen:
            with pytest.raises(SystemExit):
                action_ask("cc", "hello", None, 30, ai_root)
                
            health_data = json.loads(health_file.read_text())
            print("REASON WAS:", health_data["session_health"].get("last_failure_reason"))
            print("AVAILABILITY:", json.dumps(health_data["availability"], indent=2))
            assert health_data["availability"]["gate_open"] is True

