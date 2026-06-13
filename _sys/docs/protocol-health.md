# Protocol: Health Management (v4.2)
> Source: `_sys/ai/protocol.json["health"]` and `_sys/ai/lifecycle_policy.json["health_lifecycle"]` | Part of composable PROTOCOL.md

## 1. Operating Goals

Health management has four jobs:

1. Keep routing away from peers that are known to be blocked.
2. Detect stale or degraded peer state before delegation.
3. Preserve enough handoff state to continue work after a peer fails.
4. Recover peers only through a successful diagnostic path or an explicit manual recovery action.

All routine health reads are zero-token local file reads. A command that contacts a model or external service is not a routine health check unless it is explicitly requested as a diagnostic.

## 2. Health Files

Each peer owns one health manifest:

| Peer | Health file |
|------|-------------|
| cc/ca | `_sys/claude/health.json` |
| gc | `_sys/gemini/health.json` |
| ag | `_sys/antigravity/health.json` |
| cx | `_sys/codex/health.json` |

Minimum schema:

```json
{
  "_version": "1.0",
  "peer_id": "gc",
  "context_health": {
    "status": "GREEN",
    "jsonl_mb": 0.0,
    "checked_at": "20260613T120000",
    "source": "self"
  },
  "session_health": {
    "consecutive_failures": 0,
    "last_success_at": "2026-06-13T12:00:00",
    "last_failure_reason": null,
    "session_count_today": 1,
    "session_date": "20260613"
  },
  "availability": {
    "gate_open": true,
    "entrypoint_ok": true,
    "authenticated": true,
    "rate_limit_state": "ok"
  }
}
```

Status values:

| Status | Meaning | Routing effect |
|--------|---------|----------------|
| GREEN | Healthy and recently checked. | Eligible. |
| YELLOW | Degraded but usable. | Eligible as fallback or lower priority. |
| STALE | Last check is older than `leader_election.health_stale_minutes` or active PID died. | Avoid for leadership and new assignments; explicit peer precheck fails. |
| RED | Known blocked, quarantined, over failure threshold, or gate closed. | Do not route work. |
| UNKNOWN | Health file missing or unreadable. | Do not target explicitly until initialized. |

## 3. Thresholds And State Transitions

Thresholds come from `protocol.json["health"]`:

| Transition | Rule |
|------------|------|
| GREEN | `jsonl_mb < green_mb` and `consecutive_failures < failure_warn` and `gate_open != false`. |
| YELLOW | `green_mb <= jsonl_mb < yellow_mb` or `consecutive_failures >= failure_warn`. |
| RED | `jsonl_mb >= yellow_mb`, `consecutive_failures >= failure_error`, critical failure reason, quarantine, or `gate_open == false`. |
| STALE | `checked_at` older than `leader_election.health_stale_minutes`, or recorded `active_pid` is no longer alive. |

Failure policy comes from `lifecycle_policy.json["ask_failure_classification"]` and `["health_lifecycle"]`.

Critical failure reasons close the gate immediately:

| Reason | Typical cause | Required recovery |
|--------|---------------|-------------------|
| `sandbox_spawn_eperm` | Local sandbox/process policy blocks peer launch. | Fix environment, then `peer-recover`. |
| `rate_or_session_limit` | Provider quota, session limit, or rate limit. | Wait/resolve quota, then `peer-recover`. |
| `cli_not_found` | Peer executable missing from PATH. | Repair install/PATH, then `peer-recover`. |

Transient failures such as timeout increment `consecutive_failures`. At `failure_warn` the peer becomes YELLOW; at `failure_error` it becomes RED.

## 4. Monitoring Cadence

Required checks:

| Event | Command | Purpose |
|-------|---------|---------|
| Peer entry start | `hub.py health-update --peer <peer> --status AUTO --jsonl-mb <mb> --failures <n>` | Refresh self status. |
| Before delegation | `hub.py health-precheck --peer <peer>` or `hub.py health-precheck --needs <capability>` | Block RED, gate-closed, missing explicit, and stale explicit targets. |
| Before peer-to-peer ask | Built-in `_ask_health_precheck()` | Prevent model calls to RED or gate-closed peers. |
| Periodic/session boundary | `hub.py health-sweep` | Persist timestamp-derived STALE state. |
| Human/operator view | `hub.py health-check` or `hub.py peer-status` | Show current local health table. |
| Peer exit/end | `hub.py health-update --peer <peer> --status AUTO --jsonl-mb <mb> --failures <n>` | Leave a fresh handoff signal for the next session. |

