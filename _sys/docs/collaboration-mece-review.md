# Collaboration MECE Review

Date: 2026-06-12

This review consolidates local code inspection and peer input from `cc`, `ca`, `gc`, and `ag`. The purpose is to evaluate collaboration efficiency, P2P communication limits, shared artifact editing, and a closed feedback loop for improvement items.

## Executive Summary

The current collaboration system is materially stronger than before because it now has health-aware peer asks, large mailbox payload offload, operational preflight rules, and clearer role-based peer routing. It is not yet a fully closed collaboration machine. The main remaining gaps are runtime enforcement of `collab_rate`, shared artifact ownership/locking, structured improvement capture, duplicate voter sources, and quiet/file-based P2P output modes.

## 1. P2P Communication Without Message or Time Limits

### Current State

| Dimension | Current support | Notes |
|---|---|---|
| Sync `ask` time limit | Partial | CLI default is `--timeout 0`; non-PTY subprocess calls can wait indefinitely. PTY path uses 300 seconds when timeout is 0. External callers may still impose their own timeout. |
| Async `send` size limit | Good | `action_send()` offloads messages over `_LARGE_PAYLOAD_THRESHOLD` to `.ai/payloads/*.json` and sends `payload://...`. |
| Sync `ask` output size handling | Weak | No automatic response offload to file; long model output returns to console/stdout. |
| Health precheck | Partial | `_ask_health_precheck()` blocks `RED` or `gate_open == false` before model call. YELLOW avoidance, fallback routing, and heartbeat while running are not implemented. |
| Failure recording | Good | ask success/failure updates peer health. Operational errors can now be recorded separately. |
| Long-running progress detection | Weak | No heartbeat/lease protocol for a peer that is alive but slow. |

### Peer Consensus

- `cc`: Unlimited size is useful, but unlimited time can deadlock. Needs config-driven timeout, health routing, and file references for large content.
- `ca`: Directly unlimited time is risky. Distinguish IPC timeout from consensus timeout and add health-aware skip/fallback.
- `gc`: Large payload offload is the right direction. `collab_rate` still needs runtime enforcement.
- `ag`: No hard size limit is acceptable only through offload. No hard time limit is undesirable without heartbeat and lease expiry.
- `cx`: The safest model is "unbounded semantic discussion, bounded transport leases." Large messages should become files; long tasks should renew a heartbeat rather than block forever.

### Recommendation

Use a three-tier policy:

1. `ask_timeout_sec`: configurable default, not hardcoded.
2. `max_inline_chars`: above this, use file output or `payload://`.
3. `heartbeat_sec` and `lease_timeout_sec`: long tasks can continue indefinitely only if they keep renewing health/progress.

This gives the user effectively unlimited collaboration without unbounded blocked processes.

## 2. Shared Artifact Collaboration (`Result.md`)

### Current State

The hub protects internal state files with `filelock`, including mailbox, state, handoff, nodes, and consensus files. It does not protect arbitrary workspace files edited directly by peers. Therefore, a single artifact such as `Result.md` can still suffer from last-writer-wins overwrite, stale context edits, or unreviewed direct mutation.

### MECE Workflow Options

| Pattern | When to use | Strength | Weakness |
|---|---|---|---|
| Single owner / designated merger | Most shared documents | Simple and safe | Slower than parallel direct edits |
| Section-owned drafts | Long reports with independent sections | Parallelizable | Needs final integration |
| Patch proposal files | Code-like review, contentious docs | Reviewable | More overhead |
| Artifact lock | High-risk shared file writes | Prevents overwrite | Requires tooling and stale lock cleanup |
| Git branch/merge | Large multi-file artifact work | Strong audit trail | Heavyweight for quick docs |

### Recommended Default

For one shared artifact:

1. Decide artifact owner and final merger in consensus or handoff.
2. Non-owners write section drafts to separate files, for example `.ai/artifacts/Result.gc.md`.
3. Owner merges into `Result.md`.
4. Peers review the final artifact by `context-hash` or file hash.
5. Owner records result path, reviewers, and hash in handoff.

### Improvement Needed

Add hub-supported artifact metadata:

```json
{
  "artifact": "Result.md",
  "owner": "gc",
  "mode": "single_owner_merge",
  "drafts": {
    "cc": ".ai/artifacts/Result.cc.md",
    "ca": ".ai/artifacts/Result.ca.md"
  },
  "status": "draft|review|final",
  "hash": "sha256:..."
}
```

