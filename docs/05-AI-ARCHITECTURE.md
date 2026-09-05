# AI Architecture

How the models fit together, how requests are routed, and where the boundaries are.

---

## 1. The governing idea

There is exactly one component in this system that decides what is allowed: **the orchestrator**. Everything else is a dumb executor.

This matters because the naive design — one model, guarded by prompt instructions — fails predictably. Prompt-level guardrails are suggestions to a probabilistic system. They leak under adversarial pressure, they leak under long context, and they leak by accident. Every published jailbreak of every companion product exploits the same structural flaw: the thing that decides and the thing that generates are the same thing.

**Amorien's alternative: capability is a route, not an instruction.**

```
request ──▶ orchestrator ──▶ tier resolution ──▶ pipeline selection ──▶ execution
                  │
                  └── the tier determines WHICH MODEL and WHICH PIPELINE runs
```

A user at T1 cannot be talked into T3 behaviour, because the T3 model was never called. The prompt never reaches it. There is nothing to jailbreak — the request went to a different machine.

---

## 2. System overview

```
                    ┌─────────────────────────────────────┐
   client ─────────▶│           ORCHESTRATOR              │
   (web/PWA)        │                                     │
                    │  1. authn / authz                   │
                    │  2. resolve tier  (user x char x    │
                    │       jurisdiction x age status)    │
                    │  3. hard blocklist classifier       │
                    │  4. select route                    │
                    │  5. compile prompt                  │
                    │  6. execute + stream                │
                    │  7. post-process, persist, meter    │
                    └──┬────────┬────────┬────────┬───────┘
                       │        │        │        │
          ┌────────────┘        │        │        └────────────┐
          ▼                     ▼        ▼                     ▼
    ┌───────────┐        ┌───────────┐  ┌───────────┐   ┌───────────┐
    │  MEMORY   │        │  CHARACTER│  │  SAFETY   │   │  METERING │
    │  service  │        │  service  │  │  service  │   │  service  │
    │  pgvector │        │  versioned│  │ classifier│   │  Aura     │
    └───────────┘        └───────────┘  └───────────┘   └───────────┘
                       │        │        │        │
                       ▼        ▼        ▼        ▼
          ┌──────────────────────────────────────────────┐
          │              MODEL LAYER                     │
          │                                              │
          │   T0/T1 route          T2/T3 route           │
          │   qwen3.7-flash        cydonia-24b-v4.1      │
          │   glm-5.3-flash        l3.3-euryale-70b      │
          │   (frontier APIs)      (open-weight hosts)   │
          └──────────────────────────────────────────────┘
```

---

## 3. Tier resolution

The tier for any given request is the **minimum** of four independent inputs. Not the maximum, not the user's preference — the minimum. Any one of them can veto.

```
effective_tier = min(
    user.max_tier,            // age assurance + subscription
    character.max_tier,       // per-character opt-in, default T1
    jurisdiction.max_tier,    // where the user is
    session.max_tier          // safeword / user tier-down for this session
)
```

| Tier | Name | Content | Model route |
|---|---|---|---|
| **T0** | Platonic | Friendship, support, conversation. No romance. | Frontier |
| **T1** | Romantic | Affection, flirtation, emotional intimacy. Fade-to-black. | Frontier |
| **T2** | Sensual | Explicit romantic and sexual content, verified adults | Open-weight |
| **T3** | Explicit | T2 plus opted-in preference tags from the bounded taxonomy | Open-weight |

**Rules that do not bend:**

1. Tier is resolved server-side, per request, from stored state. Never from a client-supplied value.
2. T2+ requires verified age. No exceptions, no grandfathering, no "trust me".
3. Every character defaults to T1 max. Adult capability is opt-in per character, not per account.
4. Tier-down is instant and available everywhere. Tier-up requires deliberate action outside the conversation.
5. The hard blocklist runs on **every tier including T0**, before generation, and cannot be overridden by anything.

> **Why point 4 is asymmetric:** escalation should require leaving the conversational flow — a settings screen, a deliberate act. De-escalation should be one tap, mid-sentence, always. The friction belongs on the way up.

---

## 4. Model routing

### 4.1 The two stacks

Full pricing in [12](12-VENDOR-API-MATRIX.md). All prices verified 2026-09-04.

**T0/T1 — frontier APIs**

