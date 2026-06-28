import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SYS = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SYS / "core"))

import hub  # noqa: E402
import hub_peer  # noqa: E402
import hub_profile_router  # noqa: E402


# AT-4 relies on existing action_ask(origin=...) and existing
# ProfileDecision.as_dict() fields: selected_profile, explicit,
# classifier_triggered, and fallback_from.


def _orch() -> dict:
    return {
        "hub_nodes": [
            {
                "node_id": "cx",
                "type": "peer",
                "enabled": True,
                "adapter_class": "CodexAdapter",
                "invoke": "mock-cx",
                "invoke_args": ["exec", "{query}"],
                "requires_pty": False,
                "session_mode": "none",
                "default_profile": "standard",
                "profiles": {
                    "standard": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "cx-standard"],
                    },
                    "effort": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "cx-effort"],
                    },
                    "deepthink": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "cx-deepthink"],
                    },
                },
            },
            {
                "node_id": "ag",
                "type": "peer",
                "enabled": True,
                "adapter_class": "AgyAdapter",
                "invoke": "mock-ag",
                "invoke_args": ["-p", "{query}"],
                "requires_pty": True,
                "session_mode": "none",
                "default_profile": "standard",
                "profiles": {
                    "standard": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "ag-standard"],
                    },
                    "effort": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "ag-effort"],
                    },
                    "deepthink": {
                        "enabled": True,
                        "routing_state": "eligible",
                        "profile_args": ["--model", "ag-deepthink"],
                    },
                },
            },
        ]
    }


def _nodes() -> dict:
    normalized = hub_peer.normalize_orchestration(_orch())
    return {
        node["node_id"]: {k: v for k, v in node.items() if k != "node_id"}
        for node in normalized["hub_nodes"]
    }


def _ai_root(tmp_path: Path) -> Path:
    ai_root = tmp_path / ".ai"
    ai_root.mkdir()
    (ai_root / "state.json").write_text(
        json.dumps({
            "room_id": "room-at4",
            "members": {"cx": "sid-cx"},
            "mission": "at4",
            "phase": "active",
        }),
        encoding="utf-8",
    )
    return ai_root


def _decision(peer: str, profile: str, *, explicit: bool, classifier: bool) -> dict:
    return {
        "root_peer": peer,
        "node_id": f"{peer}.{profile}",
        "selected_profile": profile,
        "requested_profile": profile,
        "explicit": explicit,
        "classifier_triggered": classifier,
        "fallback_from": None,
    }


def _patch_common(monkeypatch) -> None:
    monkeypatch.setattr(hub, "_load_orchestration", _orch)
    monkeypatch.setattr(hub, "_load_nodes", lambda ai_root: _nodes())
    monkeypatch.setattr(hub, "is_routable", lambda target, orch=None: True)
    monkeypatch.setattr(hub.shutil, "which", lambda exe: f"/bin/{Path(exe).name}")
    monkeypatch.setattr(hub, "_lease_sweep", lambda ai_root: None)
    monkeypatch.setattr(hub, "_ask_health_precheck", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_guard_action", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_record_ask_success", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_record_ask_failure", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_ask_history", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_record_routing_metric", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_open", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_renew", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_lease_close", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_append_handoff_item", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_load_peers", lambda: {"peers": {}})
    monkeypatch.setattr(hub, "_get_logger", lambda: None)


def _mock_popen(captured: dict):
    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})

        proc = MagicMock()
        proc.pid = 12345
        proc.returncode = 0
        proc.poll.return_value = 0
        proc.stdout.read.return_value = b""
        proc.stderr.read.return_value = b""

        def communicate(input=None, timeout=None):
            captured["input"] = input
            return b"ok", b""

        proc.communicate.side_effect = communicate
        return proc

    return fake_popen


def _assert_frame(prompt: str, raw_query: str, selected_target: str) -> None:
    assert "[TERMINAL RELAY FRAME]" in prompt
    assert "ROLE: thin_router" in prompt
    assert "USER_QUERY_RAW:\n" + raw_query in prompt
    assert "ROUTING_METADATA:" in prompt
    assert f'"selected_target": "{selected_target}"' in prompt
    assert "CONTEXT_REFERENCES:" in prompt
    assert "state.json" in prompt


