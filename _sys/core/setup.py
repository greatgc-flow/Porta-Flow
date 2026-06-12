"""
setup.py - Thin wrapper. Logic moved to core.provisioner.
Kept for backward compatibility (dispatch.json legacy references).
"""
import sys
from pathlib import Path

_sys = Path(__file__).parent.parent.resolve()
if str(_sys) not in sys.path:
    sys.path.insert(0, str(_sys))

from core.provisioner import deploy  # noqa: F401

if __name__ == "__main__":
    import traceback
    from core.provisioner import deploy

    _base = _sys.parent
    ctx = {
        "base_dir": _base,
        "sys_dir":  _sys,
        "paths":    {
            "state":     _sys / "data" / "state",
            "generated": _sys / "data" / "generated",
        },
        "args":  sys.argv[1:],
        "state": {},
    }
    try:
        deploy(ctx)
    except Exception as e:
        print(f"\n[FATAL] {e}")
        traceback.print_exc()
        sys.exit(1)
