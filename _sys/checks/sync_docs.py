#!/usr/bin/env python3
"""
runtime/ops/sync-docs.py — DocsSyncer (Master Plan §3)

Reads .capsule.json files from .ai/consensus/, updates docs-v2 files
based on approved_scope, cites the capsule round_id, and blocks on
normative claims without citation.

Exit codes:
  0  All capsules applied (or nothing to do).
  1  Runtime error (I/O, bad JSON, missing path).
  2  DOCS_SYNC_NEEDS_HUMAN — normative claim in capsule lacks valid citation anchor.

Usage:
  python sync-docs.py [--dry-run] [--force] [--consensus-dir DIR] [--docs-dir DIR]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CAPSULE_GLOB = "*.capsule.json"
SYNC_LOG_NAME = "sync_log.jsonl"
SYNC_HISTORY_START = "<!-- SYNC_HISTORY_START -->"
SYNC_HISTORY_END = "<!-- SYNC_HISTORY_END -->"

# RFC 2119 normative keywords that require a capsule citation
NORMATIVE_RE = re.compile(
    r"\b(MUST(?: NOT)?|SHALL(?: NOT)?|SHOULD(?: NOT)?|REQUIRED|RECOMMENDED|MAY)\b"
)

# Inline citation marker written by this script
CITATION_RE = re.compile(r"<!--\s*capsule:r-[0-9a-f]+\s*-->")


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Walk up from this file to find the repo root (contains _sys/)."""
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "_sys").is_dir():
            return parent
    # Fallback: assume script lives at _sys/checks/sync-docs.py
    return here.parents[2]


def _resolve_paths(
    consensus_dir: str | None,
    docs_dir: str | None,
) -> tuple[Path, Path, Path, Path]:
    """Returns (consensus_dir, docs_dir, log_file, repo_root)."""
    root = _repo_root()
    c_dir = Path(consensus_dir).resolve() if consensus_dir else root / ".ai" / "consensus"
    d_dir = Path(docs_dir).resolve() if docs_dir else root / "_sys" / "docs-v2"
    log_file = c_dir / SYNC_LOG_NAME
    # repo_root: two levels above consensus (.ai/consensus -> .ai -> root)
    repo_root = c_dir.parent.parent
    return c_dir, d_dir, log_file, repo_root


# ---------------------------------------------------------------------------
# Sync log helpers
# ---------------------------------------------------------------------------

def _load_applied(log_file: Path) -> set[tuple[str, str]]:
    """Return set of (round_id, doc_rel_path) already applied."""
    applied: set[tuple[str, str]] = set()
    if not log_file.exists():
        return applied
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            applied.add((entry["round_id"], entry["doc"]))
        except (json.JSONDecodeError, KeyError):
            pass
    return applied


def _append_log(log_file: Path, round_id: str, doc_rel: str, dry_run: bool) -> None:
    entry = {
        "round_id": round_id,
        "doc": doc_rel,
        "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "syncer": "sync-docs.py",
    }
    if dry_run:
        print(f"  [DRY-RUN] would log: {entry}")
        return
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Normative guard
# ---------------------------------------------------------------------------

def _check_normative(capsule: dict) -> str | None:
    """
    Return an error message if capsule contains normative language but is
    missing the citation anchor required by Master Plan §3.

    A capsule is a valid citation anchor when it has:
      - status == "finalized"
      - outcome in {"unanimous", "abstain"}
      - non-empty round_id
    """
    scope = capsule.get("approved_scope", "") or ""
    summary = capsule.get("change_summary", "") or ""
    combined = f"{scope}\n{summary}"

    if not NORMATIVE_RE.search(combined):
        return None  # no normative language → guard not triggered

    if capsule.get("status") != "finalized":
        return (
            f"Capsule {capsule.get('round_id')} contains normative language "
            f"but status is '{capsule.get('status')}' (must be 'finalized')."
        )
    if capsule.get("outcome") not in ("unanimous", "abstain"):
        return (
            f"Capsule {capsule.get('round_id')} contains normative language "
            f"but outcome is '{capsule.get('outcome')}' (must be unanimous or abstain)."
        )
    if not capsule.get("round_id"):
        return "Capsule missing round_id — cannot serve as citation anchor."

    return None  # valid citation anchor


# ---------------------------------------------------------------------------
# Sync history section helpers
# ---------------------------------------------------------------------------

def _build_history_section(entries: list[dict]) -> str:
    """Render the full Sync History section for a doc file."""
    lines = [
        SYNC_HISTORY_START,
        "",
        "## Sync History",
        "",
        "| Round | Applied At | Subject |",
        "|-------|------------|---------|",
    ]
    for e in entries:
        rid = e["round_id"]
        ts = e.get("applied_at", "unknown")[:10]
        subject = (e.get("subject") or "").replace("|", "\\|")
        lines.append(f"| `{rid}` | {ts} | {subject} |")
    lines += ["", SYNC_HISTORY_END]
    return "\n".join(lines)


