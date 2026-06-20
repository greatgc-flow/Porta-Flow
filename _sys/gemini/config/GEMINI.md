# Gemini CLI Peer Configuration

> Protocol 4.2 | Node ID: `gc` | Updated: 2026-06-20

`gc` is currently disabled. It remains registered so that it can be restored
without reconstructing provider configuration.

The authoritative state is:

- topology and lifecycle: `_sys/ai/orchestration.json`
- provider installation: `_sys/ai/peers.json`
- collaboration policy: `_sys/ai/protocol.json`
- peer-specific guidance: `_sys/docs-v2/specific/gc.md`

Disabling `gc` disables its `standard`, `effort`, and `deepthink` child
profiles. Disabled peers are excluded from active voters, role assignments, and
automatic routing.

Do not infer current room membership, health, model choice, or voter status from
this file. Query the hub instead:

```bat
_sys\cli\msg.bat peer-status --all
_sys\cli\msg.bat profile-validate
```
