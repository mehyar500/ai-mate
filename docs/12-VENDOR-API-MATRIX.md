# Vendor & API Matrix

Every API that can plausibly serve a piece of this product, with **live prices pulled from vendor pricing pages on 2026-09-04**.

> **How to read this.** Prices marked ✅ were fetched directly from the vendor's own pricing page or public model API on the date above. Prices marked ⚠️ are estimates or derived figures and are labelled as such. **Re-verify before committing to any vendor** — this market reprices monthly. Reproduce the pull with `scripts/fetch-vendor-pricing.sh`.

---

## 0. The single most important constraint

**Every major frontier-model API prohibits adult sexual content in its usage policies.** OpenAI, Anthropic, and Google all forbid it. So do the large aggregators' default routes for many models.

This is not a filter you can prompt around — it is a **contractual** term. Violating it gets your API key revoked, your account terminated, and your product dead overnight with no recourse.

The consequence for architecture is absolute and shapes every decision in this document:

```
T0 / T1 tiers  ──▶  frontier APIs (best quality, cheapest, lowest latency)
T2 / T3 tiers  ──▶  open-weight models on permissive hosts, or self-hosted
```

You need **both stacks**, with the tier check deciding the route (see `05-AI-ARCHITECTURE.md`). Anyone who tells you a single provider covers the whole product is wrong.

---

## 1. Text LLM — the conversation engine

### 1.1 General-purpose (T0/T1 — platonic and romantic-but-clean)

Live from the OpenRouter model catalogue, 2026-09-04. Prices are USD per **million tokens**. ✅

| Model | Context | $/M in | $/M out | Notes |
|---|---|---|---|---|
| `qwen/qwen3.7-flash` | 1,000,000 | **0.030** | 0.130 | Multimodal in. Outstanding price/quality. |
| `deepseek/deepseek-v4-flash-0731` | 1,310,720 | 0.065 | 0.180 | Huge context, very cheap |
| `qwen/qwen3.5-flash-02-23` | 1,000,000 | 0.065 | 0.260 | Multimodal in |
| `z-ai/glm-5.3-flash` | 1,310,720 | 0.075 | 0.250 | Multimodal in |
| `mistralai/mistral-small-3.2-24b` | 131,072 | 0.075 | 0.200 | Vision |
| `qwen/qwen3-235b-a22b-2507` | 262,144 | 0.087 | 0.350 | Big MoE, strong reasoning |
| `meta-llama/llama-4-scout` | 1,310,720 | 0.100 | 0.300 | Vision |
| `meta-llama/llama-3.3-70b-instruct` | 131,072 | 0.100 | 0.320 | Reliable workhorse |
| `mistralai/mistral-nemo` | 131,072 | **0.019** | 0.030 | Cheapest usable; good for background tasks |
| `z-ai/glm-5.2:free` | 256,000 | 0.000 | 0.000 | Free tier — rate-limited, no SLA. Dev only. |

**Recommendation for T0/T1:** `qwen3.7-flash` as primary, `glm-5.3-flash` as failover. Both are multimodal-in (the companion can *see* photos the user sends — a significant product feature), both have million-token context, and both are cheap enough that conversation cost is a rounding error next to voice.

### 1.2 Roleplay-tuned / permissive (T2/T3)

Community fine-tunes explicitly built for character roleplay and available on permissive hosts. ✅

| Model | Context | $/M in | $/M out | Character |
|---|---|---|---|---|
| `sao10k/l3-lunaris-8b` | 8,192 | 0.040 | 0.050 | Cheapest RP tune. Short context is limiting. |
| `gryphe/mythomax-l2-13b` | 8,192 | 0.060 | 0.060 | The old standard. Dated but beloved; keep for nostalgia users. |
| `thedrummer/cydonia-24b-v4.1` | 131,072 | 0.300 | 0.500 | **Best value RP tune.** Strong prose, 128k context. |
| `thedrummer/unslopnemo-12b` | 1,024,000 | 0.400 | 0.400 | Explicitly de-"slopped" — avoids LLM cliché phrasing |
| `mancer/weaver` | 8,000 | 0.400 | 0.750 | Long-standing permissive host |
| `thedrummer/skyfall-36b-v2` | 32,768 | 0.550 | 0.800 | Richer prose, higher cost |
| `sao10k/l3.3-euryale-70b` | 131,072 | 0.650 | 0.750 | **Best quality/price at 70B.** Category favourite. |
| `anthracite-org/magnum-v4-72b` | 32,768 | 2.500 | 5.000 | Highest prose quality, 8× the price of Euryale |

