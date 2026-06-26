import pytest
import json
from pathlib import Path
import sys

SYS_DIR = Path(__file__).parent.parent.parent.resolve()

def test_protocol_voters_are_disjoint():
    """A-03: r10_voters and inactive_default_voters must be disjoint."""
    protocol_path = SYS_DIR / "ai" / "protocol.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    
    consensus = protocol.get("consensus", {})
    r10_voters = set(consensus.get("r10_voters", []))
    inactive_voters = set(consensus.get("inactive_default_voters", []))
    
    intersection = r10_voters.intersection(inactive_voters)
    assert not intersection, f"Found peers in both r10_voters and inactive_default_voters: {intersection}"
