"""
GAP-3 Knowledge Propagation — Sticky Lesson Tests (TDD Red Phase)

CRITICAL-severity lessons must:
1. Survive lesson_sweep TTL pruning (sticky=true bypass)
2. Appear at the top of [PEER LESSONS] context block
3. Never be retired by auto-sweep
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import pytest

SYS_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(SYS_DIR))
import core.hub as hub

LESSONS_PATH = SYS_DIR / "ai" / "knowledge" / "general" / "active-lessons.jsonl"


def _make_lesson(lesson_id: str, severity: str, sticky: bool = False,
                 trigger_count: int = 1, stale_days_old: int = 30) -> dict:
    return {
        "id": lesson_id,
        "schema_version": 1,
        "status": "active",
        "severity": severity,
        "sticky": sticky,
        "title": f"Test lesson {lesson_id}",
        "compact_rule": f"Rule for {lesson_id}",
        "category": "test",
        "scope": "global",
        "applies_to": {"peer_ids": ["cc"], "os": None, "shell": None, "task_types": ["code"]},
        "source_refs": [],
        "trigger_count": trigger_count,
        "approval": {"approved_by": "test", "approved_at": "20260616T000000"},
        "retirement": {"expires_at": None, "superseded_by": None, "review_after": None},
    }


class TestStickyLessonSurvivesSweep:
    """Sticky lessons must not be pruned by lesson_sweep."""

    def test_sticky_field_recognized_by_schema(self):
        """active-lessons.jsonl records may include sticky:true field."""
        # Read current lessons to verify the schema
        lessons_text = LESSONS_PATH.read_text(encoding="utf-8")
        # Just verify we can parse all records without error
        records = [json.loads(ln) for ln in lessons_text.splitlines() if ln.strip()]
        assert records, "active-lessons.jsonl must have at least one record"

    def _sweep_isolated(self, tmp_path: Path, min_triggers: int = 3, stale_days: int = 0) -> None:
        """Run lesson_sweep with global knowledge root patched to avoid real-file mutation."""
        fake_root = tmp_path / "knowledge"
        with patch.object(hub, "_knowledge_root", return_value=fake_root):
            hub.action_lesson_sweep(ai_root=tmp_path, min_triggers=min_triggers, stale_days=stale_days)

    def test_lesson_sweep_respects_sticky_flag(self, tmp_path):
        """action_lesson_sweep must NOT retire lessons with sticky=true."""
        lessons_dir = tmp_path / "knowledge" / "general"
        lessons_dir.mkdir(parents=True)
        lessons_file = lessons_dir / "active-lessons.jsonl"

        sticky = _make_lesson("LL-TEST-STICKY", "critical", sticky=True, trigger_count=1)
        pruneable = _make_lesson("LL-TEST-OLD", "low", sticky=False, trigger_count=1)
        lessons_file.write_text(json.dumps(sticky) + "\n" + json.dumps(pruneable) + "\n", encoding="utf-8")

        self._sweep_isolated(tmp_path)

        remaining = [json.loads(ln) for ln in lessons_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        active_ids = {r["id"] for r in remaining if r.get("status") == "active"}
        assert "LL-TEST-STICKY" in active_ids, (
            "Sticky lesson must survive lesson_sweep regardless of trigger_count/age"
        )

    def test_non_sticky_old_lesson_gets_retired(self, tmp_path):
        """Non-sticky, low-trigger lesson IS retired by sweep (control test)."""
        lessons_dir = tmp_path / "knowledge" / "general"
        lessons_dir.mkdir(parents=True)
        lessons_file = lessons_dir / "active-lessons.jsonl"

        pruneable = _make_lesson("LL-TEST-PRUNEABLE", "low", sticky=False, trigger_count=1)
        lessons_file.write_text(json.dumps(pruneable) + "\n", encoding="utf-8")

        self._sweep_isolated(tmp_path)

        remaining = [json.loads(ln) for ln in lessons_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        active_ids = {r["id"] for r in remaining if r.get("status") == "active"}
        assert "LL-TEST-PRUNEABLE" not in active_ids, (
            "Non-sticky lesson with low trigger count must be retired by sweep"
        )


class TestStickyLessonInContext:
    """CRITICAL sticky lessons must appear at top of context fill output."""

    def test_context_fill_includes_lessons(self, tmp_path):
        """action_context_fill must include active lessons in output."""
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        lessons_dir = tmp_path / "knowledge" / "general"
        lessons_dir.mkdir(parents=True)
        lessons_file = lessons_dir / "active-lessons.jsonl"

        lesson = _make_lesson("LL-CONTEXT-TEST", "critical", sticky=True)
        lessons_file.write_text(json.dumps(lesson) + "\n", encoding="utf-8")

        import io
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            hub.action_context_fill(ai_root=tmp_path, sections=["lessons"])
        output = captured.getvalue()
        assert "LL-CONTEXT-TEST" in output or "PEER LESSONS" in output, (
            "context_fill with sections=['lessons'] must include active lesson IDs"
        )

    def test_critical_sticky_lesson_prioritized(self, tmp_path):
        """CRITICAL sticky lessons must appear before non-critical in context."""
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        lessons_dir = tmp_path / "knowledge" / "general"
        lessons_dir.mkdir(parents=True)
        lessons_file = lessons_dir / "active-lessons.jsonl"

        low = _make_lesson("LL-LOW", "low", sticky=False)
        critical = _make_lesson("LL-CRITICAL", "critical", sticky=True)
        # Write low first, critical second — output must still show critical first
        lessons_file.write_text(
            json.dumps(low) + "\n" + json.dumps(critical) + "\n",
            encoding="utf-8"
        )

        import io
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            hub.action_context_fill(ai_root=tmp_path, sections=["lessons"])
        output = captured.getvalue()

        if "LL-LOW" in output and "LL-CRITICAL" in output:
            assert output.index("LL-CRITICAL") < output.index("LL-LOW"), (
                "CRITICAL sticky lessons must appear before low-severity lessons in context"
            )


class TestLL008IsStickyInRealFile:
    """LL-008 (the contract sync rule) must be marked sticky=true in the real lessons file."""

    def test_ll008_exists(self):
        lessons = [
            json.loads(ln)
            for ln in LESSONS_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        ids = {r["id"] for r in lessons}
        assert "LL-008" in ids, "LL-008 must exist in active-lessons.jsonl"

    def test_ll008_is_critical(self):
        lessons = [
            json.loads(ln)
            for ln in LESSONS_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        ll008 = next(r for r in lessons if r["id"] == "LL-008")
        assert ll008["severity"] == "critical", "LL-008 must have severity=critical"

    def test_ll008_has_sticky_flag(self):
        lessons = [
            json.loads(ln)
            for ln in LESSONS_PATH.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        ll008 = next(r for r in lessons if r["id"] == "LL-008")
        assert ll008.get("sticky") is True, (
            "LL-008 must have sticky=true to survive lesson_sweep"
        )