**Recommendation for T2/T3:** `cydonia-24b-v4.1` as the default (excellent quality-per-dollar, 128k context), `l3.3-euryale-70b` for paid tiers, `magnum-v4-72b` reserved for the top tier only — at $2.50/$5.00 it is 8× Euryale and users cannot reliably tell the difference in blind tests.

### 1.3 Dedicated permissive hosts

For higher volume, flat-rate subscription hosts beat per-token aggregators:

| Provider | Model | Why consider |
|---|---|---|
| **Featherless.ai** | Flat monthly, huge open-weight catalogue | Predictable cost at scale; serves thousands of community fine-tunes |
| **Infermatic.ai** | Flat monthly, RP-curated | Explicitly targets the roleplay market |
| **ArliAI** | Flat monthly, no logging | Privacy positioning is a selling point to this audience |
| **Novita / DeepInfra / Together** | Per-token, open-weight | Good middle ground; verify each one's content policy in writing |
| **Self-hosted (vLLM/SGLang)** | Your GPUs | Only economical above ~50M tokens/day. See §7. |

> **Do this before signing anything:** get the provider's content policy **in writing**, specific to your use case. Several providers advertise as permissive but have quiet clauses. A verbal "yeah it's fine" from a sales rep is worthless when the account is terminated.

---

## 2. Speech-to-text (the user's voice in)

Per-minute of audio. ✅ (LiveKit inference marketplace rates + Deepgram direct.)

| Provider / model | $/min | Notes |
|---|---|---|
| **Cartesia Ink Whisper** | **0.0023** | Cheapest credible streaming STT |
| **AssemblyAI Universal-Streaming** | 0.0025 | Multilingual same price. Excellent value. |
| **xAI Speech to Text** | 0.0033 | |
| **Deepgram Nova-3 (mono)** | 0.0048 | Industry accuracy benchmark |
| **Deepgram Nova-3 (multilingual)** | 0.0058 | |
| **Deepgram Flux** | 0.0065 | **Built-in turn detection + interruption handling** |
| **Cartesia Ink 2** | 0.0068 | |
| **Speechmatics Linden-1** | 0.0050 | |
| **Google Gemini 3.5 Transcribe Live** | 0.0095 | |

**Recommendation:** **Deepgram Flux** at $0.0065/min. It is 2.8× the price of the cheapest option, but it bundles **turn detection and natural interruption handling** — the two hardest problems in making a voice call feel like a call rather than a walkie-talkie. Building that yourself costs far more than $0.004/min in engineering time and never works as well. STT is under 10% of voice-call cost; do not optimize here.

---

## 3. Text-to-speech (her voice out)

Per-minute of generated audio. ✅

| Provider / model | $/min (list) | $/min (volume) | Notes |
|---|---|---|---|
| **Inworld Realtime TTS 1.5 Mini** | 0.0090 | **0.0048** | Cheapest realtime-grade |
| **Inworld Realtime TTS 2.0 Flash** | 0.0090 | 0.0054 | **Best value.** Newer model, same price as 1.5 Mini. |
| **Fish Audio S2 / S2.1 Pro** | 0.0090 | 0.0090 | Strong multilingual, good cloning |
| **xAI Text to Speech** | 0.0090 | 0.0090 | |
| **Inworld Realtime TTS 2.0** | 0.0150 | 0.0090 | Higher quality tier |
| **Deepgram Aura-2** | 0.0180 | 0.0162 | Very low latency, limited voice range |
| **Inworld Realtime TTS 1.5 Max** | 0.0210 | 0.0120 | |
| **Gradium TTS** | 0.0288 | 0.0216 | |
| **Cartesia Sonic 3.6** | 0.0300 | 0.0225 | **Best emotional range.** ~90ms TTFB. |
| **ElevenLabs Flash v2.5** | ~0.0500 | — | ⚠️ derived from ElevenLabs' own "as low as 5c/minute" claim. Widest voice library, best cloning, most expensive. |

