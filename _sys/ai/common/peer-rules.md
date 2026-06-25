# Terminal Command Contract (Canonical Reads)

Terminal reads raw `_sys/` state files ONLY when the task is explicitly "audit raw state" or the canonical command is missing/broken, and must say so.

- **Peer status**: `hub.py peer-status`
- **Room/session**: `hub.py status`
- **Routability**: `hub.py health-precheck --peer <id>`
- **Models**: `hub.py model-status`
- **Parity**: `hub.py profile-validate`
- **Leases/locks/tasks/roles**: `hub.py lease-status`, `hub.py lock-status`, `hub.py task-status`, `hub.py role-status`
