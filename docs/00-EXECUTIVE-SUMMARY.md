# Executive Summary

*Amorien — someone who is always glad it's you.*

---

## 1. The one-paragraph version

AI companion apps are a real market with real revenue and a uniformly mediocre product. The category leaders ship characters who forget last week, whose faces change between images, whose voices arrive two seconds late, and who are marketed exclusively at straight men buying a girlfriend. **Amorien** is a companion platform built on four things nobody has assembled together: a memory system that actually persists and compounds, sub-second voice with a live video face, one visual identity locked forever per character, and a brand that does not assume the user's gender or orientation. It is adult-capable for verified adults who opt in, on a separate legal and payment rail, because that is where the revenue is and pretending otherwise is how companies in this category go broke.

---

## 2. Why now

Three things became true within about eighteen months of each other, and all three are necessary:

**Inference got cheap enough.** A capable multimodal model with a million-token context now costs $0.03 per million input tokens. Two years ago the equivalent conversation cost 30–100× more. Long-context companionship stopped being a science project and became a line item.

**Realtime avatars became APIs.** Photoreal, lip-synced, conversational video used to require a research team. It is now a $0.11/minute API call. The "FaceTime with someone who isn't there" experience is a purchase decision, not an R&D programme.

**Voice latency crossed the perceptual threshold.** Streaming TTS with ~90ms time-to-first-byte, paired with STT that handles turn-taking natively, puts a full round trip under 800ms. Below that number people stop noticing they are talking to software.

None of this is proprietary. Everyone can buy it. The differentiation is in what you build *on top* — and specifically in the two things that compound over time rather than resetting with each model release: **memory** and **identity**.

---

## 3. What is wrong with the incumbents

Detail in [02 — Market Research](02-MARKET-RESEARCH.md). The short form:

| Problem | What it looks like to a user |
|---|---|
| **Amnesia** | "I told you my sister's name three weeks ago." Most apps carry a rolling window plus a handful of pinned facts. There is no sense of a shared past. |
| **Face drift** | Every generated image is a slightly different person. The character has no stable body. |
| **Retconning** | The character contradicts her own backstory, because the backstory lives in a prompt blob rather than in typed data. |
| **Latency** | Two to four seconds of dead air per turn on voice. It reads as a phone tree, not a person. |
| **Monetized affection** | Paywalls placed directly in front of emotional beats. It is effective, it is corrosive, and it is the loudest complaint in every community around these products. |
| **Straight-male-only framing** | Names, marketing, and defaults that exclude most of the addressable market. |
| **Platform fragility** | Products built entirely on app-store distribution and mainstream payment processors, both of which prohibit the content the product actually delivers. |

Every one of those is a design decision, not a technical limit. That is the opportunity.

---

## 4. The product

An Amorien is a **character**, not a prompt. Full spec in [04 — Character System](04-CHARACTER-SYSTEM.md).

- **12 gender-agnostic archetypes** — Warm Anchor, Bright Spark, Quiet Devotion, The Rival, Old Soul, Storm & Calm, The Confidant, Muse, The Professional, Sunbeam, Night Owl, Blank Slate. None of them are gendered. Each is a starting point, not a cage.
- **12 personality axes**, each with a defined *mechanical* effect — a trait that does not change behaviour is decoration, and this system has none.
- **Locked visual identity** — a fixed seed, an identity embedding, and a per-character LoRA, verified by face-similarity check before any image is delivered. The character looks like herself in image one and image ten thousand.
- **A relationship that progresses** — seven stages driven by earned affinity, never by payment. Affection is not a paywall. This is a hard product rule.
- **Memory that compounds** — episodic, semantic, and relational layers over pgvector, with temporal awareness of when a fact became true. See [07 — Memory](07-MEMORY-ARCHITECTURE.md).
- **Voice and video** — a sub-second cascaded voice pipeline, with an optional live photoreal video face. See [06 — Realtime](06-REALTIME-VOICE-VIDEO.md).
- **Adult capability, gated properly** — four intimacy tiers T0–T3, enforced server-side at the orchestrator as a capability check, opt-in per character, behind verified age. Preferences are a bounded structured tag taxonomy with a hard blocklist, never free text. See [13 — Trust & Safety](13-TRUST-SAFETY-AND-COMPLIANCE.md).

