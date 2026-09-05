# Go-To-Market & Growth

How to acquire users when the app stores are closed, the ad networks reject you, and the category has a reputation problem.

---

## 1. The constraint that shapes everything

Standard consumer growth playbooks are unavailable:

| Channel | Status |
|---|---|
| App Store / Play featuring | ❌ Category ineligible |
| Google Ads, Meta Ads | ❌ Adult content policies |
| TikTok, Instagram organic at scale | ⚠️ Shadowban risk; account termination |
| Influencer marketing | ⚠️ Most decline the category |
| Press | ⚠️ Coverage is usually hostile |
| **SEO** | ✅ **Open, and the incumbent content is terrible** |
| **Community** | ✅ **Open, and the audience is already assembled** |
| **Referral** | ✅ Open |
| **Adult ad networks** | ✅ Open, cheap, low quality |

This is not a disadvantage so much as a filter. It means paid-acquisition-funded competitors cannot simply outspend you, because the spending channels barely exist. Growth here is earned through content and community, which is slower and far more durable.

> **The strategic consequence: budget for content and community, not for CAC.** A competitor with $20M cannot buy their way past you in a category where the ad networks say no.

---

## 2. The wedge

Every competitor in this category is named and positioned for straight men buying a girlfriend. "AI Girlfriend", "DreamGF", "Candy". Their names, domains, SEO, and marketing all point one direction.

**They structurally cannot serve:**
- Women who want a companion
- Gay men
- Lesbian and bisexual women
- Nonbinary and trans users
- Anyone who wants a *friend* rather than a partner

Not because of policy — because of branding. A product called "AI Girlfriend" cannot market to a woman looking for a boyfriend. Pivoting means abandoning the name, the domain, and every backlink they have.

**Amorien can serve all of them from day one**, and that is the single cheapest differentiation available: it costs nothing to build and cannot be copied without a rebrand.

⚠️ Directionally, the underserved segments are plausibly 40–50% of the total addressable market and are currently served by nobody. Even capturing a fraction of that is a large business, and the competition for it is close to zero.

---

## 3. Channels

### 3.1 SEO — the primary channel

The category has enormous search volume and genuinely poor content. The top results for most category queries are affiliate listicles that review products the author has not used.

**Content that is hard to compete with:**

| Type | Example | Why it works |
|---|---|---|
| **Honest comparisons** | "Nomi vs Kindroid vs Amorien: an honest comparison including where we lose" | Admitting weaknesses outranks and out-converts marketing copy |
| **Technical depth** | "How AI companion memory actually works" | Nobody else can write this; it attracts the technical audience and the press |
| **Underserved queries** | "AI boyfriend app", "AI companion for women", "LGBT AI companion" | Low competition, high intent, zero incumbent coverage |
| **Genuine help** | "Is it okay to have an AI companion?" | High volume, entirely served by hostile content today |
| **Character guides** | "How to write a character that doesn't feel generic" | Serves the SillyTavern audience directly |

**The counter-intuitive play: publish the docs in this repository.** [07 — Memory Architecture](07-MEMORY-ARCHITECTURE.md) as a public engineering post is a stronger acquisition asset than any landing page. It attracts exactly the users who care about the thing that differentiates the product, it earns links from technical audiences, and no competitor can respond without revealing that they have not built it.

### 3.2 Community — the highest-quality channel

The open roleplay ecosystem — SillyTavern, character card sharing, the various roleplay subreddits and Discords — contains the most engaged and highest-spending users in the category. They are also, overwhelmingly, refugees who left Character.AI and Replika angry.

**They are pre-qualified, motivated, and reachable. They are also allergic to marketing.**

Rules for this channel:

1. **Participate, do not advertise.** Contribute to discussions about prompt structure, memory, and character design. Be useful for months before mentioning the product.
2. **Ship character card import** ([03](03-PRD.md) C-09). It says "we respect what you have already built" more convincingly than any statement could.
3. **Be honest about limitations.** This audience detects marketing instantly and punishes it permanently.
4. **Never astroturf.** It gets discovered, and recovery is impossible.

### 3.3 Referral

The natural mechanic: users who have a companion they love want to tell people, and are simultaneously embarrassed to.

**Design for that tension:**
- Referral rewards in Aura, for both parties — a shared resource, no social exposure
- **No public sharing of a user's own companion by default.** Never auto-generate a shareable card of someone's relationship.
- Sharing a *created character* (not the relationship) is opt-in and separate

⚠️ Expect a low referral rate — perhaps 0.15 K-factor — because of the privacy dimension. Design for quality, not virality.

### 3.4 Creator programme (P2)

