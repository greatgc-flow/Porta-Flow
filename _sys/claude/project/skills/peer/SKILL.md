# Peer Management Skill (Common)

Handles peer STATUS, TOGGLE, and RATIO — functions common to all peers (gc, cc, cx, ag).
Peer-specific functions (USAGE, COLLAB, AXIS) live in each peer's own skill file.

## Trigger Mapping

| User Request | Action |
|-------------|--------|
| "peer status", "피어 상태", "all peers", "all peer status" | → STATUS |
| "peer on/off", "enable/disable {peer}", "{peer} 켜기/끄기" | → TOGGLE |
| "collab rate", "collab_rate N", "rate N", "협업 비율" | → RATIO |

---

## ACTION: STATUS

Show all peers' current health via hub.py.

```
python P:\_sys\core\hub.py peer-status
```

Report format: Gate / Health / Version / Details per peer.
If a specific peer is mentioned (e.g., "gemini status"), run Gemini skill STATUS instead.

---

## ACTION: TOGGLE

Enable or disable a peer via hub.py health gate.

**Disable (quarantine):**
```
python P:\_sys\core\hub.py peer-quarantine --peer {peer_id} --reason "manual"
```

**Enable (recover):**
```
python P:\_sys\core\hub.py peer-recover --peer {peer_id}
```

Peer IDs: `gc` (Gemini), `cc` (Claude), `cx` (Codex), `ag` (Antigravity)

Note: For Gemini, also check `gemini-status.bat` to verify CLI gate.

---

## ACTION: RATIO

Read or change the global `collab_rate` in `protocol.json`.

**Query (no arg):**
1. Read `P:\_sys\ai\protocol.json` → `collab_rate.current`
2. Report level + description from table below.

**Change (with N):**
```
cmd /c "P:\_sys\cli\set-collab-rate.bat {N}"
```

### Collab Rate Levels

| Rate | Mode | Intervention Point |
|:----:|:-----|:------------------|
| 0 | **Inactive** | None |
| 1 | **Manual** | Explicit calls only |
| 2 | **Architecture** | Before arch/structure decisions |
| 3 | **Planning** | Before multi-file planning |
| 4 | **Checkpoint** | Before start + after completion |
| 5 | **Code Partner** | Before every Edit/Write |
| 6 | **Error Partner** | All edits + on any error |
| 7 | **Direction** | All edits + trade-off analysis |
| 8 | **Milestone** | Every sub-task review |
| 9 | **Pairing** | Every 5 explores + direction verify |
| 10 | **Sync** | Full Phase — unanimous consent |
