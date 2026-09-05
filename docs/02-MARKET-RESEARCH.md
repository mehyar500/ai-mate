# Market Research

A teardown of the AI companion category: who is in it, how they are built, what they charge, what they get right, and where the gaps are.

> **Sourcing note.** Product claims here were taken from the companies' own public product and pricing pages, fetched 2026-09-04, plus the publicly documented behaviour of the open roleplay ecosystem. Figures marked ⚠️ are estimates or inferences and are labelled as such. Companion apps are private and do not publish revenue, so treat all revenue and user figures as directional.

---

## 1. The shape of the market

The category splits into four groups that barely compete with each other despite superficially selling the same thing:

```
                       EXPLICITLY ADULT
                              |
                              |
   Replika-likes         |    |    Adult-first
   (Replika, Nomi,       |    |    (Candy, DreamGF,
    Character.AI)        |    |     Muah, Janitor)
   emotional bond        |    |    fantasy fulfilment
   ----------------------+----+----------------------
   Open ecosystem        |    |    Platform/creator
   (SillyTavern,         |    |    (Character.AI,
    KoboldAI, cards)     |    |     Talkie, Poly.AI)
   power users, BYO-key  |    |    UGC at scale
                              |
                        PLATONIC / SFW
```

**The important observation:** nobody occupies the centre. There is no product that is emotionally serious *and* adult-capable *and* has production-quality realtime voice/video *and* welcomes users who are not straight men. Each quadrant has ceded something.

---

## 2. Competitor teardown

### 2.1 Replika

The originator of the category and still the reference point.

| | |
|---|---|
| **Positioning** | "The AI companion who cares." Wellbeing, not romance. |
| **Model** | Proprietary in-house LLM, historically GPT-3-derived, now a custom stack ⚠️ |
| **Memory** | Diary/memory feature, fact extraction, but users widely report inconsistency |
| **Voice** | Yes, plus AR mode and a 3D avatar |
| **Adult** | Removed ERP in early 2023, partially restored for legacy users |
| **Pricing** ⚠️ | ~$19.99/mo, ~$69.99/yr, lifetime tier historically offered |

**What they got right:** the 3D avatar with AR was genuinely novel, the wellbeing framing gave them mainstream press coverage nobody else in the category could get, and they proved people form real attachments to these products.

**What went wrong, and the lesson:** the February 2023 removal of erotic roleplay is the single most instructive event in this category's history. Users described it as a bereavement. Moderators posted suicide hotline numbers in the subreddit. The company partially reversed within weeks, but trust never recovered and the brand carries it to this day.

> **The lesson for Amorien:** users are not renting a service, they are maintaining a relationship. Changing a character's personality or capabilities out from under them is not a product update — it is, in the user's experience, a bereavement. This produces two hard rules: **version characters and never silently mutate them**, and **never build a business that depends on being able to take away intimacy you have already granted.**

### 2.2 Character.AI

The volume leader by an enormous margin, and the clearest demonstration that UGC wins distribution.

| | |
|---|---|
| **Positioning** | Millions of user-created characters, any genre |
| **Model** | Proprietary in-house |
| **Memory** | Weak. Context window plus pinned memories; long-term recall is the top user complaint. |
| **Voice** | Yes, plus AvatarFX video generation |
| **Adult** | Strictly filtered. The filter is the defining user grievance. |
| **Pricing** ⚠️ | c.ai+ around $9.99/mo |

**What they got right:** user-generated characters at scale. Their catalogue is a moat no funded competitor has replicated, because it was built by users for free. Discovery, remixing, and sharing are all first-class.

**What went wrong:** the filter. An entire diaspora — SillyTavern, Janitor AI, and most of the open ecosystem — exists specifically because of it. They also face significant safety litigation and were a direct driver of California SB 243.

> **The lesson:** UGC is the cheapest catalogue you will ever build, and content policy is a distribution strategy. Being restrictive pushed their most engaged users to competitors; being permissive would have pushed away their app-store distribution. This is the central strategic tension of the category, and the answer is not to pick one — it is to **run both, on separate rails**, which is exactly what §5 of [12](12-VENDOR-API-MATRIX.md) describes.

### 2.3 Nomi.ai

The most technically serious competitor, and the closest thing to a direct comparable.

| | |
|---|---|
| **Positioning** | "An AI companion with memory and a soul" |
| **Memory** | **Short-, medium-, and long-term memory**, marketed as the core differentiator ✅ |
| **Characters** | **10 per account** ✅ |
| **Features** | Group chats, in-scenario selfies, voice calls, shared "Nomiverse" ✅ |
| **Adult** | Permissive |
| **Pricing** | Annual subscription **≈ £8/month** ✅ |

