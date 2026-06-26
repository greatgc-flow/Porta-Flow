import pytest
import json
from pathlib import Path
import sys

SYS_DIR = Path(__file__).parent.parent.parent.resolve()

def test_routing_targets_exist_in_orchestration():
    """A-02: Validate every <peer>::<profile> routing target exists in orchestration.json profiles."""
    routing_path = SYS_DIR / "ai" / "routing-config.json"
    orchestration_path = SYS_DIR / "ai" / "orchestration.json"
    
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8"))
    
    valid_targets = set()
    for node in orchestration.get("hub_nodes", []):
        peer = node.get("node_id")
        profiles = node.get("profiles", {})
        for profile_name, profile_data in profiles.items():
            valid_targets.add(f"{peer}::{profile_name}")
            # Also allow legacy model_id or runtime_model references
            if "model_id" in profile_data:
                valid_targets.add(f"{peer}::{profile_data['model_id']}")
            if "runtime_model" in profile_data:
                valid_targets.add(f"{peer}::{profile_data['runtime_model']}")
            
    # Also support nodes that might not have explicit profiles but are valid fallback
    for node in orchestration.get("hub_nodes", []):
        peer = node.get("node_id")
        if peer:
            valid_targets.add(peer)
            
    # Check all routing weights
    weights = routing.get("routing_weights", {})
    for r_key, r_val in weights.items():
        primary = r_val.get("primary")
        fallback = r_val.get("fallback")
        
        for target in (primary, fallback):
            if not target or "::" not in target:
                continue
            # target is e.g. 'ag::effort::none::none' — check ALL peers' peer::profile,
            # not just ag (A-02 was an ag::default bug, but the ratchet guards every peer).
            parts = target.split("::")
            if len(parts) >= 2:
                peer_profile = f"{parts[0]}::{parts[1]}"
                assert peer_profile in valid_targets, f"Target {target} in {r_key} invalid: {peer_profile} not in orchestration"
            else:
                assert target in valid_targets, f"Target {target} in {r_key} invalid"