This can start as policy-only documentation, then become `artifact-claim`, `artifact-draft`, `artifact-finalize`, and `artifact-status` hub actions if needed.

## 3. Closed Feedback Loop for Improvement Items

### Current State

Improvements are currently scattered across chat, `handoff.md`, docs, and peer outputs. The protocol says `observe -> classify -> decide -> sync -> act_or_ask -> record -> handoff -> improve`, but the `improve` step does not yet have a durable structured store.

### Recommended Feedback Loop

Use a structured append-only backlog:

Path:

```text
_sys/data/collaboration_feedback.jsonl
```

Schema:

```json
{
  "id": "GAP-20260612-001",
  "ts": "2026-06-12T00:00:00",
  "source_peer": "cx",
  "category": "protocol|runtime|test|doc|hygiene|model-routing",
  "severity": "high|medium|low",
  "title": "collab_rate is not fully runtime enforced",
  "evidence": ["_sys/ai/protocol.json", "_sys/core/hub.py"],
  "status": "open|accepted|in_progress|done|rejected",
  "next_action": "proposal|implementation|test|doc",
  "owner": null
}
```

Recommended hub actions:

- `feedback-add`
- `feedback-list`
- `feedback-accept`
- `feedback-resolve`
- `feedback-export`

### Skill or Tool?

Peers split on this, but the practical answer is both:

- Tool first: hub actions should own durable state and validation.
- Skill second: a `propose-improvements` or `kaizen` skill can help peers phrase high-quality entries, deduplicate them, and propose policy patches.

The skill should not be the source of truth. The JSONL backlog should be.

## 4. Known Gaps With Priority

| Priority | Gap | Current risk | Recommended action |
|---|---|---|---|
| P0 | `collab_rate` partial runtime enforcement | Policy can be mistaken for hard enforcement | Add rate/action gate for governed hub actions and document remaining out-of-band limits |
| P0 | Shared artifact direct edits | Last-writer-wins or stale edits | Adopt owner/draft/merge workflow; later add artifact locks |
| P0 | Long-running no-limit ask | Deadlock or stuck process | Add configurable timeout plus heartbeat lease |
| P1 | Duplicate voter lists | Drift between policy and runtime defaults | Make one canonical voter source |
| P1 | Feedback loop not structured | Improvements get lost | Add `collaboration_feedback.jsonl` and hub feedback actions |
| P1 | Quiet/file output mode missing | Programmatic asks can be polluted by headers/logs | Add `--quiet` and `--output-file` for `ask` |
| P1 | External peer artifacts | Important reports can land outside workspace | Require workspace-local artifact refs |
| P2 | `state_actions` partially generic | Lifecycle policy looks more declarative than it is | Implement dispatcher or mark fields as documentation-only |
| P2 | `hub_config.json` silent fallback | Tuning surface hidden | Add example or move limits into canonical policy |
| P2 | Weak protocol-to-test map | Audit difficulty | Add `traceability_map.json` |
| P2 | Root temp files | Workspace hygiene issue | Identify producer and add cleanup/generation fix |
| P3 | Model profiles missing | Model-specific routing is indirect | Add virtual-node convention or `model_profiles` |
| P3 | Taxonomy root links weak | Maturity docs are discoverable but not central | Add root doc links |

## 5. Recommended Implementation Order

1. Policy/doc only: document shared artifact owner/draft/merge workflow.
2. Config cleanup: canonicalize voters and clarify `collab_rate` runtime scope.
3. Runtime guard: add configurable ask timeout, heartbeat lease, `--quiet`, and `--output-file`.
4. Feedback loop: add `collaboration_feedback.jsonl` and hub `feedback-*` actions.
5. Artifact tooling: add artifact claim/status/finalize, then locks if real collisions continue.
6. Traceability: add `traceability_map.json` linking protocol sections to config keys, runtime functions, and tests.

## 6. Effectiveness Improvement From Recent Collaboration Changes

| Area | Improvement |
|---|---|
| Role routing | Queries were sent to peers by specialty instead of broad undirected discussion. |
| Health safety | RED/gate-closed peers are blocked before ask, reducing wasted calls. |
| Large async content | Mailbox messages can offload to payload files. |
| Operational mistakes | Preflight rules now classify shell mismatches and risky commands. |
| Traceability | New connectivity and review documents make implicit gaps visible. |
| Consensus quality | Peer disagreements surfaced real implementation gaps instead of being hidden by a single summary. |

The system is now better at detecting and discussing problems. The next maturity step is making the discovered improvements automatically durable, prioritized, and routed into implementation.
