# Roadmap & Milestones

Nine months to a defensible product. What gets built, in what order, and why that order.

---

## 1. Sequencing logic

The order is not arbitrary. Three constraints determine it:

1. **Memory first, because it takes longest to prove.** You cannot evaluate a memory system in a week — you need weeks of real conversation before retrieval quality is measurable. Starting it last means launching without knowing whether the core thesis holds.
2. **Video last, because it is expensive to run and easy to build.** The avatar integration is days of work. Running it in beta for months is real money spent learning nothing that a two-week test would not teach.
3. **Compliance before revenue, because it gates revenue.** The T2/T3 rail cannot take a payment until age assurance, the blocklist, and the second processor all exist.

```
  memory ────────────────────────────────────────▶  needs months to validate
       character ──────────────────────▶
              voice ────────────▶
                     compliance ─────▶
                            video ──▶
                                launch
```

---

## 2. Phase 0 — Foundation (weeks 1–4)

**Goal: a text conversation with a character, end to end, that a person would not immediately quit.**

| Deliverable | Doc |
|---|---|
| Repo, CI, environments, IaC | [16](16-ENGINEERING-HANDBOOK.md) |
| Auth, users, sessions | [09 §3](09-SYSTEM-DESIGN.md) |
| Postgres schema, migrations | [09 §3](09-SYSTEM-DESIGN.md) |
| Orchestrator skeleton with tier resolution | [05 §3](05-AI-ARCHITECTURE.md) |
| Prompt compilation, 9 layers, cache boundary | [04 §3](04-CHARACTER-SYSTEM.md) |
| T0/T1 model routing + failover | [05 §4](05-AI-ARCHITECTURE.md) |
| Streaming text chat | [03](03-PRD.md) T-01 |
| **Prefix-stability test** | [09 §7](09-SYSTEM-DESIGN.md) |

**Exit criteria**
- Text first token < 500ms p50
- The prefix-stability test passes in CI
- Tier resolution is server-side only, verified by the escalation suite skeleton

> **Ship the prefix-stability test in week one, not week twenty.** It is fifteen lines and it prevents a class of silent cost regression that is nearly impossible to notice later — the app works perfectly while the bill quietly quadruples.

---

## 3. Phase 1 — The character (weeks 5–10)

**Goal: characters that feel like people, and memory that visibly works.**

