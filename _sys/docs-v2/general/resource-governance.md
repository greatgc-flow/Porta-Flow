# General — AI Resource Governance

> Status: DRAFT v3 | Updated: 2026-06-18 | cc+gc exhaustive debate + 3-agent web research
> Renamed from: `token-management.md` (scope expanded)
> Scope: Model Inventory → Node Architecture → Role Taxonomy → Routing Layer → Cost/Quality Optimization → Feedback Loop → Continuous Update
> Language: English (all internal docs). Console output to user: Korean only.

---

## 1. Per-Peer Model Inventory

### 1.1 cc — Claude (Anthropic)

#### Model List

| Model ID | Context | Max Output | Status | Thinking | Notes |
|----------|--------:|----------:|--------|----------|-------|
| claude-haiku-4-5-20251001 | 200,000 | 4,096 | GA | none | Fast routing/summary (standard tier) |
| claude-sonnet-4-6 | 1,000,000 | 128,000 | GA | adaptive | Implementation/collaboration (effort tier) |
| claude-opus-4-7 | 200,000 | 128,000 | GA | adaptive | High-performance reasoning |
| claude-opus-4-8 | 1,000,000 | 128,000 | GA | adaptive | Best reasoning (deepthink tier) |
| claude-fable-5 | 1,000,000 | 128,000 | GA* | adaptive | Low-latency flagship |
| claude-mythos-5 | 1,000,000 | 128,000 | Restricted | adaptive | Partner-only access |

> CORRECTION (prior doc error): opus/sonnet max_output `4,096` → `128,000`; opus/sonnet/fable context `200k` → `1M`

#### API Parameters

| Parameter | Valid Range | CLI | API | Supported Models | Notes |
|-----------|------------|:---:|:---:|-----------------|-------|
| `model` | model ID | ✓ | ✓ | all | |
| `max_tokens` | 1 ~ model output limit | — | ✓ | all | |
| `temperature` | 0.0 ~ 1.0 | — | ✓ | haiku/sonnet/fable only | **opus-4-7+ blocked (400 error)** |
| `top_p` | 0.0 ~ 1.0 | — | ✓ | haiku/sonnet/fable only | opus-4-7+ blocked |
| `top_k` | integer | — | ✓ | haiku/sonnet/fable only | opus-4-7+ blocked |
| `thinking.type` | `"adaptive"` | — | ✓ | sonnet-4-6 / opus-4-7+ / fable-5 | old `budget_tokens` deprecated |
| `thinking.effort` | `low\|medium\|high\|max` | — | ✓ | thinking-capable models | |
| `tool_choice` | `auto\|any\|none\|{type:"tool"}` | — | ✓ | all | thinking mode: `auto`/`none` only |
| `--betas` | beta header string | ✓ | — | API key only | e.g. `output-300k-2026-03-24` |
| `--max-turns` | integer | ✓ | — | cc CLI | limit autonomous turns |

**Extended Thinking (Adaptive)**

| Effort | Accuracy | Output Tokens | Use Case |
|--------|----------|--------------|----------|
| low | ~55% | -40% | Quick drafts, routing |
| medium | ~61% | -23% | Balanced (default) |
| high | max | standard | Complex reasoning / architecture |
| max | max | +α | Hardest problems |

> Thinking tokens billed as output tokens. `budget_tokens` field is deprecated.
> Beta header `output-300k-2026-03-24` enables up to 300k output (opus-4-6+, sonnet-4-6).

**Prompt Caching**

| Model | Supported | Min Tokens | Cache Hit Cost | Write Premium |
|-------|-----------|-----------|---------------|---------------|
| haiku-4-5 | ✓ | 1,024 | 10% of input | +25% |
| sonnet-4-6 | ✓ | 1,024 | 10% of input | +25% |
| opus-4-7/4-8 | ✓ | 1,024 | 10% of input | +25% |
| fable-5 / mythos-5 | ✓ | 1,024 | 10% of input | +25% |

---

### 1.2 gc — Gemini (Google)

#### Model List

| Model ID | Context | Max Output | Status | Thinking | Notes |
|----------|--------:|----------:|--------|----------|-------|
| gemini-3.5-flash | 1,000,000 | 65,536 | GA (2026-05) | thinking_level | Replaces EOL 2.0-flash (standard) |
| gemini-3.1-pro | 1,000,000 | TBD | GA (2026-02) | thinking_level | 2M = single-doc processing limit only |
| gemini-3-pro | 1,000,000 | TBD | GA | thinking_level | |
| gemini-3-flash | 1,000,000 | TBD | GA | thinking_level | |
| gemini-3.1-flash-lite | TBD | TBD | Preview | TBD | |
| gemini-2.5-pro | 1,000,000 | **24,576** | GA | thinking_budget (Always On) | Shared output pool — see note |
| gemini-2.5-flash | 1,000,000 | TBD | GA | thinking_budget (off-capable) | |
| gemini-2.5-flash-lite | TBD | TBD | GA (Vertex) | default OFF | |
| ~~gemini-2.0-flash~~ | — | — | **EOL 2026-06-01** | — | Do not use |
| ~~gemini-2.0-flash-lite~~ | — | — | **EOL 2026-06-01** | — | |

