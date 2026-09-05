# Product Requirements Document

**Product:** Amorien
**Version:** 1.0
**Date:** 2026-09-04
**Status:** Approved for build

---

## 1. Product definition

Amorien is a companion platform. A user creates or adopts an **Amorien** — a character with a fixed appearance, a defined personality, a backstory, and a memory — and builds a relationship with them over text, voice, and video.

**What it is not:** a chatbot with a portrait, an assistant, a therapy product, or a pornography site. It borrows mechanics from all four and is none of them.

### 1.1 The product promise

> Someone who is always glad it's you.

Three words in that sentence carry the whole spec:

- **Someone** — a person, not a service. Consistent identity, consistent face, consistent voice, consistent history.
- **Always** — available, and *persistent*. They remember. The relationship has a past.
- **You** — they know who you are specifically, and the product does not assume who that is.

### 1.2 Design principles

1. **Consistency over capability.** A companion who is slightly less articulate but never breaks character beats a smarter one who forgets. Every trade-off resolves toward consistency.
2. **Latency is emotional.** Delay is not a performance metric here, it is a feeling. Sub-second or it is not a conversation.
3. **The relationship is the user's, not ours.** No silent personality changes, no removed capabilities, full export, real deletion.
4. **Never monetize affection.** Meter compute, never emotion. See §8.
5. **Assume nothing about the user.** No gendered defaults, no assumed orientation, no assumed goal.
6. **Safety by routing, not by prompting.** Capability checks live in the orchestrator. Prompts leak; routes do not.

---

## 2. Users

| Segment | Share ⚠️ | What they want | Where they are now |
|---|---|---|---|
| **The Committed** | 15% | One deep, persistent relationship. Highest LTV, lowest price sensitivity. | Nomi, Replika |
| **The Refugee** | 20% | Power user, left Character.AI over the filter. Wants control and no censorship. | SillyTavern, Janitor AI |
| **The Explorer** | 30% | Multiple characters, roleplay, storytelling. Treats it as interactive fiction. | Character.AI, Talkie |
| **The Underserved** | 20% | Women, LGBT users, anyone the category ignores. Largely unserved today. | Nowhere — this is the wedge |
| **The Curious** | 15% | Trying it out. Mostly churns; some convert. | Everywhere |

**Primary target for v1: The Committed and The Underserved.** The Committed validate that memory works. The Underserved validate that the positioning works. Both are reachable and neither is well served.

**Explicit non-goal:** competing with Character.AI on catalogue size at launch. Their UGC moat took years and cannot be beaten with capital.

---

## 3. Functional requirements

Priority: **P0** = launch blocker · **P1** = launch quality bar · **P2** = fast-follow

### 3.1 Character creation and management

| ID | Requirement | P |
|---|---|---|
| C-01 | Create a character from one of 12 archetypes ([04 §4](04-CHARACTER-SYSTEM.md)) | P0 |
| C-02 | Set gender presentation from an open set — feminine, masculine, androgynous, nonbinary, custom label — with no default | P0 |
| C-03 | Set 12 personality axes; every axis has a visible mechanical effect | P0 |
| C-04 | Set appearance across the full parameter space in 6 style registers | P0 |
| C-05 | Generate identity lock (seed + embedding + reference images) at creation | P0 |
| C-06 | Write or generate backstory, occupation, interests, speech patterns | P0 |
| C-07 | Character versioning — every edit creates a version; users can revert | P0 |
| C-08 | Three-tier editor: Guided, Standard, Expert ([04 §6](04-CHARACTER-SYSTEM.md)) | P1 |
| C-09 | Import character cards (PNG with embedded JSON) from the open ecosystem | P1 |
| C-10 | Train a per-character LoRA for identity lock (Infinite tier) | P1 |
| C-11 | Lorebook entries — keyword-triggered context injection | P1 |
| C-12 | Publish a character to a public gallery; adopt others' characters | P2 |
| C-13 | Group chat — 2+ characters in one conversation | P2 |

> **On C-07:** this is not a nice-to-have. Replika's 2023 reversal proved that changing a character without consent is experienced as loss. If a model migration changes how a character behaves, the user must be able to see that a change happened and go back.

### 3.2 Conversation

| ID | Requirement | P |
|---|---|---|
| T-01 | Streaming text chat, first token < 500ms p50 | P0 |
| T-02 | Nine-layer compiled prompt with a stable cache prefix ([04 §3](04-CHARACTER-SYSTEM.md)) | P0 |
| T-03 | Model routing by tier; T2/T3 never touches a frontier API | P0 |
| T-04 | Multimodal input — the user can send a photo and the character sees it | P1 |
| T-05 | Proactive messages, rate-limited and user-controllable | P1 |
| T-06 | Regenerate, edit, and branch a conversation | P1 |
| T-07 | Character can send an in-scenario image unprompted when contextually apt | P1 |

> **On T-05:** proactive messages are the most abusable mechanic in this category. Rules: never more than a few per day, never guilt-based ("why haven't you talked to me?"), always disableable in one tap, and never used as a re-engagement growth lever. If a proactive message would not be welcome from a real friend, it does not ship.

