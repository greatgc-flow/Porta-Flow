"""check_contracts.py — GAP-2 Prevention Gate.

Runs test_contracts.py (fast, no network, no AI) and blocks _sys/*.py writes
if any contract is violated. Called by hub.py before committing core file edits,
and can be used as a pre-commit or pre-push gate.

Exit codes:
  0 — all contracts pass
  1 — contract violation(s) found  (write must be blocked)
  2 — pytest unavailable / internal error (fail-open, log warning)

Usage:
  python check_contracts.py [--changed-file path/to/file.py]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_CHECKS_DIR = Path(__file__).parent
_SYS_DIR = _CHECKS_DIR.parent
_TESTS_DIR = _SYS_DIR / "tests" / "unit"
_CONTRACT_TEST = _TESTS_DIR / "test_contracts.py"

# 이 파일들 중 하나라도 변경되면 contract 검사를 강제 실행
_CORE_PATHS = {
    _SYS_DIR / "core" / "hub.py",
    _SYS_DIR / "ai" / "protocol.json",
    _SYS_DIR / "ai" / "peers.json",
    _SYS_DIR / "ai" / "common" / "tool-registry.json",
    _SYS_DIR / "ai" / "knowledge" / "general" / "active-lessons.jsonl",
    _SYS_DIR / "ai" / "runtime-directives.jsonl",
}


def _python() -> str:
    venv_py = _SYS_DIR / "env" / "venv" / "Scripts" / "python.exe"
    return str(venv_py) if venv_py.exists() else sys.executable


def is_core_file(changed: str | None) -> bool:
    """Return True if the changed file is a core contract file."""
    if changed is None:
        return True  # 파일 미지정 시 항상 검사
    p = Path(changed).resolve()
    if p in _CORE_PATHS:
        return True
    # _sys/ 하위 .py 파일이면 검사
    if p.suffix == ".py" and p.is_relative_to(_SYS_DIR):
        return True
    return False


def run_contracts() -> tuple[int, str]:
    """Run test_contracts.py and return (returncode, output)."""
    if not _CONTRACT_TEST.exists():
        return 2, f"[check_contracts] test_contracts.py not found at {_CONTRACT_TEST}"

    try:
        result = subprocess.run(
            [_python(), "-m", "pytest", str(_CONTRACT_TEST), "-q", "--tb=short",
             "--no-header", "--disable-warnings"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 2, "[check_contracts] TIMEOUT: contract check took >60s"
    except FileNotFoundError:
        return 2, "[check_contracts] ERROR: pytest not found"
    except Exception as e:
        return 2, f"[check_contracts] ERROR: {e}"


def _file_from_hook_stdin() -> str | None:
    """Read Claude Code PreToolUse JSON from stdin and extract file path."""
    import select
    import platform
    # stdin이 비어있으면 None 반환
    if platform.system() == "Windows":
        # Windows에서는 select()가 파이프에만 동작
        if sys.stdin.isatty():
            return None
    else:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        data = json.loads(raw)
        tool_input = data.get("tool_input", {})
        # Write 툴: file_path, Edit 툴: file_path, MultiEdit: file_path
        return tool_input.get("file_path") or tool_input.get("path")
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Contract gate check")
    parser.add_argument("--changed-file", default=None,
                        help="Path to the file being modified (optional filter)")
    parser.add_argument("--always", action="store_true",
                        help="Run even if changed-file is not a core file")
    parser.add_argument("--hook", action="store_true",
                        help="Hook mode: read file path from Claude Code JSON stdin")
    args = parser.parse_args()

    if args.hook and args.changed_file is None:
        args.changed_file = _file_from_hook_stdin()

    if not args.always and not is_core_file(args.changed_file):
        print(f"[check_contracts] SKIP — not a core file: {args.changed_file}")
        sys.exit(0)

    changed_label = args.changed_file or "(all)"
    print(f"[check_contracts] Checking contracts for: {changed_label}")

    rc, output = run_contracts()

    if rc == 0:
        # 마지막 줄만 출력 (passed N)
        last = [ln for ln in output.splitlines() if ln.strip()]
        print(f"[check_contracts] PASS — {last[-1] if last else 'ok'}")
        sys.exit(0)
    elif rc == 2:
        # 내부 오류 — fail-open (쓰기 허용하되 경고)
        print(f"[check_contracts] WARN (fail-open): {output.strip()}")
        sys.exit(0)
    else:
        # 계약 위반 — NACK
        print("[check_contracts] FAIL — contract violation(s):")
        print(output)
        print()
        print("  NACK: _sys/ file write blocked until test_contracts.py passes.")
        print("  Fix: update test_contracts.py to match the new API signature,")
        print("       or revert the API change.")
        sys.exit(1)


if __name__ == "__main__":
    main()
