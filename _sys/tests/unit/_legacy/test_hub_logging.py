"""Comprehensive tests for hub_logging.py — 7-type structured logging + rolling."""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))
import hub_logging
from hub_logging import HubLogger

# ── Fixtures ──────────────────────────────────────────────────────────────────

_MINIMAL_CONFIG = {
    "log_dir": "_sys/data/logs",
    "types": {
        "ipc-log":      {"file": "ipc-log.jsonl",      "max_mb": 50},
        "console-log":  {"file": "console-log.jsonl",   "max_mb": 20},
        "cost-log":     {"file": "cost-log.jsonl",       "max_mb": None},
        "error-log":    {"file": "error-log.jsonl",      "max_mb": 10},
        "reasoning-log":{"file": "reasoning-log.jsonl",  "max_mb": 30},
        "model-drift":  {"file": "model-drift.jsonl",    "max_mb": 5},
        "self-care-log":{"file": "self-care-log.jsonl",  "max_mb": 10},
    },
    "rolling": {
        "strategy": "size_and_age",
        "archive_dir": "archive",
        "archive_format": "{name}-{date}.jsonl.gz",
        "compress": True,
    },
}


def make_logger(tmp_path: Path, config: dict | None = None) -> HubLogger:
    cfg = config or _MINIMAL_CONFIG
    cfg_file = tmp_path / "logging-config.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")
    logger = HubLogger(config_path=cfg_file)
    logger._log_dir = tmp_path / "logs"
    logger._log_dir.mkdir(parents=True, exist_ok=True)
    return logger


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines if l.strip()]


# ── Config loading ────────────────────────────────────────────────────────────

class TestConfigLoading:
    def test_loads_valid_config(self, tmp_path):
        logger = make_logger(tmp_path)
        assert "ipc-log" in logger._cfg.get("types", {})

    def test_missing_config_returns_defaults(self, tmp_path):
        logger = HubLogger(config_path=tmp_path / "nonexistent.json")
        assert logger._cfg == {"types": {}, "rolling": {}}

    def test_invalid_json_returns_defaults(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid}", encoding="utf-8")
        logger = HubLogger(config_path=bad)
        assert logger._cfg == {"types": {}, "rolling": {}}

    def test_log_dir_created_on_init(self, tmp_path):
        cfg_file = tmp_path / "logging-config.json"
        cfg_file.write_text(json.dumps({"log_dir": "_sys/data/logs", "types": {}, "rolling": {}}), encoding="utf-8")
        # log_dir creation happens in __init__
        logger = HubLogger(config_path=cfg_file)
        assert logger._log_dir.is_dir()


# ── log_ipc ───────────────────────────────────────────────────────────────────