`health-sweep` is the durable stale marker. When a peer first becomes STALE, it writes the status and appends a handoff issue so the next coordinator sees the risk without reading logs.

## 5. Routing Gate

A peer is routable only when:

```text
context_health.status in {GREEN, YELLOW}
AND availability.gate_open != false
AND availability.quarantined != true
```

Routing preferences:

1. Prefer GREEN peers.
2. Use YELLOW only when capability, continuity, or cost justifies it.
3. Avoid STALE for new assignments and leadership.
4. Block RED and gate-closed peers.
5. If every suitable peer is RED, gate-closed, missing, or stale, escalate to the human interface peer.

Direct `hub.py ask` still performs its own RED/gate-closed precheck. STALE is treated as an assignment risk, not an absolute invocation ban, because a successful explicit diagnostic call can refresh a stale peer to GREEN.

## 6. Recovery Runbooks

### YELLOW Recovery

Use when the peer is degraded but still gate-open.

1. Reduce routing priority for new work.
2. Record a checkpoint at the next pause if the peer owns active work.
3. Run the smallest relevant diagnostic or normal ask.
4. On success, `_record_ask_success()` resets `consecutive_failures`, clears transient availability flags, and returns the peer to GREEN.
5. If failures continue to `failure_error`, transition to RED.

### STALE Recovery

Use when `checked_at` is old or the recorded PID died.

1. Run `hub.py health-sweep` to persist the STALE status.
2. Do not assign new leadership or task ownership to that peer.
3. If the peer is needed, run an explicit precheck or small diagnostic.
4. On success, update health to GREEN.
5. If the peer does not respond, reassign active tasks with `hub.py task-failover`.

### RED Recovery

Use when the peer is known blocked or quarantined.

1. Stop routing work to the peer.
2. If it owns active work, write a checkpoint with `hub.py task-checkpoint`.
3. Quarantine if not already quarantined: `hub.py peer-quarantine --peer <peer> --reason <reason>`.
4. Repair the root cause outside the model call path.
5. Validate the repair with the smallest safe diagnostic.
6. Reopen only with `hub.py peer-recover --peer <peer> --reason <reason>`.
7. Reassign or resume work only after `health-precheck` passes.

Manual `health-update --status GREEN` is not a substitute for repair. It may refresh a healthy peer's self-report, but RED recovery should use `peer-recover` so the handoff records the event.

## 7. Continuity Requirements

Before a degraded owner yields, is quarantined, or fails over, the coordinator must preserve:

- Task id and owner.
- Files or artifacts currently being edited.
- Last known good decision.
- Pending risks or blocked commands.
- Next concrete action.

Preferred commands:

```text
hub.py task-checkpoint --id <task_id> --peer <peer> --msg <summary>
hub.py checkpoint --agent <peer> --msg <summary>
hub.py task-failover --task-id <task_id> --peer <new_peer> --reason <reason>
```

Recovery must prefer durable state references (`.ai/state.json`, `.ai/sessions/<room>/handoff.md`, `.ai/task_registry.json`) over pasted chat transcripts.

## 8. Operator Quick Checks

```text
hub.py health-check
hub.py peer-status
hub.py health-precheck --needs code
hub.py health-precheck --peer gc
hub.py health-sweep
hub.py peer-quarantine --peer gc --reason quota
hub.py peer-recover --peer gc --reason quota_reset
```

## 9. Anti-Patterns

- Do not call a RED or gate-closed peer hoping the call will fix it.
- Do not clear `gate_open=false` without identifying the root cause.
- Do not use model calls for routine health checks when local files are enough.
- Do not let a stale coordinator keep ownership without a checkpoint.
- Do not route around a failing peer silently; record quarantine, failover, or recovery in handoff.

## HISTORY

- v4.2 (2026-06-13): Expanded monitoring cadence, state machine, routing gate, and recovery runbooks; aligned with `health-precheck`, `health-sweep`, `peer-quarantine`, `peer-recover`, and task failover behavior.
- v4.1 (2026-06-12): Standardized zero-token health check thresholds.
- v4.0 (2026-06-11): New file; health management system designed with all peers (cc,gc,ag,cx).