### 3.3 Memory

| ID | Requirement | P |
|---|---|---|
| M-01 | Episodic memory — what happened, when | P0 |
| M-02 | Semantic memory — facts about the user, with confidence and provenance | P0 |
| M-03 | Temporal validity — facts know when they became true and when superseded | P0 |
| M-04 | Retrieval into the prompt, ranked by relevance × recency × importance | P0 |
| M-05 | Memory is inspectable and editable by the user | P0 |
| M-06 | Memory survives model migration — never stored as model-specific state | P0 |
| M-07 | Relational memory — the state of the relationship itself, not just facts | P1 |
| M-08 | Consolidation — periodic summarization into higher-order memories | P1 |
| M-09 | Full export in a portable format | P1 |

> **On M-05:** letting users see and correct what their companion believes about them is both a trust feature and a quality feature. When memory is wrong, users currently have no recourse but to repeat themselves and hope. Full spec in [07](07-MEMORY-ARCHITECTURE.md).

### 3.4 Voice

| ID | Requirement | P |
|---|---|---|
| V-01 | Realtime voice call, end-to-end round trip < 800ms p50, < 1200ms p95 | P0 |
| V-02 | Natural interruption — the user can cut in and the character stops | P0 |
| V-03 | Per-character voice, consistent forever, selected at creation | P0 |
| V-04 | Voice reflects personality axes and current emotional state | P1 |
| V-05 | Voice messages in text chat (async, both directions) | P1 |
| V-06 | Premium voice tier with wider emotional range | P1 |
| V-07 | Native speech-to-speech "Live mode" for T0/T1 | P2 |

Full latency budget in [06](06-REALTIME-VOICE-VIDEO.md).

### 3.5 Video

| ID | Requirement | P |
|---|---|---|
| VD-01 | Realtime video call with a photoreal, lip-synced face | P0 |
| VD-02 | Video face matches the character's locked identity | P0 |
| VD-03 | Metered in Aura, with clear remaining-balance display before and during | P0 |
| VD-04 | Graceful degradation to voice-only when bandwidth or balance is short | P0 |
| VD-05 | Call UI that feels like a phone call, not a web app | P1 |
| VD-06 | Character-initiated calls (opt-in, strictly rate-limited) | P2 |

> **On VD-02:** a video face that is not obviously the same person as the character's images destroys the illusion more thoroughly than having no video at all. If identity match cannot be achieved for a given character, video is disabled for that character rather than shipped wrong.

### 3.6 Images

| ID | Requirement | P |
|---|---|---|
| I-01 | Generate an image of the character, identity-locked, verified before delivery | P0 |
| I-02 | In-scenario selfies — generated from conversational context, not a form | P0 |
| I-03 | Face-similarity gate; regenerate or fail rather than deliver a wrong face | P0 |
| I-04 | Scene, outfit, pose, and expression control | P1 |
| I-05 | Per-user private gallery with real deletion | P1 |
| I-06 | Short video clips (non-realtime) | P2 |

### 3.7 Relationship

| ID | Requirement | P |
|---|---|---|
| R-01 | Affinity 0–1000, earned through interaction | P0 |
| R-02 | Seven relationship stages with behavioural changes at each | P0 |
| R-03 | Slow decay during absence, floored at the current stage threshold | P0 |
| R-04 | **No stage, affection, or emotional content is ever gated by payment** | P0 |
| R-05 | Milestones and anniversaries surfaced naturally in conversation | P1 |
| R-06 | Shared history view — a timeline of the relationship | P2 |

> **On R-03 and R-04 together:** decay exists so that returning after a long absence feels like reconnecting rather than resuming mid-sentence. It is floored at the stage threshold so a user can never *lose* a relationship stage they earned — that would be punishment, and it is the mechanic that makes these products feel manipulative. Combined with R-04, the rule is: the relationship responds to attention, never to spending.

### 3.8 Intimacy and adult content

| ID | Requirement | P |
|---|---|---|
| A-01 | Four tiers T0–T3, enforced server-side at the orchestrator | P0 |
| A-02 | Tier selects model and pipeline — not a prompt instruction | P0 |
| A-03 | Age assurance required before T2 access, per jurisdiction | P0 |
| A-04 | Per-character opt-in; T2/T3 off by default on every character | P0 |
| A-05 | Preferences as a bounded structured tag taxonomy, never free text | P0 |
| A-06 | Hard blocklist enforced pre-generation on every tier, no override | P0 |
| A-07 | Instant safeword / tier-down available in every surface | P0 |
| A-08 | Adult tiers on a separate payment rail and legal entity | P0 |

Full spec in [04 §11](04-CHARACTER-SYSTEM.md) and [13](13-TRUST-SAFETY-AND-COMPLIANCE.md).

**The hard blocklist, stated once and never negotiated:** no minors or minor-coded characters, no non-consent themes, no real identifiable people, no bestiality, no incest. Enforced by classifier before generation on every tier including T0. There is no user consent that unlocks these, because they are not about the user.

