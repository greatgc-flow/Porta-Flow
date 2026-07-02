"""Comprehensive tests for hub_error.py — taxonomy-driven error visibility."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))
import hub_error
from hub_error import HubError, report_error

# ── Test taxonomy + governance ────────────────────────────────────────────────

_TAXONOMY = {
    "tiers": {
        "T0": {"label": "ignore",  "log": False, "console": False, "peer_escalate": False, "halt": False},
        "T1": {"label": "info",    "log": True,  "console": False, "peer_escalate": False, "halt": False},
        "T2": {"label": "warn",    "log": True,  "console": True,  "peer_escalate": False, "halt": False},
        "T3": {"label": "error",   "log": True,  "console": True,  "peer_escalate": True,  "halt": False},
        "T4": {"label": "fatal",   "log": True,  "console": True,  "peer_escalate": True,  "halt": True},
    },
    "errors": {
        "PEER_TIMEOUT":        {"tier": "T2", "category": "peer", "5whys": "peer_timeout"},
        "PEER_RATE_LIMIT":     {"tier": "T2", "category": "peer", "5whys": "resource_limit"},
        "PEER_RED_GATE":       {"tier": "T2", "category": "peer", "5whys": "health_degraded"},
        "PEER_NOT_FOUND":      {"tier": "T2", "category": "peer"},
        "PEER_REFUSAL":        {"tier": "T1", "category": "peer"},
        "CONFIG_NOT_FOUND":    {"tier": "T3", "category": "config", "5whys": "config_missing"},
        "CONFIG_INVALID":      {"tier": "T3", "category": "config"},
        "ROUTING_NO_ELIGIBLE": {"tier": "T3", "category": "routing"},
        "CONTEXT_GATE_REJECT": {"tier": "T2", "category": "context"},
        "CONSENSUS_TIMEOUT":   {"tier": "T3", "category": "consensus"},
        "CONSENSUS_DEADLOCK":  {"tier": "T3", "category": "consensus"},
        "INV_VIOLATION":       {"tier": "T4", "category": "governance"},
        "DOCS_MECE_FAIL":      {"tier": "T3", "category": "docs"},
        "HUB_INTERNAL":        {"tier": "T3", "category": "hub"},
        "WORKSPACE_INIT_FAIL": {"tier": "T3", "category": "workspace"},
    },
    "5whys_templates": {
        "peer_timeout": ["Was the peer process running?", "Was the network reachable?", "Did hub.py health-check pass?"],
        "resource_limit": ["Is the daily quota exhausted?", "Is there a cost spike?"],
        "health_degraded": ["Is health.json showing RED?", "Did consecutive failures exceed threshold?"],
        "config_missing": ["Does the file exist?", "Was workspace-init run?"],
    }
}

_GOVERNANCE = {
    "error_show_stacktrace": True,
    "error_5whys_auto_log": True,
    "error_escalate_after_n": 2,
}


def _reset_cache():
    HubError._taxonomy = None
    HubError._gov = None


def make_context(taxonomy=None, governance=None):
    tax = taxonomy or _TAXONOMY
    gov = governance or _GOVERNANCE
    return patch.multiple(
        HubError,
        _get_taxonomy=classmethod(lambda cls: tax),
        _get_gov=classmethod(lambda cls: gov),
    )


# ── report() basic ────────────────────────────────────────────────────────────

class TestReport:
    def setup_method(self):
        _reset_cache()

    def test_returns_record_dict(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("PEER_TIMEOUT", peer="gc", message="timeout")
        assert isinstance(record, dict)
        assert record["error_type"] == "PEER_TIMEOUT"

    def test_record_has_tier(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("PEER_TIMEOUT", peer="gc", message="timeout")
        assert record["tier"] == "T2"

    def test_unknown_error_type_defaults_to_t2(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("NONEXISTENT_TYPE", message="x")
        assert record["tier"] == "T2"

    def test_peer_and_action_stored(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("PEER_TIMEOUT", peer="gc", action="action_ask", message="x")
        assert record["peer"] == "gc"
        assert record["action"] == "action_ask"

    def test_extra_dict_merged_into_record(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("PEER_TIMEOUT", message="x", extra={"custom_key": "custom_val"})
        assert record.get("custom_key") == "custom_val"

    def test_exc_stacktrace_included_when_show_stacktrace_true(self, capsys):
        gov = dict(_GOVERNANCE)
        gov["error_show_stacktrace"] = True
        try:
            raise ValueError("test exception")
        except ValueError as exc:
            with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
                 patch.object(HubError, "_get_gov", return_value=gov), \
                 patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
                record = HubError.report("PEER_TIMEOUT", message="x", exc=exc)
        assert record["stacktrace"] is not None
        assert "ValueError" in record["stacktrace"]

    def test_exc_stacktrace_omitted_when_show_stacktrace_false(self, capsys):
        gov = dict(_GOVERNANCE)
        gov["error_show_stacktrace"] = False
        try:
            raise ValueError("test exception")
        except ValueError as exc:
            with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
                 patch.object(HubError, "_get_gov", return_value=gov), \
                 patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
                record = HubError.report("PEER_TIMEOUT", message="x", exc=exc)
        assert record["stacktrace"] is None

    def test_no_exc_stacktrace_is_none(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            record = HubError.report("PEER_TIMEOUT", message="x")
        assert record["stacktrace"] is None


# ── Console display ───────────────────────────────────────────────────────────

class TestConsoleDisplay:
    def setup_method(self):
        _reset_cache()

    def test_t2_displays_to_stderr(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", peer="gc", message="timeout test")
        captured = capsys.readouterr()
        assert "경고" in captured.err or "T2" in captured.err

    def test_t1_does_not_display_to_stderr(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_REFUSAL", message="refused")
        captured = capsys.readouterr()
        # T1 console=False → nothing printed
        assert captured.err.strip() == ""

    def test_peer_shown_in_display(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", peer="gc", message="timeout")
        captured = capsys.readouterr()
        assert "gc" in captured.err

    def test_error_type_shown_in_display(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="timeout")
        captured = capsys.readouterr()
        assert "PEER_TIMEOUT" in captured.err

    def test_message_shown_in_display(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="unique message xyz789")
        captured = capsys.readouterr()
        assert "unique message xyz789" in captured.err

    def test_5whys_shown_when_enabled(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="x")
        captured = capsys.readouterr()
        assert "Was the peer process running?" in captured.err

    def test_5whys_hidden_when_disabled(self, capsys):
        gov = dict(_GOVERNANCE)
        gov["error_5whys_auto_log"] = False
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=gov), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="x")
        captured = capsys.readouterr()
        assert "Was the peer process running?" not in captured.err

    def test_separator_lines_in_display(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="x")
        captured = capsys.readouterr()
        assert "━" in captured.err

    def test_null_peer_shown_as_dash(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="x")
        captured = capsys.readouterr()
        assert "피어" in captured.err


# ── T4 halt ───────────────────────────────────────────────────────────────────

class TestT4Halt:
    def setup_method(self):
        _reset_cache()

    def test_t4_calls_sys_exit_4(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)), \
             pytest.raises(SystemExit) as exc_info:
            HubError.report("INV_VIOLATION", message="invariant broken")
        assert exc_info.value.code == 4

    def test_t2_does_not_exit(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            # Should not raise SystemExit
            HubError.report("PEER_TIMEOUT", message="x")


# ── report_from_legacy ────────────────────────────────────────────────────────

class TestReportFromLegacy:
    def setup_method(self):
        _reset_cache()

    def test_exact_match_pattern(self, capsys):
        reported = []
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "report",
                          classmethod(lambda cls, et, **kw: reported.append(et) or {})):
            HubError.report_from_legacy("gc", "PEER_TIMEOUT", "timeout", "warn")
        assert "PEER_TIMEOUT" in reported

    def test_severity_error_maps_to_hub_internal(self, capsys):
        reported = []
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "report",
                          classmethod(lambda cls, et, **kw: reported.append(et) or {})):
            HubError.report_from_legacy("gc", "some_unknown_pattern", "", "error")
        assert reported[0] == "HUB_INTERNAL"

    def test_severity_warn_maps_to_peer_timeout(self, capsys):
        reported = []
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "report",
                          classmethod(lambda cls, et, **kw: reported.append(et) or {})):
            HubError.report_from_legacy("gc", "no_match_pattern", "", "warn")
        assert reported[0] == "PEER_TIMEOUT"


# ── _severity_to_error_type ───────────────────────────────────────────────────

class TestSeverityToErrorType:
    def setup_method(self):
        _reset_cache()

    def test_exact_match_returned_directly(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            result = HubError._severity_to_error_type("PEER_TIMEOUT", "warn")
        assert result == "PEER_TIMEOUT"

    def test_case_insensitive_pattern(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            result = HubError._severity_to_error_type("peer_timeout", "warn")
        assert result == "PEER_TIMEOUT"

    def test_hyphen_normalized_to_underscore(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            result = HubError._severity_to_error_type("peer-timeout", "warn")
        assert result == "PEER_TIMEOUT"

    def test_severity_error_fallback(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            result = HubError._severity_to_error_type("totally_unknown", "error")
        assert result == "HUB_INTERNAL"

    def test_severity_info_fallback(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            result = HubError._severity_to_error_type("totally_unknown", "info")
        assert result == "PEER_REFUSAL"


# ── Remediation hints ─────────────────────────────────────────────────────────

class TestRemediationHints:
    def setup_method(self):
        _reset_cache()

    def test_peer_timeout_has_hint(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            hint = HubError._remediation_hint("PEER_TIMEOUT")
        assert hint != ""

    def test_unknown_error_returns_empty(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            hint = HubError._remediation_hint("TOTALLY_UNKNOWN_TYPE")
        assert hint == ""

    def test_hint_shown_in_display(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            HubError.report("PEER_TIMEOUT", message="x")
        captured = capsys.readouterr()
        assert "해결" in captured.err


# ── 5whys template lookup ────────────────────────────────────────────────────

class TestWhysTemplate:
    def setup_method(self):
        _reset_cache()

    def test_known_key_returns_list(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            whys = HubError._whys_template("peer_timeout")
        assert isinstance(whys, list)
        assert len(whys) >= 1

    def test_unknown_key_returns_empty_list(self):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY):
            whys = HubError._whys_template("nonexistent_template")
        assert whys == []


# ── Logging integration ───────────────────────────────────────────────────────

class TestLoggingIntegration:
    def setup_method(self):
        _reset_cache()

    def test_log_error_called_on_report(self):
        logged = []
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: logged.append(r))):
            HubError.report("PEER_TIMEOUT", message="x")
        assert len(logged) == 1

    def test_logging_failure_does_not_propagate(self):
        def _raise(r):
            raise Exception("log fail")

        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch("hub_logging.HubLogger.log_error", side_effect=Exception("log fail")):
            # hub_error._log_error has try/except — should not propagate
            HubError.report("PEER_TIMEOUT", message="x")


# ── report_error convenience function ────────────────────────────────────────

class TestReportErrorFunction:
    def setup_method(self):
        _reset_cache()

    def test_module_level_shortcut(self, capsys):
        with patch.object(HubError, "_get_taxonomy", return_value=_TAXONOMY), \
             patch.object(HubError, "_get_gov", return_value=_GOVERNANCE), \
             patch.object(HubError, "_log_error", classmethod(lambda cls, r: None)):
            result = report_error("PEER_TIMEOUT", peer="gc", message="test")
        assert isinstance(result, dict)
        assert result["error_type"] == "PEER_TIMEOUT"


# ── Caching behavior ─────────────────────────────────────────────────────────

class TestCaching:
    def setup_method(self):
        _reset_cache()

    def test_taxonomy_cached_after_first_load(self, tmp_path):
        _reset_cache()
        # Load taxonomy once
        tax_path = tmp_path / "error-taxonomy.json"
        tax_path.write_text(json.dumps(_TAXONOMY), encoding="utf-8")
        with patch.object(hub_error, "_TAXONOMY_PATH", tax_path):
            t1 = HubError._get_taxonomy()
            t2 = HubError._get_taxonomy()
        assert t1 is t2  # Same object = cached

    def test_reset_clears_cache(self):
        _reset_cache()
        assert HubError._taxonomy is None
        assert HubError._gov is None
