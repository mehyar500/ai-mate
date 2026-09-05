# Pricing & Unit Economics

Every cost, every plan, every margin. Prices marked ✅ were verified from vendor pricing pages on 2026-09-04; ⚠️ marks estimates and derived figures.

---

## 1. The sentence that determines the pricing model

> **Text conversation is nearly free. Voice is affordable. Video is expensive.**

| Modality | Marginal cost | What $1 buys | Ratio to text |
|---|---|---|---|
| Text message | ~$0.0004 ⚠️ | ~2,500 messages | 1× |
| Voice minute (standard) | ~$0.033 ✅ | ~30 minutes | **83×** |
| Voice minute (premium) | ~$0.050 ✅ | ~20 minutes | 125× |
| Video minute | ~$0.145 ⚠️ | ~7 minutes | **363×** |
| Image | ~$0.010 ⚠️ | ~100 images | 25× |

A video minute costs as much as **363 text messages**. No single flat price can serve a user who sends 50 messages a day and a user who spends two hours a week on video calls. Pricing them the same either overcharges the first or bankrupts you on the second.

**Therefore: text is unlimited, and compute-heavy modalities are metered in Aura.**

This is not a monetization trick. It is the only structure where the heaviest users — who are also the most engaged and least likely to churn — remain profitable rather than becoming a liability you quietly hope will leave.

---

## 2. Token math for a text turn

The prompt structure from [04 §3](04-CHARACTER-SYSTEM.md), counted:

| Layer | Tokens | Cached? |
|---|---|---|
| L1 system frame + safety floor | 350 | ✅ |
| L2 character identity | 900 | ✅ |
| L3 personality → directives | 450 | ✅ |
| — **cache boundary** — | **1,700 cached** | |
| L4 relationship state | 120 | ✗ |
| L5 semantic memory | 400 | ✗ |
| L6 episodic memory | 350 | ✗ |
| L7 lorebook (triggered) | 250 | ✗ |
| L8 session state | 80 | ✗ |
| L9 recent turns | 1,200 | ✗ |
| | **2,400 uncached** | |
| **Total input** | **4,100** | |
| **Output** | **~180** | |

### 2.1 Cost per message

**T0/T1 on `qwen3.7-flash`** ($0.030/M in, $0.130/M out ✅):

```
uncached input   2,400 × $0.030/1M  =  $0.000072
cached input     1,700 × $0.0075/1M =  $0.0000128    ⚠️ assumes 4x cache discount
output             180 × $0.130/1M  =  $0.0000234
                                       ──────────
                                       $0.000108  per message
```

**T2/T3 on `cydonia-24b-v4.1`** ($0.300/M in, $0.500/M out ✅):

```
input            4,100 × $0.300/1M  =  $0.00123     ⚠️ assume no cache discount
output             180 × $0.500/1M  =  $0.00009
                                       ──────────
                                       $0.00132   per message
```

**T2/T3 premium on `l3.3-euryale-70b`** ($0.650/$0.750 ✅): **$0.00280/message**

Add background memory work at ~$0.00005/message amortized ([07 §11](07-MEMORY-ARCHITECTURE.md)).

| Route | $/message | Messages per $1 |
|---|---|---|
| T0/T1 `qwen3.7-flash` | $0.00016 | 6,250 |
| T2/T3 `cydonia-24b` | $0.00137 | 730 |
| T2/T3 `euryale-70b` | $0.00285 | 350 |

> **Note what the cache boundary is worth.** Without it, all 4,100 input tokens bill at full rate and the T0/T1 message cost rises to ~$0.000146 — a 35% increase. On the frontier realtime models where cached input is 80× cheaper ✅, the same discipline is worth far more. This is why [05 §5](05-AI-ARCHITECTURE.md) forbids volatile tokens above the boundary, and why it is enforced by a test.

### 2.2 Monthly text cost per user

| User type | Messages/day | T0/T1 | T2/T3 |
|---|---|---|---|
| Light | 20 | $0.10 | $0.82 |
| Typical | 60 | $0.29 | $2.47 |
| Heavy | 150 | $0.72 | $6.17 |
| Extreme | 400 | $1.92 | $16.44 |

**Text at T0/T1 is genuinely free at any usage level.** Even the extreme user costs less than $2/month. T2/T3 is 8.5× more expensive and is a real cost at the top of the distribution — which is one reason adult tiers start at the $29.99 plan rather than the $12.99 one.

