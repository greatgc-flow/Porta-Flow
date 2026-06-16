# General — Leader Election & Role Assignment
> Source: protocol-routing.md v4.1

---

## 1. Leader (Active Coordinator)

Leader coordinates task framing, role assignment, and synthesis.
Leader is NOT a superior authority — all peers remain equal for consensus.

**Election Score:**
```
score =
  capability_match    0..10
+ health_score        GREEN=3, YELLOW=1, STALE=-5, RED=blocked
+ continuity_bonus    0..2  (current task owner preferred if healthy)
+ console_fit_bonus   0..1  (avoid forwarding if human-interface peer fits)
- cost_penalty        low=0, mid=1, high=2
- cold_start_penalty  0..1
```

**Tiebreak order:** task checkpoint owner → healthier → lower cost (low risk) → higher capability (high risk) → ask human interface peer.

**Commands:**
```
hub.py elect-leader --needs <capability> --effort <low|mid|high>
hub.py leader-claim --agent <peer> --needs <domain> --reason <reason>
hub.py leader-yield --agent <peer> --reason <reason>
```

**Runtime state:** `.ai/state.json.active_coordinator` / `.ai/state.json.leadership`

**Governance:** Low-risk routing = optimistic claim (logged). `_sys/` / protocol / destructive ops = election visible before execution + R:10 rules apply.

---

## 2. Peer Roles (session-scoped)

| Role | Responsibility |
|------|---------------|
| coordinator | Frames task, delegates |
| implementer | Edits files, focused checks |
| verifier | Reviews output, validates risk |
| researcher | Broad context, web/large-corpus |
| documenter | Durable handoff + design artifacts |
| observer | Receives context, does not mutate |

**Commands:**
```
hub.py assign-role --role <role> --peer <peer>
hub.py release-role --role <role> [--peer <peer>]
hub.py role-status
```

**Runtime state:** `.ai/state.json.role_assignments`

---

## 3. Failover Rules

- RED peer: stop routing immediately
- STALE peer: avoid new assignments/leadership; run precheck if needed
- If all suitable peers are RED/gate-closed/STALE: escalate to human interface peer
- Task failover: `hub.py task-failover --task-id <id> --peer <new_peer> --reason <reason>`

---

## 4. Forwarding Contract

- Single-hop forwarding only (`single_hop_forwarding_only: true`)
- Human interface peer stays fixed — not re-routed mid-session
- `hub.py ask-coordinator --from <peer> --query <query>`

---

## 5. Challenge Window

**Source:** `hub.py:action_leader_claim` — `protocol.json["leader_election"]["challenge_window_minutes"]` (default: `1`)

When a peer calls `hub.py leader-claim`, it does **not** become coordinator instantly.
Instead it enters a `PENDING` state with a **challenge window** that allows other peers to contest the claim.

### State Written on Claim

```json
"leadership": {
  "peer":            "<agent>",
  "status":          "PENDING",
  "domain":          "<domain>",
  "reason":          "<reason>",
  "claimed_at":      "<ISO8601>",
  "challenge_until": "<ISO8601 = claimed_at + challenge_window_minutes>"
}
```

Fields set in `state.json`: `leader`, `active_coordinator`, `leadership`.

### Challenge Rules

| Condition | Action |
|-----------|--------|
| Current time < `challenge_until` | Another peer may challenge; claim is overwritten (logged) |
| Current time ≥ `challenge_until` AND current leader is GREEN/YELLOW | `[HUB:ERR]` — claim rejected, `sys.exit(1)` |
| Current time ≥ `challenge_until` AND current leader is RED/STALE | Claim succeeds unconditionally |
| No current leader | Claim succeeds immediately |

> Default window is 1 minute (`challenge_window_minutes: 1`), chosen for USB-drive latency.

### Handoff Entry

Each successful claim appends to `handoff.md[ACTIVE_THREADS]`:
```
[<ts>] (<agent>) [CLAIM-PENDING] claiming leadership. Challenge until: <ts> Reason: <reason>
```

---

## 6. AP-20: Coordinator Monopoly Guard

**Source:** `hub.py:action_leader_claim` — checked on every `leader-claim` call.

### Rule

If a peer has been coordinator for **3 consecutive terms**, it is blocked from claiming leadership again until another peer leads at least once.

### Implementation

```python
history = state.get("coordinator_history", [])   # last 10 entries kept
last_3  = [h.get("peer") for h in history[-3:]]
if len(last_3) == 3 and all(p == agent for p in last_3):
    print(f"[HUB:ERR] AP-20 Violation: {agent} has been coordinator for 3 consecutive terms.")
    sys.exit(1)
```

- `coordinator_history` stores up to the last 10 entries: `{"peer": str, "at": ISO8601, "room": str}`.
- History is appended on every successful claim (after AP-20 passes).
- The check is **pre-claim** — it runs before the challenge window is opened.

### Error

```
[HUB:ERR] AP-20 Violation: {agent} has been coordinator for 3 consecutive terms. Yield to others.
```
Exit code: `1`. No state mutation occurs when the violation fires.
