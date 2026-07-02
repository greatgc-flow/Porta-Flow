"""Lifecycle command contracts for root state and child-local state preservation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cli"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))
import peer_mgr
import hub_peer


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _configure(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    orch = tmp_path / "orchestration.json"
    peers = tmp_path / "peers.json"
    protocol = tmp_path / "protocol.json"
    status = tmp_path / "status_checks.json"
    monkeypatch.setattr(peer_mgr, "_ORCH", orch)
    monkeypatch.setattr(peer_mgr, "_PEERS", peers)
    monkeypatch.setattr(peer_mgr, "_PROTOCOL", protocol)
    monkeypatch.setattr(peer_mgr, "_STATUS", status)
    monkeypatch.setattr(peer_mgr, "_SPECIFIC", tmp_path / "docs-v2" / "specific")
    monkeypatch.setattr(peer_mgr, "_SYS", tmp_path)
    return orch, peers, protocol, status


def test_suspend_resume_preserves_child_local_routing_state(monkeypatch, tmp_path):
    orch, peers, protocol, status = _configure(monkeypatch, tmp_path)
    _write(orch, {
        "consensus": {
            "default_voters": ["p"],
            "inactive_default_voters": [],
        },
        "roles_registry": {"reviewer": ["p"], "coder": ["p"]},
        "hub_nodes": [{
            "node_id": "p",
            "type": "peer",
            "profiles": {
                "standard": {"routing_state": "eligible"},
                "effort": {"routing_state": "eligible"},
                "deepthink": {"routing_state": "blocked"},
            },
        }]
    })
    _write(peers, {"peers": {"provider": {"enabled": True, "node_ids": ["p"]}}})
    _write(protocol, {"consensus": {
        "default_voters": ["p"],
        "r10_voters": ["p"],
        "inactive_default_voters": [],
    }})
    _write(status, {"peers": {"p": {"safe_checks": []}}})

    assert peer_mgr.cmd_suspend("p", "test", False) == 0
    suspended = json.loads(orch.read_text(encoding="utf-8"))["hub_nodes"][0]
    assert suspended["enabled"] is False
    assert suspended["profiles"]["deepthink"]["routing_state"] == "blocked"
    assert suspended["profiles"]["standard"]["routing_state"] == "eligible"
    suspended_orch = json.loads(orch.read_text(encoding="utf-8"))
    assert "p" not in suspended_orch["consensus"]["default_voters"]
    assert "p" in suspended_orch["consensus"]["inactive_default_voters"]
    assert all("p" not in members for members in suspended_orch["roles_registry"].values())
    suspended_protocol = json.loads(protocol.read_text(encoding="utf-8"))
    assert "p" not in suspended_protocol["consensus"]["r10_voters"]

    assert peer_mgr.cmd_resume("p", False) == 0
    resumed_orch = json.loads(orch.read_text(encoding="utf-8"))
    resumed = resumed_orch["hub_nodes"][0]
    assert resumed.get("enabled", True) is True
    assert resumed["profiles"]["deepthink"]["routing_state"] == "blocked"
    assert resumed["profiles"]["standard"]["routing_state"] == "eligible"
    assert "p" in resumed_orch["consensus"]["default_voters"]
    assert "p" not in resumed_orch["consensus"]["inactive_default_voters"]
    assert all("p" in members for members in resumed_orch["roles_registry"].values())
    resumed_protocol = json.loads(protocol.read_text(encoding="utf-8"))
    assert "p" in resumed_protocol["consensus"]["r10_voters"]
    assert "p" not in resumed_protocol["consensus"]["inactive_default_voters"]

    assert hub_peer.is_routable("p.standard", orch=resumed_orch)
    assert not hub_peer.is_routable("p.deepthink", orch=resumed_orch)


def test_add_remove_updates_all_generic_surfaces(monkeypatch, tmp_path):
    orch, peers, protocol, status = _configure(monkeypatch, tmp_path)
    _write(orch, {
        "consensus": {"default_voters": ["p"], "inactive_default_voters": []},
        "roles_registry": {"reviewer": ["p"], "coder": ["p"]},
        "hub_nodes": [{
            "node_id": "p",
            "type": "peer",
            "invoke": "peer-cli",
            "adapter_class": "BaseAdapter",
            "invoke_args": ["-p", "{query}"],
            "profiles": {
                name: {"model_id": "m", "routing_state": "eligible"}
                for name in ("standard", "effort", "deepthink")
            },
        }],
    })
    _write(peers, {"peers": {
        "provider": {"enabled": True, "node_ids": ["p"]}
    }})
    _write(protocol, {"consensus": {
        "default_voters": ["p"],
        "r10_voters": ["p"],
        "inactive_default_voters": [],
    }})
    _write(status, {"peers": {"p": {"safe_checks": []}}})

    assert peer_mgr.cmd_add("q", "peer-cli", "m", False) == 0
    assert peer_mgr.cmd_add("q", "peer-cli", "m", False) == 0
    added_orch = json.loads(orch.read_text(encoding="utf-8"))
    assert sum(node["node_id"] == "q" for node in added_orch["hub_nodes"]) == 1
    assert "q" in added_orch["consensus"]["default_voters"]
    assert all("q" in members for members in added_orch["roles_registry"].values())
    assert "q" in json.loads(peers.read_text(encoding="utf-8"))["peers"]["provider"]["node_ids"]
    assert "q" in json.loads(protocol.read_text(encoding="utf-8"))["consensus"]["r10_voters"]
    assert json.loads(status.read_text(encoding="utf-8"))["peers"]["q"]["inherits"] == "p"
    assert (tmp_path / "docs-v2" / "specific" / "q.md").exists()

    assert peer_mgr.cmd_suspend("q", "remove", False) == 0
    assert peer_mgr.cmd_remove("q", False) == 0
    removed_orch = json.loads(orch.read_text(encoding="utf-8"))
    assert all(node["node_id"] != "q" for node in removed_orch["hub_nodes"])
    assert "q" not in json.loads(peers.read_text(encoding="utf-8"))["peers"]["provider"]["node_ids"]
    assert "q" not in json.loads(protocol.read_text(encoding="utf-8"))["consensus"]["inactive_default_voters"]
    assert "q" not in json.loads(status.read_text(encoding="utf-8"))["peers"]
    assert (tmp_path / "docs" / "history" / "specific-q.md").exists()
