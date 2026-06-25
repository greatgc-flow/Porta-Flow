"""M4 — dispatch coverage ratchet.

Prevents test-coverage rot: every hub.py dispatched action (`act == "..."`) must
have a direct test reference OR be in the KNOWN_UNTESTED allowlist. A NEW action
added without a test fails this meta-test. The allowlist may only SHRINK over time
(backfill a test for an action, then delete it from the allowlist).
"""
import re
from pathlib import Path

_CORE = Path(__file__).resolve().parents[2] / "core" / "hub.py"
_TESTS_DIR = Path(__file__).resolve().parent

# Actions known to lack direct test coverage as of 2026-06-25 (P1/M4 baseline).
# RULE: this set may only get SMALLER. Do NOT add to it — write a test instead.
KNOWN_UNTESTED = {
    "append-handoff", "approval-request", "assign-role", "check-gate", "discover",
    "file-lock", "file-unlock", "leader-yield", "lesson-inject", "lessons-list",
    "lock-status", "profile-validate", "proposal-list", "release-role", "role-status",
    "task-failover", "task-status", "thread-react",
}


def _dispatched_actions() -> set[str]:
    src = _CORE.read_text(encoding="utf-8")
    return set(re.findall(r'\bact\s*==\s*["\']([a-z][a-z0-9\-]+)["\']', src))


def _all_test_text() -> str:
    return "".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in _TESTS_DIR.glob("*.py")
        if p.name != "test_dispatch_coverage.py"
    )


def _untested(actions: set[str], test_text: str) -> set[str]:
    return {
        a for a in actions
        if a not in test_text and a.replace("-", "_") not in test_text
    }


def test_every_dispatched_action_has_test_or_is_allowlisted():
    """A dispatched action with no test and not on the allowlist fails the ratchet."""
    untested = _untested(_dispatched_actions(), _all_test_text())
    new_untested = untested - KNOWN_UNTESTED
    assert not new_untested, (
        f"New dispatched action(s) without a test: {sorted(new_untested)}. "
        f"Write a test (preferred) or — only if truly deferred — add to KNOWN_UNTESTED."
    )


def test_allowlist_only_shrinks_no_stale_entries():
    """Allowlist must not contain actions that are now tested or no longer dispatched
    (keeps the ratchet honest)."""
    actions = _dispatched_actions()
    test_text = _all_test_text()
    untested = _untested(actions, test_text)
    stale = {a for a in KNOWN_UNTESTED if a not in untested}
    assert not stale, (
        f"KNOWN_UNTESTED has stale entries (now tested or removed from dispatch): "
        f"{sorted(stale)}. Remove them from the allowlist."
    )
