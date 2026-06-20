"""Data-driven Gemini lifecycle and health check (zero-token)."""
import json
import os
import sys
from pathlib import Path


def main() -> None:
    override = os.environ.get("_AI_SYS_DIR")
    sys_dir = Path(override) if override else Path(__file__).parent.parent
    try:
        orch = json.loads((sys_dir / "ai" / "orchestration.json").read_text(encoding="utf-8"))
        gc = next(n for n in orch.get("hub_nodes", []) if n.get("node_id") == "gc")
        health_path = sys_dir / "gemini" / "health.json"
        health = json.loads(health_path.read_text(encoding="utf-8")) if health_path.exists() else {}
        gate_open = health.get("availability", {}).get("gate_open", True)
        state = health.get("context_health", {}).get("status", "UNKNOWN")
        if gc.get("enabled") is not False and gate_open and state != "RED":
            print("[GATE] gemini=ON")
            sys.exit(0)
    except Exception:
        pass
    print("[GATE] gemini=OFF")
    sys.exit(1)


if __name__ == "__main__":
    main()