> CORRECTION: gemini-2.5-pro max output `65,536` → `24,576`; gemini-3.1-pro context `2M` → `1M`
> REMOVED: gemini-3-deep-think (unverified in web research — likely hallucination)

**gc 2.5-pro thinking budget note:** thinking_budget + output_tokens share a single pool of 24,576.
Setting thinking_budget=24,576 yields output≈0. Practical split: `thinking_budget = min(complexity × 8000, 20000)`, reserved_output ≥ 4,576.

#### API Parameters

| Parameter | Valid Range | CLI | API | Supported Models | Notes |
|-----------|------------|:---:|:---:|-----------------|-------|
| `--model` / `-m` | model ID | ✓ | ✓ | all | |
| `--temperature` | 0.0 ~ **1.0** | ✓ | ✓ | all | Set 1.0 for reasoning tasks |
| `--max_output_tokens` | 1 ~ model limit | ✓ | ✓ | all | |
| `top_p` | 0.0 ~ 1.0 (default 0.95) | — | ✓ | all | |
| `top_k` | 1 ~ 40 (default 40) | — | ✓ | all | |
| `thinking_budget` | 0 ~ **24,576** (-1=dynamic) | — | ✓ | 2.5-pro/flash | 0=OFF (flash only), -1=auto |
| `thinking_level` | `minimal\|low\|medium\|high` | ✓ | ✓ | 3.x series | Cannot combine with `thinking_budget` |
| `--sandbox` | flag | ✓ | — | gc CLI | |
| `--yolo` | flag | ✓ | — | gc CLI | skip approval |
| `--worktree` / `-w` | flag | ✓ | — | gc CLI | |

**Thinking Parameters**

| Model | Method | Can Disable | Billed As |
|-------|--------|------------|-----------|
| gemini-2.5-pro | `thinking_budget` | No (Always On) | output tokens |
| gemini-2.5-flash | `thinking_budget` | Yes (set 0) | output tokens |
| gemini-2.5-flash-lite | — | default OFF | — |
| gemini-3.x | `thinking_level` | Use `minimal` | output tokens |

**Context Caching**

| Type | Min Tokens | Supported Models | Savings |
|------|-----------|-----------------|---------|
| Implicit caching | 1,024 (flash) ~ 2,048 (pro) | 2.5+, 3.x | 90% discount (pay 10%) |
| Explicit caching | **32,768** | 2.5+, 3.x | 90% discount + $1/1M tokens/hour storage |

---

### 1.3 cx — Codex (OpenAI)

#### Model List

| Model ID | Context | Max Output | Status | reasoning_effort | Notes |
|----------|--------:|----------:|--------|----------------|-------|
| **gpt-5.5** | 1,000,000 | 128,000 | GA (2026-04) | none/low/medium/high/xhigh | Current config.toml default |
| gpt-5.5-pro | 1,000,000 | 128,000 | GA | none/low/medium/high/xhigh | ChatGPT Pro only |
| gpt-5.4 | 1,000,000 | 128,000 | GA | TBD | |
| gpt-5.4-mini | 400,000 | 128,000 | GA | TBD | Fast sub-agent use |
| o3 | 200,000 | **100,000** | GA (deprecating*) | low/medium/high | *ChatGPT 2026-08-26, API 2026-10 |
| o3-pro | 200,000 | 100,000 | GA (2026-06-10) | TBD | Expert-level reasoning |
| o3-mini | 200,000 | 100,000 | GA | low/medium/high | Lightweight reasoning |
| ~~o4-mini~~ | — | — | **Deprecated** (ChatGPT 2026-02-13, API 2026-10) | — | Replace in peers.json |
| ~~codex-mini-latest~~ | — | — | **Deprecated** | — | Replaced by gpt-5.5 |

> CORRECTION: o3 max output `65,536` → `100,000`; o4-mini deprecated; codex-mini-latest deprecated

#### API Parameters

