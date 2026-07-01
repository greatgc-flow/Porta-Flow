import importlib.util
import io
import json
import sys
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


# ── TDD slice 1: normalized telemetry record (§4/§13.1) ─────────────────────────

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


# ── TDD slice 2: redaction (§5) ─────────────────────────────────────────────────

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
