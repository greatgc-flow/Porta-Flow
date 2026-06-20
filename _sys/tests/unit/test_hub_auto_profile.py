"""Integration boundary tests for hub root-to-profile routing."""
import sys
from pathlib import Path
from unittest.mock import patch

SYS = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SYS / "core"))

import hub


def test_hub_selects_standard_for_simple_root_request():
    with patch("hub._read_peer_health", return_value=(Path("health.json"), {})):
        target, decision = hub._select_ask_profile("cx", "Show repository status.")
    assert target == "cx.standard"
    assert decision["selected_profile"] == "standard"


def test_hub_selects_deepthink_for_high_risk_root_request():
    query = "Redesign the architecture and perform an exhaustive security review."
    with patch("hub._read_peer_health", return_value=(Path("health.json"), {})):
        target, decision = hub._select_ask_profile("cc", query)
    assert target == "cc.deepthink"
    assert decision["selected_profile"] == "deepthink"


def test_hub_preserves_explicit_profile():
    with patch("hub._read_peer_health", return_value=(Path("health.json"), {})):
        target, decision = hub._select_ask_profile(
            "cx.deepthink", "Show repository status."
        )
    assert target == "cx.deepthink"
    assert decision["explicit"] is True
