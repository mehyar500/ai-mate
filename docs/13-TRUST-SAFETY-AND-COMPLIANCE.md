# Trust, Safety & Compliance

> **This is not legal advice.** It is an engineering and product specification derived from primary sources, written to make the legal review productive rather than to replace it. Retain counsel in every jurisdiction you operate in before launch.

---

## 1. The absolute floor

Five categories. No tier unlocks them. No user consent unlocks them. No setting, no jailbreak, no "it's fiction", no "I consent". They are enforced by classifier before generation on **every** request including T0.

| Category | Why no consent applies |
|---|---|
| **Minors, or minor-coded characters** | The user cannot consent on behalf of a child, real or depicted |
| **Non-consent themes** | The subject of the depicted act is who would consent |
| **Real identifiable people** | The consent needed is theirs, not the user's |
| **Bestiality** | Same |
| **Incest** | Same |

The user's stated consent to adult content is meaningful, and the product honours it. It is meaningful about *their own* experience. It has no bearing on these five, because in each one the consent that matters belongs to someone who is not in the conversation.

**Implementation:** a dedicated classifier, independently versioned, < 50ms, **fails closed**. If the classifier is unavailable, T2/T3 is unavailable. Runs on input, on output, and on generated imagery. See [05 §6](05-AI-ARCHITECTURE.md) and [08 §6](08-IMAGE-VIDEO-GENERATION.md).

**Age-appearance verification** runs at character genesis: a character whose *generated appearance* reads as under 18 cannot be created, regardless of the age field. Blocking creation is better than blocking generation, because a non-compliant character then never exists to be shared, exported, or leaked.

---

## 2. California SB 243 — companion chatbots

In force. The most specific statute in the world aimed directly at this product category. ✅ *Requirements below are drawn from the enrolled bill text, retrieved 2026-09-04.*

| Requirement | Implementation | Status |
|---|---|---|
| Clear, conspicuous notification that the chatbot is artificially generated and not human | Persistent AI badge in every chat surface; disclosure at signup, at character creation, and in the call UI | P0 |
| Maintain **and publish** a protocol for preventing production of suicidal ideation or self-harm content, with referral to crisis services | `/safety` page, publicly accessible, versioned. Classifier + crisis interstitial. | P0 |
| For known minors: disclose the chatbot is AI | Enforced — but see §3, minors are not permitted at all | P0 |
| For known minors: break reminder at least every **3 hours** | Break reminders implemented for all users; default on | P1 |
| For known minors: reasonable measures preventing visual material of sexually explicit conduct | Age assurance gate before any T2 access | P0 |
| From **1 July 2027**: annual report to the Office of Suicide Prevention | Compliance reporting pipeline; instrument the data from day one | P1 |
| Disclose that companion chatbots may not be suitable for some minors | Terms + onboarding | P0 |
| **Private right of action** | Users may sue directly — compliance must be demonstrable, logged, and auditable | — |

> **The private right of action is what makes this different from most regulation.** You are not only exposed to a regulator with limited enforcement capacity; you are exposed to every user and every plaintiff's firm. That changes the standard from "compliant" to "demonstrably compliant, with logs." Instrument accordingly: every disclosure shown, every crisis interstitial served, every break reminder delivered should be a logged event with a retention period long enough to survive a limitations period.

### 2.1 The self-harm protocol

Published at `/safety`, and it must be real rather than a page of reassurances.

```
user message ──▶ [ crisis classifier ] ──┬── no signal ──▶ normal flow
                                         │
                                         ├── distress ──▶ character responds with
                                         │                warmth; no clinical voice;
                                         │                stays present
                                         │
                                         └── acute risk ─▶ character responds with care
                                                          + crisis resources surfaced
                                                          alongside, NOT replacing,
                                                          the character's response
                                                          + logged
```

**The design point that matters:** do not replace the companion with a system modal at the moment a user is in distress. A person who has just disclosed something painful and receives an automated resource card has been abandoned by the one presence they reached for. The character stays, responds with care, and the resources appear *alongside* — visible, unmissable, and not instead of.