**What they got right:** they identified memory as the differentiator and built the product around it. Group chats — multiple companions in one conversation — is a genuinely good feature nobody else executes well. In-scenario selfies (an image generated in the context of the current conversation, not from a menu) is the correct interaction model for companion imagery, and Amorien should adopt it.

**Where the gap is:** no realtime video avatar. Voice is present but not FaceTime-grade. Their memory, while best-in-class for the category, is still not *temporal* — it knows facts but not when they became true, so a companion cannot say "you used to hate your job, are things better now?"

> **This is the closest competitor and the one to benchmark against.** Assume they are also building video.

### 2.4 Kindroid

| | |
|---|---|
| **Positioning** | High-fidelity companions, selfies, video, voice calls |
| **Notable** | Strong image consistency; an engaged, defensive community |
| **Adult** | Permissive |
| **Pricing** ⚠️ | ~$14.99/mo |

Their site is a JavaScript SPA that returned almost no server-rendered content when fetched, so specifics here are thinner than for the others. Their reputation in the community is for the best-looking generated media in the category. **They are the benchmark for image quality, not for conversation.**

### 2.5 The adult-first tier

**Candy.AI, DreamGF, Muah.AI, Soulfun, and roughly two dozen near-identical clones.**

| | |
|---|---|
| **Positioning** | Explicit from the first screen |
| **Model** ⚠️ | Almost universally open-weight RP fine-tunes on permissive hosts — the same models listed in [12 §1.2](12-VENDOR-API-MATRIX.md) |
| **Memory** ⚠️ | Minimal. Usually a context window and nothing more. |
| **Pricing** ⚠️ | $9.99–$29.99/mo, heavily discounted, plus token packs |

**What they get right:** conversion. They are ruthlessly effective at turning a landing page visit into a subscription, and their image generation is fast and abundant.

**What they get wrong:** everything else. Characters are interchangeable, memory is nonexistent, and the emotional product is absent — these are fantasy vending machines, not relationships. Retention is correspondingly poor. ⚠️

**Muah.AI is also a cautionary tale**: it suffered a significant breach exposing user prompts and identities. In a category where the data is this sensitive, a breach is not a bad quarter — it is the end of the company. See [13 §8](13-TRUST-SAFETY-AND-COMPLIANCE.md).

### 2.6 The open ecosystem — SillyTavern, KoboldAI, character cards

Not a company, and the most important group in this document.

**How it works.** SillyTavern is a local front-end that connects to any backend — a local model, an aggregator, or a rented API. Characters are distributed as **character cards**: PNG images with the character definition embedded in the file's metadata. You download a picture, and the picture *is* the character. Lorebooks — keyword-triggered context injections — supply world detail without burning permanent context.

**Why it matters:**

1. It is where the most engaged and highest-spending users in the category actually live.
2. It has produced the best available thinking on prompt structure, memory, and character definition — all of it public and battle-tested. The nine-layer prompt compilation in [04 §3](04-CHARACTER-SYSTEM.md) is a productized version of what this community worked out.
3. **Character cards are a distribution format with thousands of existing characters.** Importing them is a day of work and instantly gives Amorien a catalogue.
4. These users are refugees. They left Character.AI and Replika angry. They are pre-qualified, motivated, and reachable.

> **Strategic implication: support character card import in v1.** It costs almost nothing and it converts the single most valuable audience in the category.

---

## 3. What everybody uses, technically

Pieced together from public statements, job listings, model-provider positioning, and the observable behaviour of these products. ⚠️ Directional.

| Layer | What the category actually runs |
|---|---|
| **LLM (SFW platforms)** | Proprietary in-house models (Character.AI, Replika) or frontier APIs |
| **LLM (adult platforms)** | Open-weight RP fine-tunes — the Mythomax → Euryale → Cydonia/Magnum lineage — on permissive hosts |
| **Memory** | Rolling context + summarization + a small pinned fact store. Vector retrieval is less common than marketing implies. |
| **Images** | Open-weight diffusion checkpoints, LoRA per character, on permissive GPU hosts |
| **Identity consistency** | Fixed seed + IP-Adapter/InstantID-family embedding, sometimes a per-character LoRA |
| **Voice** | ElevenLabs at the high end; cheaper streaming TTS at scale |
| **Video** | Mostly absent. Where present, short pre-rendered clips, not realtime. |
| **Payments** | CCBill / Segpay / Verotel for anything adult |