def _parse_existing_history(text: str) -> list[dict]:
    """Extract existing sync entries from doc text."""
    start = text.find(SYNC_HISTORY_START)
    end = text.find(SYNC_HISTORY_END)
    if start == -1 or end == -1:
        return []
    block = text[start:end]
    entries: list[dict] = []
    for line in block.splitlines():
        m = re.match(r"\|\s*`(r-[0-9a-f]+)`\s*\|\s*([^|]+)\s*\|\s*(.+?)\s*\|", line)
        if m:
            entries.append({
                "round_id": m.group(1),
                "applied_at": m.group(2).strip(),
                "subject": m.group(3).strip(),
            })
    return entries


def _update_doc(
    doc_path: Path,
    capsule: dict,
    repo_root: Path,
    dry_run: bool,
) -> None:
    """Append (or update) Sync History section in doc_path for this capsule."""
    text = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""

    existing = _parse_existing_history(text)
    round_id = capsule["round_id"]

    # De-duplicate if already in history (force re-run path)
    existing = [e for e in existing if e["round_id"] != round_id]

    new_entry = {
        "round_id": round_id,
        "applied_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subject": capsule.get("subject", ""),
    }
    existing.append(new_entry)
    # Sort by applied_at ascending
    existing.sort(key=lambda e: e.get("applied_at", ""))

    new_section = _build_history_section(existing)

    # Replace existing section or append
    if SYNC_HISTORY_START in text:
        start = text.find(SYNC_HISTORY_START)
        end = text.find(SYNC_HISTORY_END) + len(SYNC_HISTORY_END)
        new_text = text[:start].rstrip() + "\n\n" + new_section + "\n"
    else:
        new_text = text.rstrip() + "\n\n" + new_section + "\n"

    rel = doc_path.relative_to(repo_root) if doc_path.is_relative_to(repo_root) else doc_path
    if dry_run:
        print(f"  [DRY-RUN] would update: {rel}  (capsule {round_id})")
        return

    doc_path.write_text(new_text, encoding="utf-8")
    print(f"  updated: {rel}  (capsule {round_id})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="DocsSyncer — apply finalized capsules to docs-v2 (Master Plan §3)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--force", action="store_true", help="Re-apply already-applied capsules")
    parser.add_argument("--consensus-dir", metavar="DIR", help="Override .ai/consensus/ path")
    parser.add_argument("--docs-dir", metavar="DIR", help="Override _sys/docs-v2/ path")
    args = parser.parse_args(argv)

    consensus_dir, docs_dir, log_file, repo_root = _resolve_paths(
        args.consensus_dir, args.docs_dir
    )

    if not consensus_dir.is_dir():
        print(f"ERROR: consensus dir not found: {consensus_dir}", file=sys.stderr)
        return 1
    if not docs_dir.is_dir():
        print(f"ERROR: docs-v2 dir not found: {docs_dir}", file=sys.stderr)
        return 1

    capsule_files = sorted(consensus_dir.glob(CAPSULE_GLOB))
    if not capsule_files:
        print(f"No {CAPSULE_GLOB} files found in {consensus_dir}")
        return 0

    applied = _load_applied(log_file)
    needs_human: list[str] = []
    processed = 0

    for cfile in capsule_files:
        try:
            capsule = json.loads(cfile.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"WARN: skipping {cfile.name} — {exc}", file=sys.stderr)
            continue

        round_id: str = capsule.get("round_id", "")
        status: str = capsule.get("status", "")
        outcome: str = capsule.get("outcome", "")
        doc_targets: list[str] = capsule.get("doc_targets", [])

        if not doc_targets:
            # No doc targets — nothing to sync
            continue

        # ---- Normative guard (all capsules with doc_targets) ----
        # A normative claim needs a valid citation anchor (finalized + unanimous/abstain).
        err = _check_normative(capsule)
        if err:
            needs_human.append(f"[{round_id}] {err}")
            continue

        # Only apply finalized, successful capsules
        if status != "finalized" or outcome not in ("unanimous", "abstain"):
            continue

        print(f"\nCapsule {round_id}: {capsule.get('subject', '')}")

        for target_rel in doc_targets:
            doc_path = (repo_root / target_rel).resolve()

            if not args.force and (round_id, target_rel) in applied:
                print(f"  skip (already applied): {target_rel}")
                continue

            if not doc_path.exists():
                print(f"  WARN: target not found, skipping: {target_rel}", file=sys.stderr)
                continue

            _update_doc(doc_path, capsule, repo_root, dry_run=args.dry_run)

            if not args.dry_run:
                _append_log(log_file, round_id, target_rel, dry_run=False)
            else:
                _append_log(log_file, round_id, target_rel, dry_run=True)

            processed += 1

    # ---- Final report ----
    print(f"\n--- DocsSyncer complete: {processed} doc(s) updated ---")

    if needs_human:
        print("\nDOCS_SYNC_NEEDS_HUMAN — normative claims require human review:")
        for msg in needs_human:
            print(f"  {msg}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
