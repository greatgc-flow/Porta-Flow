"""
dispatcher.py - Pipeline executor for Portable Dev Environment.
Reads dispatch.json and executes ordered operations per command.
"""
import os
import sys
import json
import datetime
import importlib
from pathlib import Path

sys_dir = Path(__file__).parent.parent.resolve()
base_dir = sys_dir.parent
if str(sys_dir) not in sys.path:
    sys.path.insert(0, str(sys_dir))


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[Warning] Failed to load {path.name}: {e}")
    return {}


def _resolve_paths(base: Path, sys: Path) -> dict:
    """Load paths.json and resolve all aliases to absolute Paths."""
    raw = _load_json(sys / "paths.json")
    resolved = {"localappdata": Path(os.environ.get("LOCALAPPDATA", ""))}
    for key, rel in raw.items():
        if key.startswith("_"):
            continue
        resolved[key] = (base / rel) if rel else base
    return resolved


def _build_ctx(cmd: str, extra_args: list) -> dict:
    paths = _resolve_paths(base_dir, sys_dir)
    ctx = {
        "base_dir": base_dir,
        "sys_dir":  sys_dir,
        "paths":    paths,
        "args":     extra_args,
        "command":  cmd,
        "state":    {},
    }
    # Pre-load prior register state for commands that undo it
    if cmd in ("unregister", "cleanup"):
        for fname in ("register.state.json", "install.state.json"):
            sf = paths["state"] / fname
            if sf.exists():
                ctx["prior_state"] = _load_json(sf)
                break
    return ctx


_REGISTER_STATE_KEYS = {"subst_drive", "registry_entries", "junctions"}


def _write_state(ctx: dict) -> None:
    state_dir = ctx["paths"]["state"]
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.datetime.now().isoformat(),
        "base_dir":  str(ctx["base_dir"]),
        **ctx.get("state", {}),
    }
    state_file = state_dir / f"{ctx['command']}.state.json"
    state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [OK] State saved → _sys/data/state/{state_file.name}")
    # install pipeline also performs registration ops → keep register.state.json in sync
    if ctx["command"] != "register" and _REGISTER_STATE_KEYS & ctx.get("state", {}).keys():
        reg_file = state_dir / "register.state.json"
        reg_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _prune_state(ctx: dict) -> None:
    state_dir = ctx["paths"]["state"]
    for target in ("register.state.json",):
        f = state_dir / target
        if f.exists():
            f.unlink()
            print(f"  [OK] State pruned: {f.name}")


def _run_operation(op_id: str, op_cfg: dict, ctx: dict) -> None:
    module_name = op_cfg["module"]
    method_name = op_cfg.get("method", "main")
    failure     = op_cfg.get("failure_policy", "abort")

    try:
        mod    = importlib.import_module(module_name)
        method = getattr(mod, method_name)
        method(ctx)
    except SystemExit:
        raise
    except Exception as e:
        print(f"  [Error] Operation '{op_id}' ({module_name}.{method_name}): {e}")
        if failure == "continue":
            return
        if failure == "warn":
            return
        raise


def run_pipeline(cmd: str, extra_args: list) -> None:
    dispatch_path = sys_dir / "dispatch.json"
    if not dispatch_path.exists():
        print(f"[Error] dispatch.json not found: {dispatch_path}")
        sys.exit(1)

    cfg        = _load_json(dispatch_path)
    pipelines  = cfg.get("pipelines", {})
    operations = cfg.get("operations", {})

    if cmd not in pipelines:
        print(f"[Error] Unknown command: '{cmd}'")
        print(f"  Available: {', '.join(pipelines.keys())}")
        sys.exit(1)

    ctx = _build_ctx(cmd, extra_args)

    for op_id in pipelines[cmd]:
        if op_id == "state.write":
            _write_state(ctx)
            continue
        if op_id == "state.prune":
            _prune_state(ctx)
            continue
        op_cfg = operations.get(op_id)
        if not op_cfg:
            print(f"  [Warning] Unknown operation '{op_id}' — skipped")
            continue
        _run_operation(op_id, op_cfg, ctx)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dispatcher.py <command> [args...]")
        sys.exit(1)
    run_pipeline(sys.argv[1].lower(), sys.argv[2:])
