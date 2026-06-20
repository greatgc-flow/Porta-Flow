# Engram

[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://www.microsoft.com/windows)
[![Python: 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](_sys/runtimes.json)
[![Tests: 790 passing](https://img.shields.io/badge/tests-790%20passing-brightgreen.svg)](_sys/tests/unit)
[![Protocol: 4.2](https://img.shields.io/badge/protocol-4.2-purple.svg)](_sys/ai/protocol.json)
[![Active peers: 3](https://img.shields.io/badge/active%20peers-3-ff69b4.svg)](_sys/ai/orchestration.json)

Engram is a portable Windows development environment with a multi-peer AI
collaboration system. It provides isolated runtimes, CLI launchers, peer
orchestration, automatic model-profile routing, health checks, consensus, and
test-driven validation from one relocatable directory.

## Current Peer Topology

`_sys/ai/orchestration.json` is the canonical topology source. A peer is a
provider-level participant. Its runtime nodes are generated from the profile
tree in memory:

```text
peer
|-- standard
|-- effort
`-- deepthink
```

Disabling a peer disables every child profile. Profiles have equal governance
weight and collaboration rights; model cost or capability does not grant
additional authority.

| Peer | CLI | State | Standard | Effort | Deepthink |
|------|-----|-------|----------|--------|-----------|
| `cc` | Claude Code | Active | Haiku 4.5 / low | Sonnet 4.6 / high | Opus 4.8 / max |
| `ag` | Antigravity | Active | Gemini 3.5 Flash / low | Gemini 3.5 Flash / high | Gemini 3.1 Pro / high |
| `cx` | Codex | Active | GPT-5.4-mini / low | GPT-5.5 / high | GPT-5.5 / xhigh |
| `ca` | Claude alternate | Disabled | Inherited disabled | Inherited disabled | Inherited disabled |
| `gc` | Gemini CLI | Disabled | Inherited disabled | Inherited disabled | Inherited disabled |

The default profile is deliberately low cost. The hub analyzes each request and
can promote or demote it among `standard`, `effort`, and `deepthink`.

## Quick Start

Requirements:

- Windows 10 or Windows 11
- Git for the initial checkout
- Network access during installation
- Provider authentication for each AI CLI you intend to use

Install or rebuild the portable environment:

```bat
INSTALL.bat
```

Register the current directory on the host and map the configured drive:

```bat
register.bat
```

Remove host registration:

```bat
unregister.bat
```

## Using the AI System

Start a peer-specific terminal:

```bat
_sys\cli\claude.bat
_sys\cli\codex.bat
_sys\cli\agy.bat
```

The terminal is only the human interface. Collaboration roles and the active
coordinator can change independently through the hub.

Send a request to a peer and let the router select the profile:

```bat
_sys\cli\msg.bat ask --to cx --query "Implement and test this change"
```

Force a profile only when required:

```bat
_sys\cli\msg.bat ask --to cx.standard --query "Make a small local edit"
_sys\cli\msg.bat ask --to cc.effort --query "Review this architecture"
_sys\cli\msg.bat ask --to ag.deepthink --query "Analyze the full repository"
```

Request all active peers:

```bat
_sys\cli\msg.bat ask-all --query "Review this design and identify risks"
```

Useful status and validation commands:

```bat
_sys\cli\msg.bat peer-status
_sys\cli\msg.bat model-status
_sys\cli\msg.bat profile-validate
python _sys\checks\validate_peer_config.py --strict
```

## Automatic Profile Routing

Routing is deterministic and configuration-driven. It considers request risk,
scope, reasoning needs, explicit overrides, peer health, profile eligibility,
and fallback rules.

```text
request
   |
   v
classify risk and complexity
   |
   v
select peer.profile
   |
   v
validate enabled state, health, and availability
   |
   v
invoke provider CLI
```

Explicit overrides are supported for reproducible tests and exceptional tasks:

```bat
_sys\cli\msg.bat ask --to cx --query "[PROFILE:deepthink] Investigate this failure"
_sys\cli\msg.bat ask --to cc --query "[RISK:10] Review this migration"
```

See
[`automatic-profile-routing-2026-06-20.md`](_sys/docs-v2/ops/automatic-profile-routing-2026-06-20.md)
for the classifier, promotion and demotion rules, fallback behavior, tests, and
benchmarks.

## Repository Layout

```text
.
|-- INSTALL.bat                 portable environment bootstrap
|-- register.bat                host registration and drive mapping
|-- unregister.bat              host integration removal
|-- CLEANUP.bat                 generated-data cleanup
|-- AGENTS.md                   contributor instructions
|-- PROTOCOL.md                 collaboration protocol entry point
|-- _sys/
|   |-- ai/                     runtime policy and topology JSON
|   |-- checks/                 health, dependency, and consistency checks
|   |-- cli/                    peer terminals and command wrappers
|   |-- core/                   hub, routing, setup, and lifecycle logic
|   |-- docs-v2/                current architecture and operating docs
|   |-- hooks/                  collaboration lifecycle hooks
|   |-- templates/              reusable workspace and tool templates
|   `-- tests/                  unit, integration, scenario, and stress tests
`-- workspace/                  user projects and working documents
```

Generated state, credentials, logs, caches, and downloaded runtimes are not
source files and must remain outside version control.

## Configuration

| File | Responsibility |
|------|----------------|
| `_sys/ai/orchestration.json` | Peer tree, profiles, models, invocation arguments, enabled state |
| `_sys/ai/protocol.json` | Collaboration, consensus, leadership, and forwarding policy |
| `_sys/ai/routing-config.json` | Automatic routing thresholds, fallback, and role weights |
| `_sys/ai/model-registry.json` | Provider model specifications and validation metadata |
| `_sys/ai/peers.json` | Peer capabilities and operational metadata |
| `_sys/ai/status_checks.json` | Current health and model verification scenarios |
| `_sys/ai/error-taxonomy.json` | Structured failure classification |

Do not add provider or model logic to multiple call sites. Add or remove a peer,
profile, model, or option through the canonical configuration and adapters, then
run the strict validators and tests.

## Testing

Run the normal complete suite:

```bat
_sys\tests\run-tests.bat --all
```

Run every suite, including high-memory stress tests:

```bat
_sys\tests\run-tests.bat --full
```

Run unit tests directly:

```bat
python -m pytest _sys\tests\unit -q
```

Run targeted validation:

```bat
_sys\checks\check-deps.bat
_sys\checks\check-portability.bat
python _sys\checks\check_docs_mece.py --json
python _sys\checks\validate_peer_config.py --strict
python _sys\tests\benchmark_peer_routing.py
```

Current verified baseline: 790 unit tests passing, strict peer validation with
zero warnings, profile parity validation passing for 12 active runtime nodes,
and documentation checks CHK-01 through CHK-07 passing.

## Documentation

Start with:

- [`_sys/docs-v2/MOC.md`](_sys/docs-v2/MOC.md) for the documentation map
- [`_sys/docs-v2/10-invariants.md`](_sys/docs-v2/10-invariants.md) for hard rules
- [`_sys/docs-v2/20-architecture.md`](_sys/docs-v2/20-architecture.md) for system structure
- [`_sys/docs-v2/ops/peer-debate-2026-06-19.md`](_sys/docs-v2/ops/peer-debate-2026-06-19.md) for the peer architecture decision
- [`_sys/docs-v2/ops/automatic-profile-routing-2026-06-20.md`](_sys/docs-v2/ops/automatic-profile-routing-2026-06-20.md) for automatic profile routing

## Contribution Rules

- Use English in source, comments, documentation, JSON, agent definitions, and
  batch output.
- Keep paths portable and derive them from the repository root.
- Add focused tests before or with behavior changes.
- Keep configuration machine-readable and minimally reformatted.
- Run relevant targeted checks before the full suite.
- Use Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`,
  `refactor:`, and `test:`.