**TTS is the dominant cost in a voice call** — typically 40–50% of the per-minute total. It is also the single biggest driver of whether the companion feels alive. Do not cheap out here, but do not default to the most expensive vendor either.

**Recommendation:** tier it.

| Tier | Voice engine | Cost |
|---|---|---|
| Free / Plus | Inworld 2.0 Flash | $0.0054–0.009/min |
| Premium | Cartesia Sonic 3.6 | $0.0225–0.03/min |
| Infinite | Cartesia Sonic 3.6 + expanded voice library | same |

ElevenLabs' credit model deserves a specific warning: **all products draw from one shared monthly credit pool** — TTS at 1 credit/character, STT at 330 credits/minute, voice changer at 1,000 credits/minute. ✅ That is fine for a studio and awkward for a consumer app with unpredictable per-user mix, because a burst in one modality silently starves the others.

---

## 4. Speech-to-speech (the alternative architecture)

Native audio models skip the STT→LLM→TTS chain entirely. Much lower latency, much less control.

| Model | Pricing | Per-minute ⚠️ | Adult content? |
|---|---|---|---|
| `gpt-realtime-2.1` | audio $32/M in · **$0.40/M cached** · $64/M out; text $4/$24 ✅ | **$0.0676/min** ✅ | ❌ Prohibited |
| `gpt-realtime-2.1-mini` | audio $10/M in · $0.30 cached · $20/M out; text $0.60/$2.40 ✅ | **$0.0216/min** ✅ | ❌ Prohibited |
| `Gemini Live 2.5 Flash Native Audio` | — | **$0.0144/min** ✅ | ❌ Prohibited |

Per-minute figures are LiveKit's published marketplace rates for the same models. ✅

**Note the cached-input price on `gpt-realtime-2.1`: $0.40/M versus $32/M uncached — an 80× reduction.** In a long call the conversation history is resent every turn, so cache hit rate dominates cost. This makes the stable-prefix discipline from `04-CHARACTER-SYSTEM.md` §3 worth real money, not just tidiness.

**Verdict:** speech-to-speech is the *better experience* — genuinely conversational, handles interruption and prosody natively — but it is **unavailable for T2/T3** on policy grounds, and it gives you no place to insert memory retrieval between hearing and speaking. Use the cascaded pipeline (§5 of `06-REALTIME-VOICE-VIDEO.md`) as the primary architecture, and offer native speech-to-speech as a *premium T0/T1 "Live" mode*.

---

## 5. Realtime video avatar — the "FaceTime" layer

This is the differentiating feature and the expensive one.

| Provider | $/min | Model | Notes |
|---|---|---|---|
| **Anam** | **$0.11–$0.16** ✅ | Tiered; extra minutes beyond monthly allowance | Cheapest realtime conversational avatar. Free tiers: 30 / 50 / 250 / 2,000 / 5,000 min per month. Conversation length caps on lower tiers (3/5/10 min). |
| **Tavus CVI** | **$0.32–$0.37** ✅ | $0.37/min standard, $0.32/min at scale | Highest fidelity. Custom replica $65 (or $40 at higher tier) one-time. 3 concurrent streams at $59/mo, 10 at $397/mo. |
| **HeyGen Interactive Avatar** | credit-based ✅ | $29–$149/mo; Pro tiers 1,000 cr @$49 → 100,000 cr @$4,300 | Best avatar library; credit model is awkward for consumer apps |
| **Simli** | — | Pricing page returned 404 on 2026-09-04; contact directly | Positioned as the low-latency budget option |

