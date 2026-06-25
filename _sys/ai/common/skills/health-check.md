# Skill: Health Check (Audit/Maintenance)

Raw reads of health files for audit. (For routine checks, use `peer-status`).

## Commands

```
python _sys/core/hub.py peer-status              # full gate + health table (canonical operator view)
python _sys/core/hub.py health-check             # all peers (audit/maintenance)
python _sys/core/hub.py health-check --peer gc   # specific peer (audit/maintenance)
```

## Output Example

```
[HUB:GATE] HEALTH | claude=GREEN(0.4MB) gemini=YELLOW(1.0MB) antigravity=GREEN codex=UNKNOWN
```

## Interpreting Results

- GREEN: fully operational, can accept tasks
- YELLOW: degraded, monitor closely
- RED: do not assign tasks, escalate to Human if all peers RED
- UNKNOWN: health.json missing, peer may not be initialized

## Self-Report

Write your own health at session start/end:
```
python _sys/core/hub.py health-update --peer {peer_id} --status GREEN --jsonl-mb 0.3
```
