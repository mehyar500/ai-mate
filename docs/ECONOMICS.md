# Prices, costs and savings

USD, 2026-09-07. Generated from [config](../config/economics.json); assumptions, not measured earnings.

Free: portrait, 900 clean exchanges/month, daily ceiling 30, prerecorded voice sample. Paid: 2000 exchanges/month plus calls below. Adult service only in approved states and advertised hours.

| Plan | Monthly price | Minutes | Full-use contribution | Margin before fixed costs |
|---|---:|---:|---:|---:|
| Close | $24.99 | 60 | $13.02 | 52.1% |
| Together | $49.99 | 180 | $27.30 | 54.6% |

Top-up $12.99/60 minutes. Clip pack $9.99/5 delivered videos. Minutes include listening. No rollover/automatic overage; disclose expiry, pause pilot deductions on degradation, restore failed clips.

## Our call cost

| Route | Cost/min | 30 min | 60 min |
|---|---:|---:|---:|
| Local GPU | $0.0518 | $1.55 | $3.11 |
| Cloudflare voice/portrait | $0.0310 | $0.93 | $1.86 |
| Cloudflare voice/GPU face | $0.0810 | $2.43 | $4.86 |

Assumed ($1.00 GPU + $0.20 VM extras)/hour; 50% utilization; 1 call/GPU. Add $0.000423/minute media, $0.001 other cost, 25% contingency. Local tokens have no separate API bill.
Hosted context: 12,288 input tokens/minute; thirty minutes 368,640 input + 3,000 output; sixty 737,280 + 6,000. Repeated history counts. Speech: 450 characters/minute. [AI prices](https://developers.cloudflare.com/workers-ai/platform/pricing/), [SFU prices](https://developers.cloudflare.com/realtime/sfu/pricing/).

| Utilization | Local cost/min | 60 min |
|---|---:|---:|
| 10% | $0.2518 | $15.11 |
| 20% | $0.1268 | $7.61 |
| 50% | $0.0518 | $3.11 |

Always-warm VM at assumed rates: $864.00/30 days; do not count again alongside idle allocation. Free text $0.70/user/month; paid text $3.12. Separate adult-text worker must cover loading/idle/safety within $0.0015/exchange. Scheduled service, not unbudgeted 24/7 capacity.

## Earnings are conditional

Fee assumptions: 15% + $0.50/payment, 3% refund/dispute loss, 10% withheld reserve; support $0.75/payer; fixed $250.00/month; verification $1.00/new free or paid account. Reserve affects cash, not profit.
Configured 100-payer/500-free cohort: revenue $3749.00; surplus $1416.85; cash after reserve and $600.00 age checks: $441.95. Excludes salary, acquisition, legal and tax.
[CCBill](https://ccbill.com/pricing) fees need a quote; applicable $1,450–$1,950 annual card registration is amortized in fixed costs but payable upfront. Actual verification pricing also needs a quote.
Clip assumption: 120 allocated GPU seconds/attempt, 80% success, $0.35 other cost plus contingency: $0.50/delivered clip. Include load/idle/retries. Speed and realism are unproved.

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
| Close | $0.416 | 13.2% | 82.6% |
| Together | $0.278 | 42.1% | 88.4% |
| Top-up | $0.216 | 54.9% | 91.0% |

Savings assume all minutes used and the wire valuation. Low use can make subscriptions more expensive; public streams may be free. ChatGPT prices and product differences: [REPORT](REPORT.md).
Launch price gate: measured live cost ≤$0.055/minute and ≥50% recurring contribution after actual fees. Quick talking clips need measured p95≤15s; cinematic clips p95≤120s and cost≤$0.50. No guarantee of arbitrary live actions or unrestricted content.