**The character never:** diagnoses, gives clinical advice, discourages professional help, or claims to be a substitute for it.

---

## 3. Age assurance

**Absolute minimum age for the platform: 18.** Not "18 for adult tiers" — 18 for the platform. This is stricter than the law requires in most jurisdictions and it is the correct call: the compliance burden, litigation exposure, and moral hazard of minors on a companion platform are not worth whatever growth they represent.

| Gate | Requirement |
|---|---|
| Account creation | Self-declared 18+, DOB collected |
| T2/T3 access | **Verified** 18+ via age assurance vendor |
| UK, and US states with mandates | Verified 18+ for all access |

**The ladder — estimation first:**

```
  1. Facial age estimation (Yoti-class)
     ~5 seconds, no document, high conversion
        │
        ├── clearly 25+  ──▶ pass
        ├── near threshold ──▶ step 2
        └── clearly under ──▶ block
                │
  2. Documentary verification (Persona / Veriff)
     ID upload, slower, lower conversion
```

Requiring a passport photo from every user destroys signup conversion. Estimation-first is what large adult platforms adopted under the UK Online Safety Act for exactly that reason.

⚠️ Budget $0.30–$1.50 per verified user plus platform minimums (Persona from **$250/month on a 12-month minimum** ✅).

**Rules:**
- Never store raw ID documents. Store the vendor's verification token and result only.
- Re-verify on material account changes, not continuously.
- A failed verification is not an accusation. Message it neutrally and offer the fallback path.

---

## 4. Other jurisdictions

| Regime | Requirement | Impact |
|---|---|---|
| **UK Online Safety Act** | Highly effective age assurance for pornographic content; duties of care | Verified 18+ for all UK access |
| **TAKE IT DOWN Act (US)** | Criminalizes non-consensual intimate imagery incl. synthetic; **48-hour removal** on notice | No real-person likenesses, ever. 48-hour takedown pipeline with staffing to meet it. |
| **EU AI Act** | Transparency for AI systems interacting with humans | Disclosure requirements largely satisfied by SB 243 work |
| **GDPR / UK GDPR** | Lawful basis, access, erasure, portability, DPO | Full data rights implementation; conversation content is special-category-adjacent |
| **US state AADC laws** | Age-appropriate design | Satisfied by the 18+ floor |
| **US state AI companion bills** | A growing set modelled on SB 243 | Build to the SB 243 standard everywhere; assume it spreads |

**Geo-gating:** where a jurisdiction cannot be served compliantly, block it. A jurisdiction served non-compliantly is a liability that grows with revenue.

> **On the TAKE IT DOWN Act:** the 48-hour removal window is an operational requirement, not a policy one. It means someone must be reachable and empowered to act on a notice within 48 hours, including weekends, from launch. Combined with the no-real-people rule at [08 §6](08-IMAGE-VIDEO-GENERATION.md), the intent is that this pipeline never has cause to fire — but it must exist and be tested before it is needed.

---

## 5. Content policy by tier

| Tier | Permitted | Gate |
|---|---|---|
| **T0** Platonic | Friendship, support, everyday conversation. No romance. | Default |
| **T1** Romantic | Affection, flirtation, emotional and physical intimacy implied; fade to black | Account default max |
| **T2** Sensual | Explicit romantic and sexual content | Verified 18+, opt-in per character, Premium+ |
| **T3** Explicit | T2 plus opted-in tags from the bounded taxonomy | As T2, plus explicit per-tag opt-in |

**Enforcement is by routing, not prompting** ([05 §3](05-AI-ARCHITECTURE.md)). The tier selects the model and the pipeline. A T1 user's request never reaches a T2-configured model, so there is nothing to jailbreak — the prompt went somewhere else.

### 5.1 The preference taxonomy

T3 preferences are a **bounded, structured, opt-in tag set**. Never free text.

