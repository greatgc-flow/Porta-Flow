import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SYS_DIR = Path(__file__).parent.parent.parent.resolve()
if str(SYS_DIR / "core") not in sys.path:
    sys.path.insert(0, str(SYS_DIR / "core"))

import hub


def test_hub_ask_sets_deepthink_tier(tmp_path):
    """A-04: an auto-routed deepthink ask must set HUB_PEER_TIER from the resolved
    profile (selected_profile), NOT default 'standard'."""
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()

    captured = {}

    def fake_popen(cmd, *args, **kwargs):
        captured["env"] = kwargs.get("env", {})
        proc = MagicMock()
        proc.returncode = 0
        proc.pid = 12345
        proc.communicate.return_value = (b"answer", b"")
        proc.stdout.read.side_effect = [b"answer", b""] + [b""] * 50
        proc.stderr.read.side_effect = [b"", b""] + [b""] * 50
        proc.poll.return_value = 0
        return proc

    # cx is a subprocess peer; route it to deepthink via the profile decision.
    with patch("hub._select_ask_profile", return_value=("cx", {"selected_profile": "deepthink"})), \
         patch("hub._ask_health_precheck"), \
         patch("hub._append_ask_history"), \
         patch("shutil.which", return_value="dummy_path"), \
         patch("subprocess.Popen", side_effect=fake_popen) as mock_popen:
        try:
            hub.action_ask(
                "cx", "Complex deepthink query", None, 30, ai_root,
                quiet=True, include_context=False,
            )
        except SystemExit:
            pass

    assert mock_popen.called, "subprocess.Popen was not reached"
    assert captured["env"].get("HUB_PEER_TIER") == "deepthink", (
        f"HUB_PEER_TIER was {captured['env'].get('HUB_PEER_TIER')!r}, expected 'deepthink' "
        f"(regression: reading 'tier' instead of 'selected_profile')"
    )
