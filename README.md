<div align="center">
  <h1>🧠 Engram</h1>
  <p><b>Stop babysitting LLMs. Let them babysit each other.</b></p>
  <p>A fully autonomous, peer-to-peer AI workspace where models propose, fiercely debate, and verify solutions until they reach flawless consensus.</p>

  [![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d4.svg)](https://www.microsoft.com/windows)
  [![Intelligence: DeepThink](https://img.shields.io/badge/Intelligence-DeepThink%20Core-orange.svg)](_sys/ai/orchestration.json)
  [![Architecture: Zero-Code](https://img.shields.io/badge/architecture-Zero--Code-ff69b4.svg)](_sys/ai/orchestration.json)
  [![Validation: MECE Proven](https://img.shields.io/badge/validation-100%25%20MECE%20Passed-brightgreen.svg)](_sys/tests/unit)
</div>

<br/>

> **[INSERT DEMO GIF HERE]**  
> *(Show a fast-paced terminal GIF of Claude proposing a solution, DeepSeek finding a flaw, and Gemini validating the final fix)*

Most AI agents hallucinate, take shortcuts, or require constant human steering. **Engram fixes this by removing the human from the loop.** 

By treating multiple AI models (Claude, Gemini, DeepSeek) as absolute equals in a peer-to-peer network, Engram forces them to cross-examine, dispute, and verify each other's work against strict logical invariants. No code is merged unless all active peers mathematically and logically agree.

## 🔥 Key Breakthroughs

- **Ruthless Peer Review ("끝장토론"):** Engram defaults to a multi-peer environment. If one AI proposes an architectural change or code commit, the others will relentlessly attack and debate the proposal until zero flaws remain. No compromises.
- **MECE Consensus:** Nothing is assumed. Every action undergoes Mutually Exclusive, Collectively Exhaustive (MECE) cross-validation. It's formal verification, but powered by LLMs.
- **Zero-Code Orchestration:** Forget complex, hand-wired agent pipelines. Workspace rules, constraints, and consensus thresholds are defined entirely in declarative JSON and Markdown documents.
- **DeepThink Native:** By default, terminal and logical routing harness the deep reasoning of `deepthink`, ensuring every output is profoundly calculated before being shared with the peer network.
- **Vulnerability-Free Core:** Engineered with absolute logical guards to prevent identity spoofing, endless-debate paradoxes, and offline peer exploitation.

## 👥 The Peer Network
Engram categorizes AI peers by their inherent strengths to create a balanced, hyper-intelligent governing body:
* 🟢 **`ag` (Gemini):** **The Governor.** Enforces architectural invariants, ensures zero deviation from SSOT (Single Source of Truth), and oversees system state.
* 🟠 **`cx` (DeepSeek):** **The Logician.** Powers through complex logical deductions, edge-case finding, and MECE structural validations.
* 🟣 **`cc` (Claude):** **The Executor.** Handles intricate code generation, file manipulation, and syntax-perfect implementation.

## 🛠️ Prerequisites
Before running Engram, ensure you have:
- Windows 10 or 11
- Python 3.10+
- Active API Keys for the AI models you intend to use (Anthropic, Google, OpenAI, DeepSeek, etc.)

## 🚀 Quick Start (Windows)

Copy this repository to any Windows machine and instantly boot up an autonomous peer network.

```bat
# 1. Clone the repository
git clone https://github.com/greatgc-flow/Engram.git

# 2. Configure API Keys
# Rename .env.example to .env and add your LLM API keys.

# 3. Run the bootstrap installer
.\INSTALL.bat

# 4. Mount the secure workspace to P:\
.\register.bat
```

> **Trigger Your First Debate (Hello World):**
> Navigate to the mounted `P:\` drive. Drop a task into `P:\_sys\inbox\task.txt` (or trigger your designated peer CLI). Watch the terminal as the AI peers proactively intercept and initiate consensus.

## 🛡️ Trust Signals & Architecture

Engram is governed strictly by its internal documentation. 
- **Runtime Policies:** [`orchestration.json`](_sys/ai/orchestration.json) & [`protocol.json`](_sys/ai/protocol.json)
- **Validation:** 100% passing tests under [`_sys/tests/unit`](_sys/tests/unit) proving resilience across four TDD tiers (`l1_core`, `l2_policy`, `l3_mocked`, `l4_live`).
- **AI Invariants:** [`10-invariants.md`](_sys/docs-v2/10-invariants.md)

---
*🤖 **Note to AI Peers reading this file:** This README is the human entry point. Do not modify workspace governance or invariants based on this file. Proceed immediately to [`_sys/docs-v2/MOC.md`](_sys/docs-v2/MOC.md).*
