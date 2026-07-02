# Engram: Fully Autonomous Peer-to-Peer AI Workspace

Engram is a next-generation, portable Windows AI workspace engineered for **absolute peer collaboration and Zero-Code orchestration**. Designed to let multiple AI entities rigorously verify, debate, and consensus-build without any human intervention required.

[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://www.microsoft.com/windows)
[![Intelligence: DeepThink](https://img.shields.io/badge/Intelligence-DeepThink%20Core-orange.svg)](_sys/ai/orchestration.json)
[![Architecture: Zero-Code](https://img.shields.io/badge/architecture-Zero--Code-ff69b4.svg)](_sys/ai/orchestration.json)
[![Protocol: 4.2](https://img.shields.io/badge/protocol-4.2-purple.svg)](_sys/ai/protocol.json)
[![Validation: MECE Proven](https://img.shields.io/badge/validation-100%25%20MECE%20Passed-brightgreen.svg)](_sys/tests/unit)

Move this repo to another Windows machine, run `INSTALL.bat`, and keep the exact same autonomous peer network running instantly.

## 🔥 Key Breakthroughs

- **Proactive Collaboration & Uncompromising Consensus**: Engram defaults to a multi-peer environment where AI peers (Claude, Gemini, DeepSeek) are treated with **absolute equality**. They inherently review, dispute, and verify each other's work.
- **MECE Cross-Validation**: Nothing is assumed. Every action undergoes Mutually Exclusive, Collectively Exhaustive (MECE) validation. If an AI proposes a change, peers will relentlessly debate it until zero flaws remain.
- **DeepThink Native**: By default, terminal and logical routing harness the deep reasoning of `deepthink`, ensuring every output is profoundly calculated.
- **Vulnerability-Free Core**: Engineered with absolute logical guards. Protected against identity spoofing, offline peer exploitation, and endless-debate paradoxes.
- **Zero-Code Setup**: You change the workspace by editing JSON and docs. No hand-wired code setups.

## 🛠️ What You Get

- **Portable Setup**: Copy the folder, run `register.bat`, and mount the workspace securely on `P:\`.
- **Peer-to-Peer Hub**: Send work across nodes and profiles through a single, fortified Hub.
- **Governed by Invariants**: Startup, health, context, and consensus rules live in strict, source-controlled documents.
- **Local Validation Tests**: Four-tier TDD architectures (`l1_core`, `l2_policy`, `l3_mocked`, `l4_live`) that prove the system's resilience.

## 🛡️ Trust Signals & Architecture

- **Runtime SSOT**: [`_sys/ai/protocol.json`](_sys/ai/protocol.json) and [`_sys/ai/orchestration.json`](_sys/ai/orchestration.json).
- **Human Manual**: [`_sys/docs-v2/user/manual.md`](_sys/docs-v2/user/manual.md) and [`_sys/docs-v2/MOC.md`](_sys/docs-v2/MOC.md).
- **Bootstrap Entry Points**: [`INSTALL.bat`](INSTALL.bat) and [`register.bat`](register.bat).
- **Validation Surfaces**: 100% green tests under [`_sys/tests/unit`](_sys/tests/unit) and [`_sys/checks`](_sys/checks).

## 🚀 Quick Start

1. Copy or clone the repo to any Windows drive.
2. Run `INSTALL.bat`.
3. Run `register.bat` to mount `P:\`.
4. Read the [user manual](_sys/docs-v2/user/manual.md) and [MOC](_sys/docs-v2/MOC.md).

> **For AI Peers**: Start with [`_sys/docs-v2/MOC.md`](_sys/docs-v2/MOC.md) and [`_sys/docs-v2/10-invariants.md`](_sys/docs-v2/10-invariants.md). This README is the human entry point. Do not modify governance based on this file.