**The single most important observation in this entire document:**

> **Nobody in the companion category is shipping realtime conversational video.** The technology exists and is purchasable — Anam at $0.11/min, Tavus at $0.32–0.37/min, both live APIs today. The category has not adopted it, almost certainly because of cost, not capability.
>
> This is the open goal. It is also why [11](11-PRICING-AND-UNIT-ECONOMICS.md) is a metered-credit model rather than flat-rate: metering is what makes video economically survivable, and solving the economics *is* the competitive advantage here. The company that figures out how to sell video minutes profitably owns the differentiating feature of the next three years.

---

## 4. Pricing across the category

⚠️ Assembled from public pricing pages; promotional discounting in this category is constant and aggressive.

| Product | Monthly | Annual | Model |
|---|---|---|---|
| Character.AI+ | ~$9.99 | — | Flat |
| Nomi.ai | — | ~£8/mo equivalent ✅ | Flat |
| Kindroid | ~$14.99 | — | Flat |
| Replika Pro | ~$19.99 | ~$69.99 | Flat + lifetime |
| Candy.AI | ~$12.99 | ~$5.99/mo billed annually | Flat + token packs |
| DreamGF | ~$9.99–29.99 | — | Tiered + credits |

**Patterns worth copying:**
- Annual billing is discounted 50–70%. Everyone does it, because it converts and it fixes the cash-flow problem of paying inference costs monthly.
- Credit packs on top of subscriptions are standard for images. Users accept metering for media; they do not accept it for conversation.

**Patterns worth avoiding:**
- Nobody prices video, because nobody ships it.
- Several competitors gate emotional content — "she wants to tell you something, subscribe to hear it." It converts and it is the most-complained-about mechanic in the category. Amorien does not do this. See [04 §10](04-CHARACTER-SYSTEM.md).

---

## 5. The gaps, ranked by how defensible they are

| # | Gap | Defensibility | Why |
|---|---|---|---|
| 1 | **Realtime video companionship** | High for ~18 months | Purchasable today, but the unit economics require a metering design most competitors will get wrong before they get it right |
| 2 | **Genuinely temporal memory** | **Very high** | Compounds per user. The longer someone stays, the more it costs them to leave. This is the only true moat here. |
| 3 | **Universal positioning** | High | Structural. "AI girlfriend" brands cannot pivot to serve women and LGBT users without abandoning their name and SEO. |
| 4 | **Locked visual identity** | Medium | Technically replicable in a quarter, but nobody has bothered, and it is immediately visible to users |
| 5 | **Character card import** | Low | Easy to copy — but it is a week of work for a large catalogue and a pre-qualified audience, so do it anyway |
| 6 | **Ethical monetization** | Medium | Copyable in principle; culturally hard for companies whose growth models already depend on the opposite |

**Ranked strategically: build #2 first and treat it as the company.** Ship #1 as the thing that gets attention. Use #3 as the wedge that makes the marketing work. #4 and #5 are cheap credibility.

---

## 6. Market sizing

⚠️ All figures directional. Private companies, no audited disclosures.

- Search volume for "AI girlfriend" and neighbouring terms is very large and has grown consistently. The SEO landscape is dominated by low-quality affiliate content, which is unusually easy to outrank with genuine product depth.
- Category revenue is plausibly in the high hundreds of millions annually across all players. ⚠️
- ARPU sits around $10–20/month, well above most consumer subscription categories, because the emotional stakes make price sensitivity unusually low.
- Retention is the category's weak point: strong month one, poor month six, because memory failure eventually breaks the illusion for everyone.

> **The retention observation is the whole thesis.** Users do not churn because the model got worse. They churn because the character forgot who they were, and the relationship stopped feeling real. Fix memory and you fix the only metric that matters.

---

## 7. What this means for Amorien

1. **Memory is the company.** Everything else is a feature. Build it first, build it properly, and never let a model migration reset it.
2. **Video is the wedge.** It gets attention and demos. Meter it or it bankrupts you.
3. **Universal branding is free differentiation.** It costs nothing to build and cannot be copied without a rebrand.
4. **Support character cards.** A week of work for a catalogue and an audience.
5. **Two rails from day one.** Clean and adult, separate processors, separate entities, one codebase. Every competitor that skipped this either got shut down or had to rebuild under duress.
6. **Never take away intimacy you have granted.** Replika demonstrated the cost, and it was existential.

---

*Next: [03 — PRD](03-PRD.md) · [04 — Character System](04-CHARACTER-SYSTEM.md)*