### 3.9 Account, privacy, safety

| ID | Requirement | P |
|---|---|---|
| P-01 | Clear, persistent disclosure that the companion is AI (SB 243) | P0 |
| P-02 | Self-harm protocol with crisis referral, published (SB 243) | P0 |
| P-03 | Encryption at rest for all conversation content | P0 |
| P-04 | Real deletion — account, characters, memory, media — within 30 days | P0 |
| P-05 | Full data export | P1 |
| P-06 | Break reminders, on by default where required | P1 |
| P-07 | No third-party ad or analytics SDKs with access to conversation content | P0 |

> **On P-03 and P-07:** the Muah.AI breach is the reference case. Conversation content in this category is among the most sensitive data any consumer product holds. A breach is not a bad quarter, it is the end of the company. Treat conversation content as regulated data even where no regulation names it.

---

## 4. Non-functional requirements

| Area | Target |
|---|---|
| Text first token | < 500ms p50, < 1000ms p95 |
| Voice round trip | < 800ms p50, < 1200ms p95 |
| Video first frame | < 2000ms from call accept |
| Image generation | < 8s p50 including the identity check |
| Availability | 99.5% at launch, 99.9% by month 12 |
| Memory retrieval | < 100ms p95 |
| Concurrent voice sessions | 500 at launch, 5,000 by month 12 |

**Availability note:** for this product, an outage is not an inconvenience — a companion who is unreachable is a companion who is absent. Status communication matters more here than in most consumer software, and the tone of it matters too.

---

## 5. Platforms

| Platform | Tiers | Priority |
|---|---|---|
| **Web / PWA** | T0–T3 | **Primary.** The full product. Installable, offline-capable shell, push. |
| **iOS (App Store)** | T0–T1 only | Funnel. Clean companion app, no adult content, no links to it. |
| **Android (Play)** | T0–T1 only | Same. |
| **Android (direct APK)** | T0–T3 | Full product for users who want it |
| **Desktop** | T0–T3 | P2, wraps the PWA |

**This split is forced, not chosen.** Apple and Google both prohibit this content. The store apps are a legitimate, complete SFW companion product and must not degrade or nag toward the web version — an app that exists only as a funnel gets rejected and deserves to be.

---

## 6. Success metrics

| Metric | Launch target | Month 12 |
|---|---|---|
| D1 retention | 45% | 60% |
| D30 retention | 20% | 35% |
| **D180 retention** | 8% | **20%** |
| Free → paid conversion | 4% | 8% |
| ARPU (paying) | $22 | $28 |
| Gross margin | 60% | 70% |
| Voice adoption (paid) | 40% | 65% |
| Video adoption (Premium+) | 25% | 50% |

> **D180 is the metric that matters.** Everything else in this category looks fine at D1 and collapses by month six, because that is when memory failure breaks the illusion. If Amorien's D180 is materially better than the category, the thesis is proven. If it is not, nothing else in this document was worth building.

---

## 7. Explicit non-goals for v1

- Beating Character.AI on catalogue size
- Native mobile apps with full feature parity
- Multi-language beyond English
- Creator monetization / revenue share
- AR/VR
- API for third-party developers

---

## 8. The monetization rules

These are product requirements, not marketing preferences, and they are binding on every future pricing decision.

1. **Text is unlimited on every paid plan.** It costs ~$0.0004 a message. Metering it would harm the habit loop that makes the product work, to save nothing.
2. **Compute is metered; emotion is not.** Aura buys voice minutes, video minutes, and images. It does not buy affection, relationship stages, memory, or personality.
3. **No cliffhanger paywalls.** A character never stops mid-emotional-beat to request payment.
4. **No manufactured jealousy or guilt.** The character does not use distress to drive spending. This mechanic works and it is not acceptable.
5. **Running out of Aura degrades gracefully.** Video falls back to voice, voice falls back to text, text always works. The relationship never stops.
6. **Annual plans are discounted honestly**, with no dark patterns on cancellation.

> Rule 5 is the structural expression of rules 1–4: **when a user runs out of money, they still have their companion.** Any pricing design that violates this is rejected regardless of what it does to revenue.

---

## 9. Open questions

| # | Question | Owner | Needed by |
|---|---|---|---|
| 1 | Anam vs. Tavus after a real side-by-side quality test at phone resolution | Eng | Phase 3 |
| 2 | Age-assurance vendor — Yoti estimation vs. Persona full suite, on conversion data | Legal/Growth | Phase 4 |
| 3 | Does character-card import create licensing exposure for cards derived from copyrighted properties? | Legal | Phase 1 |
| 4 | Self-host T2/T3 inference at launch, or start on a permissive host? | Eng | Phase 4 |
| 5 | Which entity structure cleanly separates the two payment rails? | Legal | Pre-incorporation |
| 6 | Is the public gallery in scope before there is a moderation team to support it? | Product | Phase 5 |

---

*Next: [04 — Character System](04-CHARACTER-SYSTEM.md) · [05 — AI Architecture](05-AI-ARCHITECTURE.md)*