def _assert_no_terminal_analysis(prompt: str) -> None:
    forbidden = [
        '"score"',
        '"signals"',
        '"confidence"',
        "[TERMINAL ANALYSIS]",
        "recommendation",
        "because",
    ]
    lowered = prompt.lower()
    for marker in forbidden:
        assert marker.lower() not in lowered


def test_subprocess_terminal_relay_frame(monkeypatch, tmp_path):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    raw_query = "Show repository status."

    monkeypatch.setattr(
        hub,
        "_select_ask_profile",
        lambda target, query: ("cx.standard", _decision("cx", "standard", explicit=False, classifier=True)),
    )
    captured = {}
    monkeypatch.setattr(hub.subprocess, "Popen", _mock_popen(captured))

    hub.action_ask("cx", raw_query, None, 30, ai_root, quiet=True, include_context=False)

    prompt = captured["input"].decode("utf-8")
    _assert_frame(prompt, raw_query, "cx.standard")
    assert '"classifier_triggered": true' in prompt
    assert '"explicit_profile": false' in prompt


def test_pty_terminal_relay_frame(monkeypatch, tmp_path):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    monkeypatch.setattr(hub.sys, "platform", "win32")
    raw_query = "Show repository status."

    monkeypatch.setattr(
        hub,
        "_select_ask_profile",
        lambda target, query: ("ag.standard", _decision("ag", "standard", explicit=False, classifier=True)),
    )
    captured = {}

    def fake_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        captured["cmd"] = cmd
        captured["node_id"] = node_id
        return hub._PtyAskResult(
            text="ok",
            elapsed=1,
            exit_code=0,
            timed_out=False,
            timeout_kind=None,
            pid=12345,
            transport_error=None,
        )

    monkeypatch.setattr(hub, "_ask_with_pty", fake_pty)

    hub.action_ask("ag", raw_query, None, 30, ai_root, quiet=True, include_context=False)

    prompt = next(arg for arg in captured["cmd"] if "[TERMINAL RELAY FRAME]" in arg)
    assert captured["node_id"] == "ag.standard"
    _assert_frame(prompt, raw_query, "ag.standard")


def test_subprocess_explicit_profile_is_not_classifier_promoted(monkeypatch, tmp_path):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    raw_query = "Architecture protocol security exhaustive review."

    def select(target, query):
        assert target == "cx.standard"
        assert query == raw_query
        return "cx.standard", _decision("cx", "standard", explicit=True, classifier=False)

    monkeypatch.setattr(hub, "_select_ask_profile", select)
    captured = {}
    monkeypatch.setattr(hub.subprocess, "Popen", _mock_popen(captured))

    hub.action_ask("cx.standard", raw_query, None, 30, ai_root, quiet=True, include_context=False)

    prompt = captured["input"].decode("utf-8")
    assert captured["env"]["HUB_PEER_TIER"] == "standard"
    assert "cx-standard" in captured["cmd"]
    assert "cx-deepthink" not in captured["cmd"]
    assert '"selected_target": "cx.standard"' in prompt
    assert '"explicit_profile": true' in prompt
    assert '"classifier_triggered": false' in prompt


def test_pty_explicit_profile_is_not_classifier_promoted(monkeypatch, tmp_path):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    monkeypatch.setattr(hub.sys, "platform", "win32")
    raw_query = "Architecture protocol security exhaustive review."

    def select(target, query):
        assert target == "ag.standard"
        assert query == raw_query
        return "ag.standard", _decision("ag", "standard", explicit=True, classifier=False)

    monkeypatch.setattr(hub, "_select_ask_profile", select)
    captured = {}

    def fake_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        captured["cmd"] = cmd
        captured["env"] = process_env
        captured["node_id"] = node_id
        return hub._PtyAskResult(
            text="ok",
            elapsed=1,
            exit_code=0,
            timed_out=False,
            timeout_kind=None,
            pid=12345,
            transport_error=None,
        )

    monkeypatch.setattr(hub, "_ask_with_pty", fake_pty)

    hub.action_ask("ag.standard", raw_query, None, 30, ai_root, quiet=True, include_context=False)

    prompt = next(arg for arg in captured["cmd"] if "[TERMINAL RELAY FRAME]" in arg)
    assert captured["env"]["HUB_PEER_TIER"] == "standard"
    assert captured["node_id"] == "ag.standard"
    assert "ag-standard" in captured["cmd"]
    assert "ag-deepthink" not in captured["cmd"]
    assert '"explicit_profile": true' in prompt
    assert '"classifier_triggered": false' in prompt


