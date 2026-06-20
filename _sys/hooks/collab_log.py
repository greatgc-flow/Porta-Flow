"""collab_log.py — Append structured entry to collab-log (replaces collab-log.bat).

Usage: python collab_log.py <AXIS> <SCRIPT> <STATUS> <DETAIL>
  STATUS: OK | FAIL | REFUSED | ESCALATED
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def log_collab(axis: str, script: str, status: str, detail: str) -> None:
    """Append one structured entry to _archive/collab-log/YYYY-MM-DD.md."""
    sys_dir = Path(__file__).parent.parent
    base_dir = sys_dir.parent
    now = datetime.now()

    log_dir = base_dir / "_archive" / "collab-log"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{now.strftime('%Y-%m-%d')}.md"

    entry = (
        f"\n## [{now.strftime('%H:%M:%S')}] {axis} | {script}\n"
        f"Status: {status}\n{detail}\n---"
    )
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)



def main() -> None:
    if len(sys.argv) < 5:
        print("Usage: collab_log.py <AXIS> <SCRIPT> <STATUS> <DETAIL>", file=sys.stderr)
        sys.exit(1)
    log_collab(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])


if __name__ == "__main__":
    main()
