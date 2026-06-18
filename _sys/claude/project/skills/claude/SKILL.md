---
name: claude
description: "Claude (cc) peer monitoring — status, gate, memory management. Use for: claude status, cc status, claude on/off, claude 상태, cc 상태."
---

# Claude Peer Skill

Claude-specific actions. For TOGGLE/RATIO across all peers → use `/peer` skill.

## Trigger Mapping

| User Request | Action |
|-------------|--------|
| "claude status", "cc status", "cc 상태" | → STATUS |
| "claude on/off", "cc on/off", "cc 켜기/끄기" | → TOGGLE |

---

## ACTION: STATUS

1. Run: `cmd /c "P:\_sys\claude\claude-status.bat"`
2. Read `_sys\claude\health.json`
3. Report: Gate / Health / Model / Last active

For all peers: use `/peer status`.

---

## ACTION: TOGGLE

Claude gate is managed via hub.py health — no separate gate.bat needed.

**Disable:**
```
python P:\_sys\core\hub.py peer-quarantine --peer cc --reason "manual"
```

**Enable:**
```
python P:\_sys\core\hub.py peer-recover --peer cc
```

Note: Claude Code CLI itself is always available; quarantine only affects hub.py routing decisions.
