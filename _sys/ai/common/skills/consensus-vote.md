# Skill: Consensus Vote

How any peer participates in or initiates consensus rounds.

## Propose a Round

```
python _sys/core/hub.py consensus-propose \
  --subject "Brief description" \
  --voters cc,gc,ag,cx \
  --from {your_peer_id}
```

## Cast a Vote

```
python _sys/core/hub.py consensus-vote \
  --round-id r-XXXX \
  --voter {your_peer_id} \
  --vote agree|disagree|abstain \
  --reason "Optional reason"
```

## PTY Peer (ag) — Direct Write Method

ag must NOT use `hub.py ask` for votes. Write directly:

```json
// .ai/consensus/{round_id}.json — add to "votes" array:
{"voter": "ag", "vote": "agree", "reason": "...", "voted_at": "ISO8601"}
```

## Check Round Status

```
python _sys/core/hub.py consensus-check --round-id r-XXXX
```

## Final Call (R:8+)

After all votes: proposer sends "Any additional feedback or missed context?"
All peers reply `ACK/Proceed`. Only then is the round finalized.