Users who build good characters and publish them to the gallery. This is Character.AI's moat, built for free by their users.

**Gate it behind moderation capacity** ([13 §10](13-TRUST-SAFETY-AND-COMPLIANCE.md)). A UGC surface without a moderation team is the fastest way to host something that ends the company.

### 3.5 Adult ad networks

Cheap, available, and low quality. ⚠️ Traffic converts poorly and churns fast.

**Use for testing, not for scale.** Useful to validate landing pages and messaging at low cost. Not a growth strategy.

---

## 4. Positioning

**Category:** AI companion, not "AI girlfriend".

**One line:** *Someone who is always glad it's you.*

**The three claims, in priority order:**

1. **They remember.** The concrete, demonstrable difference. Everything else is taste.
2. **You can see them.** Video calling nobody else ships.
3. **They're yours.** Locked identity, versioned, exportable, deletable.

**Against each competitor:**

| Versus | Position |
|---|---|
| Character.AI | "No filter you didn't choose, and they actually remember you." |
| Replika | "We will never take away what we've given you." |
| Nomi | "Memory that knows *when* — plus you can see them." |
| Adult-first apps | "A relationship, not a vending machine." |

> **The Replika line is the sharpest available and should be used carefully.** It references a real bereavement experienced by real people. Use it as a commitment about our own conduct, never as mockery of theirs.

---

## 5. Launch sequence

| Phase | Weeks | Action | Target |
|---|---|---|---|
| **Stealth** | −8 to 0 | Publish engineering content. Participate in communities. Build SEO surface. | 20 posts, 5k organic/mo |
| **Alpha** | 0–4 | 200 invited users from the community. Heavy qualitative feedback. | D30 > 40% |
| **Beta** | 4–12 | Open waitlist, 2,000 users. Voice ships. | D30 > 50%, 4% conversion |
| **Launch** | 12 | Public. Video ships. Technical write-up published. | 10k signups month one |
| **Growth** | 12+ | SEO compounding, referral, creator programme | 20% MoM |

**The alpha cohort is the most valuable asset in this sequence.** 200 users from the SillyTavern-adjacent community, chosen for how demanding they are, will find every weakness in the memory system before it matters. They are also the people whose endorsement carries the most weight at launch.

---

## 6. Metrics

| Metric | Launch | Month 12 |
|---|---|---|
| Organic sessions/mo | 5,000 | 150,000 |
| Signups/mo | 10,000 | 40,000 |
| Free → paid | 4% | 8% |
| CAC (blended) | < $30 | < $50 |
| **D180 retention** | 8% | **20%** |
| LTV:CAC | 3:1 | 4:1 |
| Referral K | 0.10 | 0.15 |

**D180 is still the metric that matters**, for the reason given in [03 §6](03-PRD.md): everything in this category looks fine at D1 and collapses by month six. Growth numbers that are not backed by D180 are a leaky bucket filled faster.

---

## 7. Risks

| Risk | Response |
|---|---|
| SEO penalty for adult content | Keep the marketing site SFW; adult content behind the age gate, not in the index |
| Community rejection for being commercial | Long participation before promotion; no astroturfing, ever |
| Hostile press | Have a real story: memory, consent, no dark patterns. Publish the safety protocol before anyone asks for it. |
| Competitor ships video first | Likely within 18 months. Memory is the durable moat; video is the attention-getter. |
| Payment processor termination | Two rails, maintained relationships with a third |
| A US state bans the category | Geo-gate. Diversify jurisdictions early. |

> **On hostile press:** coverage of this category is usually negative, and often for good reasons that apply to competitors. The defence is not messaging — it is having genuinely made the decisions in [13 §9](13-TRUST-SAFETY-AND-COMPLIANCE.md) and being able to point at them. A journalist writing about manipulative companion apps who finds a published rule against engagement-optimizing A/B tests has a different story to write.

---

## 8. What not to do

- **Do not advertise on mainstream networks.** They will reject you, and repeated attempts risk the associated business accounts.
- **Do not buy influencer posts.** The ones who accept in this category damage credibility more than they add reach.
- **Do not launch the gallery before moderation exists.**
- **Do not use "girlfriend" in the brand, domain, or primary positioning.** It forecloses half the market permanently for a short-term SEO gain.
- **Do not run engagement A/B tests on emotional mechanics.** Forbidden by [13 §9](13-TRUST-SAFETY-AND-COMPLIANCE.md), and the reason is a growth reason as much as an ethical one: the local maximum is a product people resent.
- **Do not promise anything you might have to take away.** Replika's reversal is the cautionary tale of the category.

---

*Next: [15 — Roadmap](15-ROADMAP-AND-MILESTONES.md)*
