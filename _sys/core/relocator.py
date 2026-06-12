"""
relocator.py - Thin compatibility shim.
Drive relocation logic is now embedded in core.launcher._relocate(),
which reads relocate.patch / relocate.delete from peers.json.
"""
import sys
from pathlib import Path

_sys = Path(__file__).parent.parent.resolve()
if str(_sys) not in sys.path:
    sys.path.insert(0, str(_sys))


def relocate():
    """Delegate to launcher's _relocate for backward compat."""
    from core.launcher import _relocate
    base = _sys.parent
    _relocate(base, _sys)


if __name__ == "__main__":
    relocate()
