import json
import pytest
from pathlib import Path
import hub

# ── Mock Config for TDD ──
MOCK_BIVCA_CONFIG = {
    "cortex_hard_cap": 10,
    "hippocampus_soft_cap": 5,
    "decay_rate_per_day": 0.05,
    "promotion_weight_threshold": 0.8,
    "retirement_weight_threshold": 0.2,
    "exception_ttl_days": 7
}

def test_zero_token_shorthand_extraction(tmp_path):
    """Test that [LEARN: ...] markers are correctly extracted from peer responses."""
    response_text = "Here is the code. [LEARN: Windows requires os.replace for atomic writes] Also, [LEARN: Never use shell=True unnecessarily]"
    
    extracted = hub._extract_shorthand_lessons("gc", response_text)
    
    assert len(extracted) == 2
    assert "Windows requires os.replace" in extracted[0]["content"]
    assert "Never use shell=True" in extracted[1]["content"]
    assert extracted[0]["status"] == "proposed"
    assert extracted[0]["source"] == "gc"

def test_context_builder_hard_caps(tmp_path):
    """Test that context builder respects the JSON-configured hard caps."""
    # Create 15 critical lessons (over the mock cap of 10)
    critical_lessons = [{"id": f"LL-{i}", "weight": 0.9, "domain_tags": ["general"]} for i in range(15)]
    
    # Simulate the context building (we will pass the mock config limit)
    capped_lessons = hub._apply_hard_cap(critical_lessons, max_cap=10)
    
    assert len(capped_lessons) == 10
    # Should keep the ones with highest weights (we didn't vary weights here, but cap should work)

def test_auto_focus_inference():
    """Test that active alerts correctly infer focus tags for the Hippocampus."""
    active_alerts = [
        {"severity": "P1", "domain_tags": ["pytest", "testing"]},
        {"severity": "P0", "domain_tags": ["security", "auth"]}
    ]
    
    inferred_tags = hub._infer_focus_tags(active_alerts)
    
    assert "pytest" in inferred_tags
    assert "security" in inferred_tags
    assert "testing" in inferred_tags
    assert len(inferred_tags) == 4

def test_exception_ttl_violation_triggers_alert(tmp_path):
    """Test that an exception older than its resolve_by date triggers a P0 alert."""
    from datetime import datetime, timedelta
    
    past_date = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S")
    exception_data = {
        "id": "EXC-001",
        "resolve_by": past_date,
        "status": "pending"
    }
    
    is_violated, reason = hub._check_exception_ttl(exception_data)
    
    assert is_violated is True
    assert "EXC-001" in reason
    assert "expired" in reason