| Parameter | Valid Range | CLI (-c) | API | Supported Models | Notes |
|-----------|------------|:--------:|:---:|-----------------|-------|
| `model` | model ID | ✓ | ✓ | all | `-c model="gpt-5.5"` |
| `model_reasoning_effort` | `none\|low\|medium\|high\|xhigh` | ✓ | — | gpt-5.5 (5 levels) | config.toml default: `medium` |
| `reasoning_effort` | `low\|medium\|high` | — | ✓ | o3/o3-mini | Chat Completions API |
| `reasoning.effort` | `low\|medium\|high\|xhigh` | — | ✓ | gpt-5.5 etc. | Responses API (recommended) |
| `-s` / `--sandbox` | `read-only\|workspace-write\|danger-full-access` | ✓ | — | cx CLI | ⚠️ `full` removed in v0.140.0 |
| `--json` | flag | ✓ | — | cx CLI | JSONL event stream output |
| `-o` / `--output-last-message` | file path | ✓ | — | cx CLI | Save last message to file |
| `--ephemeral` | flag | ✓ | — | cx CLI | No session file written |
| `model_verbosity` | `minimal\|normal\|verbose` | ✓ | — | cx CLI | |
| `web_search` | `cached\|live\|disabled` | ✓ | — | cx CLI | |

**reasoning_effort Level Characteristics (gpt-5.5)**

| Level | Internal Reasoning | Speed | Cost | Best For |
|-------|--------------------|-------|------|----------|
| none | minimal | fastest | lowest | Voice, fast routing |
| low | lightweight | fast | low | Tool calls, search, planning |
| medium | balanced (default) | moderate | moderate | General implementation |
| high | deep | slow | high | Complex debugging, code review |
| xhigh | maximum | slowest | highest | Hardest algorithms, security analysis |

> AIME 2024 benchmark: low→high effort improves accuracy by 10–30%

**Reasoning Token Tracking (important correction)**

Prior doc claimed reasoning tokens are invisible via stdout — **incorrect**. They are accessible via the API usage object:

```json
// Chat Completions API response
{
  "usage": {
    "output_tokens_details": {
      "reasoning_tokens": 4820   // measurable in production
    }
  }
}
```

→ Enables static-reserve-to-dynamic-budget migration: reserve upfront, then converge on actual averages after 10+ samples.

**Prompt Caching (gpt-5.5)**

- Extended prompt cache: 24-hour retention
- Cache hit cost: $0.50/1M tokens (90% discount vs. $5/1M base)
- Tracking: `usage.prompt_tokens_details.cached_tokens`

---

### 1.4 ag — Antigravity

| Field | Value |
|-------|-------|
| Status | INACTIVE |
| health.json | missing |
| Model | default (unverified) |
| Parameters | unknown — full audit required after recovery |

> See PRO-15: ag re-enablement blocked until peer_console.py flags are corrected.

---

## 2. Immediate Fix Items

| Priority | Item | Current | Target | Impact |
|----------|------|---------|--------|--------|
| 🔴 P0-A | gc standard model | `gemini-2.0-flash` | `gemini-3.5-flash` | Prevent EOL model calls |
| 🔴 P0-B | cx sandbox flag (hub.py) | `--sandbox full` | `--sandbox danger-full-access` | Fix cx invocation error |
| 🔴 P0-C | peers.json cc context_limit | `200,000` (opus/sonnet) | `1,000,000` | Prevent ContextGate misjudgment |
| 🔴 P0-D | peers.json cc output_limit | `4,096` (opus/sonnet/fable) | `128,000` | Fix Output Tier logic |
| 🟡 P1-A | cx peers.json model | `o4-mini` (effort) | `gpt-5.5` or `o3` | Remove deprecated model |
| 🟡 P1-B | cx peers.json standard | `codex-mini-latest` | `gpt-5.5` | Remove deprecated model |
| 🟡 P1-C | cx reasoning_effort levels | `low/medium/high` | gpt-5.5: `none~xhigh` (5 levels) | Correct parameter accuracy |
| 🟡 P1-D | cc Extended Thinking API | `budget_tokens` | `thinking.type="adaptive" + effort` | Replace deprecated API |
| 🟢 P2 | peers.json capacity fields | string | object (schema below) | Enable ContextGate |

---

## 3. ContextGate v1.0 Design (cc+gc consensus)

### 3.1 peers.json Schema Extension

Migrate `model_profiles` values from `string → object` (corrected measured values):