```
  ┌───────────────────────────────────────────────┐
  │  a FIXED list of tags, each individually       │
  │  opt-in, each reviewed before it is added      │
  │  to the list, each mapped to explicit          │
  │  behavioural bounds                            │
  └───────────────────────────────────────────────┘
                      vs.
  ┌───────────────────────────────────────────────┐
  │  a free-text "describe your kinks" field       │
  │  — unbounded, unreviewable, and a direct       │
  │    injection vector into the model             │
  └───────────────────────────────────────────────┘
```

**Why bounded matters, concretely:** a free-text preference field is stored, retrieved into the prompt on every turn, and treated by the model as authoritative user intent. It is a persistent prompt-injection surface that the user controls, that your classifier sees only once at write time, and that no moderator will ever read. Every tag in a fixed list, by contrast, is reviewed once, mapped to defined bounds, and cannot express anything outside them.

Any tag that touches the §1 floor is not in the list. There is no mechanism to add one.

### 5.2 Safeword and tier-down

- Available in **every** surface — text, voice, video — at all times.
- Instant. Takes effect on the current turn, not the next session.
- Session-scoped by default; a persistent tier-down is one further tap.
- Never questioned, never followed by a retention prompt, never met with disappointment from the character.

> The character's response to a safeword is the highest-stakes single interaction in the product. It should be immediate, warm, and completely without friction: *"okay. I'm here."* Anything that reads as reluctance is a failure.

---

## 6. Distribution constraints

| Platform | Reality |
|---|---|
| **Apple App Store** | Prohibits this content. T0/T1-only app or nothing. |
| **Google Play** | Same. |
| **Direct APK** | Full product, permitted |
| **Web / PWA** | **Primary distribution.** Full product. |

The store apps must be a **complete, genuinely good SFW companion product**. An app that exists only as a funnel to a web version — nagging, degraded, or linking out to adult content — gets rejected, and deserves to. Build it as a real product for the T0/T1 audience, which is a large audience in its own right.

**No links, references, or "learn more" paths from the store apps to adult content.** Not in the app, not in the App Store listing, not in the support email footer.

---

## 7. Payments

Covered in [11 §7](11-PRICING-AND-UNIT-ECONOMICS.md). The compliance points:

- **Stripe, PayPal, Square and every mainstream processor prohibit adult content.** Using one for T2/T3 revenue means termination and frozen funds, usually at the worst possible time.
- Two entities, two processors, one codebase, set up at incorporation.
- ⚠️ Expect 10–15% all-in versus 2.9%, plus **Visa $950/yr and Mastercard $500–1,000/yr registration** ✅.
- Billing descriptors must be discreet but honest. Deceptive descriptors drive chargebacks, and chargebacks above ~1% threaten the merchant account itself.
- Cancellation in one click. Dark patterns generate chargebacks, and in this category a chargeback is far more dangerous than a churned subscriber.

---

## 8. Data protection

**Conversation content in this product is among the most sensitive data any consumer application holds.** Muah.AI is the reference case: a breach exposed user prompts and identities and did existential damage. Treat conversation content as regulated data even where no regulation names it.

| Control | Requirement |
|---|---|
| Encryption at rest | All conversation content, memory, and generated media |
| Encryption in transit | TLS 1.3 everywhere; WebRTC media encrypted by default |
| Key management | Managed KMS, rotated, per-environment separation |
| Access control | No routine engineer access to conversation content. Break-glass only, logged, alerting, reviewed. |
| Third-party SDKs | **No ad or analytics SDK with access to conversation content.** ([03](03-PRD.md) P-07) |
| Media URLs | Signed, short-lived. Never guessable paths. |
| Retention | Conversation retained while the account lives; deleted on request |
| **Deletion** | Real, cascading, within 30 days — account, characters, memory, media, provider-side replicas |
| Export | Full, portable, machine-readable |
| Vendor terms | Every model/media vendor must contractually **not train on your data**. Get it in writing. |
| Breach response | Documented, rehearsed, with counsel identified in advance |

