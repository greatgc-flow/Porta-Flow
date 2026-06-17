# Operational Governance Policies

This document defines the lifecycle of discarded files, data retention periods, and audit triggers for the Engram environment.

## 1. /Garbage Folder Governance

The `/Garbage/` folder serves as a staging area for discarded or superseded artifacts.

- **Manual Control**: Engram agents may move items to `/Garbage/`, but the **final deletion is a human-only action**.
- **No Auto-Deletion**: No system process or agent is permitted to automatically empty this folder.
- **Git Protocol**: The `/Garbage/` directory must be included in `.gitignore` to prevent cluttering the repository history.
- **Classification**:
  - **Included**: Superseded documentation, failed experiments, renamed files (after verification), temporary architectural drafts.
  - **Excluded**: Active configuration files (`.json`, `.md`), tracked source files, environment binaries (`_sys/env/`).

## 2. Data Retention Policy

To balance historical traceability with system performance, the following retention rules apply:

| Data Target | Retention Period | Action after Expiry |
| :--- | :--- | :--- |
| **_archive/** | Indefinite | Permanent storage of session logs and handoffs. |
| **_sys/data/temp/** | Per-Session | Cleared automatically during Tier 1 cleanup. |
| **_sys/data/logs/** | 30 Days | Retained for 30 days then archived. |
| **runtime-directives.jsonl** | 6 Hours (TTL) | Expired entries swept on session start. |
| **health.json** | Per-Session | Overwritten each session; not retained. |

## 3. Audit Trigger Policy

Formal audits (using `ops/audit-checklist.md`) are mandatory under the following conditions:

- **Script Changes**: Before any modification to `_sys/` core scripts.
- **Hub Updates**: Before updating `hub.py` or its dependencies.
- **Protocol Shifts**: Before committing changes to `PROTOCOL.md` or `protocol.json`.
- **Release/Push**: Before any major release or push to a remote repository.
- **System Failure**: Automatically triggered when `consecutive_failures > 5`.

## 4. Garbage Cleanup Procedure (Manual)

When the human decides to purge the `/Garbage/` folder, the following steps must be followed:

1. **Review**: Manually inspect items in `/Garbage/` to ensure no active drafts are mistakenly included.
2. **Confirm**: Use `git rm` (if previously tracked) or `rm -rf` to permanently remove items.
3. **Log**: Commit the purge with the standardized message:
   `chore: purge Garbage/ items`