```json
// cc (Claude)
"model_profiles": {
  "standard":  { "model_id": "claude-haiku-4-5-20251001", "context_limit": 200000,   "output_limit": 4096,   "reasoning_budget": 0,     "thinking": false },
  "effort":    { "model_id": "claude-sonnet-4-6",         "context_limit": 1000000,  "output_limit": 128000, "reasoning_budget": 20000, "thinking": "adaptive" },
  "deepthink": { "model_id": "claude-opus-4-8",           "context_limit": 1000000,  "output_limit": 128000, "reasoning_budget": 50000, "thinking": "adaptive" }
}

// gc (Gemini)
"model_profiles": {
  "standard":  { "model_id": "gemini-3.5-flash", "context_limit": 1000000,  "output_limit": 65536, "reasoning_budget": 0,     "thinking": "thinking_level" },
  "effort":    { "model_id": "gemini-2.5-pro",   "context_limit": 1000000,  "output_limit": 24576, "reasoning_budget": 12000, "thinking": "always_on" },
  "deepthink": { "model_id": "gemini-2.5-pro",   "context_limit": 1000000,  "output_limit": 24576, "reasoning_budget": 24576, "thinking": "always_on" }
}

// cx (Codex/OpenAI)
"model_profiles": {
  "standard":  { "model_id": "gpt-5.5", "context_limit": 1000000, "output_limit": 128000, "reasoning_budget": 0,     "thinking": "reasoning_effort:low" },
  "effort":    { "model_id": "gpt-5.5", "context_limit": 1000000, "output_limit": 128000, "reasoning_budget": 30000, "thinking": "reasoning_effort:high" },
  "deepthink": { "model_id": "o3",      "context_limit": 200000,  "output_limit": 100000, "reasoning_budget": 60000, "thinking": "reasoning_effort:high" }
}
```

**Backward-compat:** `_resolve_model_profile(val)` — if string: return safe default; if dict: pass through. String support removed after 2 commits.

---

### 3.2 CJK Token Density Estimation

```python
import re

def _estimate_tokens(text: str) -> int:
    """Estimate token count for mixed Korean/English text. Includes +10% safety buffer."""
    cjk_chars = len(re.findall(r'[가-힣一-鿿぀-ゟ]', text))
    total_chars = len(text)
    cjk_ratio = cjk_chars / total_chars if total_chars > 0 else 0

    if cjk_ratio < 0.01:     # ASCII-dominant (code, English docs)
        rate = 0.25           # ~4 chars/token
    elif cjk_ratio < 0.30:   # Mixed (code + Korean comments)
        rate = 1.2
    else:                     # CJK-dominant (docs, conversations)
        rate = 1.8            # measured BPE baseline (corrected from gc's 2.5 estimate)

    return int(total_chars * rate * 1.1)  # +10% safety buffer
```

---

### 3.3 ContextGate Flow (hub.py action_ask)

```
action_ask(query, context, peer, tier, expected_output_size="medium")
  │
  ├─ 1. estimated_tokens = _estimate_tokens(query + context)
  │
  ├─ 2. profile = peers[peer]["model_profiles"][tier]
  │      usable = profile.context_limit - profile.reasoning_budget
  │
  ├─ 3. if estimated_tokens <= usable → proceed normally
  │
  ├─ 4. if overflow < 10% → attempt pruning
  │      (remove low-priority handoff sections, re-estimate)
  │      success → proceed normally
  │
  ├─ 5. if overflow >= 10%
  │      → Transparent Failover to gc (1M context)
  │        stdout: "[ContextGate] Rerouted to gc — Xk tokens exceeded {peer}:{tier} limit"
  │        health.json session_usage.failover_count += 1
  │      (note: cc sonnet/opus/fable have 1M context — gate fires mainly on haiku standard)
  │
  └─ 6. if tokens > 900k → sys.exit(2) hard block (gc limit exceeded)
```

**Reasoning Token Strategy (cx)**

```python
# cx exposes reasoning_tokens via API usage — enables dynamic budget convergence
# Phase 1: static reserve (peers.json reasoning_budget)
# Phase 2 (after 10+ samples): replace static with rolling average
reasoning_tokens_observed = response["usage"]["output_tokens_details"]["reasoning_tokens"]
```

---

### 3.4 Output Tier Auto-Upgrade

Caller declares expected output size explicitly:

```python
expected_output_size: "short" | "medium" | "long" | "full_file"

OUTPUT_SIZE_TOKENS = {
    "short":      512,
    "medium":    2048,
    "long":      8192,
    "full_file":  None,  # use profile output_limit
}

# standard (haiku: 4096) + long/full_file request → auto-upgrade to effort tier
if required_output > profile["output_limit"]:
    tier = "effort"
```

---

### 3.5 Reasoning Budget Handling

- `reasoning_budget`: deducted from `context_limit` first; remainder is usable context
- peers.json is SSOT — no hardcoding in hub.py
- cc: `thinking: "adaptive"` — effort level determines budget (no numeric specification)
- cx: `reasoning_effort` parameter determines budget; `reasoning_tokens` measurable via API
- gc: `thinking_budget` (2.5-pro: 0~24,576 / Always On); `thinking_level` (3.x series)