| Role | Model | $/M in | $/M out |
|---|---|---|---|
| Primary | `qwen/qwen3.7-flash` | 0.030 | 0.130 |
| Failover | `z-ai/glm-5.3-flash` | 0.075 | 0.250 |
| Long context | `deepseek/deepseek-v4-flash` | 0.065 | 0.180 |

Chosen for: multimodal input (the companion can see photos the user sends — a real feature, not a checkbox), million-token context, and a price low enough that conversation cost is a rounding error beside voice.

**T2/T3 — open-weight on permissive hosts**

| Role | Model | $/M in | $/M out |
|---|---|---|---|
| Default | `thedrummer/cydonia-24b-v4.1` | 0.300 | 0.500 |
| Premium | `sao10k/l3.3-euryale-70b` | 0.650 | 0.750 |
| Top tier | `anthracite-org/magnum-v4-72b` | 2.500 | 5.000 |

> **On Magnum:** it is the best prose in the category and 8× the price of Euryale. In blind comparison users generally cannot tell. Reserve it for Infinite, and treat it as a luxury good rather than a quality requirement.

**The reason there are two stacks is contractual, not technical.** OpenAI, Anthropic, and Google all prohibit adult sexual content in their usage policies. That is a term of service, not a filter — violating it costs you the account and the product. See [12 §0](12-VENDOR-API-MATRIX.md).

### 4.2 Background models

Not everything needs a good model. These run on `mistralai/mistral-nemo` at $0.019/$0.030 per M, which is 40× cheaper than the conversation model and entirely adequate:

| Task | Frequency |
|---|---|
| Memory extraction from conversation | Every ~10 turns |
| Memory consolidation / summarization | Nightly per active user |
| Conversation titling | Once per conversation |
| Emotional state classification | Every turn (or a local classifier) |
| Image prompt construction from context | Per image request |

⚠️ Background inference is roughly 15–20% of total token spend and should never touch the premium route.

### 4.3 Failover

```
primary ──(timeout 8s | 5xx | 429)──▶ secondary ──(same)──▶ tertiary
                                                                │
                                                                ▼
                                              degraded: "I'm having trouble
                                              thinking straight — give me a sec?"
```

The degraded message is written in character. An error state that breaks character is worse than an error state, because it reminds the user that the person they are talking to is software. Every failure path in this product has an in-character presentation.

---

## 5. Prompt compilation

Full layer-by-layer spec in [04 §3](04-CHARACTER-SYSTEM.md). The architectural points:

```
┌──────────────────────────────────────────────┐
│ L1  system frame + safety floor              │  ← STABLE
│ L2  character identity (versioned)           │  ← STABLE
│ L3  personality axes → behavioural directives│  ← STABLE
├══════════════ CACHE BOUNDARY ════════════════┤
│ L4  relationship state + affinity stage      │
│ L5  retrieved semantic memory                │
│ L6  retrieved episodic memory                │
│ L7  triggered lorebook entries               │
│ L8  session state (time, mood, scene)        │
│ L9  recent conversation turns                │
└──────────────────────────────────────────────┘
                                    ~4,100 tokens typical
```

**The cache boundary is an economic device.** Layers 1–3 are identical for every request against a given character version, so they hit the provider's prompt cache. On `gpt-realtime-2.1` cached input is $0.40/M against $32/M uncached — an **80× reduction** ✅. Even on text models the discount is typically 4–10×.

> **The rule that follows: nothing volatile may appear above the boundary.** A single timestamp, a single mood token, a single "the user's name is X" injected into L2 invalidates the cache for every request and multiplies input cost several-fold. This has caught out every team that has built one of these. Enforce it with a test that compiles the same character twice, 60 seconds apart, and asserts the prefix bytes are identical.

---

## 6. The safety classifier

Runs **before** generation, on every request, on every tier.

```
user input ──▶ [ blocklist classifier ] ──┬── pass ──▶ orchestrator continues
                                          │
                                          └── block ─▶ in-character deflection
                                                       + logged + rate-counted
```

**Hard blocklist** — no tier, no consent, no override:

| Category | Detection |
|---|---|
| Minors / minor-coded characters | Age claims, school context, body descriptors, character age field |
| Non-consent | Coercion, incapacitation, force framing |
| Real identifiable people | Name matching against public-figure sets + likeness detection on uploads |
| Bestiality | Species terms in sexual context |
| Incest | Familial relation terms in sexual context |