def test_subprocess_explicit_unavailable_fails_visible_without_spawn(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)

    def raise_unavailable(target, query):
        raise hub_profile_router.ProfileRoutingError(
            "explicit profile 'deepthink' is currently unavailable"
        )

    monkeypatch.setattr(hub, "_select_ask_profile", raise_unavailable)
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("subprocess must not spawn for unavailable explicit profile"),
    )

    with pytest.raises(SystemExit) as exc:
        hub.action_ask("cx.deepthink", "Show status.", None, 30, ai_root, quiet=True)

    assert exc.value.code == 1
    assert "explicit profile 'deepthink' is currently unavailable" in capsys.readouterr().err


def test_pty_explicit_unavailable_fails_visible_without_spawn(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    monkeypatch.setattr(hub.sys, "platform", "win32")

    def raise_unavailable(target, query):
        raise hub_profile_router.ProfileRoutingError(
            "explicit profile 'deepthink' is currently unavailable"
        )

    monkeypatch.setattr(hub, "_select_ask_profile", raise_unavailable)
    monkeypatch.setattr(
        hub,
        "_ask_with_pty",
        lambda *a, **k: pytest.fail("PTY must not spawn for unavailable explicit profile"),
    )

    with pytest.raises(SystemExit) as exc:
        hub.action_ask("ag.deepthink", "Show status.", None, 30, ai_root, quiet=True)

    assert exc.value.code == 1
    assert "explicit profile 'deepthink' is currently unavailable" in capsys.readouterr().err


def test_classifier_uses_raw_query_and_frame_has_no_terminal_analysis(monkeypatch, tmp_path):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    raw_subprocess = "List active peers."
    raw_pty = "Read current health."

    seen_queries = []

    def select(target, query):
        seen_queries.append(query)
        if target.startswith("ag"):
            return "ag.standard", _decision("ag", "standard", explicit=False, classifier=True)
        return "cx.standard", _decision("cx", "standard", explicit=False, classifier=True)

    monkeypatch.setattr(hub, "_select_ask_profile", select)

    captured_subprocess = {}
    monkeypatch.setattr(hub.subprocess, "Popen", _mock_popen(captured_subprocess))
    hub.action_ask("cx", raw_subprocess, None, 30, ai_root, quiet=True, include_context=False)

    subprocess_prompt = captured_subprocess["input"].decode("utf-8")
    _assert_frame(subprocess_prompt, raw_subprocess, "cx.standard")
    _assert_no_terminal_analysis(subprocess_prompt)

    monkeypatch.setattr(hub.sys, "platform", "win32")
    captured_pty = {}

    def fake_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        captured_pty["cmd"] = cmd
        return hub._PtyAskResult(
            text="ok",
            elapsed=1,
            exit_code=0,
            timed_out=False,
            timeout_kind=None,
            pid=12345,
            transport_error=None,
        )

    monkeypatch.setattr(hub, "_ask_with_pty", fake_pty)
    hub.action_ask("ag", raw_pty, None, 30, ai_root, quiet=True, include_context=False)

    pty_prompt = next(arg for arg in captured_pty["cmd"] if "[TERMINAL RELAY FRAME]" in arg)
    _assert_frame(pty_prompt, raw_pty, "ag.standard")
    _assert_no_terminal_analysis(pty_prompt)

    assert seen_queries == [raw_subprocess, raw_pty]


def test_context_gate_failover_explicit_profile_is_immutable(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)

    class FailoverGate:
        def check(self, query, model_id):
            return {
                "action": "failover",
                "failover_model": "cx.effort",
                "ratio": 0.91,
            }

    monkeypatch.setattr(hub, "_CONTEXT_GATE_AVAILABLE", True, raising=False)
    monkeypatch.setattr(hub, "_ContextGate", FailoverGate, raising=False)
    monkeypatch.setattr(
        hub,
        "_select_ask_profile",
        lambda target, query: ("cx.standard", _decision("cx", "standard", explicit=True, classifier=False)),
    )
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        lambda *a, **k: pytest.fail("explicit ContextGate failover must not spawn subprocess"),
    )

    with pytest.raises(SystemExit) as exc:
        hub.action_ask("cx.standard", "Show status.", None, 30, ai_root, quiet=True, include_context=False)

    assert exc.value.code == 1
    assert "[HUB:ERROR] explicit profile immutable" in capsys.readouterr().err