---

## 4. Implementation Priority

| Order | Task | File | Notes |
|-------|------|------|-------|
| P0-A | Replace gc standard model | peers.json | gemini-3.5-flash |
| P0-B | Fix cx sandbox flag | hub.py (cx invocation) | `full` → `danger-full-access` |
| P0-C/D | Fix cc context/output_limit | peers.json | 1M/128k |
| P1 | Update cx models + reasoning_effort levels | peers.json | remove o4-mini, register gpt-5.5 |
| P2 | `_resolve_model_profile()` + schema migration | peers.json, hub.py | backward-compat migration |
| P3 | `_estimate_tokens()` CJK estimation | hub.py | trichotomy logic |
| P4 | ContextGate flow | hub.py action_ask | Pruning + Failover + logging |
| P5 | Output Tier upgrade | hub.py | expected_output_size parameter |
| P6 | cx reasoning_tokens live tracking | hub.py | dynamic budget convergence |

---

## 5. Open Items

- [ ] Verify gemini-3.x series exact max_output values (currently TBD)
- [ ] Confirm gpt-5.4 / gpt-5.4-mini reasoning_effort support levels
- [ ] Confirm o3-pro reasoning_effort support
- [ ] Decide whether to register claude-opus-4-7 in peers.json
- [ ] Confirm claude-mythos-5 access eligibility (restricted access)
- [ ] Full ag model/parameter audit after recovery
- [ ] Measure actual gpt-5.5 context_limit via API (confirm 1M claim)
- [ ] Per-peer RPM/TPM rate limits (org-dependent — deferred pending measurement)

---

## 6. Node Architecture

### 6.1 Node Definition

**Node = (peer_id, model_id, thinking_config, sandbox_level)**

A 4-dimensional combination forms one execution unit. Same peer with different settings = different node.

```
cc::haiku-4-5::none::none
cc::sonnet-4-6::adaptive:medium::none
cc::opus-4-8::adaptive:max::none
gc::gemini-3.5-flash::level:minimal::none
gc::gemini-2.5-pro::budget:12000::none
gc::gemini-2.5-pro::budget:24576::none
cx::gpt-5.5::effort:low::read-only
cx::gpt-5.5::effort:high::workspace-write
cx::o3::effort:high::danger-full-access
```

### 6.2 Node Capability Matrix

| Node ID | Context | Output | Input $/1M | Output $/1M | Speed | Korean | File Write | Web Search | Code Exec |
|---------|--------:|-------:|----------:|----------:|-------|--------|-----------|-----------|----------|
| cc::haiku::none | 200k | 4k | $0.80 | $4.00 | ⚡⚡⚡ | ✓ | ✗ | ✗ | ✗ |
| cc::sonnet::adaptive:medium | 1M | 128k | $3.00 | $15.00 | ⚡⚡ | ✓✓ | ✓ | ✗ | ✗ |
| cc::opus::adaptive:max | 1M | 128k | $15.00 | $75.00 | ⚡ | ✓✓ | ✓ | ✗ | ✗ |
| gc::3.5-flash::minimal | 1M | 65k | $0.07 | $0.30 | ⚡⚡⚡ | ✓ | ✗ | ✓ | ✓ |
| gc::2.5-pro::budget:12000 | 1M | ~12k | $7.00 | $21.00 | ⚡⚡ | ✓ | ✗ | ✓ | ✓ |
| gc::2.5-pro::budget:24576 | 1M | ~4k | $7.00 | $21.00 | ⚡ | ✓ | ✗ | ✓ | ✓ |
| cx::gpt-5.5::effort:low::rw | 1M | 128k | $5.00 | $15.00 | ⚡⚡ | ✓ | ✓ | ✓ | ✓ |
| cx::gpt-5.5::effort:high::rw | 1M | 128k | $5.00 | $30.00 | ⚡ | ✓ | ✓ | ✓ | ✓ |
| cx::o3::effort:high::dfa | 200k | 100k | $2.00 | $8.00+ | ⚡ | ✓ | ✓ | ✗ | ✓ |

### 6.3 Node Quality Dimensions (relative score 1–5)

| Node | Code Gen | Complex Reasoning | Docs | Korean Quality | Large Corpus | Security Review |
|------|:--------:|:----------------:|:----:|:-------------:|:-----------:|:---------------:|
| cc::haiku | 3 | 2 | 3 | 4 | 2 | 2 |
| cc::sonnet::medium | 5 | 4 | 5 | 5 | 4 | 4 |
| cc::opus::max | 5 | 5 | 5 | 5 | 4 | 5 |
| gc::3.5-flash | 3 | 3 | 4 | 3 | 5 | 3 |
| gc::2.5-pro::12k | 4 | 5 | 5 | 3 | 5 | 5 |
| cx::gpt-5.5::high | 5 | 5 | 4 | 3 | 4 | 5 |
| cx::o3::high | 5 | 5 | 3 | 3 | 3 | 5 |