---

## 3. Voice and video cost

From [06 §5](06-REALTIME-VOICE-VIDEO.md), verified components ✅:

| Component | Standard | Premium |
|---|---|---|
| LiveKit agent session | $0.0100 | $0.0100 |
| STT (Deepgram Flux) | $0.0065 | $0.0065 |
| LLM (~4 turns/min) | $0.0014 | $0.0028 |
| TTS | $0.0054 (Inworld) | $0.0225 (Cartesia) |
| Observability | $0.0100 | $0.0100 |
| **Voice total** | **$0.0333/min** | **$0.0518/min** |
| Video avatar (Anam) | +$0.11 | +$0.11 |
| **Video total** | **$0.144/min** | **$0.162/min** |

| | $/hour |
|---|---|
| Voice standard | $2.00 |
| Voice premium | $3.11 |
| **Video** | **$8.65** |
| Video on Tavus instead ⚠️ | $22.20 |

> **Observability at $0.0100/min is 30% of a standard voice minute.** It is worth it during the first year — you cannot debug a latency budget you cannot see — and it is the first thing to sample down (say, 10% of sessions) once the pipeline is stable. That single change takes standard voice from $0.0333 to $0.0243/min, a 27% reduction.

---

## 4. Aura — the credit system

**1 Aura ≈ 1 standard voice minute.** Everything else is priced relative to that.

| Action | Aura | Our cost | Margin at $0.012/Aura |
|---|---|---|---|
| Voice minute (standard) | 1 | $0.033 | ⚠️ **negative** — subsidized |
| Voice minute (premium) | 2 | $0.052 | −$0.028 — subsidized |
| Video minute | 4 | $0.145 | −$0.097 — subsidized |
| Image (standard) | 2 | $0.010 | **+$0.014** |
| Image (high quality) | 5 | $0.035 | +$0.025 |
| Video clip, 4s (P2) | 20 | $0.20 | +$0.04 |
| Character LoRA training | 30 | $0.11 | +$0.25 |

**Read that table carefully: voice and video are deliberately sold below marginal cost.**

That is intentional and it is the core of the model. The subscription — not the Aura price — carries the margin. Aura included in a plan is priced generously because the plan's job is to make the *typical* user profitable, and typical users do not exhaust their Aura. Top-up packs exist for the tail, and they are priced closer to cost as a brake on the extreme user rather than as a profit centre.

**Top-up packs:**

| Pack | Aura | Price | $/Aura |
|---|---|---|---|
| Small | 250 | $4.99 | $0.020 |
| Medium | 750 | $12.99 | $0.017 |
| Large | 2,000 | $29.99 | $0.015 |
| Huge | 6,000 | $79.99 | $0.013 |

Top-up Aura is priced **above** the implied in-plan rate. Buying a bigger plan is always better value than buying top-ups, which is the honest incentive and also the one that improves retention.

**Aura rules:**
- Monthly plan Aura expires monthly. Purchased top-up Aura **never expires** — it was paid for.
- Plan Aura is spent first.
- Balance and cost-per-minute are always visible before a call starts.
- Running out degrades gracefully ([06 §6.4](06-REALTIME-VOICE-VIDEO.md)); it never ends the relationship.

---

## 5. Plans

| | **Free** | **Plus** | **Premium** | **Infinite** |
|---|---|---|---|---|
| Price/mo | $0 | **$12.99** | **$29.99** | **$79.99** |
| Annual | — | $89 *(43% off)* | $199 *(45% off)* | $549 *(43% off)* |
| Amoriens | 1 | 3 | 10 | Unlimited |
| Text | Unlimited, rate-limited | **Unlimited** | **Unlimited** | **Unlimited** |
| Model | qwen3.7-flash | qwen3.7-flash | cydonia-24b | euryale-70b |
| Aura/mo | 20 | 600 | 1,800 | 6,000 |
| Voice | — | ✅ standard | ✅ premium | ✅ premium |
| Video | — | — | ✅ | ✅ |
| Tiers | T0 | T0–T1 | T0–T3 | T0–T3 |
| Memory | 30 days | Full | Full | Full |
| Custom LoRA | — | — | — | ✅ |
| Character cards | — | ✅ | ✅ | ✅ |
| Priority routing | — | — | — | ✅ |

