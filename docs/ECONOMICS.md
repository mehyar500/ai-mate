# Prices, costs and savings

USD, 2026-09-07. Generated from [config](../config/economics.json); assumptions, not measured earnings.

Free: portrait, 900 clean exchanges/month, daily ceiling 30, prerecorded voice sample. Paid: 2000 exchanges/month plus calls below. Adult service only in approved states and advertised hours.

| Plan | Monthly price | Minutes | Full-use contribution | Margin before fixed costs |
|---|---:|---:|---:|---:|
| Close | $99.00 | 30 | $52.74 | 53.3% |
| Together | $179.00 | 60 | $94.27 | 52.7% |

Top-up $89.00/30 minutes. Clip pack $9.99/5 delivered videos. Minutes include listening. No rollover/automatic overage; disclose expiry, pause pilot deductions on degradation, restore failed clips.

## Our call cost

| Route | Cost/min | 30 min | 60 min |
|---|---:|---:|---:|
| GPU rendering + transport only (no conversation) | $0.7731 | $23.19 | $46.38 |
| Cloudflare conversation only (no video) | $0.0314 | $0.94 | $1.89 |
| Cloudflare conversation + 8-GPU video baseline | $0.8023 | $24.07 | $48.14 |

Assumed ($18.00 GPU + $0.50 VM extras)/hour; 50% utilization; 1 call per allocated GPU group. Add $0.000798/minute media, $0.001 other cost, 25% contingency. Video GPU price is the TOTAL allocated group, not one card. Baseline pays for eight H100s even if five execute the model. No spare-card concurrency saving is assumed.
Hosted context: 12,288 input tokens/minute; thirty minutes 368,640 input + 3,000 output; sixty 737,280 + 6,000. Repeated history counts. Speech: 450 characters/minute. [AI prices](https://developers.cloudflare.com/workers-ai/platform/pricing/), [SFU prices](https://developers.cloudflare.com/realtime/sfu/pricing/).

| Utilization | Complete clean call cost/min | 60 min |
|---|---:|---:|
| 10% | $3.8856 | $233.14 |
| 20% | $1.9585 | $117.51 |
| 50% | $0.8023 | $48.14 |

Always-warm VM at assumed rates: $13320.00/30 days; do not count again alongside idle allocation. Free text $0.70/user/month; paid text $3.12. Separate adult-text worker must cover loading/idle/safety within $0.0015/exchange. Scheduled service, not unbudgeted 24/7 capacity.

## Earnings are conditional

Fee assumptions: 15% + $0.50/payment, 3% refund/dispute loss, 10% withheld reserve; support $0.75/payer; fixed $250.00/month; verification $1.00/new free or paid account. Reserve affects cash, not profit.
Configured 100-payer/500-free cohort: revenue $13900.00; surplus $6751.79; cash after reserve and $600.00 age checks: $4761.79. Excludes salary, acquisition, legal and tax.
[CCBill](https://ccbill.com/pricing) fees need a quote; applicable $1,450–$1,950 annual card registration is amortized in fixed costs but payable upfront. Actual verification pricing also needs a quote.
Clip assumption: 120 allocated GPU seconds/attempt, 80% success, $0.35 other cost plus contingency: $0.50/delivered clip. Include load/idle/retries. Separate clip worker costs $1.20/hour; it does not use the live cluster. Speed and realism are unproved.

## Chaturbate in dollars

Wire buyer $0.08/token with **$250 funding minimum**; performer $0.05/token. Card prices not verified. [Buyer](https://support.chaturbate.com/hc/en-us/articles/360036511091-How-do-I-buy-tokens), [performer](https://support.chaturbate.com/hc/en-us/articles/360037125852-How-do-I-convert-my-tokens).

| Tokens/min | Buyer $/min | Performer $/min | Buyer 30 / 60 min | Performer 30 / 60 min |
|---|---:|---:|---:|---:|
| 6 | $0.48 | $0.30 | $14.40 / $28.80 | $9.00 / $18.00 |
| 18 | $1.44 | $0.90 | $43.20 / $86.40 | $27.00 / $54.00 |
| 30 | $2.40 | $1.50 | $72.00 / $144.00 | $45.00 / $90.00 |
| 60 | $4.80 | $3.00 | $144.00 / $288.00 | $90.00 / $180.00 |
| 90 | $7.20 | $4.50 | $216.00 / $432.00 | $135.00 / $270.00 |

Rate examples, not averages; the wire minimum still applies. Tips/taxes/minimum durations change spending. Gross spread is not platform profit. [Show rules](https://support.chaturbate.com/hc/en-us/articles/360048401752-Show-Types), [listed categories](https://chaturbate.com/support/).

| Our full-use offer | Buyer $/min | Cheaper than 6 tokens/min | Cheaper than 30 tokens/min |
|---|---:|---:|---:|
| Close | $3.300 | -587.5% | -37.5% |
| Together | $2.983 | -521.5% | -24.3% |
| Top-up | $2.967 | -518.1% | -23.6% |

Savings assume all minutes used and the wire valuation. Low use can make subscriptions more expensive; public streams may be free. ChatGPT prices and product differences: [REPORT](REPORT.md).
Prices above are a premium feasibility scenario, not approved offers. Require measured call cost and at least 50% recurring contribution after actual fees. Cinematic clips target p95 <=120s and cost <=$0.50, both unproved. See BUILD for quality and streaming gates.

## Video alternatives: same conversation stack

All costs below include hosted conversation, transport, idle allocation and contingency. Hardware prices are assumptions except advertised starting prices; H100 performance must be reproduced rather than inferred from H800 results.

| Renderer hardware scenario | Cost/min | 30 min | 60 min |
|---|---:|---:|---:|
| FlashHead Lite: 1 RTX 4090, quality challenger | $0.0544 | $1.63 | $3.26 |
| FlashHead Pro: 2 RTX 5090, quote assumption | $0.1689 | $5.07 | $10.14 |
| Quark LiveAvatar: 5 H100 billed, availability unverified | $0.5210 | $15.63 | $31.26 |
| Quark LiveAvatar: 8 H100 billed, conservative baseline | $0.8023 | $24.07 | $48.14 |

Conditional adult route replaces hosted conversation with a separate $1.20/hour speech/language/safety worker: $0.8231/min, $24.69/30 min, $49.38/60 min. One simultaneous call, same utilization; throughput and provider eligibility unproved. The cheaper of these routes must not subsidize an unmeasured expensive route.

50% contribution price floor = (call cost + monthly text/support + fixed payment fee) / (1 - processing fraction - refund fraction - 0.50). Acquisition, salaries, legal work and taxes still reduce profit.
