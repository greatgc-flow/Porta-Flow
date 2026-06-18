---
name: antigravity
description: "Antigravity/agy (ag) peer monitoring — status, gate. Use for: agy status, ag status, antigravity status, ag on/off, ag 상태."
---

# Antigravity Peer Skill

Antigravity (agy)-specific actions. For TOGGLE/RATIO across all peers → use `/peer` skill.

## Trigger Mapping

| User Request | Action |
|-------------|--------|
| "agy status", "ag status", "ag 상태" | → STATUS |
| "agy on/off", "ag on/off", "ag 켜기/끄기" | → TOGGLE |

---

## ACTION: STATUS

1. Run: `cmd /c "P:\_sys\antigravity\agy-status.bat"`
2. Read `_sys\antigravity\health.json`
3. Report: Gate / Health / Binary present / Last active

For all peers: use `/peer status`.

> Note: ag peer requires `_sys\tools\agy\agy.exe` — bootstrapped via `setup.py`, not npm.

---

## ACTION: TOGGLE

**Disable:**
```
python P:\_sys\core\hub.py peer-quarantine --peer ag --reason "manual"
```

**Enable:**
```
python P:\_sys\core\hub.py peer-recover --peer ag
```
