# Adult-first companion: commercial plan

Research checked September 7, 2026. The new objective is a useful product with roughly 60% direct contribution margin, enough cash to fulfill purchases, and controlled startup spending. A large markup on GPU seconds is not company profit.

## Executive summary

**Self-hosting commercially licensed open weights is a plausible route, but it does not establish intended-content quality, nationwide legality or immunity from lawsuits.** Start with rented US GPUs under an accepted commercial contract. Apache-2.0 candidates exist without a blanket adult-content ban; model dependencies, hosting and payment terms still matter. See the licensing distinction in [USA](USA.md).

Budget **$12,096.50 before relying on payouts** for a build month and two conditional pilot months, including $1,500 working cash. Round to **$12,500 baseline**, or **$16,000 with more room for acquisition/review costs**, excluding paid engineering. These are allowances, not quotes. The illustrative 0/50/150 payer ramp loses **$5,368.14 over the quarter** after startup costs. If no build-month loss is acceptable, this launch cannot meet that constraint.

## Mandatory product decision

**Adult content is the primary product requirement, not a future add-on. No adult capability means no commercial launch.** Preserve non-explicit interactions as a user preference within the adult service, not a replacement business. All accounts must pass the accepted adult-access flow before using restricted content.

The intended offer includes lawful consensual adult text/voice, adult images and scenes, and adult-compatible clips/visual calls wherever those features are sold. Each advertised modality must be demonstrated; a clothed portrait demo does not prove explicit image or video capability. Do not market a talking portrait as arbitrary full-body action generation.

First spend goes to an **adult viability gate**, before a polished PWA, elaborate proactive features or merchant registration. Confirm intended-use eligibility, model/checkpoint rights, actual intended-content quality, consistency, latency and delivered cost. If no candidate passes, stop at the capped experiment and report the missing capability. Do not silently substitute a non-explicit product or route to an incompatible provider.

| Requirement | Evidence required before launch | Current status |
|---|---|---|
| ADULT-01: intended content works | Reviewed capability results for every advertised text/audio/image/video feature, including consistency and usability | Not demonstrated |
| ADULT-02: permitted commercial route | Exact checkpoint/dependency licenses plus host and processor acceptance for the complete adult service | Not established |
| ADULT-03: controlled adult access | Accepted age-assurance method, reviewed state availability, consent/privacy/reporting controls | Not implemented |
| ADULT-04: affordable fulfillment | Actual billed cost, retries/rejections and latency on the approved adult workload | Forecast only |

Founder owns the content/business specification and approvals; engineer owns capability and cost evidence. The founder must explicitly approve any later reduction in launch scope. No adult request is promised without limits: minors/age ambiguity, nonconsensual imagery, exploitation and real-person impersonation remain excluded.

