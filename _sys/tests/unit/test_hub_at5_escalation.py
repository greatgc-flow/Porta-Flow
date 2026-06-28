import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SYS = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SYS / "core"))

import hub  # noqa: E402
import hub_peer  # noqa: E402


def _orch() -> dict:
    return {
        "profile_contract": {
            "required_profiles": ["standard", "effort", "deepthink"],
        },
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
        ],
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
        json.dumps(
            {
                "room_id": "room-at5",
                "members": {"cx": "sid-cx", "ag": "sid-ag"},
                "mission": "at5",
                "phase": "active",
            }
        ),
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
    monkeypatch.setattr(hub, "_resolve_profile_id", lambda node_id: node_id if "." in node_id else f"{node_id}.standard")
    monkeypatch.setattr(hub.shutil, "which", lambda exe: f"/bin/{Path(exe).name}")
    monkeypatch.setattr(hub, "_lease_cfg", lambda: (1, 30, 1))
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
    monkeypatch.setattr(hub, "_session_reuse_enabled", lambda *a, **k: False)
    monkeypatch.setattr(hub, "_kill_process_tree", lambda *a, **k: None)
    monkeypatch.setattr(hub, "_CONTEXT_GATE_AVAILABLE", False, raising=False)
    monkeypatch.setattr(hub, "_ContextGate", None, raising=False)


def _patch_selector(monkeypatch, selections: dict[str, tuple[str, bool]]) -> list[str]:
    calls = []

    def select(target, query):
        calls.append(target)
        selected, explicit = selections[target]
        peer, profile = selected.split(".", 1)
        return selected, _decision(peer, profile, explicit=explicit, classifier=not explicit)

    monkeypatch.setattr(hub, "_select_ask_profile", select)
    return calls


def _as_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def _mock_popen_sequence(calls: list[dict], responses: list[dict]):
    response_iter = iter(responses)

    def fake_popen(cmd, *args, **kwargs):
        try:
            response = next(response_iter)
        except StopIteration:
            pytest.fail("unexpected subprocess spawn")

        call = {
            "cmd": cmd,
            "env": kwargs.get("env", {}),
            "input": None,
            "cwd": kwargs.get("cwd"),
        }
        calls.append(call)

        proc = MagicMock()
        proc.pid = 12345 + len(calls)
        proc.returncode = response.get("returncode", 0)
        proc.poll.return_value = proc.returncode
        proc.stdout.read.return_value = _as_bytes(response.get("stdout", b""))
        proc.stderr.read.return_value = _as_bytes(response.get("stderr", b""))

        def communicate(input=None, timeout=None):
            call["input"] = input
            return (
                _as_bytes(response.get("stdout", b"")),
                _as_bytes(response.get("stderr", b"")),
            )

        proc.communicate.side_effect = communicate
        return proc

    return fake_popen


def _mock_timeout_popen(calls: list[dict]):
    def fake_popen(cmd, *args, **kwargs):
        call = {
            "cmd": cmd,
            "env": kwargs.get("env", {}),
            "input": None,
            "cwd": kwargs.get("cwd"),
        }
        calls.append(call)

        proc = MagicMock()
        proc.pid = 22222
        proc.returncode = None
        proc.poll.return_value = None
        proc.stdout.read.return_value = b"[ESCALATE]"
        proc.stderr.read.return_value = b""

        def communicate(input=None, timeout=None):
            call["input"] = input
            raise subprocess.TimeoutExpired(cmd, timeout or 1, output=b"[ESCALATE]")

        proc.communicate.side_effect = communicate
        return proc

    return fake_popen


