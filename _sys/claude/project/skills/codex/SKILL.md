---
name: codex
description: "Codex (cx) peer monitoring — status, gate. Use for: codex status, cx status, codex on/off, cx 상태."
---

# Codex Peer Skill

Codex-specific actions. For TOGGLE/RATIO across all peers → use `/peer` skill.

## Trigger Mapping

| User Request | Action |
|-------------|--------|
| "codex status", "cx status", "cx 상태" | → STATUS |
| "codex on/off", "cx on/off", "cx 켜기/끄기" | → TOGGLE |

---

## ACTION: STATUS

1. Run: `cmd /c "P:\_sys\codex\codex-status.bat"`
2. Read `_sys\codex\health.json`
3. Report: Gate / Health / Model / Last active

For all peers: use `/peer status`.

---

## ACTION: TOGGLE

**Disable:**
```
python P:\_sys\core\hub.py peer-quarantine --peer cx --reason "manual"
```

**Enable:**
```
python P:\_sys\core\hub.py peer-recover --peer cx
```