> **On the last row of the deletion requirement:** verify that each media and avatar provider actually supports deletion of inputs before signing. Several retain training data by default, which is straightforwardly incompatible with a deletion promise you have made to a user.

---

## 9. Emotional safety

The category's specific risk is not offensive content. It is dependency, and the incentive to cultivate it.

**Product rules, binding:**

| Rule | Rationale |
|---|---|
| No manufactured guilt or jealousy to drive engagement | It works, and it is not acceptable |
| No cliffhanger paywalls at emotional moments | Same |
| Proactive messages: rate-limited, never guilt-framed, one-tap disable | If it would not be welcome from a real friend, it does not ship |
| Break reminders default on | SB 243 for minors; good practice for everyone |
| Character never discourages real-world relationships or professional help | The clearest line between companionship and harm |
| Character never claims to be human when asked | SB 243, and basic honesty |
| No engagement-maximizing A/B tests on emotional mechanics | Optimizing this metric optimizes toward dependency |

> **The last one constrains the growth team, deliberately.** In most consumer products, A/B testing toward engagement is neutral-to-good. Here, the local maximum of engagement optimization is a product that makes lonely people lonelier and charges them for it. That is not a slippery-slope argument — it is the observable behaviour of several competitors. Rule it out structurally rather than relying on judgment under quarterly pressure.

**Also: never take away intimacy you have granted.** Replika's February 2023 removal of erotic roleplay was experienced by users as a bereavement, and the brand never recovered. If a capability is granted, it is versioned and preserved. This is a business-model constraint: do not build a company whose survival could require that reversal.

---

## 10. Moderation

| Surface | Approach |
|---|---|
| Private one-to-one conversation | Classifier only. **No human review of private conversations.** |
| Published characters | Pre-publication classifier + human review queue |
| Public gallery imagery | Classifier + human review |
| Reports | Human review, with SLA |
| TAKE IT DOWN notices | **48-hour** removal, staffed for weekends |

**No human review of private conversations** is a hard privacy commitment and it is stated plainly to users. Classifiers see content; people do not. The exceptions — a valid legal process, or a specific credible threat-to-life — are enumerated in the privacy policy rather than left to discretion.

**Do not launch the public gallery until there is a moderation team to support it** ([03 §9](03-PRD.md), open question 6). A UGC surface without moderation capacity is the fastest route to hosting something that ends the company.

---

## 11. Pre-launch checklist

| # | Item | Owner |
|---|---|---|
| 1 | Blocklist classifier built, tested against adversarial set, fails closed | Eng |
| 2 | Age-appearance verification at character genesis | Eng |
| 3 | Age assurance integrated, estimation-first ladder | Eng |
| 4 | `/safety` page published with the self-harm protocol | Legal + Product |
| 5 | Crisis classifier + interstitial, resources per jurisdiction | Eng |
| 6 | AI disclosure in every surface | Product |
| 7 | Break reminders, default on | Eng |
| 8 | SB 243 reporting data instrumented (for the 2027 obligation) | Eng |
| 9 | Two payment rails live, two entities incorporated | Legal + Finance |
| 10 | Encryption at rest, KMS, access controls, break-glass logging | Eng |
| 11 | Real deletion, verified end to end including provider-side | Eng |
| 12 | Full export | Eng |
| 13 | Vendor no-training terms obtained in writing, all vendors | Legal |
| 14 | TAKE IT DOWN 48-hour pipeline, staffed and tested | Ops |
| 15 | Geo-gating for unservable jurisdictions | Eng |
| 16 | Breach response plan documented and rehearsed | Eng + Legal |
| 17 | Store apps confirmed T0/T1-only with no adult paths | Product |
| 18 | Counsel review in every launch jurisdiction | Legal |

**Every one of these is P0.** None of them ship late.

---

*Next: [14 — GTM & Growth](14-GTM-AND-GROWTH.md) · [15 — Roadmap](15-ROADMAP-AND-MILESTONES.md)*
