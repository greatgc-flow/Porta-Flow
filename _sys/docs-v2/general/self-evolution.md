# General — Autonomous Environment Maintenance (Self-Evolution)
> Status: DRAFT (Pending Phase 1 Protocol Consensus)
> Purpose: Defines the mechanisms for peers to autonomously heal, document, and refactor the environment.

## 1. Core Principle: Autonomy vs. Consensus
Under COLLAB_RATE:10, governed decisions require unanimous consensus. Autonomous maintenance does not bypass this; instead, it layers actions by severity:
- **Observation & Validation:** Always exempt.
- **Action Execution:** Tiered by severity (Tier-0 auto-execute, Tier-1 fast-consensus, Tier-2 full R:10 consensus).

## 2. Three Subsystems

### 2.1. SelfHealer (Auto-Remediation)
Detects and fixes systemic errors.
- **Triggers:** `operational_errors.jsonl`, `health.json` (RED > 5m), `pytest` regressions.
- **Tier-0 (Low Risk):** Reversible changes, local to `_sys/data/` or `_archive/`. Excludes `_sys/core/`. Executes immediately with an audit log.
- **Tier-1 (Medium Risk):** Local file writes. Requires fast-consensus (15 min, 2/3 voters).
- **Tier-2 (High Risk):** Protocol/config edits. Requires full R:10 consensus.
- **DIR-003 Guard:** Any `hub.py` API change automatically escalates to Tier-2.

### 2.2. DocsSyncer (Automated Documentation)
Keeps `_sys/docs-v2` synchronized with actual protocol changes without requiring a separate vote.
- **Trigger:** Successful execution of the `consensus_finalize` connector.
- **Mechanism (Inherited Consensus):** Since the parent action already achieved consensus, the documentation update inherits this approval.
- **Roles:** `gc` drafts the update (large-corpus); `cc` validates against invariants.

### 2.3. SaturationDetector (Proactive Refactoring)
Monitors structural health and prevents architectural bloat.
- **Triggers:** Every 10 commits or manual `saturation-scan`.
- **Metrics:**
  - File saturation (lines > 800)
  - Git churn (> 5 commits in 7 days)
  - Protocol saturation (`protocol.json` > 850 lines or > 30 invariants)
  - Coupling (shared modules imported by > 3 peers)
  - Tech debt backlog (> 3 unresolved `_exceptions`)
- **Action:** Auto-generates a `proposal-add` for architecture refactoring. *Never auto-executes.*

## 3. Protocol.json Integration (Proposed)
A new `"autonomous_maintenance"` section will be added to `protocol.json` to define thresholds, voters, and triggers for these subsystems.

## 4. Implementation Roadmap
- **Phase 1:** Update `protocol.json` with the new section (Requires R:10).
- **Phase 2:** Implement `saturation-scan.py` (Read-only, Low risk).
- **Phase 3:** Implement `sync-docs.py` and hook into `consensus_finalize` (Requires R:8).
- **Phase 4:** Add SelfHealer actions to `hub.py` and sync contracts (Requires R:10).