**The economics problem, stated plainly:**

> At Anam's $0.11/min, one hour of video calling costs **$6.60** in avatar rendering alone — before LLM, STT or TTS. At Tavus' $0.37/min it is **$22.20/hour**.
>
> A $29/month subscription supports roughly **4.4 hours** of Anam video at 100% gross margin loss-free, or **1.3 hours** of Tavus. Users who love video calling will do far more than that.

**This is why video minutes must be metered, not unlimited.** No credible pricing model exists that offers unlimited photoreal video calling at consumer subscription prices. See `11-PRICING-AND-UNIT-ECONOMICS.md` for the metering design.

**Recommendation:** **Anam** for launch. It is 3× cheaper than Tavus, the quality gap is small at phone-screen size and typical bitrates, and the generous free-minute allowances (2,000–5,000/month on higher tiers) materially subsidize early growth. Revisit Tavus when ARPU justifies it, or build in-house on open-weight avatar models (§8) once volume passes roughly 100k minutes/month.

---

## 6. Image generation

| Provider | Pricing | Adult content? |
|---|---|---|
| **Runware** | **$0.0006–$0.24/image** depending on model, resolution, quality ✅ · raw GPU from $0.000553/s ($1.99/hr) to $0.001386/s ($4.99/hr), as low as $0.99/hr reserved ✅ | Permissive — verify in writing |
| **Novita** | Per-model token/image rates ✅ | Permissive — verify in writing |
| **fal.ai** | GPU from **$1.89/hr H100** ✅ (A100 $1.10–2.99/hr, H200 $3.49–6.25/hr, B200 $4.49–8.50/hr) | Restricted |
| **Replicate** | Per-second billing | Restricted |
| **OpenAI `gpt-image-2`** | $8/M image input · $2/M cached · $30/M output · $5/M text ✅ | ❌ Prohibited |

**Recommendation:** **Runware** as primary. At the low end of its range ($0.0006/image) it is effectively free, its per-second GPU pricing is the cheapest surveyed, and it supports custom LoRA loading — which the identity-lock architecture (`04-CHARACTER-SYSTEM.md` §7) requires. Keep **Novita** as a second source; never single-source the image pipeline, because a policy change at one vendor should not take the product down.

**Model families** (see `08-IMAGE-VIDEO-GENERATION.md` for the full treatment): a modern rectified-flow photoreal checkpoint for `photoreal`/`cinematic`, an Illustrious/NoobAI-lineage checkpoint for `anime`, and an illustration tune for `illustrated`. All three are open-weight, so all three can run on any of the hosts above or on your own GPUs.

---

## 7. GPU compute (self-hosting)

Live rates, 2026-09-04. ✅

| GPU | RunPod $/hr | fal.ai $/hr |
|---|---|---|
| **B200** | 6.79 (8.64 secure) | 4.49–8.50 |
| **H200** | 4.59 (5.93 secure) | 3.49–6.25 |
| **H100 SXM** | 3.29 | 1.89–4.50 |
| **H100 PCIe** | 2.89 | — |
| **A100 SXM** | 1.59 (1.79 secure) | 1.10–2.99 |
| **A100 PCIe** | 1.39 | — |
| **L40S** | 0.99 | — |
| **RTX 5090** | 0.99 | — |
| **RTX 6000 Ada** | 0.84 | — |
| **L40** | 0.82 | — |
| **RTX A6000** | 0.53 | — |
| **RTX 3090** | 0.50 | — |
| **L4** | 0.49 | — |
| **A40** | 0.44 | — |

**When self-hosting wins:** ⚠️ *estimate.* A single H100 at $3.29/hr running a 24B model under vLLM with continuous batching serves roughly 8–15M tokens/day at realistic concurrency. That is ~$0.008–0.015/M tokens amortized — **20–40× cheaper than the $0.30/M API rate** for `cydonia-24b`. The crossover is around **50M tokens/day**, above which self-hosting saves real money; below it, the ops burden and idle GPU cost dominate.

