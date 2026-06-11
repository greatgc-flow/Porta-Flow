"""codex_entry.py — Codex (cx) session entry point.

Calls hub.py init-session, health-update, context-fill, then launches codex.cmd.
try-finally로 비정상 종료 시에도 health.json 갱신 보장.
"""
import os
import subprocess
import sys
from pathlib import Path

_CLI_DIR = Path(__file__).parent
_SYS_DIR = _CLI_DIR.parent
_PORTABLE_ROOT = _SYS_DIR.parent

_VENV_PY = _SYS_DIR / "env" / "venv" / "Scripts" / "python.exe"
_HUB = _SYS_DIR / "core" / "hub.py"
_CODEX_CMD = _SYS_DIR / "env" / "nodejs" / "npm-global" / "codex.cmd"

_PYTHON = str(_VENV_PY) if _VENV_PY.exists() else sys.executable


def _env() -> dict:
    e = {**os.environ, "PYTHONUTF8": "1"}
    venv_scripts = str(_SYS_DIR / "env" / "venv" / "Scripts")
    e["PATH"] = venv_scripts + ";" + e.get("PATH", "")
    codex_config = _SYS_DIR / "codex" / "config"
    if codex_config.exists():
        e["CODEX_HOME"] = str(codex_config)
    return e


def _health(env: dict, status: str, failures: int = 0) -> None:
    subprocess.run(
        [_PYTHON, str(_HUB), "health-update", "--peer", "cx",
         "--status", status, "--failures", str(failures)],
        capture_output=True, env=env,
    )


def main() -> None:
    env = _env()
    subprocess.run([_PYTHON, str(_HUB), "init-session", "--agent", "cx"],
                   capture_output=True, env=env)
    fill = subprocess.run([_PYTHON, str(_HUB), "context-fill"],
                          capture_output=True, text=True, env=env)
    if fill.stdout.strip():
        print(fill.stdout)
    subprocess.run([_PYTHON, str(_HUB), "status"], env=env)

    if not _CODEX_CMD.exists():
        print(f"[ERROR] codex.cmd not found at {_CODEX_CMD}")
        print("  Install: npm install -g @openai/codex")
        sys.exit(1)

    exit_code = 1
    try:
        _health(env, "GREEN")
        result = subprocess.run(["cmd", "/c", str(_CODEX_CMD), *sys.argv[1:]], env=env)
        exit_code = result.returncode
        final_status = "GREEN" if exit_code == 0 else "RED"
        _health(env, final_status, failures=0 if exit_code == 0 else 1)
    except KeyboardInterrupt:
        exit_code = 130
    except Exception as e:
        print(f"[codex_entry] error: {e}", file=sys.stderr)
        exit_code = 1
    finally:
        if exit_code not in (0, 130):
            _health(env, "RED", failures=1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