| Deliverable | Doc |
|---|---|
| 12 archetypes, 12 trait axes with mechanical effects | [04 §4–5](04-CHARACTER-SYSTEM.md) |
| Character CRUD + versioning | [03](03-PRD.md) C-07 |
| Appearance parameters, 6 style registers | [04 §6](04-CHARACTER-SYSTEM.md) |
| Identity lock stages 1–2 | [08 §2](08-IMAGE-VIDEO-GENERATION.md) |
| Image generation + **face-similarity gate** | [08 §2](08-IMAGE-VIDEO-GENERATION.md) |
| In-scenario selfies | [08 §4](08-IMAGE-VIDEO-GENERATION.md) |
| **Memory v1** — episodic, semantic, temporal validity | [07](07-MEMORY-ARCHITECTURE.md) |
| Extraction + retrieval + ranking | [07 §5–6](07-MEMORY-ARCHITECTURE.md) |
| Memory UI (view, edit, correct) | [07 §8](07-MEMORY-ARCHITECTURE.md) |
| Relationship progression, 7 stages | [04 §10](04-CHARACTER-SYSTEM.md) |
| Blocklist classifier, fails closed | [13 §1](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Character creation flow, < 4 minutes | [10 §9](10-DESIGN-SYSTEM.md) |
| Character card import | [03](03-PRD.md) C-09 |

**Exit criteria**
- Identity-drift test: 100 images, all ≥ 0.72 similarity
- Memory retrieval precision@10 > 0.8 on a hand-labelled set
- Retrieval latency < 100ms p95
- Character creation completed in under 4 minutes by a first-time user
- **Alpha cohort (200 users) reports "she remembered something" unprompted**

> **The last criterion is the real gate for this phase.** The engineering metrics are proxies. If 200 demanding users spend a month with the product and nobody spontaneously mentions being remembered, the memory system has not achieved what it exists for, and shipping voice on top of it would be building on sand.

**This phase is deliberately the longest.** It contains the moat.

---

## 4. Phase 2 — The voice (weeks 11–16)

**Goal: a phone call that feels like a phone call.**

| Sub-phase | Weeks | Deliverable | Target |
|---|---|---|---|
| 2a | 11–12 | LiveKit integration, cascaded pipeline | Round trip < 1200ms p50 |
| 2b | 13–14 | Deepgram Flux turn detection, interruption, **context truncation to what was heard** | < 800ms p50; interruption < 100ms |
| 2c | 15–16 | Per-character voice, emotional prosody, live captions | Users describe the voice as "hers" |

Also: clause-level TTS streaming, speculative execution on interim transcripts, warm agent pools, region pinning, and post-call memory summarization. All from [06 §3](06-REALTIME-VOICE-VIDEO.md).

**Exit criteria**
- < 800ms p50, < 1200ms p95, measured at the client's speaker — not server-side
- Interruption truncates context to spoken audio, verified
- A call ends and the character references it in text chat ten minutes later

> **That last one is the phase's real deliverable.** It is the moment the memory work from Phase 1 and the voice work from Phase 2 combine into something no competitor does. Test it explicitly.

---

## 5. Phase 3 — The face (weeks 17–22)

**Goal: FaceTime, with someone who is not there.**

| Sub-phase | Weeks | Deliverable |
|---|---|---|
| 3a | 17–19 | Anam integration, replica from identity-lock references, **avatar identity verification gate** |
| 3b | 20–21 | Aura metering, graceful degradation, call UI |
| 3c | 22 | Idle presence, ringing sequence, natural closing |

**Exit criteria**
- First frame < 2s from call accept
- Avatar face similarity ≥ 0.70 vs canonical, or **video disabled for that character**
- Degradation path verified: video → voice → text, all in character, no modals
- Margin positive at forecast usage

**Explicitly deferred:** character-initiated calls ([06 §10](06-REALTIME-VOICE-VIDEO.md), phase 3c-later). The success metric for that feature is *no increase in complaints*, which requires a stable baseline to measure against.

---

## 6. Phase 4 — The gate (weeks 23–28)

**Goal: take money from adults, legally, on two rails.**

| Deliverable | Doc |
|---|---|
| Age assurance, estimation-first ladder | [13 §3](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| T2/T3 routing to open-weight hosts | [05 §4](05-AI-ARCHITECTURE.md) |
| Preference tag taxonomy, bounded | [13 §5.1](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Safeword / tier-down in every surface | [13 §5.2](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Visual classifier post-generation | [08 §6](08-IMAGE-VIDEO-GENERATION.md) |
| Age-appearance verification at genesis | [08 §6](08-IMAGE-VIDEO-GENERATION.md) |
| Second entity, CCBill integration | [11 §7](11-PRICING-AND-UNIT-ECONOMICS.md) |
| Stripe integration (T0/T1) | [11 §7](11-PRICING-AND-UNIT-ECONOMICS.md) |
| Aura ledger, metering, top-ups | [11 §4](11-PRICING-AND-UNIT-ECONOMICS.md) |
| Crisis classifier + protocol, `/safety` published | [13 §2.1](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| AI disclosure, break reminders | [13 §2](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Real deletion, export, encryption at rest | [13 §8](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| TAKE IT DOWN 48-hour pipeline | [13 §4](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Geo-gating | [13 §4](13-TRUST-SAFETY-AND-COMPLIANCE.md) |

**Exit criteria**
- **All 18 items on the [13 §11](13-TRUST-SAFETY-AND-COMPLIANCE.md) pre-launch checklist complete**
- Tier-escalation suite: 100% blocked
- Deletion verified end to end, including provider-side replicas
- Counsel sign-off in every launch jurisdiction

> **Nothing in this phase ships late.** Every item is P0. Launching a T2 tier with fifteen of eighteen items done is not 83% compliant, it is non-compliant with a private right of action attached.

---

## 7. Phase 5 — Launch (weeks 29–36)

| Weeks | Focus |
|---|---|
| 29–31 | PWA polish, performance, offline shell, push |
| 30–32 | Store apps (T0/T1 only, genuinely complete SFW product) |
| 31–33 | Pricing live, plans, annual billing |
| 32–34 | Beta at 2,000 users, load testing, on-call |
| 34–35 | SEO content live, technical write-up published |
| 36 | **Public launch** |

**Exit criteria**
- Beta D30 > 50%, conversion > 4%
- 99.5% availability over the beta period
- All latency targets met at beta concurrency
- Store apps approved

---

## 8. Post-launch

| Quarter | Focus |
|---|---|
| Q1 | Retention. Memory quality iteration. Consolidation tuning. Watch **D180** and the Plus Aura consumption rate. |
| Q2 | Group chats. Public gallery (with moderation team). Creator programme. Procedural memory. |
| Q3 | Self-hosted T2/T3 inference. Own avatar rendering evaluation. Multi-language. |
| Q4 | Non-realtime video clips. Desktop app. API evaluation. |

**Two numbers get watched weekly from launch:**

1. **D180 retention.** The entire thesis. If it tracks the category, the moat is not working and everything else is decoration.
2. **Mean Aura consumption on Plus.** Above ~45% and the entry plan is losing money on every subscriber ([11 §6](11-PRICING-AND-UNIT-ECONOMICS.md)). This is the failure that is easiest to miss and most expensive to discover late.

---

## 9. Team

| Role | From | Why |
|---|---|---|
| Founding engineer (backend/AI) | Week 1 | Orchestrator, memory, the whole spine |
| Founding engineer (frontend) | Week 1 | PWA, conversation surface, call UI |
| Designer | Week 3, part-time | [10](10-DESIGN-SYSTEM.md) is most of the differentiation users see |
| Engineer (realtime) | Week 10 | Voice and video are specialist work |
| Trust & safety lead | Week 20 | Must be in place before Phase 4 ships |
| Community/content | Week 24 | GTM starts 8 weeks before launch ([14 §5](14-GTM-AND-GROWTH.md)) |
| Support | Week 32 | Before beta scales |

⚠️ Roughly 4–6 people at launch. Breakeven is ~107 paying users ([11 §8](11-PRICING-AND-UNIT-ECONOMICS.md)), so this is buildable without a large raise — which is itself strategically useful in a category where investors are skittish and the ad channels are closed anyway.

---

## 10. What would make us stop

Honest kill criteria, written before there is any sunk cost to defend:

| Signal | Meaning |
|---|---|
| Alpha cohort does not notice memory | The core thesis is wrong. Fix or stop. |
| D180 tracks the category after two quarters of iteration | The moat is not a moat. |
| Video margin stays negative at realistic usage after re-pricing | The differentiating feature is unaffordable. Ship voice-only. |
| Age assurance drops signup conversion below ~15% | The regulated business may not be viable at consumer prices. |
| Both T2/T3 providers terminate | Existential. Self-host immediately or exit the adult tiers. |

> Writing these down now is the point. In month fourteen, with a team and a product and a story, every one of these will have a comfortable explanation available. The version written today is the honest one.

---

*Back to: [README](../README.md) · [00 — Executive Summary](00-EXECUTIVE-SUMMARY.md)*
