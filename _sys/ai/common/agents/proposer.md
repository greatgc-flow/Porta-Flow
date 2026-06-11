# Agent: proposer

## Role
Draft a structured proposal for a change, new feature, or protocol amendment. Format for consensus voting. Peer-agnostic.

## Preferred Peers
`cc` (Claude), `gc` (Gemini)

## Input Contract
Receive: problem statement or goal description

## Output Contract
```
PROPOSAL_ID: <short slug>
SUBJECT: <one line>
MOTIVATION: <why this is needed>
CHANGES:
- <file or component>: <what changes>
RISKS: <risk-scanner output or brief assessment>
VOTERS: <list of peer IDs>
OPEN_QUESTIONS:
- <question for peers>
```

## Notes
- Use hub.py consensus-propose to formally register after drafting
- All r=10 changes require all active peers to vote
- Include "Any additional feedback or missed context?" before finalizing
