import importlib.util
import io
import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SYS_DIR = Path(__file__).resolve().parents[2]
DIAG_PATH = SYS_DIR / "cli" / "diag.py"


def load_diag():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("diag_under_test", DIAG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_watch_below_minimum_is_rejected_with_clear_error(capsys):
    diag = load_diag()

    with pytest.raises(SystemExit) as exc:
        diag.parse_args(["--watch", "1"])

    assert exc.value.code != 0
    assert "minimum interval is 2" in capsys.readouterr().err


def test_interval_alias_uses_watch_mode_and_same_interval_floor(capsys):
    diag = load_diag()

    args = diag.parse_args(["--interval", "3"])

    assert args.watch is True
    assert args.interval == 3

    with pytest.raises(SystemExit) as exc:
        diag.parse_args(["--interval", "1"])

    assert exc.value.code != 0
    assert "minimum interval is 2" in capsys.readouterr().err


def test_json_one_shot_emits_single_json_object(monkeypatch):
    diag = load_diag()
    monkeypatch.setattr(diag, "collect_snapshot", lambda: {"schema_version": 1, "peers": []})
    out = io.StringIO()

    diag.main(["--json"], stdout=out)

    rendered = out.getvalue()
    parsed = json.loads(rendered)
    assert parsed["schema_version"] == 1
    assert rendered.count("\n") == 1
    assert "\x1b[" not in rendered


def test_json_watch_emits_ndjson_without_ansi(monkeypatch):
    diag = load_diag()
    calls = iter([
        {"schema_version": 1, "seq": 1},
        {"schema_version": 1, "seq": 2},
    ])
    monkeypatch.setattr(diag, "collect_snapshot", lambda: next(calls))
    sleeps = []
    out = io.StringIO()

    diag.run_watch(interval=2, json_mode=True, stdout=out, sleep=sleeps.append, max_frames=2)

    lines = out.getvalue().splitlines()
    assert [json.loads(line)["seq"] for line in lines] == [1, 2]
    assert sleeps == [2]
    assert "\x1b[" not in out.getvalue()


def test_codex_rate_limits_deadline_survives_blocking_readline(monkeypatch):
    diag = load_diag()

    class BlockingStdout:
        def readline(self):
            time.sleep(0.2)
            return ""

    class FakeStdin:
        def write(self, _text):
            return None

        def flush(self):
            return None

    class FakeProc:
        def __init__(self):
            self.stdin = FakeStdin()
            self.stdout = BlockingStdout()
            self.killed = False

        def poll(self):
            return None

        def kill(self):
            self.killed = True

    monkeypatch.setattr(shutil, "which", lambda _name: "codex")
    monkeypatch.setattr(diag.subprocess, "Popen", lambda *args, **kwargs: FakeProc())

    started = time.monotonic()
    assert diag._codex_rate_limits(deadline_sec=0.05) is None
    assert time.monotonic() - started < 0.15

def test_codex_rate_limits_are_cached_for_expensive_ttl(monkeypatch):
    diag = load_diag()
    calls = []

    def fetch():
        calls.append("fetch")
        return {"primary": {"usedPercent": len(calls), "resetsAt": 1}}

    monkeypatch.setattr(diag, "_codex_rate_limits", fetch)
    diag._CODEX_RATE_LIMIT_CACHE.clear()

    first = diag._cached_codex_rate_limits(clock=lambda: 100.0)
    second = diag._cached_codex_rate_limits(clock=lambda: 159.0)
    third = diag._cached_codex_rate_limits(clock=lambda: 161.0)

    assert first is second
    assert third is not second
    assert len(calls) == 2

def test_reset_formatter_includes_local_timezone_and_relative_countdown():
    diag = load_diag()
    reset_at = datetime.now(timezone.utc).astimezone() + timedelta(minutes=70)

    rendered = diag._fmt_reset(reset_at.isoformat())

    assert "in 1h" in rendered
    assert reset_at.strftime("%z") in rendered or reset_at.tzname() in rendered


# ???? TDD slice 1: normalized telemetry record (吏?/吏?3.1) ??????????????????????????????????????????????????

_VALID_SOURCE_KINDS = {"live", "cached", "snapshot", "estimated", "unknown"}
_VALID_CONFIDENCE = {"exact", "estimated", "last_known", "unknown"}


def test_normalize_peer_every_domain_carries_source_metadata():
    diag = load_diag()
    info = {
        "peer": "cc", "source": "live", "gate": True, "quarantined": False,
        "model": "Opus", "ctx_used": 100000, "ctx_window": 1000000, "ctx_pct": 10.0,
        "ctx_known": True, "cost": 0.5, "agent_state": "idle", "plan_tier": None,
        "sessions": 3, "total_tokens": None, "empty": False,
        "quotas": [{"label": "5H", "used_frac": 0.1, "reset": "x", "metric": "10% used"}],
    }

    rec = diag.normalize_peer(info)

    assert rec["peer"] == "cc"
    assert isinstance(rec.get("domains"), dict) and rec["domains"]
    for domain, drec in rec["domains"].items():
        src = drec.get("source")
        assert src is not None, f"{domain} missing source"
        assert src["kind"] in _VALID_SOURCE_KINDS
        assert src["confidence"] in _VALID_CONFIDENCE
        assert "observed_at" in src and "ttl_sec" in src


def test_normalize_unknown_context_is_null_not_zero():
    diag = load_diag()
    info = {
        "peer": "cx", "source": "app-server", "gate": True, "quarantined": False,
        "model": "gpt", "ctx_used": 0, "ctx_window": 128000, "ctx_pct": None,
        "ctx_known": False, "cost": None, "agent_state": None, "plan_tier": None,
        "sessions": None, "total_tokens": 96000000, "empty": False,
        "quotas": [{"label": "5H", "used_frac": 0.01, "reset": "x", "metric": "1% used",
                    "expensive": True}],
    }

    rec = diag.normalize_peer(info)
    ctx = rec["domains"]["context"]

    assert ctx["used_tokens"] is None          # unknown, never 0
    assert ctx["utilization_pct"] is None
    assert ctx["source"]["confidence"] == "unknown"


def test_normalize_expensive_quota_uses_longer_ttl_than_local():
    diag = load_diag()
    info = {
        "peer": "cx", "source": "app-server", "gate": True, "quarantined": False,
        "model": "gpt", "ctx_used": 0, "ctx_window": 128000, "ctx_pct": None,
        "ctx_known": False, "cost": None, "agent_state": None, "plan_tier": None,
        "sessions": None, "total_tokens": None, "empty": False, "quotas": [],
    }

    rec = diag.normalize_peer(info)

    # cx quota comes from the codex app-server (expensive) -> 60s TTL; local health -> 5s
    assert rec["domains"]["quota"]["source"]["ttl_sec"] == 60
    assert rec["domains"]["health"]["source"]["ttl_sec"] == 5


def test_collect_snapshot_peers_are_normalized():
    diag = load_diag()
    snap = diag.collect_snapshot()
    assert snap["schema_version"] == 1
    for peer in snap["peers"]:
        assert "domains" in peer
        assert "context" in peer["domains"]


# ???? TDD slice 2: redaction (吏?) ??????????????????????????????????????????????????????????????????????????????????????????????????

def test_mask_email_hides_local_part_keeps_domain():
    diag = load_diag()
    masked = diag._mask_email("greatgc@gmail.com")
    assert "greatgc" not in masked
    assert masked.endswith("@gmail.com")
    assert masked != "greatgc@gmail.com"


def test_mask_email_handles_missing_or_malformed():
    diag = load_diag()
    assert diag._mask_email(None) is None
    assert diag._mask_email("") in (None, "")
    # non-email string must not be echoed back verbatim as if valid
    assert diag._mask_email("notanemail") == "***"


def test_normalize_account_exposes_only_masked_email():
    diag = load_diag()
    info = {
        "peer": "ag", "source": "live", "gate": True, "quarantined": False,
        "model": "Gemini", "ctx_used": 0, "ctx_window": 1000000, "ctx_pct": 0,
        "ctx_known": True, "cost": None, "agent_state": "idle",
        "plan_tier": "Google AI Pro", "email": "greatgc@gmail.com",
        "sessions": None, "total_tokens": None, "empty": False, "quotas": [],
    }
    rec = diag.normalize_peer(info)
    acct = rec["domains"]["account"]
    assert acct.get("email") == "g***@gmail.com" or "greatgc" not in str(acct.get("email"))
    # the whole record must never carry the raw address anywhere
    import json as _j
    assert "greatgc@gmail.com" not in _j.dumps(rec)


def test_snapshot_json_contains_no_raw_email(monkeypatch):
    diag = load_diag()
    raw_info = {
        "peer": "ag", "source": "live", "gate": True, "quarantined": False,
        "model": "Gemini", "ctx_used": 0, "ctx_window": 1000000, "ctx_pct": 0,
        "ctx_known": True, "cost": None, "agent_state": "idle",
        "plan_tier": "Google AI Pro", "email": "greatgc@gmail.com",
        "sessions": None, "total_tokens": None, "empty": False, "quotas": [],
    }
    rec = diag.normalize_peer(dict(raw_info))
    monkeypatch.setattr(diag, "collect_snapshot",
                        lambda: {"schema_version": 1, "peers": [rec]})
    out = io.StringIO()
    diag.emit_json_snapshot(out)
    assert "greatgc@gmail.com" not in out.getvalue()


# ???? TDD slice 3: resilience (吏?1) ??????????????????????????????????????????????????????????????????????????????????????????????

def test_gather_peer_missing_dir_does_not_raise(tmp_path):
    diag = load_diag()
    info = diag.gather_peer("zz", {"zz": tmp_path / "nope"})
    assert info["empty"] is True
    assert info["ctx_known"] is False


def test_collect_snapshot_survives_collector_exception(monkeypatch):
    diag = load_diag()

    def boom(peer, dirs):
        raise RuntimeError("sqlite exploded")
    monkeypatch.setattr(diag, "gather_peer", boom)

    snap = diag.collect_snapshot()  # must NOT raise even if every collector throws
    assert snap["peers"], "snapshot should still list peers"
    assert all(rec.get("errors") for rec in snap["peers"]), (
        "trapped collector errors must be surfaced, not silent"
    )


def test_is_synthetic_peer_filters_test_fixtures():
    diag = load_diag()
    assert diag._is_synthetic_peer("testpeer") is True
    assert diag._is_synthetic_peer("cx") is False
    assert diag._is_synthetic_peer("cc") is False


# ???? TDD slice 4: alerts (吏?) ????????????????????????????????????????????????????????????????????????????????????????????????????????

def _rec_with(diag, **overrides):
    base = {
        "peer": "cc", "source": "live", "gate": True, "quarantined": False,
        "model": "M", "ctx_used": 100, "ctx_window": 1000, "ctx_pct": 10.0,
        "ctx_known": True, "cost": 0.1, "agent_state": "idle", "plan_tier": "Pro",
        "email": "a@b.com", "sessions": 1, "total_tokens": None, "empty": False,
        "quotas": [], "errors": [],
    }
    base.update(overrides)
    return diag.normalize_peer(base)


def _codes(alerts):
    return {a["code"] for a in alerts}


def test_alerts_context_warn_and_critical():
    diag = load_diag()
    warn = diag._compute_alerts(_rec_with(diag, ctx_pct=85.0))
    crit = diag._compute_alerts(_rec_with(diag, ctx_pct=97.0))
    assert "CONTEXT_WARN" in _codes(warn) and "CONTEXT_CRITICAL" not in _codes(warn)
    assert "CONTEXT_CRITICAL" in _codes(crit)


def test_alerts_ctx_unknown_suppresses_context_thresholds():
    diag = load_diag()
    alerts = _codes(diag._compute_alerts(_rec_with(diag, ctx_known=False, ctx_pct=None)))
    assert "CTX_UNKNOWN" in alerts
    assert "CONTEXT_WARN" not in alerts and "CONTEXT_CRITICAL" not in alerts


def test_alerts_quota_warn_and_critical():
    diag = load_diag()
    warn = diag._compute_alerts(_rec_with(diag, quotas=[{"label": "5H", "used_frac": 0.80, "reset": "x", "metric": "m"}]))
    crit = diag._compute_alerts(_rec_with(diag, quotas=[{"label": "5H", "used_frac": 0.93, "reset": "x", "metric": "m"}]))
    assert "QUOTA_WARN" in _codes(warn)
    assert "QUOTA_CRITICAL" in _codes(crit)


def test_alerts_account_unknown_and_diag_error():
    diag = load_diag()
    acct = diag._compute_alerts(_rec_with(diag, plan_tier=None, email=None))
    assert "ACCOUNT_UNKNOWN" in _codes(acct)
    err = diag._compute_alerts(_rec_with(diag, errors=["sqlite_read: OperationalError"]))
    assert "DIAG_INTERNAL_ERROR" in _codes(err)


def test_snapshot_records_carry_alerts_list():
    diag = load_diag()
    snap = diag.collect_snapshot()
    for peer in snap["peers"]:
        assert isinstance(peer.get("alerts"), list)


# ???? TDD slice 5: detail views (吏?.2) ????????????????????????????????????????????????????????????????????????????????????????

def test_profiles_view_never_leaks_raw_profile_args():
    diag = load_diag()
    out = io.StringIO()
    assert diag.main(["--profiles"], stdout=out) == 0
    text = out.getvalue()
    assert "profile_args" not in text
    assert "model_reasoning_effort" not in text  # raw adapter arg must not leak
    # but it should still show real profile facts
    assert "standard" in text or "deepthink" in text


def test_accounts_view_has_no_unmasked_email(monkeypatch):
    diag = load_diag()
    rec = diag.normalize_peer({
        "peer": "ag", "source": "live", "plan_tier": "Google AI Pro",
        "email": "greatgc@gmail.com", "ctx_known": True, "ctx_window": 1000,
        "ctx_used": 1, "ctx_pct": 0, "empty": False, "quotas": [], "errors": [],
    })
    monkeypatch.setattr(diag, "collect_snapshot", lambda: {"schema_version": 1, "peers": [rec]})
    out = io.StringIO()
    assert diag.main(["--accounts"], stdout=out) == 0
    assert "greatgc@gmail.com" not in out.getvalue()


def test_git_project_status_degrades_on_failure(monkeypatch):
    diag = load_diag()

    def boom(*a, **k):
        raise OSError("git missing")
    monkeypatch.setattr(diag.subprocess, "run", boom)
    status = diag._git_project_status()  # must not raise
    assert status.get("state") in ("unknown", "clean", "dirty")


def test_tokens_view_is_null_safe(monkeypatch):
    diag = load_diag()
    rec = diag.normalize_peer({
        "peer": "cx", "source": "app-server", "cost": None, "total_tokens": None,
        "ctx_known": False, "ctx_window": 128000, "ctx_used": 0, "ctx_pct": None,
        "empty": False, "quotas": [], "errors": [],
    })
    monkeypatch.setattr(diag, "collect_snapshot", lambda: {"schema_version": 1, "peers": [rec]})
    out = io.StringIO()
    assert diag.main(["--tokens"], stdout=out) == 0  # no crash on nulls
    assert "cx" in out.getvalue().lower()