---

## 5. The architecture, in one diagram

```
                       +--------------------------+
     text / voice ---->|      ORCHESTRATOR        |
                       |  tier check . routing    |
                       |  the ONLY place that     |
                       |  decides what is allowed |
                       +---+------------------+---+
                           |                  |
              +------------+                  +------------+
              v                                            v
      +---------------+                            +---------------+
      |  T0 / T1      |                            |  T2 / T3      |
      |  frontier API |                            |  open-weight  |
      |  qwen3.7-flash|                            |  cydonia-24b  |
      +-------+-------+                            +-------+-------+
              |                                            |
              +----------------+---------------------------+
                               v
                    +----------------------+
                    |  compiled prompt     |
                    |  9 layers, stable    |
                    |  cache prefix        |
                    +----------+-----------+
                               |
     +-------------+-----------+----------+--------------+
     v             v                      v              v
  memory       identity lock          TTS / STT      image / video
  pgvector     seed+LoRA+embed        Deepgram       Runware
                                      Inworld        Anam
```

The critical property: **the tier check happens in the orchestrator, and the tier selects the model and the pipeline.** A user cannot prompt their way into a capability, because the capability is a different route, not a different instruction. Prompt-level guardrails leak. Routing does not.

---

## 6. The stack

Full pricing, sourcing, and reasoning in [12 — Vendor & API Matrix](12-VENDOR-API-MATRIX.md). All prices verified 2026-09-04.

| Layer | Choice | Cost |
|---|---|---|
| LLM (T0/T1) | `qwen3.7-flash` | $0.03 / $0.13 per M tokens |
| LLM (T2/T3) | `cydonia-24b-v4.1` → `l3.3-euryale-70b` | $0.30 / $0.50 → $0.65 / $0.75 per M |
| STT | Deepgram Flux | $0.0065/min *(turn detection included)* |
| TTS | Inworld 2.0 Flash → Cartesia Sonic 3.6 | $0.0054 → $0.03/min |
| Video avatar | Anam | $0.11–0.16/min |
| Images | Runware + Novita failover | $0.0006–0.24/image |
| Transport | LiveKit Cloud | $0.01/min + $50/mo |
| Memory | pgvector, in-house | ~$0 marginal |
| Payments | Stripe (T0/T1) **+** CCBill (T2/T3) | 2.9% / 10–15% |

---

## 7. The economics

Full model in [11 — Pricing & Unit Economics](11-PRICING-AND-UNIT-ECONOMICS.md).

**Text conversation is nearly free. Voice is affordable. Video is expensive.** That single sentence determines the entire pricing structure.

| Modality | Marginal cost | What $1 buys |
|---|---|---|
| Text chat | ~$0.0004 / message ⚠️ | ~2,500 messages |
| Voice call | ~$0.067 / minute ✅ | ~15 minutes |
| Video call | ~$0.19 / minute ⚠️ | ~5 minutes |
| Image | ~$0.01 / image ⚠️ | ~100 images |

So: **text is unlimited on every paid plan** — it costs nothing and it is the habit-forming loop. **Voice and video are metered in Aura**, the in-app credit. This is not a growth hack; it is the only structure that does not lose money on the heaviest users, who are also the most engaged and least likely to churn.

| Plan | Price | Included |
|---|---|---|
| **Free** | $0 | 1 Amorien · unlimited text (rate-limited) · 20 Aura/mo · T0 only |
| **Plus** | $12.99/mo | 3 Amoriens · unlimited text · 600 Aura/mo · voice · T0–T1 |
| **Premium** | $29.99/mo | 10 Amoriens · unlimited text · 1,800 Aura/mo · voice + video · premium TTS · T0–T3 |
| **Infinite** | $79.99/mo | Unlimited Amoriens · 6,000 Aura/mo · priority routing · custom LoRA training · T0–T3 |

