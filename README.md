# Engram

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://microsoft.com/windows)
[![Tests: 469](https://img.shields.io/badge/tests-469%20collected-success.svg)](_sys/tests)
[![Peers: 4](https://img.shields.io/badge/AI%20peers-4%20equal-purple.svg)](_sys/ai/peers.json)
[![Architecture: Brain-Inspired](https://img.shields.io/badge/architecture-Brain--Inspired-ff69b4.svg)](_sys/docs-v2/20-architecture.md)

> **A portable Windows environment where Claude, Gemini, Codex, and Antigravity collaborate as truly equal AI peers — debating, self-healing, and evolving together.**

---

## What Is This?

Engram is not a chatbot wrapper. It's a **multi-agent operating system** that runs entirely from a USB drive or cloud-synced folder — no host installation, no registry pollution, no hardcoded paths.

Four AI peers share a single workspace, coordinate through a lightweight hub, and hold each other accountable through unanimous consensus. When one peer makes a mistake, all peers learn. When the system detects architectural bloat, it proposes its own refactoring. No single AI is in charge.

---

## Why It's Different

| Typical AI Tool | Engram |
|----------------|--------|
| One AI, one chat | Four equal AI peers, parallel execution |
| Human writes all prompts | Peers debate, draft, and review each other |
| Forgets between sessions | Brain-inspired memory: short-term → long-term → semantic |
| Breaks on new machines | Portable: runs from USB, drive-letter-agnostic |
| You manage complexity | Self-care pipeline runs automatically on session close |

---

## Architecture: The Four-Layer Brain

```
┌──────────────────────────────────────────────────────┐
│  NEOCORTEX      docs-v2/        Semantic SSOT        │
│  HIPPOCAMPUS    _archive/       Session memory       │
│  PREFRONTAL     hub.py          Orchestration        │
│  AMYGDALA       check_risk.py   Risk/Safety gate     │
└──────────────────────────────────────────────────────┘
```

Every action passes through the Amygdala first. The Prefrontal Cortex (`hub.py`) coordinates peers. The Hippocampus records what happened. The Neocortex (`docs-v2/`) stores what's normatively true — and can only be updated by unanimous consensus.

---

## Hello World: Three AIs, One Decision

```bash
# Ask all active peers a question in parallel
python _sys/core/hub.py ask-all --query "Should we split this 800-line file?"

# ━━ cc (Claude) ━━━━━━━━━━━━━━━━━━━━━━━━━
# Yes. Lines 1-400 are routing logic, 401-800 are health checks.
# Split into routing.py + health.py. Zero shared state.
#
# ━━ gc (Gemini) ━━━━━━━━━━━━━━━━━━━━━━━━━
# Agree. Saturation scan confirms churn rate > 5 commits/7 days.
# Recommend splitting before the next feature addition.
#
# ━━ cx (Codex) ━━━━━━━━━━━━━━━━━━━━━━━━━━
# Confirmed. No shared imports detected. Safe to split now.

# Unanimous? Lock it in.
python _sys/core/hub.py consensus-propose \
  --subject "Split hub.py into routing.py + health.py" \
  --voters "cc,gc,cx"
```

No human prompt engineering required. The peers read the codebase, debate the tradeoffs, and reach a decision together.

---

## Quick Start

**Prerequisites:** Windows 10/11, API keys for the AI CLIs you want.

```bat
git clone https://github.com/your-org/engram.git
cd engram
INSTALL.bat      :: bootstraps Python, Node, all AI CLIs into _sys/env/
REGISTER.bat     :: sets up SUBST drive P:, context menu entry
P:\start.bat     :: launch
```

**Teardown** — leaves zero trace on the host:

```bat
P:\UNREGISTER.bat
P:\CLEANUP.bat
```

---

## Core Concepts

### Equal Peers, Unanimous Decisions

All AI peers (`cc`, `gc`, `cx`, `ag`) have identical authority. No peer can unilaterally modify the protocol or another peer's scope. High-stakes changes require unanimous ACK from all active peers.

```bash
# Propose → Vote → Finalize (any peer can do any step)
python _sys/core/hub.py consensus-propose --subject "Change COLLAB_RATE to 8" --voters "cc,gc,cx"
python _sys/core/hub.py consensus-vote --voter cc --vote ACK
python _sys/core/hub.py consensus-vote --voter gc --vote ACK
python _sys/core/hub.py consensus-vote --voter cx --vote ACK
# → Applied.
```

### Self-Care on Every Session Close

```
ctx-end
  → sweep expired directives (TTL-based, zero manual work)
  → validate all junctions
  → scan for architectural saturation
  → auto-propose refactors if needed (never auto-applies)
  → log to _archive/self-care-log.jsonl
```

### Collaboration Rate — One Dial

| Rate | Mode | Trigger |
|:----:|------|---------|
| 0 | Solo | Read-only exploration |
| 3 | Guard | `_sys/` script changes |
| 5 | Partner | Multi-file refactors |
| 10 | Brain Sync | Protocol/config edits |

### Model Selection Per Task

Each peer selects the right model automatically — hub.py stays thin:

| Peer | standard | effort | deepthink |
|------|----------|--------|-----------|
| Claude | haiku-4-5 | sonnet-4-6 | opus-4-8 |
| Gemini | 2.0-flash | 2.5-pro | 2.5-pro |
| Codex | mini | o4-mini | o3 |

---

## Structure

```
P:\
├── _sys/
│   ├── core/hub.py              ← orchestration engine
│   ├── ai/peers.json            ← peer registry + model profiles
│   ├── ai/protocol.json         ← collab_rate, consensus, election rules
│   ├── checks/self_care.py      ← 7-step session-end pipeline
│   ├── checks/saturation_scan.py
│   ├── docs-v2/                 ← SSOT for all normative docs (Neocortex)
│   │   ├── general/             ← universal rules, all peers inherit
│   │   ├── specific/            ← per-peer deltas only
│   │   └── ops/                 ← audit, debate, governance
│   └── tests/unit/              ← 469 tests, TDD-first
├── workspace/                   ← your projects
└── _archive/                    ← session logs, handoffs, self-care logs
```

---

## Roadmap

- [ ] Phase 4: SelfHealer auto-remediation in hub.py (Tier-0/1/2)
- [ ] Linux/macOS portability (SUBST → symlink equivalent)
- [ ] MCP registry for workspace-specific tool extensions
- [ ] Web dashboard for peer collaboration visualization

---

## Contributing

Built on three recursive principles:

1. **MECE** — every classification is mutually exclusive and collectively exhaustive
2. **5-Whys** — every fix traces to root cause, not symptom
3. **Closed Feedback Loop** — every process output improves the process itself

Open an issue, create a debate round, or add a peer via `peers.json`.

---

*Built by a human and four AI peers who don't always agree but always ship.*
