"""Tests for hub_context.py — ContextGate v1.0 and token estimation."""
import json
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "core"))

from hub_context import estimate_tokens, ContextGate, ContextGateError, _FAILOVER_CHAIN


# ── estimate_tokens ───────────────────────────────────────────────────────────

class TestEstimateTokens:
    def test_ascii_text_uses_3_5_divisor(self):
        text = "a" * 350
        assert estimate_tokens(text) == 100

    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_cjk_heavy_text_uses_1_8_multiplier(self):
        # 100 Korean chars (100% CJK) → len/2 * 1.8 = 50 * 1.8 = 90
        text = "가" * 100
        tokens = estimate_tokens(text)
        assert tokens == 90

    def test_mixed_text_below_20pct_cjk_uses_ascii_path(self):
        # 10 CJK + 90 ASCII = 10% CJK → ascii path → 100/3.5 ≈ 28
        text = "가" * 10 + "a" * 90
        tokens = estimate_tokens(text)
        expected = int(100 / 3.5)
        assert tokens == expected

    def test_mixed_text_above_20pct_cjk_uses_cjk_path(self):
        # 25 CJK + 75 ASCII = 25% CJK → CJK path → int(100/2 * 1.8) = 90
        text = "가" * 25 + "a" * 75
        tokens = estimate_tokens(text)
        expected = int(100 / 2 * 1.8)
        assert tokens == expected

    def test_exactly_20pct_cjk_uses_cjk_path(self):
        # 20 CJK + 80 ASCII = exactly 20% → CJK path
        text = "가" * 20 + "a" * 80
        tokens = estimate_tokens(text)
        expected = int(100 / 2 * 1.8)
        assert tokens == expected


# ── ContextGate (config via tmp_path files) ───────────────────────────────────

_GOVERNANCE_DATA = {
    "context_gate_enabled": True,
    "context_gate_warn_pct": 0.80,
    "context_gate_failover_pct": 0.95,
}

_REGISTRY_DATA = {
    "models": {
        "claude-sonnet-4-6": {"context_limit": 1000000, "output_limit": 128000},
        "gemini-3-flash": {"context_limit": 1000000, "output_limit": 65536},
        "claude-haiku-4-5-20251001": {"context_limit": 200000, "output_limit": 128000},
    }
}


def _make_gate(tmp_path, governance=None, registry=None):
    gov = governance if governance is not None else _GOVERNANCE_DATA
    reg = registry if registry is not None else _REGISTRY_DATA

    gov_file = tmp_path / "governance_params.json"
    reg_file = tmp_path / "model-registry.json"
    gov_file.write_text(json.dumps(gov), encoding="utf-8")
    reg_file.write_text(json.dumps(reg), encoding="utf-8")
    return ContextGate(governance_path=gov_file, registry_path=reg_file)


class TestContextGateCheck:
    def test_small_query_returns_pass(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check("hello world", "claude-sonnet-4-6")
        assert result["action"] == "pass"

    def test_disabled_gate_always_passes(self, tmp_path):
        gov = {"context_gate_enabled": False, "context_gate_warn_pct": 0.80, "context_gate_failover_pct": 0.95}
        gate = _make_gate(tmp_path, governance=gov)
        result = gate.check("x" * 999999, "claude-sonnet-4-6")
        assert result["action"] == "pass"

    def test_unknown_model_uses_default_200k_limit(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check("hello", "unknown-model-xyz")
        assert result["action"] in ("pass", "prune", "failover", "reject")
        assert result["context_limit"] == 200_000  # default fallback

    def test_warn_threshold_triggers_prune(self, tmp_path):
        gate = _make_gate(tmp_path)
        # claude-haiku context_limit = 200k tokens → 80% warn = 160k
        # ASCII: 160k * 3.5 = 560k chars → use 570k to exceed warn
        long_text = "a" * 570_000
        result = gate.check(long_text, "claude-haiku-4-5-20251001")
        assert result["action"] in ("prune", "failover", "reject")

    def test_failover_chain_sonnet_has_haiku(self):
        assert "claude-sonnet-4-6" in _FAILOVER_CHAIN
        assert _FAILOVER_CHAIN["claude-sonnet-4-6"] == "claude-haiku-4-5-20251001"

    def test_utilization_in_result(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check("hello world", "claude-sonnet-4-6")
        assert "utilization" in result
        assert 0.0 <= result["utilization"] <= 1.0

    def test_context_limit_in_result(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check("hello", "claude-sonnet-4-6")
        assert result.get("context_limit") == 1_000_000

    def test_result_keys_present(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check("test", "claude-sonnet-4-6")
        for key in ("action", "estimated_tokens", "context_limit", "warn_threshold",
                    "failover_threshold", "utilization", "model_id", "failover_model"):
            assert key in result, f"Missing key: {key}"

    def test_failover_action_on_near_limit(self, tmp_path):
        # haiku has 200k limit; 95% = 190k; ASCII 190k * 3.5 = 665k chars
        gate = _make_gate(tmp_path)
        long_text = "a" * 680_000
        try:
            result = gate.check(long_text, "claude-haiku-4-5-20251001")
            # haiku not in _FAILOVER_CHAIN → reject (raises) or reject action
            assert result["action"] in ("reject", "failover")
        except ContextGateError:
            pass  # expected when no failover available


class TestContextGateCheckAndPrune:
    def test_small_blocks_all_survive(self, tmp_path):
        gate = _make_gate(tmp_path)
        blocks = [
            {"priority": 1, "text": "a" * 10, "label": "low"},
            {"priority": 10, "text": "b" * 10, "label": "high"},
        ]
        result = gate.check_and_prune(blocks, "claude-sonnet-4-6",
                                       priority_key="priority", text_key="text")
        assert len(result) == 2

    def test_prune_removes_low_priority_first(self, tmp_path):
        gate = _make_gate(tmp_path)
        # haiku 200k limit → target 75% = 150k tokens → 150k * 3.5 = 525k chars per block
        # Create blocks that together exceed limit
        blocks = [
            {"priority": 1, "text": "a" * 200_000, "label": "low"},
            {"priority": 10, "text": "b" * 200_000, "label": "high"},
            {"priority": 5, "text": "c" * 200_000, "label": "mid"},
        ]
        result = gate.check_and_prune(blocks, "claude-haiku-4-5-20251001",
                                       priority_key="priority", text_key="text")
        labels = [b["label"] for b in result]
        # High priority should survive if any are removed
        if len(result) < 3:
            assert "high" in labels

    def test_empty_blocks_returns_empty(self, tmp_path):
        gate = _make_gate(tmp_path)
        result = gate.check_and_prune([], "claude-sonnet-4-6",
                                       priority_key="priority", text_key="text")
        assert result == []


class TestContextGateError:
    def test_is_runtime_error(self):
        err = ContextGateError(estimated_tokens=900_000, context_limit=200_000, model_id="haiku")
        assert isinstance(err, RuntimeError)

    def test_message_contains_reject(self):
        err = ContextGateError(estimated_tokens=900_000, context_limit=200_000, model_id="haiku")
        assert "CONTEXT_GATE_REJECT" in str(err)

    def test_attributes_accessible(self):
        err = ContextGateError(estimated_tokens=500, context_limit=200_000, model_id="test-model")
        assert err.estimated_tokens == 500
        assert err.context_limit == 200_000
        assert err.model_id == "test-model"
        assert err.error_type == "CONTEXT_GATE_REJECT"

    def test_tier_is_t2(self):
        err = ContextGateError(1, 200_000, "m")
        assert err.tier == "T2"