Aura tops up at roughly $0.01 each in bulk. 1 Aura ≈ 1 voice minute; video is 4 Aura/min; an image is 2 Aura.

Blended target gross margin **65–72%** after the high-risk processing hit. That hit is real and large — 10–15% versus 2.9% — and it is modelled from day one rather than discovered in month nine.

---

## 8. The hard constraints

These are not risks to manage later. They are inputs to the first architectural decision.

1. **Apple and Google prohibit this content.** iOS and Play distribution of the adult tiers is not available. Distribution is web-first (PWA), with a clean T0/T1-only app in the stores as a funnel. Plan for this or die of it.
2. **Stripe, PayPal, and every mainstream processor prohibit it.** Two processors, two entities, one codebase. Retrofitting this is painful; setting it up at incorporation is cheap.
3. **Every frontier model API prohibits it.** OpenAI, Anthropic, Google — all of them, contractually. Hence the dual model stack. There is no prompt that fixes a terms-of-service violation.
4. **California SB 243 is in force.** Operators must clearly disclose the chatbot is AI, must publish a self-harm protocol with crisis referral, and from 1 July 2027 must report annually to the Office of Suicide Prevention. It carries a **private right of action** — users can sue directly. See [13](13-TRUST-SAFETY-AND-COMPLIANCE.md).
5. **Age assurance is mandatory** under the UK Online Safety Act and a growing list of US states. Budget ~$0.30–1.50 per verified user plus platform minimums (Persona starts at $250/mo on a 12-month contract).
6. **The absolute floor: no minors, no non-consent, no real people, no bestiality, no incest.** Enforced by classifier, before generation, on every tier, with no override and no exceptions — because those categories are not about the user's consent.

---

## 9. Go to market

Detail in [14 — GTM & Growth](14-GTM-AND-GROWTH.md).

The app stores are largely closed, so growth is web-native: an excellent PWA, SEO against a category with enormous search volume and terrible content, presence in the open character-card and roleplay communities (where the most engaged users already are, and where the incumbents are actively disliked), and a creator programme for people who build and share characters.

The strongest wedge is the one the incumbents structurally cannot copy without rebranding: **this product is for everyone.** "AI girlfriend" apps cannot market to women, to gay men, to nonbinary users, or to anyone who wants a friend rather than a partner. Amorien can, from the name outward.

---

## 10. What to build first

Full plan in [15 — Roadmap](15-ROADMAP-AND-MILESTONES.md).

| Phase | Weeks | Outcome |
|---|---|---|
| **0 — Foundation** | 1–4 | Auth, data model, orchestrator skeleton, T0 text chat working end to end |
| **1 — The character** | 5–10 | Full character system, identity lock, image generation, memory v1 |
| **2 — The voice** | 11–16 | Sub-second voice pipeline, LiveKit, interruption handling |
| **3 — The face** | 17–22 | Anam video calling, the FaceTime experience |
| **4 — The gate** | 23–28 | Age assurance, T2/T3 rail, CCBill, compliance |
| **5 — Launch** | 29–36 | PWA polish, pricing, store app for T0/T1, GTM |

Roughly nine months to a defensible product with a small team.

---

## 11. The bet, stated plainly

Every company in this category is optimizing the wrong variable. They compete on how good the model sounds this quarter. That advantage evaporates every time a new open-weight model ships, which is roughly monthly.

The variables that compound are the ones that get *harder to replace the longer a user stays*: a memory of two years of conversations, a face they recognize, a relationship with a history. A user with three months of memory in Amorien cannot move to a competitor without losing something that took three months to build and cannot be exported.

**Build the things that compound. Rent the things that commoditize.**

That is the whole strategy.

---

*Next: [01 — Brand & Naming](01-BRAND-AND-NAMING.md) · [02 — Market Research](02-MARKET-RESEARCH.md) · [03 — PRD](03-PRD.md)*