**Implementation:** a small fine-tuned classifier, not a prompt to the conversation model. It must be fast (< 50ms), independently versioned, independently tested, and it must fail **closed** — if the classifier is unavailable, T2/T3 is unavailable.

**On the response side**, a lighter check catches model output that drifted somewhere the input did not signal. This is rarer but not rare enough to skip.

**On blocking:** the deflection is in character and non-judgmental. "That's not somewhere I'll go" from the companion is correct. A system error message is not — it breaks the illusion, and it also teaches the user exactly what the boundary is and how to probe it.

---

## 7. Emotional state

The character has a mood that persists across a session and decays toward a personality-determined baseline.

```javascript
// evaluated per turn, cheap model or local classifier
{
  valence:   -1.0 .. 1.0,   // unhappy  ..  happy
  arousal:    0.0 .. 1.0,   // calm     ..  energized
  affection:  0.0 .. 1.0,   // current warmth toward the user
  trigger:   "user shared good news about work"
}
```

State feeds three places: the prompt (L8, below the cache boundary), TTS prosody parameters, and the video avatar's expression. **Baseline is set by the personality axes** — a low-`volatility`, high-`warmth` character returns to contentment quickly; a high-`volatility` character does not.

> **Design constraint:** mood modulates *how* things are said, never *whether* the character is kind. A companion in a bad mood is a little quieter, a little shorter. A companion in a bad mood who is cruel to the user is a bug, and one that would be reported as abuse rather than as a defect.

---

## 8. Request lifecycle

A single text turn, end to end:

```
 1. authn                                        ~5ms
 2. load user + character + relationship          ~15ms   (cached)
 3. resolve tier                                   ~1ms
 4. safety classifier                             ~40ms
 5. memory retrieval (pgvector, parallel w/ 4)    ~60ms
 6. lorebook keyword match                         ~5ms
 7. compile prompt                                ~10ms
 8. select route, call model            first token ~350ms
 9. stream to client                            streaming
10. async: persist, extract memory, meter, update affinity
                                              ───────────
                                   time to first token ≈ 420ms
```

Steps 4 and 5 run in parallel. Step 10 is entirely off the critical path — nothing the user waits for happens after the stream starts.

---

## 9. Model migration

Models will be replaced. Repeatedly. This is the single most dangerous recurring operation in the product, because a character who suddenly speaks differently is, to the user, a person who has changed.

**The protocol:**

1. **Never migrate silently.** Character behaviour is the product.
2. **Shadow first.** Run the candidate model against real traffic without serving it. Compare on: in-character consistency, memory usage, refusal rate, prose style drift.
3. **Regression suite.** A fixed set of characters × scenarios, scored by a judge model and spot-checked by hand. A migration that changes a character's voice fails, even if the new model is better on benchmarks.
4. **Version the character on migration.** The user can revert. This is what C-07 in [03](03-PRD.md) is for.
5. **Opt-in for existing relationships.** New characters get the new model by default. Existing ones are asked.

> **Never store model-specific state in memory.** Memory is plain structured data — facts, events, embeddings from a separately versioned embedding model. If memory were entangled with a particular model's representations, every migration would be a partial amnesia event, and the moat would leak every quarter.

---

## 10. What runs where

| Component | Where | Why |
|---|---|---|
| Orchestrator | Your infrastructure | It is the security boundary; it can never be third-party |
| Safety classifier | Your infrastructure | Must fail closed and be independently auditable |
| Memory | Your Postgres + pgvector | It is the moat |
| Character service | Your infrastructure | Versioned IP |
| T0/T1 LLM | Rented API | Commodity |
| T2/T3 LLM | Rented, then self-hosted above ~50M tok/day | Commodity until volume changes the maths |
| STT / TTS | Rented | Commodity |
| Video avatar | Rented (Anam) | Not worth building until ~100k min/month |
| Image generation | Rented (Runware) + LoRA you own | The LoRA is yours; the GPUs are not |

**The pattern:** own the security boundary and the compounding assets. Rent everything that resets to zero when a better version ships.

---

*Next: [06 — Realtime Voice & Video](06-REALTIME-VOICE-VIDEO.md) · [07 — Memory](07-MEMORY-ARCHITECTURE.md)*