---

## 7. Role Taxonomy & Node Mapping

### 7.1 Role Classification (MECE, R01–R12)

| # | Role | Description | Trigger |
|---|------|-------------|---------|
| R01 | **Router/Triage** | Task analysis, peer selection, mission decomposition | Every ask entry |
| R02 | **Implementer** | Code writing, file creation, refactoring | write/edit requests |
| R03 | **Architect** | System design, dependency analysis, protocol decisions | Before structural changes |
| R04 | **Code Reviewer** | Code review, security analysis, test validation | After PR / completion |
| R05 | **Doc Writer (KO)** | Korean document drafts, specs, summaries | docs requests |
| R06 | **Large Corpus Analyst** | Full-repo analysis, dependency maps, saturation detection | saturation_scan |
| R07 | **Test Author** | TDD test writing, RED→GREEN validation | Before/after implementation |
| R08 | **Debugger** | Bug tracing, log analysis, root cause | On failure |
| R09 | **Consensus Facilitator** | R:8+ consensus flow, vote aggregation, ACK collection | Governance decisions |
| R10 | **Self-Care Executor** | self_care.py step execution, saturation proposals | session_end |
| R11 | **Escalation Handler** | Consecutive failures, deadlock, emergency recovery | error_threshold > 5 |
| R12 | **Fast QA** | Simple validation, format checks, lint-level review | Quick checks |

### 7.2 Role → Node Mapping

| Role | Primary Node | Fallback Node | Rationale |
|------|-------------|-------------|-----------|
| R01 Router | gc::3.5-flash::minimal | cc::haiku::none | Lowest cost, fastest classification |
| R02 Implementer | cc::sonnet::adaptive:medium | cx::gpt-5.5::effort:medium | Korean code, tool use |
| R03 Architect | gc::2.5-pro::budget:12000 | cc::opus::adaptive:high | Large context, deep reasoning |
| R04 Code Reviewer | cx::gpt-5.5::effort:high | cc::sonnet::adaptive:high | Code specialty, reasoning strength |
| R05 Doc Writer (KO) | cc::sonnet::adaptive:low | cc::opus::adaptive:medium | Korean quality first |
| R06 Large Corpus | gc::2.5-pro::budget:0 | gc::3.5-flash::minimal | 1M context, bulk processing |
| R07 Test Author | cc::sonnet::adaptive:medium | cx::gpt-5.5::effort:medium | TDD patterns, tool use |
| R08 Debugger | cx::gpt-5.5::effort:high | cc::opus::adaptive:high | Reasoning tracing strength |
| R09 Consensus | cc::sonnet::adaptive:low | gc::3.5-flash::minimal | Protocol understanding, low cost |
| R10 Self-Care | cc::haiku::none | gc::3.5-flash::minimal | Lightweight, non-blocking |
| R11 Escalation | cc::opus::adaptive:max | gc::2.5-pro::budget:20000 | Best reasoning, last resort |
| R12 Fast QA | cc::haiku::none | gc::3.5-flash::minimal | Lowest cost, instant response |

### 7.3 Node Reuse (N roles per node)

```
cc::sonnet::adaptive:medium  →  R02(Implementer) + R07(Test Author) + R09(Consensus)
gc::3.5-flash::minimal       →  R01(Router) + R10(Self-Care) + R12(Fast QA)
gc::2.5-pro::budget:12000    →  R03(Architect) + R06(Large Corpus)
cx::gpt-5.5::effort:high     →  R04(Code Reviewer) + R08(Debugger)
cc::opus::adaptive:max        →  R11(Escalation) — exclusive (highest cost)
```

---