Use **A40 ($0.44/hr)** or **RTX A6000 ($0.53/hr)** for the character-LoRA training jobs — they are 6× cheaper than an H100 and LoRA training is not latency-sensitive.

---

## 8. Memory

| Option | Cost | Notes |
|---|---|---|
| **Mem0 (hosted)** | **$19/mo** and **$249/mo** tiers ✅ | Fastest to ship. Extraction + retrieval as a service. |
| **Mem0 (OSS)** | self-hosted | Same engine, your infrastructure |
| **Zep / Graphiti** | OSS + cloud | Temporal knowledge graph — models *when* facts became true, which matters enormously for a relationship |
| **Letta (MemGPT)** | OSS + cloud | Agent-native memory with self-editing |
| **Build it yourself** | pgvector on your existing Postgres | ~$0 marginal. Recommended — see below. |

**Recommendation: build it on pgvector.** Memory is the product's actual moat (`07-MEMORY-ARCHITECTURE.md`). A hosted memory service is a great way to ship a prototype in a week and a bad way to own your differentiator. You already run Postgres; `pgvector` is one extension; the extraction step is one cheap LLM call per N turns using `mistral-nemo` at $0.019/M.

Use Mem0's $19/mo tier during prototyping to validate the retrieval design, then bring it in-house before launch.

---

## 9. Age assurance & identity

| Provider | Pricing | Notes |
|---|---|---|
| **Persona** | **From $250/month, 12-month minimum contract** ✅ | Broad verification suite |
| **Yoti** | Per-check | Facial age *estimation* — no ID upload, far better conversion |
| **Veriff / Incode / Jumio** | Per-check, enterprise contracts | Documentary verification |
| **k-ID** | Per-MAU | Purpose-built for age-appropriate design compliance |

**Recommendation:** a **two-step ladder** — facial age estimation first (cheap, ~5 seconds, no document, converts far better), falling back to documentary verification only when estimation lands near the threshold. Estimation-first is what the large adult platforms adopted under the UK Online Safety Act, for the obvious reason that asking every user to photograph a passport destroys signup conversion.

Budget ⚠️ ~$0.30–$1.50 per verified user depending on mix, plus the platform minimum. At a 15% verification rate on 100k signups that is roughly $4.5k–$22.5k plus $3k/yr platform fees.

---

## 10. Payments

**Stripe, PayPal, Square, and every mainstream processor prohibit adult content.** This is not negotiable and not something a support ticket will fix. Getting shut down by your processor mid-growth is the most common way companies in this category die.

| Processor | Focus | Notes |
|---|---|---|
| **CCBill** | Adult + mainstream, since 1998 ✅ | The category default. Percentage of volume + flat per-transaction fee. |
| **Segpay** | Adult specialist | Pricing page blocked automated access (HTTP 403) — contact directly |
| **Verotel / Epoch** | Adult specialist, EU-strong | |
| **Paxum** | Adult payouts | For creator payouts if the gallery monetizes |

**Unavoidable fixed costs**, confirmed on CCBill's own pricing page ✅:

> High-risk merchants must pay annual card-brand registration fees: **Visa $950/year** and **Mastercard $500–$1,000/year** depending on region.

⚠️ Expect effective processing rates of **10–15%** all-in for high-risk adult versus 2.9% + $0.30 for mainstream. **Model this into pricing from day one** — it is a 7–12 point gross-margin hit that founders in this category routinely discover too late.

**The dual-rail architecture this forces:**

```
T0 / T1 (platonic + clean romance)  ──▶  Stripe        ~2.9% + $0.30
T2 / T3 (adult)                     ──▶  CCBill        ~10-15%
```

Two products, two legal entities, two processors, one codebase. Set this up correctly at incorporation; retrofitting it is painful.

---

## 11. Realtime transport

