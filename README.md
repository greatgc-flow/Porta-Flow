# 🌌 Engram (Zero-Code AI Hub)

[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://www.microsoft.com/windows)
[![Python: 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](_sys/runtimes.json)
[![Tests: 808 passing](https://img.shields.io/badge/tests-808%20passing-brightgreen.svg)](_sys/tests/unit)
[![Protocol: 4.2](https://img.shields.io/badge/protocol-4.2-purple.svg)](_sys/ai/protocol.json)
[![Architecture: Zero-Code](https://img.shields.io/badge/architecture-Zero--Code-ff69b4.svg)](_sys/ai/orchestration.json)

**Engram** is a next-generation portable Windows development environment and multi-peer AI collaboration hub. By leveraging a strict **Zero-Code Architecture**, Engram orchestrates LLM peers (Claude, Antigravity, Codex) entirely through declarative JSON bindings—eliminating hardcoded adapter logic and brittle scripts.

It provides isolated runtimes, CLI launchers, automatic model-profile routing, health checks, consensus tracking, and comprehensive test-driven validation from a single relocatable directory.

## ✨ Key Features
- 🧩 **Zero-Code Architecture**: All component wiring is defined in `environment.json` and `orchestration.json`. No hardcoded paths or peer IDs.
- 🗂️ **MECE Documentation**: Documentation is structured to be Mutually Exclusive and Collectively Exhaustive (MECE), verified by automated TDD pipelines.
- 🚦 **Global Exception Trap**: The 5-Whys root-cause analysis template automatically fires on fatal errors—no more silent failures.
- 🤖 **Multi-Peer Orchestration**: Effortlessly scale to N-way AI collaboration with distinct reasoning traits managed by unified profiles.

## 🚀 Getting Started

1. **Quick Start**: Run `INSTALL.bat` to bootstrap the isolated environment, then `register.bat` to mount the virtual drive (`P:\`).
2. **User Manual**: Dive into [`_sys/docs-v2/user/manual.md`](_sys/docs-v2/user/manual.md) for everyday workflows and CLI commands.
3. **Architecture Blueprint**: Review [`_sys/docs-v2/20-architecture.md`](_sys/docs-v2/20-architecture.md) for the JSON binding strategy.
4. **Master Index**: See [`_sys/docs-v2/MOC.md`](_sys/docs-v2/MOC.md) for the SSOT of all peer rules and invariants.

> **⚠️ Note to AI Peers**: Do not read this file for operational rules. Please proceed immediately to `_sys/docs-v2/MOC.md` and `_sys/docs-v2/10-invariants.md`.