September 7 research adds model-specific evidence and exclusions in [BUILD](BUILD.md#model-evidence-checked-september-7-2026) and [USA](USA.md#september-7-model-and-host-exclusions). No reviewed source demonstrates the whole required service. Recorded Wan video has a different cost/latency profile from a talking portrait. FlashHead Lite's bundled VAE terms require resolution. Prices remain hypotheses. The earlier approximately $6,000 estimate covered a narrower first-paid-month scenario with smaller review allowances and internal verification; the three-month budget below supersedes it.

## Product and pricing

All prices and allowances below are **conditional adult-product hypotheses**. Activate a tier only when every included adult modality passes the requirements above; revise its cost before sale if the validated model needs more compute or retries. A paid bundle must not contain an unvalidated video entitlement.

Free, verified pilot accounts: 150 text replies/month, max five/day; optional recorded replies up to 15 seconds; five incoming voice-note minutes; one original adult portrait and editable memory. Cap 25 free accounts initially. Paid plans provide 500 text replies with recorded playback. Opt-in check-ins count within these reply limits.

| Monthly plan | Price | Visual minutes | Voice-only minutes | Photos | Portrait videos | Scene preparations |
|---|---:|---:|---:|---:|---:|---:|
| Together | $19.99 | 20 | 20 | 4 | 1 | 4 |
| Closer | $29.99 | 40 | 40 | 8 | 3 | 6 |
| Companion | $49.99 | 90 | 60 | 12 | 6 | 10 |

Videos are up to 15 seconds. Visual calls meter connected delivered time including listening. Suggested packs: $14.99/30 visual minutes; $24.99/60 visual minutes; $9.99/60 voice-only minutes; $9.99/10 portrait videos. Visual packs include two scene preparations.

Those are portrait clips, not arbitrary full-body video. A separate general-video experiment has a proposed $1.25 accepted-delivery ceiling and $9.99 per-clip price, but its speed, quality and duration remain unproven. It contributes no revenue to this forecast. A 15-second output is not a promise of delivery within 15 seconds. Prices exclude separately collected applicable sales tax.

Proactive media uses included allowances after explicit opt-in, never an automatic extra purchase. No surprise overages or hidden cash wallet. Failed delivery restores credits; successful but unusable vendor work still costs us. Personal scenes and memory are private; generic backgrounds may be reused, never another user's conversation or likeness.

## Character continuity and scene preparation

Maintain three separate records: confirmed user facts/events, the fictional character's current scene/story state, and the technical readiness of the requested call. The companion knows only what the user has chosen to share.

If the character's fictional setting is a bathroom, create or reuse that character-in-room reference before allowing a visual call. A realistic portrait renderer can then preserve the prepared view while speaking. It is not a model of physically showering or freely navigating the room. Keep the camera framing stable.

Conversation can continue during preparation. Suggested wording: 'Give me a moment; I'll let you know when our call is ready.' Pair it with a clear 'Preparing your scene' status and honest ETA. When validation and capacity checks pass, show 'Ready to call.' Do not invent a real-world excuse to conceal failure or imply a synthetic person has a physical life. Roleplay remains clearly labeled fiction.

## One inference platform

Put dialogue, TTS, ASR, image editing and portrait video on the same approved TensorDock US provider. Use separate processes/instances as needed: one warm auxiliary pool for messages and voice, one on-demand renderer/scene worker. Models cannot all be assumed to fit and perform concurrently on a single cheap GPU.

The budget now includes $432/month for warm auxiliary inference instead of hiding cold-start or always-on costs. Renderer budget is $0.90/hour, one concurrent call until measured, 50% occupied capacity. Including transport and contingency, reserve $0.04/visual minute. The earlier $0.025 target depended on two streams and remains an optimization, not a launch assumption. [TensorDock](https://www.tensordock.com/).

Cloudflare remains the PWA/data/WebRTC candidate and CCBill the payment candidate. Eligible neutral tasks may use Workers AI; private companion history, intimate memories and adult jobs remain on the private accepted route. All product-specific provider terms still apply. A $20/month neutral-inference allowance is a budget, not a verified token tariff.

TensorDock advertises RTX4090 from $0.35/hour, A100 from $1.80/hour and H100 from $2.25/hour; our $0.60/$0.90 node budgets require current US offers and capacity tests. An 80GB recorded-video node uses a separate $2.50/hour planning allowance. Stopped/deallocated workers can avoid compute charges, but disks, backups and the control plane persist. Running idle VMs are billed. Instant response and zero idle compute cannot both be assumed.

Buying a workstation adds an illustrative $4,000–$8,000 capital allowance before redundancy, upkeep and business connectivity. This is not a hardware quote and does not provide the 80GB GPU used in Wan's official large-model example. At 300–600W average draw, 720 hours and $0.20/kWh, electricity alone is $43.20–$86.40/month. Renting avoids that initial purchase; ownership does not resolve content rights or liability.

## Startup and first three months

[ECONOMICS](ECONOMICS.md) provides the complete line-item budget and cash reconciliation. Startup is **$7,020**: $250 technical experiments, $1,950 card-registration reference, $3,000 narrow legal/state/contracts review, $1,500 narrow independent security/privacy review, $300 entity/admin setup and $20 domain. These are allowances, not completed reviews or quotes. Obtain host/model eligibility first and merchant terms before paying registration. [CCBill's current US/Canada card-fee reference](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs).

Monthly non-GPU overhead is $420: application/data $30, GPU disks/backups $50, neutral AI $20, email/monitoring $20, admin/insurance/accounting allowance $100, coding tools $100 and age-service minimum allowance $100. Age checks add $1.25 per new unique user, including a retry provision. These are not age-vendor tariffs or bound insurance quotes. Internal verification can save vendor fees only when its method is accepted; engineering and review remain costs.

| From project kickoff | M1 build | M2 pilot | M3 pilot |
|---|---:|---:|---:|
| Active paying users | 0 | 50 | 150 |
| Revenue | $0.00 | $1,624.50 | $4,873.50 |
| Total modeled expense | $7,548.25 | $1,548.04 | $2,769.86 |
| Profit / loss | -$7,548.25 | $76.46 | $2,103.64 |
| Cash payout received | $0.00 | $0.00 | $1,144.64 |

The ramp is a scenario, not a sales prediction. M3 retains 40 of the prior 50 payers and adds 110; acquisition and age checks count new customers instead of all renewals. Includes full allowance redemption, one warm pilot auxiliary GPU, processing/loss allowance of 18% + $0.50/payment, a 10% restricted reserve and a one-month payout delay. Processor terms may differ. M2 assumes approvals and development finish in time; delays can consume runway. Founder engineering is unpaid and sales tax is separately collected/remitted. Totals use unrounded calculations, so displayed rows can differ by a cent.

Quarter revenue is $6,498 and expense $11,866.14. We pay $10,596.50 outside amounts withheld by the processor and receive $1,144.64 cash during the quarter; $649.80 remains restricted and $3,433.92 is eligible but unsettled. Fund **$12,096.50 including the $1,500 buffer** to avoid relying on any quarter payout. The smaller $10,951.86 modeled month-end funding minimum depends on timely receipts and excludes intramonth timing risk. Neither reserves nor the working buffer are expenses.

With no paying customers but the same scheduled capacity, the quarter costs **$9,478.25**, requiring **$10,978.25 including the buffer**. Stop earlier if validation fails. At $20 acquisition cost per new payer, baseline funding rises to $15,296.50. Founder cash pay of $3,000/month adds $9,000. Higher legal/security quotes can add thousands; stress cases can combine. $16,000 is not a maximum-loss guarantee.

## Spending decision

Full-usage plan contribution is about 63% before overhead. At 100 active payers, modeled ongoing revenue is $3,249 and expense $2,040.57, leaving $1,208.43 before new-user acquisition/verification, startup recovery and taxes. This does not establish demand, peak capacity or first-month profit. The build month has no revenue and incurs a loss in this planning model.

Stage spending: fund only the evidence experiment first; obtain actual provider/processor and review quotes; test willingness to pay; activate a capped cohort only after all release gates and funding exist. Keep fulfillment/refund runway. Stop new acquisition and optional proactive media when the runway limit is reached, while honoring existing paid entitlements or refunding them. Refundable commitments or annual prepayments are liabilities, not spendable profit.

## How this could become a substantial business

At the assumed mix, revenue is $32.49/payer/month and direct contribution about $20.65. One thousand retained payers would produce roughly $32,490 revenue and $20,654 contribution before overhead, replacement acquisition, staffing, annual fees and taxes. Capacity and support must scale; the pilot's fixed budget cannot be held constant at that size. Retention and distribution determine whether that scale is achievable.

A realistic target is 55–65% contribution margin and 15–30% mature operating margin after actual costs. These are management targets, not forecasts. Memory, thoughtful check-ins and consistent scenes may earn renewal; unlimited free text competitors and genuine human interaction remain alternatives. No evidence proves everyone will switch or that this treats loneliness clinically.

General assistants compete on broad utility, established quality and free access. Human creator platforms offer an actual human relationship and performer agency that this service cannot replicate. Other AI companions can copy features or subsidize usage. The testable advantage is continuity, private memory and predictable spending; interview and retain paying customers before claiming superiority or scaling acquisition.

## Development with GPT-6 assistance

Planning estimate for an experienced founder/engineer actively reviewing AI-written code, not a claim about a model's guaranteed speed:

| Milestone | Engineering estimate | Evidence needed |
|---|---|---|
| Adult viability and one-character private demo | 3–5 working days for initial evidence, not assured success | Intended-content capability, license/host fit, identity and latency measurements |
| Integrated PWA alpha | 2–4 weeks cumulative | Auth, editable memory, job lifecycle, check-ins, billing sandbox |
| Limited paid pilot | 4–8 weeks cumulative | Device tests, security review, accepted age flow, provider/merchant release gates |

Processor/legal review timing is external and may extend the schedule. Off-the-shelf internal age estimation is not automatically compliant; a robust in-house identity system can add weeks. Estimate 80–160 hands-on engineering hours for the alpha and 160–320 for a narrow paid pilot, with overlap; these are uncertain, unpaid-founder assumptions. At an illustrative outsourced rate of $75/hour, pilot engineering adds $12,000–$24,000. Neither time nor rate is a quote. The $100/month tools allowance is not an asserted GPT-6 API price. Record actual spend and usage limits.

POC stop condition: if required adult capability, commercial rights, host eligibility, scene identity or warm response latency remains unresolved after the capped experiment, stop and reassess before further spending. Do not incur registration merely to continue experimenting. Successful tests inform a business decision, not automatic production release.

## Revision evidence

Scope: five product documents, planned environment placeholders, economics configuration/calculator and its tests; source commit `2b22f18`. The offline calculator change is R1 and does not execute billing, inference or legal agreements. ADULT-01/02 remain research questions; ADULT-03 is a specification; ADULT-04 now includes reproducible three-month expense, settlement, reserve and downside calculations. All runtime release requirements remain open with the owners above.

Validation: 24 unit checks pass, including cash reconciliation across settlement delays, one-time startup, new-user verification/CAC, no-sales costs and invalid inputs. Python syntax and `git diff --check` pass; generated economics match config and local document links resolve. No CI workflow, staging, independent runtime review or live integration test exists. No production migration or telemetry changed; planned environment names are not consumed by an app. Documentation rollback is a reviewed revert of this revision; no credentials or account configuration were published.
