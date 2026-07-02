import pytest
from unittest.mock import patch
from pathlib import Path
import sys

# Fix import path for core module
sys.path.insert(0, str(Path(r"P:\_sys\core").resolve()))

class MockToolCall:
    def __init__(self, tool_name, args, is_read_only=False):
        self.tool_name = tool_name
        self.args = args
        self._is_read_only = is_read_only
        
    def is_read_only(self):
        return self._is_read_only

class MockReviewResult:
    def __init__(self, vote, reason):
        self.vote = vote      # 'AGREE', 'DISAGREE', or 'ABSTAIN'
        self.reason = reason

def test_hub_intercepts_unilateral_action():
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [MockReviewResult("AGREE", "Looks MECE.")]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx"], collab_rate=10)
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}))
        mock_broadcast.assert_called_once()
        assert result.status == "APPROVED"

def test_hub_handles_disagreement_and_feedback():
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [MockReviewResult("DISAGREE", "Missing Edge Case X.")]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx"], collab_rate=10)
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}))
        assert result.status == "REJECTED_WITH_FEEDBACK"
        assert "Missing Edge Case X." in result.feedback

def test_hub_enforces_anti_sycophancy_and_tiebreaker():
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [MockReviewResult("DISAGREE", "Flawed.")]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx"], max_rounds=3, collab_rate=10)
        interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}), round_num=1)
        interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}), round_num=2)
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}), round_num=3)
        assert result.status == "ESCALATE_TO_USER"

# --- NEW EDGE CASE TESTS ---

def test_n1_isolation_read_vs_write():
    from hub_interceptor import HubInterceptor
    interceptor = HubInterceptor(active_peers=["cc"], collab_rate=10) # Only 1 peer
    
    # Read action should auto-approve
    read_action = MockToolCall("view_file", {}, is_read_only=True)
    res_read = interceptor.evaluate_action("cc", read_action)
    assert res_read.status == "APPROVED"
    
    # Write action must escalate to user (HITL) because no reviewers exist
    write_action = MockToolCall("write_to_file", {}, is_read_only=False)
    res_write = interceptor.evaluate_action("cc", write_action)
    assert res_write.status == "ESCALATE_TO_USER"
    assert "N=1" in res_write.feedback

def test_n2_tie_breaker():
    """N=2, 1v1 scenario. Quorum is 2. 1 Approve (Primary), 1 Reject (Reviewer)."""
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [MockReviewResult("DISAGREE", "I disagree")]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx"], collab_rate=10)
        
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}))
        # Must be rejected because quorum (2) is not met
        assert result.status == "REJECTED_WITH_FEEDBACK"

def test_reviewer_timeout_abstain_collab_5():
    """collab_rate=5: N=3. 1 Primary, 1 Approve, 1 Abstain (Timeout). Quorum is 2, so Approved."""
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [
            MockReviewResult("AGREE", "Good"),
            MockReviewResult("ABSTAIN", "Timeout")
        ]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx", "ag"], collab_rate=5)
        
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}))
        assert result.status == "APPROVED"

def test_reviewer_timeout_abstain_collab_10():
    """collab_rate=10: N=3. 1 Primary, 1 Approve, 1 Abstain (Timeout). R:10 requires Unanimity, so Escalates."""
    with patch("hub_interceptor.HubInterceptor.broadcast_for_review") as mock_broadcast:
        mock_broadcast.return_value = [
            MockReviewResult("AGREE", "Good"),
            MockReviewResult("ABSTAIN", "Timeout")
        ]
        from hub_interceptor import HubInterceptor
        interceptor = HubInterceptor(active_peers=["cc", "cx", "ag"], collab_rate=10)
        
        result = interceptor.evaluate_action("cc", MockToolCall("write_to_file", {}))
        # Under R:10, an Abstain fails unanimity and falls back to HITL.
        assert result.status == "ESCALATE_TO_USER"
        assert "Unanimity required" in result.feedback