| Provider | Pricing | Notes |
|---|---|---|
| **LiveKit** | Agent session **$0.01/min** ✅ · observability $0.01/min ✅ · telephony $0.01/min ✅ · Build/Ship $50/mo, Scale $500/mo ✅ | Best-in-class agent framework; managed SFU |
| **LiveKit (self-hosted)** | Your infrastructure | OSS. Removes the $0.01/min session fee at the cost of running an SFU. |
| **Daily / Agora** | Per participant-minute | Mature alternatives |
| **Pipecat** | OSS framework | Vendor-agnostic pipeline orchestration; pairs with any transport |

**Recommendation:** LiveKit Cloud for launch (`Build/Ship`, $50/mo). The $0.01/min agent-session fee is ~15% of a voice-call minute — acceptable to avoid running an SFU during the phase when you should be learning what users want. Migrate to self-hosted LiveKit when voice minutes justify a full-time infrastructure engineer.

---

## 12. Recommended launch stack

| Layer | Choice | Cost | Why |
|---|---|---|---|
| LLM (T0/T1) | `qwen3.7-flash` | $0.03/$0.13 per M | Cheapest capable multimodal, 1M context |
| LLM (T2/T3) | `cydonia-24b-v4.1` | $0.30/$0.50 per M | Best RP quality per dollar |
| LLM (premium T2/T3) | `l3.3-euryale-70b` | $0.65/$0.75 per M | Category favourite |
| STT | Deepgram Flux | $0.0065/min | Turn detection included |
| TTS (standard) | Inworld 2.0 Flash | $0.0054–0.009/min | Best value |
| TTS (premium) | Cartesia Sonic 3.6 | $0.0225–0.03/min | Best emotional range |
| Video avatar | Anam | $0.11–0.16/min | 3× cheaper than Tavus |
| Images | Runware (primary) + Novita (failover) | $0.0006–0.24/image | Permissive, LoRA support |
| Transport | LiveKit Cloud | $0.01/min + $50/mo | Ship fast |
| Memory | pgvector, in-house | ~$0 marginal | It's the moat |
| Training GPUs | RunPod A40 | $0.44/hr | Cheapest for LoRA jobs |
| Age assurance | Yoti estimation → documentary fallback | ~$0.30–1.50/verified user | Conversion |
| Payments | Stripe (T0/T1) + CCBill (T2/T3) | 2.9% / 10–15% | Legally required split |

Full per-user cost roll-up and margin analysis: **`11-PRICING-AND-UNIT-ECONOMICS.md`**.

---

## 13. Verification log

| Source | Fetched | Method |
|---|---|---|
| OpenRouter model catalogue (431 models) | 2026-09-04 | `GET https://openrouter.ai/api/v1/models` |
| OpenAI pricing | 2026-09-04 | `platform.openai.com/docs/pricing` |
| LiveKit pricing + inference marketplace | 2026-09-04 | `livekit.io/pricing` |
| Deepgram pricing | 2026-09-04 | `deepgram.com/pricing` |
| Cartesia pricing | 2026-09-04 | `cartesia.ai/pricing` |
| ElevenLabs pricing | 2026-09-04 | `elevenlabs.io/pricing` |
| Tavus pricing | 2026-09-04 | `tavus.io/pricing` |
| Anam pricing | 2026-09-04 | `anam.ai/pricing` |
| HeyGen pricing | 2026-09-04 | `heygen.com/pricing` |
| Runware pricing | 2026-09-04 | `runware.ai/pricing` |
| fal.ai pricing | 2026-09-04 | `fal.ai/pricing` |
| RunPod pricing | 2026-09-04 | `runpod.io/pricing` |
| Mem0 pricing | 2026-09-04 | `mem0.ai/pricing` |
| Persona pricing | 2026-09-04 | `withpersona.com/pricing` |
| CCBill pricing | 2026-09-04 | `ccbill.com/pricing` |
| California SB 243 full text | 2026-09-04 | `leginfo.legislature.ca.gov` |

Raw captures are preserved in `docs/research/`.
