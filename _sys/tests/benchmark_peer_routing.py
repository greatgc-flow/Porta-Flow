"""Deterministic micro-benchmark for peer/profile normalization and routing."""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

SYS = Path(__file__).parent.parent
sys.path.insert(0, str(SYS / "core"))
import hub_peer
import hub_profile_router


def _measure(fn, iterations: int) -> dict[str, float]:
    samples = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return {
        "median_ms": statistics.median(samples),
        "p95_ms": sorted(samples)[int(len(samples) * 0.95) - 1],
        "max_ms": max(samples),
    }


def run(iterations: int = 10000) -> dict:
    path = SYS / "ai" / "orchestration.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    routing = json.loads((SYS / "ai" / "routing-config.json").read_text(encoding="utf-8"))
    normalized = hub_peer.normalize_orchestration(raw)
    node_ids = [n["node_id"] for n in normalized["hub_nodes"]]
    route_iterations = max(1, iterations // len(node_ids))

    return {
        "iterations": iterations,
        "tracked_root_nodes": len(raw["hub_nodes"]),
        "normalized_nodes": len(node_ids),
        "config_bytes": path.stat().st_size,
        "normalize_uncached": _measure(
            lambda: hub_peer.normalize_orchestration(raw), iterations
        ),
        "normalize_cached": _measure(
            lambda: hub_peer.normalize_orchestration(), iterations
        ),
        "routability": _measure(
            lambda: [hub_peer.is_routable(node_id, orch=normalized) for node_id in node_ids],
            route_iterations,
        ),
        "auto_profile": _measure(
            lambda: hub_profile_router.select_profile_node(
                "cx",
                "Implement the parser change and add focused tests.",
                orchestration=raw,
                routing_config=routing,
            ),
            iterations,
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