class TestLogIpc:
    def test_writes_jsonl_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send", query_preview="test query")
        records = read_jsonl(logger._log_dir / "ipc-log.jsonl")
        assert len(records) == 1

    def test_record_has_required_fields(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send", query_preview="hello")
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert rec["peer_id"] == "gc"
        assert rec["direction"] == "send"
        assert rec["_type"] == "ipc-log"
        assert "ts" in rec

    def test_query_preview_truncated_at_500(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send", query_preview="x" * 1000)
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert len(rec["query_preview"]) == 500

    def test_response_preview_truncated_at_500(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="cc", direction="receive", response_preview="r" * 800)
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert len(rec["response_preview"]) == 500

    def test_null_response_preview_stored_as_empty(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send")
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert rec["response_preview"] == ""

    def test_elapsed_sec_stored(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="receive", elapsed_sec=3.14)
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert rec["elapsed_sec"] == pytest.approx(3.14)

    def test_success_false_stored(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="cx", direction="send", success=False)
        rec = read_jsonl(logger._log_dir / "ipc-log.jsonl")[0]
        assert rec["success"] is False

    def test_multiple_records_appended(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send")
        logger.log_ipc(peer_id="cc", direction="receive")
        records = read_jsonl(logger._log_dir / "ipc-log.jsonl")
        assert len(records) == 2


# ── log_console ───────────────────────────────────────────────────────────────

class TestLogConsole:
    def test_writes_jsonl_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_console(message="hello user")
        records = read_jsonl(logger._log_dir / "console-log.jsonl")
        assert len(records) == 1

    def test_default_channel_and_level(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_console(message="test")
        rec = read_jsonl(logger._log_dir / "console-log.jsonl")[0]
        assert rec["channel"] == "user"
        assert rec["level"] == "INFO"

    def test_custom_channel_and_level(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_console(channel="debug", message="trace info", level="DEBUG")
        rec = read_jsonl(logger._log_dir / "console-log.jsonl")[0]
        assert rec["channel"] == "debug"
        assert rec["level"] == "DEBUG"


# ── log_cost ──────────────────────────────────────────────────────────────────

class TestLogCost:
    def test_writes_cost_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_cost(peer_id="gc", model_id="gemini-3-flash", cost_usd=0.002)
        records = read_jsonl(logger._log_dir / "cost-log.jsonl")
        assert len(records) == 1

    def test_all_optional_fields(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_cost(
            peer_id="cc", model_id="claude-sonnet-4-6",
            profile_id="cc.default", task_type="code_mutation",
            input_tokens=1000, output_tokens=200, reasoning_tokens=50,
            cost_usd=0.005, quality_score=8.5, latency_sec=12.3,
            success=True,
        )
        rec = read_jsonl(logger._log_dir / "cost-log.jsonl")[0]
        assert rec["input_tokens"] == 1000
        assert rec["output_tokens"] == 200
        assert rec["reasoning_tokens"] == 50
        assert rec["quality_score"] == pytest.approx(8.5)
        assert rec["latency_sec"] == pytest.approx(12.3)
        assert rec["profile_id"] == "cc.default"

    def test_null_cost_allowed(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_cost(peer_id="gc", model_id="gemini-3-flash")
        rec = read_jsonl(logger._log_dir / "cost-log.jsonl")[0]
        assert rec["cost_usd"] is None


# ── log_error ─────────────────────────────────────────────────────────────────

class TestLogError:
    def test_writes_error_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_error(error_type="PEER_TIMEOUT", tier="T2", peer="gc", message="timeout")
        records = read_jsonl(logger._log_dir / "error-log.jsonl")
        assert len(records) == 1

    def test_resolved_defaults_false(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_error(error_type="PEER_TIMEOUT", tier="T2", message="err")
        rec = read_jsonl(logger._log_dir / "error-log.jsonl")[0]
        assert rec["resolved"] is False

    def test_stacktrace_stored(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_error(error_type="HUB_INTERNAL", tier="T3", message="oops",
                         stacktrace="Traceback (most recent call last):\n  File x\nError: x")
        rec = read_jsonl(logger._log_dir / "error-log.jsonl")[0]
        assert "Traceback" in rec["stacktrace"]

    def test_5whys_template_stored(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_error(error_type="PEER_TIMEOUT", tier="T2", message="x",
                         whys_template="peer_timeout")
        rec = read_jsonl(logger._log_dir / "error-log.jsonl")[0]
        assert rec["5whys_template"] == "peer_timeout"

    def test_null_peer_allowed(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_error(error_type="HUB_INTERNAL", tier="T3", message="x")
        rec = read_jsonl(logger._log_dir / "error-log.jsonl")[0]
        assert rec["peer"] is None


# ── log_reasoning ─────────────────────────────────────────────────────────────

class TestLogReasoning:
    def test_writes_reasoning_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_reasoning(peer_id="cc", model_id="claude-opus-4-8", reasoning_tokens=2048)
        records = read_jsonl(logger._log_dir / "reasoning-log.jsonl")
        assert len(records) == 1

    def test_all_fields(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_reasoning(peer_id="cx", model_id="gpt-5.5", reasoning_tokens=5000,
                             budget_requested=8192, effort_level="high")
        rec = read_jsonl(logger._log_dir / "reasoning-log.jsonl")[0]
        assert rec["reasoning_tokens"] == 5000
        assert rec["budget_requested"] == 8192
        assert rec["effort_level"] == "high"


# ── log_model_drift ───────────────────────────────────────────────────────────

class TestLogModelDrift:
    def test_writes_drift_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_model_drift(model_id="gemini-2.5-pro", field="output_limit",
                               expected=24576, actual=65536)
        records = read_jsonl(logger._log_dir / "model-drift.jsonl")
        assert len(records) == 1

    def test_default_source(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_model_drift(model_id="x", field="context_limit", expected=1, actual=2)
        rec = read_jsonl(logger._log_dir / "model-drift.jsonl")[0]
        assert rec["source"] == "model-registry.json"

    def test_custom_source(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_model_drift(model_id="x", field="f", expected=1, actual=2, source="peers.json")
        rec = read_jsonl(logger._log_dir / "model-drift.jsonl")[0]
        assert rec["source"] == "peers.json"


# ── log_self_care ─────────────────────────────────────────────────────────────

class TestLogSelfCare:
    def test_writes_self_care_record(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_self_care(trigger="session_end", step="docs_mece", status="OK")
        records = read_jsonl(logger._log_dir / "self-care-log.jsonl")
        assert len(records) == 1

    def test_all_fields(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_self_care(trigger="manual", step="lesson_graduation",
                             status="FAIL", detail="no candidates", duration_sec=0.42)
        rec = read_jsonl(logger._log_dir / "self-care-log.jsonl")[0]
        assert rec["trigger"] == "manual"
        assert rec["step"] == "lesson_graduation"
        assert rec["status"] == "FAIL"
        assert rec["detail"] == "no candidates"
        assert rec["duration_sec"] == pytest.approx(0.42)

    def test_default_detail_is_empty(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_self_care(trigger="x", step="y", status="OK")
        rec = read_jsonl(logger._log_dir / "self-care-log.jsonl")[0]
        assert rec["detail"] == ""


# ── JSONL schema invariants ───────────────────────────────────────────────────

class TestJsonlInvariants:
    def test_all_records_have_ts_field(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send")
        logger.log_console(message="x")
        logger.log_error(error_type="PEER_TIMEOUT", tier="T2", message="x")
        for fname in ("ipc-log.jsonl", "console-log.jsonl", "error-log.jsonl"):
            for rec in read_jsonl(logger._log_dir / fname):
                assert "ts" in rec, f"Missing ts in {fname}"
                assert rec["ts"].endswith("Z"), f"ts not ISO8601 in {fname}"

    def test_all_records_have_type_field(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send")
        logger.log_cost(peer_id="gc", model_id="gemini-3-flash")
        for fname in ("ipc-log.jsonl", "cost-log.jsonl"):
            for rec in read_jsonl(logger._log_dir / fname):
                assert "_type" in rec

    def test_records_are_valid_json(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_ipc(peer_id="gc", direction="send", query_preview='with "quotes" and \nnewlines')
        path = logger._log_dir / "ipc-log.jsonl"
        for line in path.read_text(encoding="utf-8").strip().splitlines():
            # Should not raise
            json.loads(line)

    def test_unicode_preserved(self, tmp_path):
        logger = make_logger(tmp_path)
        logger.log_console(message="한국어 메시지")
        rec = read_jsonl(logger._log_dir / "console-log.jsonl")[0]
        assert "한국어" in rec["message"]


# ── Rolling / gzip archive ────────────────────────────────────────────────────

class TestRollingPolicy:
    def _tiny_max_config(self, max_kb: float = 0.0001) -> dict:
        cfg = dict(_MINIMAL_CONFIG)
        cfg["types"] = dict(cfg["types"])
        cfg["types"]["ipc-log"] = {"file": "ipc-log.jsonl", "max_mb": max_kb / 1024}
        return cfg

    def test_roll_creates_archive_dir(self, tmp_path):
        logger = make_logger(tmp_path, self._tiny_max_config())
        logger.log_ipc(peer_id="gc", direction="send", query_preview="trigger roll")
        archive_dir = logger._log_dir / "archive"
        # Archive dir should exist (may not roll if file is tiny, but dir check)
        logger._roll("ipc-log", logger._log_dir / "ipc-log.jsonl")
        assert archive_dir.is_dir()

    def test_roll_creates_gzip_archive(self, tmp_path):
        logger = make_logger(tmp_path)
        log_path = logger._log_dir / "ipc-log.jsonl"
        log_path.write_text(json.dumps({"ts": "2026-06-18T00:00:00Z", "_type": "ipc-log"}) + "\n",
                            encoding="utf-8")
        logger._roll("ipc-log", log_path)
        archive_dir = logger._log_dir / "archive"
        archives = list(archive_dir.glob("ipc-log-*.jsonl.gz"))
        assert len(archives) == 1

    def test_roll_archive_is_valid_gzip(self, tmp_path):
        logger = make_logger(tmp_path)
        original_content = json.dumps({"ts": "2026-06-18T00:00:00Z", "_type": "ipc-log"}) + "\n"
        log_path = logger._log_dir / "ipc-log.jsonl"
        log_path.write_text(original_content, encoding="utf-8")
        logger._roll("ipc-log", log_path)
        archive_dir = logger._log_dir / "archive"
        gz_file = list(archive_dir.glob("*.gz"))[0]
        with gzip.open(str(gz_file), "rb") as f:
            content = f.read().decode("utf-8")
        assert '"ipc-log"' in content

    def test_roll_removes_original_file(self, tmp_path):
        logger = make_logger(tmp_path)
        log_path = logger._log_dir / "ipc-log.jsonl"
        log_path.write_text('{"x":1}\n', encoding="utf-8")
        logger._roll("ipc-log", log_path)
        assert not log_path.exists()

    def test_no_roll_when_max_mb_is_none(self, tmp_path):
        logger = make_logger(tmp_path)
        # cost-log has max_mb=None — write many records, should not roll
        for _ in range(5):
            logger.log_cost(peer_id="gc", model_id="gemini-3-flash")
        log_path = logger._log_dir / "cost-log.jsonl"
        assert log_path.exists()
        # Archive should be empty
        archive_dir = logger._log_dir / "archive"
        archives = list(archive_dir.glob("cost-log-*.gz")) if archive_dir.exists() else []
        assert archives == []

    def test_roll_uncompressed_when_compress_false(self, tmp_path):
        cfg = dict(_MINIMAL_CONFIG)
        cfg["rolling"] = dict(cfg["rolling"])
        cfg["rolling"]["compress"] = False
        cfg["rolling"]["archive_format"] = "{name}-{date}.jsonl"
        logger = make_logger(tmp_path, cfg)
        log_path = logger._log_dir / "ipc-log.jsonl"
        log_path.write_text('{"x":1}\n', encoding="utf-8")
        logger._roll("ipc-log", log_path)
        archive_dir = logger._log_dir / "archive"
        archives = list(archive_dir.glob("ipc-log-*.jsonl"))
        assert len(archives) == 1

    def test_maybe_roll_triggers_when_over_limit(self, tmp_path):
        logger = make_logger(tmp_path)
        log_path = logger._log_dir / "ipc-log.jsonl"
        # Write 60MB of data conceptually by mocking stat
        log_path.write_text('{"x":1}\n', encoding="utf-8")
        tcfg = {"file": "ipc-log.jsonl", "max_mb": 0.000001}  # 1 byte limit
        rolled = []
        original_roll = logger._roll
        logger._roll = lambda lt, lp: rolled.append((lt, lp))
        logger._maybe_roll("ipc-log", log_path, tcfg)
        assert len(rolled) == 1

    def test_maybe_roll_no_op_when_under_limit(self, tmp_path):
        logger = make_logger(tmp_path)
        log_path = logger._log_dir / "ipc-log.jsonl"
        log_path.write_text('{"x":1}\n', encoding="utf-8")
        tcfg = {"file": "ipc-log.jsonl", "max_mb": 100}
        rolled = []
        logger._roll = lambda lt, lp: rolled.append((lt, lp))
        logger._maybe_roll("ipc-log", log_path, tcfg)
        assert rolled == []


# ── OSError handling ─────────────────────────────────────────────────────────

class TestOsErrorHandling:
    def test_write_error_does_not_raise(self, tmp_path, capsys):
        logger = make_logger(tmp_path)
        # Make log dir read-only to force OSError
        logger._log_dir = Path("/nonexistent/path/that/does/not/exist")
        # Should not raise, should print to stderr
        logger.log_console(message="test")
        # No exception = pass

    def test_roll_oserror_does_not_raise(self, tmp_path):
        logger = make_logger(tmp_path)
        # Roll a non-existent file — should not raise
        logger._roll("ipc-log", tmp_path / "nonexistent.jsonl")


# ── _type_cfg fallback ────────────────────────────────────────────────────────

class TestTypeCfgFallback:
    def test_unknown_type_returns_empty_dict(self, tmp_path):
        logger = make_logger(tmp_path)
        result = logger._type_cfg("unknown-type-xyz")
        assert result == {}

    def test_known_type_returns_config(self, tmp_path):
        logger = make_logger(tmp_path)
        result = logger._type_cfg("ipc-log")
        assert "file" in result
        assert result["file"] == "ipc-log.jsonl"
