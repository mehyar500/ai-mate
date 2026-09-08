# Scene-ready companion: commercial plan

Research checked September 7, 2026. The new objective is a useful product with roughly 60% direct contribution margin, enough cash to fulfill purchases, and controlled startup spending. A large markup on GPU seconds is not company profit.

## Product and pricing

Free, verified pilot accounts: 150 text replies/month, max five/day; optional recorded replies up to 15 seconds; five incoming voice-note minutes; one original adult portrait and editable memory. Cap 25 free accounts initially. Paid plans provide 500 text replies with recorded playback. Opt-in check-ins count within these reply limits.

| Monthly plan | Price | Visual minutes | Voice-only minutes | Photos | Portrait videos | Scene preparations |
|---|---:|---:|---:|---:|---:|---:|
| Together | $19.99 | 20 | 20 | 4 | 1 | 4 |
| Closer | $29.99 | 40 | 40 | 8 | 3 | 6 |
| Companion | $49.99 | 90 | 60 | 12 | 6 | 10 |

Videos are up to 15 seconds. Visual calls meter connected delivered time including listening. Suggested packs: $14.99/30 visual minutes; $24.99/60 visual minutes; $9.99/60 voice-only minutes; $9.99/10 portrait videos. Visual packs include two scene preparations.

Proactive media uses included allowances after explicit opt-in, never an automatic extra purchase. No surprise overages or hidden cash wallet. Failed delivery restores credits; successful but unusable vendor work still costs us. Personal scenes and memory are private; generic backgrounds may be reused, never another user's conversation or likeness.

## Character continuity and scene preparation

Maintain three separate records: confirmed user facts/events, the fictional character's current scene/story state, and the technical readiness of the requested call. The companion knows only what the user has chosen to share.

If the character's fictional setting is a bathroom, create or reuse that character-in-room reference before allowing a visual call. A realistic portrait renderer can then preserve the prepared view while speaking. It is not a model of physically showering or freely navigating the room. Keep the camera framing stable.

Conversation can continue during preparation. Suggested wording: 'Give me a moment; I'll let you know when our call is ready.' Pair it with a clear 'Preparing your scene' status and honest ETA. When validation and capacity checks pass, show 'Ready to call.' Do not invent a real-world excuse to conceal failure or imply a synthetic person has a physical life. Roleplay remains clearly labeled fiction.

## One inference platform

Put dialogue, TTS, ASR, image editing and portrait video on the same approved TensorDock US provider. Use separate processes/instances as needed: one warm auxiliary pool for messages and voice, one on-demand renderer/scene worker. Models cannot all be assumed to fit and perform concurrently on a single cheap GPU.

The budget now includes $432/month for warm auxiliary inference instead of hiding cold-start or always-on costs. Renderer budget is $0.90/hour, one concurrent call until measured, 50% occupied capacity. Including transport and contingency, reserve $0.04/visual minute. The earlier $0.025 target depended on two streams and remains an optimization, not a launch assumption. [TensorDock](https://www.tensordock.com/).

Cloudflare remains the PWA/data/WebRTC provider and CCBill the payment candidate. Runware custom compute is an alternative to evaluate, not another dependency. Hosting all inference in one place simplifies data routing; provider and individual model conditions still apply.

## Detailed startup money

For 100 paid and 25 free users at full allowance usage, [ECONOMICS](ECONOMICS.md) budgets:

- $250 private technical POC.
- $1,950 US high-risk card registration reference.
- $1,500 legal/state/provider review allowance.
- $500 narrow independent security-review allowance.
- $100 incremental development tools/API allowance and $20 domain.
- $432 warm auxiliary inference, $100 platform/monitoring/delivery and $5 free-account usage.
- $548.75 paid-service delivery and $12.50 internal verification processing.
- $500 working buffer.

**Total funding before relying on receipts: $5,918.25.** Plan around $6,000, with $7,500 if review/engineering overruns are likely. Review budgets are estimates, not quotes; hiring a developer is excluded. A private $250 POC can stop before the commercial costs are incurred.

Internal verification has zero third-party API fee in this scenario, but four review minutes at $30/hour add $250 of economic labor value for 125 accounts. A paid fallback raises cash costs if the internal design is not accepted.

## No-bleed decision

At 18% combined processing/losses plus $0.50/transaction, modeled plan contribution margins are 63.3–63.9%, before company overhead. Baseline first-month cash operating results, including startup expense: 100 payers lose ~$2,804; 250 earn ~$279 but remain ~$533 negative after the assumed payment hold; 300 earn ~$1,307 and retain ~$332 after that hold. Break-even is about 237 payers for expense and 281 for cash after hold at this mix.

A waitlist cannot guarantee these customers. Startup money must exist before settlement. If 'no loss in month one' is absolute, do not activate the full commercial service until a funded budget and a credible path to roughly 300 paying customers exist. Refundable commitments/preorders are only permissible after processor acceptance and clear fulfillment terms, and are liabilities rather than profit.

For 300 payers, funding the entire month's promised delivery without relying on receipts is about **$7,036**, including the same $500 buffer. Ongoing operations alone, after startup is already funded, reach the modeled expense/cash-after-hold thresholds around 30/35 payers. That does not erase the $4,320 startup expense or guarantee customers. A limited paid pilot can be operationally sustainable before it recovers its launch investment.

Stage spending: fund only the POC first; obtain provider/processor quotes before registration payments; test willingness to pay; activate a capped paid cohort after all release gates. Keep one month's fulfillment/refund runway. Stop new acquisition and optional proactive media when the runway limit is reached, while honoring existing paid entitlements or refunding them.

## How this could become a substantial business

At the assumed mix, revenue is $32.49/payer/month and direct contribution about $20.65. One thousand retained payers would produce roughly $32,490 revenue and $20,654 contribution before overhead, replacement acquisition, staffing, annual fees and taxes. Ten thousand would be a larger operating business, not the same $100-overhead pilot. Retention and distribution determine whether that scale is achievable.

A realistic target is 55–65% contribution margin and 15–30% mature operating margin after actual costs. These are management targets, not forecasts. Memory, thoughtful check-ins and consistent scenes may earn renewal; unlimited free text competitors and genuine human interaction remain alternatives. No evidence proves everyone will switch or that this treats loneliness clinically.

## Development with GPT-6 assistance

Planning estimate for an experienced founder/engineer actively reviewing AI-written code, not a claim about a model's guaranteed speed:

| Milestone | Engineering estimate | Evidence needed |
|---|---|---|
| One-character private scene/call demo | 3–5 working days | Real browser audio/video, identity and latency measurements |
| Integrated PWA alpha | 2–4 weeks cumulative | Auth, editable memory, job lifecycle, check-ins, billing sandbox |
| Limited paid pilot | 4–8 weeks cumulative | Device tests, security review, accepted age flow, provider/merchant release gates |

Processor/legal review timing is external and may extend the schedule. Off-the-shelf internal age estimation is not automatically compliant; a robust in-house identity system can add weeks. Estimate 80–160 hands-on engineering hours for the alpha and 160–320 for a narrow paid pilot, with overlap; these are uncertain, unpaid-founder assumptions. The $100 tooling allowance is not an asserted GPT-6 API price. Record actual spend and usage limits.

POC stop condition: if scene identity or warm response latency fails after the capped experiment, do not expand scope or incur registration merely to continue experimenting. Successful tests authorize a business decision, not automatic production release.