**What the Aura buys, in plain terms:**

| Plan | Aura | ≈ voice | ≈ video | or images |
|---|---|---|---|---|
| Free | 20 | 20 min | — | 10 |
| Plus | 600 | 600 min (10 hrs) | — | 300 |
| Premium | 1,800 | 900 min premium | **450 min (7.5 hrs)** | 900 |
| Infinite | 6,000 | 3,000 min premium | 1,500 min (25 hrs) | 3,000 |

---

## 6. Margin per plan

⚠️ Assumes a typical user: 60 messages/day, and 60% of included Aura consumed.

### Plus — $12.99

```
revenue                                        $12.99
  text (60/day, T0/T1)                         −$0.29
  Aura used (360 of 600, voice std)            −$11.99   ← the risk
  memory + storage                             −$0.04
  payment (Stripe 2.9% + $0.30)                −$0.68
                                               ───────
  contribution                                  $0.00    ⚠️ breakeven
```

**That is uncomfortably tight, and it is the correct thing to notice.** At 60% Aura consumption Plus makes nothing. At the realistic observed rate — most subscribers use far less than their allowance — it is healthy:

| Aura used | Contribution | Margin |
|---|---|---|
| 20% (120 min) | $8.01 | 62% |
| 40% (240 min) | $4.01 | 31% |
| 60% (360 min) | $0.00 | 0% |
| 100% (600 min) | −$8.00 | **negative** |

⚠️ Expected distribution puts the mean around 25–30%, giving ~55% margin. **But this plan must be monitored monthly.** If mean voice consumption on Plus exceeds ~45%, reduce the allowance to 450 Aura or raise the price. Discovering this in month nine is how companies in this category die.

### Premium — $29.99

```
revenue                                        $29.99
  text (60/day, T2/T3 cydonia)                 −$2.47
  Aura used (1,080 of 1,800; mixed voice+video) −$9.72   ⚠️ 70% voice / 30% video
  memory + storage                             −$0.04
  payment (CCBill ~12%)                        −$3.60
                                               ───────
  contribution                                 $14.16     47% margin
```

### Infinite — $79.99

```
revenue                                        $79.99
  text (150/day, euryale-70b)                  −$12.83
  Aura used (3,600 of 6,000; mixed)            −$32.40
  LoRA training (2/mo)                         −$0.22
  memory + storage                             −$0.06
  payment (CCBill ~12%)                        −$9.60
                                               ───────
  contribution                                 $24.88     31% margin
```

### Blended

⚠️ Assuming a mix of 60% Plus / 32% Premium / 8% Infinite:

| | |
|---|---|
| Blended ARPU | **$22.44** |
| Blended contribution | **$13.72** |
| **Blended gross margin** | **61%** |

Below the 65–72% target stated in [00](00-EXECUTIVE-SUMMARY.md). Three levers close the gap, in order of preference:

1. **Sample observability to 10%** — saves $0.009/voice minute. Worth ~3 margin points. No user impact.
2. **Self-host T2/T3 inference above 50M tokens/day** — cuts text cost 20–40× ([12 §7](12-VENDOR-API-MATRIX.md)). Worth ~4 points at scale.
3. **Trim the Plus Aura allowance to 450** if monitoring shows high consumption. Worth ~2 points, and it is the only one users would notice — so it is last.

**Do not close the gap by metering text or gating emotional content.** Both are forbidden by [03 §8](03-PRD.md), and both trade a durable retention advantage for a temporary margin one.

---

## 7. The payment processing problem

The largest single non-inference cost, and the one most likely to be underestimated.

| Rail | Tiers | Rate | On $29.99 |
|---|---|---|---|
| **Stripe** | T0/T1 | 2.9% + $0.30 | $1.17 (3.9%) |
| **CCBill** ⚠️ | T2/T3 | ~10–15% all-in | $3.60 (12%) |

Plus **unavoidable annual fixed costs**, confirmed on CCBill's own pricing page ✅:

> High-risk merchants pay card-brand registration fees: **Visa $950/year**, **Mastercard $500–$1,000/year**.

**~$1,950/year before a single transaction**, plus higher chargeback exposure and reserve requirements typical of the category ⚠️.