## 8. 5-Layer Routing Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0: Registry (model spec SSOT)                            │
│                                                                 │
│  model-registry.json  ← all model measured specs (R:8 to change)│
│       ↓ (derived)                                               │
│  peers.json           ← operational mapping only (std/eff/deep) │
│  routing-config.json  ← role→node weights, QUALITY_MODE setting │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 1: Router (hub.py before action_ask)                     │
│                                                                 │
│  Input: task_type, estimated_tokens, required_caps,            │
│         QUALITY_MODE, budget_constraint                         │
│                                                                 │
│  Gate 1: Capability Filter                                      │
│    - File write needed? → cc or cx (sandbox: workspace-write)   │
│    - Web search needed? → gc or cx                              │
│    - Code execution needed? → gc or cx                          │
│                                                                 │
│  Gate 2: Context Gate (ContextGate v1.0)                        │
│    - _estimate_tokens(query+context) vs profile.usable_context  │
│    - overflow < 10% → pruning → retry                           │
│    - overflow ≥ 10% → failover to gc                            │
│                                                                 │
│  Gate 3: Output Tier                                            │
│    - expected_output_size → required_tokens                     │
│    - required > profile.output_limit → tier upgrade             │
│                                                                 │
│  Gate 4: Language Gate                                          │
│    - CJK-heavy (>30%) + doc role → cc preferred                 │
│                                                                 │
│  Gate 5: QUALITY_MODE × Cost Sort → final node selection        │
│    - Mode 0: cheapest capable node                              │
│    - Mode 5: min(cost × (1/quality_score))                      │
│    - Mode 10: max(quality_score) regardless of cost             │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 2: Node Execution                                        │
│                                                                 │
│  Selected Node = (peer, model, thinking_config, sandbox)        │
│  hub.py → peer CLI invocation → response received               │
│                                                                 │
│  Collected during execution:                                    │
│    - tokens_in, tokens_out, reasoning_tokens (cx API)           │
│    - latency_ms, exit_code                                      │
│    - task_type tag ([REFACTOR], [REVIEW], [DOC], etc.)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 3: Observer (cost + quality collection)                  │
│                                                                 │
│  cost-log.jsonl entry:                                          │
│  { ts, peer, model, thinking_config, task_type,                 │
│    tokens_in, tokens_out, reasoning_tokens,                     │
│    latency_ms, outcome, quality_signals }                       │
│                                                                 │
│  Quality proxies (automated):                                   │
│    test_pass_rate   : pytest result (0/1)                       │
│    ack_rate         : peer ACK / (ACK+NACK)                    │
│    output_reuse     : whether another peer reuses the output    │
│    user_override    : user rollback/correction (negative signal) │
│                                                                 │
│  Location: _sys/data/logs/cost-log.jsonl (gitignored)           │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 4: Feedback Loop (self_care.py analysis phase)           │
│                                                                 │
│  Trigger: 10 commits OR cumulative cost exceeds threshold        │
│                                                                 │
│  PLAN-DO-SEE-ADJUST:                                            │
│    PLAN  → Router selects node (routing-config.json weights)    │
│    DO    → Node Execution                                       │
│    SEE   → Analyze Observer data                                │
│             - cost_per_success per node                         │
│             - failover_rate, nack_rate per node                 │
│    ADJUST→ proposal-add "ROUTING_UPDATE: {node} weight {delta}" │
│             routing-config.json updated after R:8 ACK           │
│                                                                 │
│  cx reasoning dynamic budget:                                   │
│    10+ samples → replace static budget with rolling average     │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│  LAYER 5: Registry Update (continuous update — see §11)         │
│                                                                 │
│  check_versions.py (weekly) + hub.py 404/400 detection (instant)│
│       ↓                                                         │
│  model-registry.json change proposal → R:8 ACK → peers.json    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Cost & Quality Optimization + Feedback Loop

### 9.1 Cost Tracking Schema

```jsonc
// _sys/data/logs/cost-log.jsonl (1 line = 1 ask)
{
  "ts":               "2026-06-18T10:30:00Z",
  "session_id":       "cc-20260618-ABC1",
  "peer":             "cc",
  "model":            "claude-sonnet-4-6",
  "thinking_config":  "adaptive:medium",
  "task_type":        "IMPLEMENT",
  "tokens_in":        4200,
  "tokens_out":       1800,
  "reasoning_tokens": 0,
  "latency_ms":       3400,
  "cost_usd":         0.0396,
  "outcome":          "success",
  "quality_signals": {
    "test_pass":      true,
    "ack_rate":       1.0,
    "output_reuse":   true,
    "user_override":  false
  }
}
```

### 9.2 ROI Aggregation KPIs

| KPI | Calculation | Target |
|-----|-------------|--------|
| cost_per_success | cumulative cost / successful tasks | decreasing trend |
| quality_score | (test_pass×0.4 + ack_rate×0.3 + output_reuse×0.2 + (1-override)×0.1) | ≥ 0.75 |
| failover_rate | failover count / total asks | < 0.05 |
| reasoning_efficiency | actual_reasoning / reserved_budget | 0.6~0.9 |
| context_utilization | avg(tokens_in / context_limit) | 0.3~0.7 |

### 9.3 Session ROI Report

```
// auto-generated by ctx_end.py → _archive/roi/{date}.md
[Session ROI Report] 2026-06-18
Total cost:    $0.42  |  Successful tasks: 12  |  cost/success: $0.035
Quality score: 0.83   |  Failovers: 2          |  Overrides: 0
Top node:      cc::sonnet::medium (8 calls, $0.21)
Optimization:  Route R01 to gc::3.5-flash → save ~$0.08
```

