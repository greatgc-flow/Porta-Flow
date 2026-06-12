"""
cleanup.py - Thin wrapper. Logic moved to core.scrubber.
Kept for backward compatibility and direct CLI invocation.
"""
import sys
from pathlib import Path

_sys = Path(__file__).parent.parent.resolve()
if str(_sys) not in sys.path:
    sys.path.insert(0, str(_sys))

from core.scrubber import run


def run_cleanup(tier=1, all_yes=False, dry_run=False, base_dir=None):
    """Legacy API shim."""
    if base_dir is None:
        base = _sys.parent
    else:
        base = Path(base_dir)
    ctx = {
        "base_dir": base,
        "sys_dir":  base / "_sys",
        "paths":    {"state": base / "_sys" / "data" / "state"},
        "args":     (["--tier", str(tier)] + (["--all"] if all_yes else []) + (["--dry-run"] if dry_run else [])),
        "state":    {},
    }
    run(ctx)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Portable Dev Environment Cleanup")
    parser.add_argument("--tier",    type=int, default=None)
    parser.add_argument("--all", "-y", action="store_true")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    _base = _sys.parent
    ctx = {
        "base_dir": _base,
        "sys_dir":  _sys,
        "paths":    {"state": _sys / "data" / "state"},
        "args":     sys.argv[1:],
        "state":    {},
    }
    run(ctx)
