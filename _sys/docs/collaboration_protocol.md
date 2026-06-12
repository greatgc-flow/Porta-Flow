# Collaboration Protocol v4.1

This document defines the General-Specific collaboration policy model, connector contract, ambiguity contract, and zero-token feedback loop for this portable multi-peer environment.

## 1. General-Specific Model

The protocol is split into four MECE layers:

- General layer: invariant semantics, lifecycle, authority rules, required state, and failure defaults.
- Specific layer: project, room, peer, and task scoped preferences.
- Connector layer: stateless mappings from an intent to a selectable implementation.
- Ambiguity layer: structured uncertainty, ask thresholds, and escalation paths.

Effective configurable policy is resolved in this order:

`default -> general -> project -> room -> peer -> task`

General invariants are authority-bound constraints, not ordinary overrides. Lower layers may only narrow, parameterize, or add stricter constraints. They must not weaken, redefine, or bypass General invariants.

Peer equality means AI peers have equal proposal, review, and voting rights within their granted authority level. It does not remove Human veto, security boundaries, repository ownership rules, or task-specific delegated authority.

## 2. Canonical Feedback Loop

Every collaboration cycle follows one state machine:

`observe -> classify -> decide -> sync -> act_or_ask -> record -> handoff -> improve`

- Observe: read existing JSON, logs, health, mailbox, handoff, and payload references.
- Classify: map observations to declared rules without semantic invention.
- Decide: choose the next local action, connector, peer ask, or human escalation.
- Sync: acquire the declared lock target, resolve contention, and apply retry/backoff.
- Act or ask: execute a declared connector, ask a peer, or escalate according to policy.
- Record: write provenance, event name, policy version, input refs, output refs, and result.
- Handoff: compact durable state into the blackboard; store large content as file refs.
- Improve: convert resolved ambiguity into a narrower Specific rule or a General proposal.

Handoff is an emitted lifecycle artifact. It records state; it is not an independent policy authority.

## 3. Connector Resolution

Connectors do not own state semantics. They bind a General intent to Specific choices through this deterministic pipeline:

`intent -> candidate choices -> policy filters -> selected action -> recorded rationale`

Each connector must declare its side effect class, lock requirement, idempotency behavior, path safety assumptions, exit-code mapping, and record fields. Write and execute actions require a lock target. Non-idempotent actions must be explicit.

## 4. Ambiguity Contract

Ambiguity entries expose uncertainty without becoming a second policy system. Each entry records:

- uncertainty
- candidate interpretations
- confidence
- ask threshold
- escalation vector
- owner or actor
- status
- resolution reference

If confidence is below the ask threshold, the peer must ask or escalate before acting. If local records conflict or are stale and no declared rule resolves them, the loop fails closed into ask/escalate.

## 5. Zero-Token Boundary and Governance

Zero-token operations are local operations performed before model calls. 

### 5.1 Exempt vs. Governed Operations
COLLAB_RATE controls governance depth for **governed decisions and side-effecting actions**. It is NOT a ban on zero-token local orientation.
- **Exempt Operations (Allowed at all Rates)**:
  - `local_observe/read`: Reading file/directory contents and environment state.
  - `local_validate/schema`: Running syntax, schema validation, or declared dry checks (e.g. `check-health.bat`, `check-deps.bat`).
  - `local_classify/risk routing`: Routing tasks based on static metadata without executing logic edits.
- **Governed Operations (Subject to COLLAB_RATE)**:
  - Write operations, workspace edits, and command executions with potential side-effects.
  - Commands and tests default to governed and require classification. Only explicitly registered dry-run or read-only connectors are exempt.

### 5.1.1 Declared Dry Connector Rule

A command, test, or check is not exempt merely because it is described as "dry", "test", "check", or "read-only" at runtime. Exemption requires schema-validated connector metadata:

- `operation_class`: what the peer intends to do, such as `observe`, `validate`, `classify`, `ask`, `decide`, `implement`, or `record`.
- `effect_class`: what the operation can affect, such as `read_only`, `declared_dry_validate`, `local_temp_write`, `governance_write`, `workspace_write`, `process_mutation`, or `external_io`.
- `action_policy`: the resulting gate, such as `exempt`, `requires_classification`, `pre_consensus_allowed`, `requires_finalized_consensus`, or `human_override_required`.
- `idempotent`, `external_io`, `cache_policy`, and path safety fields.

For an operation to be exempt at R:10, its connector metadata must declare `action_policy: "exempt"`, an allowed non-mutating `effect_class`, idempotent behavior, no workspace writes, and no undeclared external I/O. Runtime-only claims are rejected. Missing or uncertain metadata defaults to `requires_classification`; any potential side effect at R:10 requires finalized consensus before execution.

### 5.1.2 Out-of-Band Direct Writes

Out-of-band direct file writes (e.g., modifying files directly via tool APIs/file writes instead of command executions routed through hub guards) are technically non-enforceable at runtime, but they are strictly governed by developer consensus and policy alignment.

### 5.2 Pre-Consensus Peer Asks
- **Non-Binding Info Gathering**: Peer asks are permitted without prior consensus when gathering facts, clarifying assumptions, or soliciting objections (non-binding).
- **Binding Decisions**: As soon as a peer ask is framed as a vote, approval request, or binding decision, it is governed under the consensus protocol.
- *Safety Invariant*: No side-effecting implementation or workspace modification can be executed based on non-binding gathering; all modifications must proceed via the official COLLAB_RATE consensus workflow.

### 5.3 R:10 Unanimity & Offline Rules
- **Requirements**: R:10 requires unanimous active voter consensus PLUS a Final Call check (explicit ACK/Proceed from all peers) before governed decisions or side-effecting implementation.
- **Offline Node Policy**: An offline peer auto-abstain does NOT satisfy the unanimity requirement at R:10. If a node is offline, a human override or policy downgrade is required to resolve the deadlock.
- **Handoff recording**: Writing the handoff for finalized consensus is part of the consensus connector itself, but editing protocol files or core configuration still requires full consensus.

## 6. Required Safety Dimensions

The policy schema must cover:

- versioning and compatibility
- authority levels
- precedence and invariant narrowing
- lifecycle events
- concurrency, locks, retry, and backoff
- idempotency and replay behavior
- observability and provenance
- failure modes that fail closed by default
- security and privacy boundaries
- `x-*` extension fields for project-specific additions

Schema-valid configuration is not sufficient by itself. Semantic validation must still reject unsafe paths, undeclared connector ownership, invariant weakening, and stale or incompatible policy versions.