def test_parsed_marker_subprocess_escalates_one_tier(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(
        monkeypatch,
        {
            "cx": ("cx.standard", False),
            "cx.effort": ("cx.effort", True),
        },
    )
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [
                {"stdout": "first pass requests [ESCALATE]\n", "returncode": 0},
                {"stdout": "second pass settled\n", "returncode": 0},
            ],
        ),
    )

    hub.action_ask("cx", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert select_calls == ["cx", "cx.effort"]
    assert len(popen_calls) == 2
    assert "cx-standard" in popen_calls[0]["cmd"]
    assert "cx-effort" in popen_calls[1]["cmd"]
    assert "[HUB:ESCALATE] cx.standard -> cx.effort" in captured.err


def test_parsed_marker_pty_escalates_one_tier(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    monkeypatch.setattr(hub.sys, "platform", "win32")
    select_calls = _patch_selector(
        monkeypatch,
        {
            "ag": ("ag.standard", False),
            "ag.effort": ("ag.effort", True),
        },
    )
    pty_calls = []
    responses = iter(["pty requests [ESCALATE]\n", "pty settled\n"])

    def fake_pty(cmd, node_id, timeout_sec, process_env, quiet, ai_root, ask_id, cwd):
        pty_calls.append({"cmd": cmd, "node_id": node_id, "env": process_env})
        return hub._PtyAskResult(
            text=next(responses),
            elapsed=1,
            exit_code=0,
            timed_out=False,
            timeout_kind=None,
            pid=33333 + len(pty_calls),
            transport_error=None,
        )

    monkeypatch.setattr(hub, "_ask_with_pty", fake_pty)

    hub.action_ask("ag", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert select_calls == ["ag", "ag.effort"]
    assert [call["node_id"] for call in pty_calls] == ["ag.standard", "ag.effort"]
    assert "ag-standard" in pty_calls[0]["cmd"]
    assert "ag-effort" in pty_calls[1]["cmd"]
    assert "[HUB:ESCALATE] ag.standard -> ag.effort" in captured.err


def test_depth_ceiling_blocks_runtime_escalation(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx": ("cx.standard", False)})
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [{"stdout": "still requests [ESCALATE]\n", "returncode": 0}],
        ),
    )

    hub.action_ask(
        "cx",
        "review this",
        None,
        30,
        ai_root,
        quiet=True,
        include_context=False,
        _escalation_depth=hub.RUNTIME_ESCALATION_DEPTH_CEILING,
    )


    captured = capsys.readouterr()
    assert select_calls == ["cx"]
    assert len(popen_calls) == 1
    assert "[HUB:ESCALATE]" not in captured.err


def test_failed_final_output_marker_does_not_escalate(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx": ("cx.standard", False)})
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [{"stdout": "failed worker output [ESCALATE]\n", "stderr": "", "returncode": 1}],
        ),
    )

    with pytest.raises(SystemExit) as exc:
        hub.action_ask("cx", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert select_calls == ["cx"]
    assert len(popen_calls) == 1
    assert "[HUB:ESCALATE]" not in captured.err


def test_timeout_failure_is_not_promoted_to_escalation(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx": ("cx.standard", False)})
    popen_calls = []
    monkeypatch.setattr(hub.subprocess, "Popen", _mock_timeout_popen(popen_calls))

    with pytest.raises(SystemExit) as exc:
        hub.action_ask("cx", "review this", None, 1, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert select_calls == ["cx"]
    assert len(popen_calls) == 1
    assert "[HUB:ESCALATE]" not in captured.err


def test_explicit_profile_marker_does_not_escalate(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx.standard": ("cx.standard", True)})
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [{"stdout": "explicit profile requests [ESCALATE]\n", "returncode": 0}],
        ),
    )

    hub.action_ask("cx.standard", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert select_calls == ["cx.standard"]
    assert len(popen_calls) == 1
    assert "cx-standard" in popen_calls[0]["cmd"]
    assert "[HUB:ESCALATE]" not in captured.err


def test_top_tier_marker_has_no_escalation_target(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx": ("cx.deepthink", False)})
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [{"stdout": "top tier requests [ESCALATE]\n", "returncode": 0}],
        ),
    )

    hub.action_ask("cx", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert select_calls == ["cx"]
    assert len(popen_calls) == 1
    assert "cx-deepthink" in popen_calls[0]["cmd"]
    assert "[HUB:ESCALATE]" not in captured.err


def test_runtime_escalation_reaches_deepthink_after_recursive_dotted_target(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(
        monkeypatch,
        {
            "cx": ("cx.standard", False),
            "cx.effort": ("cx.effort", True),
            "cx.deepthink": ("cx.deepthink", True),
        },
    )
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [
                {"stdout": "standard requests [ESCALATE]\n", "returncode": 0},
                {"stdout": "effort requests [ESCALATE]\n", "returncode": 0},
                {"stdout": "deepthink settled\n", "returncode": 0},
            ],
        ),
    )

    hub.action_ask("cx", "review this", None, 30, ai_root, quiet=True, include_context=False)

    captured = capsys.readouterr()
    assert select_calls == ["cx", "cx.effort", "cx.deepthink"]
    assert len(popen_calls) == 3
    assert "cx-standard" in popen_calls[0]["cmd"]
    assert "cx-effort" in popen_calls[1]["cmd"]
    assert "cx-deepthink" in popen_calls[2]["cmd"]
    assert "[HUB:ESCALATE] cx.standard -> cx.effort" in captured.err
    assert "[HUB:ESCALATE] cx.effort -> cx.deepthink" in captured.err


def test_direct_output_file_write_failure_does_not_escalate(monkeypatch, tmp_path, capsys):
    ai_root = _ai_root(tmp_path)
    _patch_common(monkeypatch)
    select_calls = _patch_selector(monkeypatch, {"cx": ("cx.standard", False)})
    bad_output_path = tmp_path / "bad-output"
    bad_output_path.mkdir()
    monkeypatch.setattr(hub, "_portable_state_path", lambda base, output_file: bad_output_path)
    popen_calls = []
    monkeypatch.setattr(
        hub.subprocess,
        "Popen",
        _mock_popen_sequence(
            popen_calls,
            [{"stdout": "successful output requests [ESCALATE]\n", "returncode": 0}],
        ),
    )

    with pytest.raises(SystemExit) as exc:
        hub.action_ask(
            "cx",
            "review this",
            None,
            30,
            ai_root,
            quiet=True,
            output_file="reply.txt",
            include_context=False,
        )

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert select_calls == ["cx"]
    assert len(popen_calls) == 1
    assert "failed to write output file" in captured.err
    assert "[HUB:ESCALATE]" not in captured.err