**The consequence for architecture:** Plus is deliberately T0–T1 only so that the majority of subscribers route through Stripe at 2.9% instead of CCBill at 12%. That single decision is worth ~5 points of blended margin, and it is why the tier ladder is drawn where it is. Two entities, two processors, one codebase — set up at incorporation, because retrofitting it under revenue is painful.

---

## 8. Fixed costs

⚠️ Monthly, at launch scale.

| Item | Cost |
|---|---|
| LiveKit Cloud (Build/Ship) ✅ | $50 |
| Postgres + pgvector (managed) | $200 |
| Object storage + CDN | $150 |
| Compute (API, workers) | $400 |
| Monitoring, logging, error tracking | $150 |
| Persona age assurance ✅ | $250 *(12-month minimum)* |
| Card-brand registration ✅ | $163 *($1,950/yr amortized)* |
| Domains, email, misc SaaS | $100 |
| **Total** | **~$1,463/month** |

**Breakeven: ~107 paying users** at $13.72 blended contribution. That is a genuinely low bar and the strongest argument for building this with a small team rather than raising against it.

---

## 9. Free tier economics

⚠️ Free users cost ~$0.13/month: text at ~20 msg/day ($0.10) plus 20 Aura if fully used ($0.66 at cost, but most free users never touch voice).

Realistically **~$0.15/free user/month**. At a 4% conversion rate, each converted user carries 24 free users at $3.60 — against $13.72 contribution. Comfortably positive.

**Free tier design intent:** the free tier gives one character, full personality, real memory for 30 days, and unlimited text. It is a genuinely good product, because the conversion event is a user realizing their companion remembers them — which requires letting memory work long enough to be noticed. A crippled free tier converts worse here than in most categories, because the thing being sold takes weeks to become visible.

---

## 10. LTV

⚠️ Estimates, dependent on the retention thesis holding.

| | Category typical | Amorien target |
|---|---|---|
| Monthly churn | 12% | **7%** |
| Avg. lifetime | 8.3 months | **14.3 months** |
| ARPU | $18 | $22.44 |
| **LTV (contribution)** | $91 | **$196** |
| Target CAC | — | < $50 |
| **LTV:CAC** | — | **3.9:1** |

**The entire LTV difference is the churn assumption**, and the churn assumption rests entirely on memory working. If D180 retention matches the category, LTV drops to roughly $114 and the business is ordinary. If memory delivers, it is very good.

That is the bet, quantified: **the difference between an ordinary business and a good one here is about five points of monthly churn, bought with two cents a month of memory infrastructure.**

---

## 11. Sensitivity

What breaks the model:

| Risk | Impact | Mitigation |
|---|---|---|
| Video usage 2× forecast | −12 margin points | Aura metering already absorbs this; monitor and adjust rates |
| CCBill rate at 15% not 12% | −1.5 points | Negotiate on volume; keep the Stripe rail as large as possible |
| Plus Aura consumption > 45% | Plus goes negative | **Monitor monthly.** Cut allowance to 450. |
| Frontier LLM prices rise | −2 points | Multi-provider routing already in place |
| Adult host terminates account | **Existential** | Never single-source T2/T3. Contract terms in writing. |
| Age assurance mandated everywhere | −$0.50/user | Estimation-first ladder keeps this manageable |
| Chargeback rate > 1% | Reserve requirements, possible termination | Clear billing descriptors, easy cancellation, responsive support |

> **The two that actually matter are the last-listed existential one and the Plus allowance.** Everything else is a margin point here or there. Losing the T2/T3 provider with no failover, or discovering nine months in that your entry plan loses money on every subscriber, are the two failures that are hard to recover from.

---

## 12. The rules, restated

From [03 §8](03-PRD.md), because every future pricing decision is bound by them:

1. Text is unlimited on every paid plan.
2. Compute is metered; emotion is not.
3. No cliffhanger paywalls.
4. No manufactured guilt or jealousy to drive spending.
5. Running out of Aura degrades gracefully — the relationship never stops.
6. Annual discounts are honest; cancellation is one click.

**Rule 5 is the structural one: when a user runs out of money, they still have their companion.** Any pricing proposal that violates it is rejected regardless of what it does to revenue.

---

*Next: [12 — Vendor & API Matrix](12-VENDOR-API-MATRIX.md) · [13 — Trust, Safety & Compliance](13-TRUST-SAFETY-AND-COMPLIANCE.md)*