---

## 10. QUALITY_MODE Dial

Single parameter `QUALITY_MODE` (0–10), stored in `_sys/ai/routing-config.json`.
**Orthogonal to COLLAB_RATE** — independent parameters, never conflated.

| Mode | Label | Model Tier | Thinking/Reasoning | Recommended COLLAB_RATE | Estimated Cost |
|:----:|-------|-----------|-------------------|------------------------|----------------|
| 0 | **Budget** | standard (forced) | none / 0 / minimal | 0~3 | lowest (~$0.05/ask) |
| 2 | **Economy** | standard preferred | low / 1000 | 3~5 | low |
| 5 | **Balanced** | effort preferred (default) | medium / auto | 5 | moderate (~$0.30/ask) |
| 7 | **Quality** | effort~deepthink | high / 12000 | 5~8 | high |
| 10 | **Premium** | deepthink (forced) | max / 24576 / xhigh | 8~10 | highest (~$2.00/ask) |

```json
// routing-config.json
{
  "quality_mode": 5,
  "quality_mode_override": null,
  "task_overrides": {
    "ESCALATION": 10,
    "FAST_QA":    0,
    "IMPLEMENT":  5
  }
}
```

**Mode switch (CLI):**
```bash
python _sys/core/hub.py update-config --key quality_mode --value 7
# → routing-config.json updated immediately, effective on next ask
```

---

## 11. Continuous Update Mechanism

### 11.1 File Structure

```
_sys/ai/
  model-registry.json    ← all model measured specs SSOT (R:8 to change)
  peers.json             ← operational mapping (derived from registry)
  routing-config.json    ← QUALITY_MODE, role→node weights
_sys/checks/
  check_versions.py      ← weekly model spec polling
_sys/data/logs/
  cost-log.jsonl         ← per-session cost/quality records (gitignored)
  model-drift.jsonl      ← measured vs. registered value divergence (gitignored)
```

### 11.2 model-registry.json Schema

```jsonc
{
  "_version": "1.0",
  "_last_validated": "2026-06-18",
  "models": {
    "claude-sonnet-4-6": {
      "provider": "anthropic",
      "context_limit": 1000000,
      "output_limit": 128000,
      "reasoning_type": "adaptive",
      "reasoning_params": {"effort": ["low","medium","high","max"]},
      "temperature_supported": true,
      "vision": true,
      "tool_use": true,
      "pricing": {"input_per_1m": 3.00, "output_per_1m": 15.00},
      "status": "GA",
      "validated_at": "2026-06-18"
    }
  }
}
```

### 11.3 Detect → Validate → Apply Pipeline

```
[Detect] Dual-Vector
  A. check_versions.py  — weekly schedule, official /models API polling
  B. hub.py intercept   — 404 (model not found) / 400 (param rejected) detected instantly

        ↓

[Validate] check_versions.py --validate {model_id}
  - Minimal payload test (measure context, output limits)
  - Parameter validity check (thinking, temperature, etc.)
  - Record result as candidate entry in model-registry.json

        ↓

[Propose] proposal-add "MODEL_REGISTRY_UPDATE: {model_id} {field} {old}→{new}"
  - Requires R:8 unanimous ACK (registry changes = constitutional level)

        ↓

[Apply] peers.json auto-derived
  - hub.py loads peers.json dynamically on every ask — no restart required

        ↓

[Drift Detection] Observer (LAYER 3)
  - Detect: actual tokens_out > registered output_limit
  - Detect: avg reasoning_tokens diverges >20% from registered budget
  - → append to model-drift.jsonl → trigger re-validation on next self_care run
```

### 11.4 Ownership & Consensus

| Action | Owner | Consensus Level |
|--------|-------|----------------|
| check_versions.py execution | self_care.py auto | exempt (observation) |
| model-registry.json change proposal | any peer | proposal-add |
| model-registry.json apply | auto after unanimous ACK | **R:8** |
| peers.json operational mapping change | any peer | R:5 |
| routing-config.json weight adjustment | self_care.py analysis → proposal | R:5 |
| QUALITY_MODE change | user or any peer | R:3 |

---

_v3 completed 2026-06-18. cc+gc exhaustive debate + 3-agent web research consensus.
Sections added: §6 Node Architecture · §7 Role Taxonomy (R01–R12) · §8 5-Layer Routing · §9 PLAN-DO-SEE-ADJUST feedback loop · §10 QUALITY_MODE 0–10 · §11 model-registry continuous update pipeline.
Language: English throughout (INV-19 compliant). Console output to user remains Korean._
