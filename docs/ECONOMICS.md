# Scene-ready PWA economics

USD, checked 2026-09-07. Generated from [config](../config/economics.json). No benchmark, binding provider quote or customer forecast. Full allowance redemption; before income tax.

## Unit delivery and payment assumptions

Renderer node $0.90/hour, 1 concurrent stream, 50% occupancy. Renderer allocation $0.030/connected minute; transport, contingency and floor produce $0.040/visual minute. A separate warm auxiliary GPU pool costs $432/month and is counted below. One provider does not mean one GPU holds every model.
Voice-only $0.02/minute; accepted portrait video $0.15; photo $0.05; prepared scene $0.10. Paid text/recorded voice/check-ins/memory $0.50/month plus $0.75 support allowance. These are budgets requiring measured acceptance/retry costs.
Processor 16% + refunds/losses 2% + $0.50/transaction; hold 10% of gross receipts. All are planning assumptions, not CCBill quotes.

## Monthly plans: full usage

| Plan | Price | Visual / voice min | Photos / videos / scenes | Direct cost | Contribution | Margin |
|---|---:|---:|---:|---:|---:|---:|
| Together | $19.99 | 20 / 20 | 4 / 1 / 4 | $7.30 | $12.69 | 63.5% |
| Closer | $29.99 | 40 / 40 | 8 / 3 / 6 | $11.00 | $18.99 | 63.3% |
| Companion | $49.99 | 90 / 60 | 12 / 6 / 10 | $18.05 | $31.94 | 63.9% |

Optional proactive photos/videos consume these included allowances only after opt-in; no extra surprise charge. Failed preparation restores the user's credit but may still cost us. Do not use unused credits as the profitability assumption.

| Optional pack | Price | Direct cost | Margin |
|---|---:|---:|---:|
| Visual call 30 | $14.99 | $4.70 | 68.7% |
| Visual call 60 | $24.99 | $7.70 | 69.2% |
| Voice call 60 | $9.99 | $3.60 | 64.0% |
| Portrait videos 10 | $9.99 | $3.90 | 61.0% |

## First-month funding at configured cohort

| Item | Budget | Basis |
|---|---:|---|
| Technical POC | $250 | Fixed experiment cap |
| Card registration | $1950 | CCBill US/Canada reference, subject to approval/quote |
| Legal/state/provider review | $1500 | Planning allowance, not a quote or completed national review |
| Independent security review | $500 | Narrow pilot scope allowance, not a full audit quote |
| Development tools/API allowance | $100 | Not a published GPT-6 price; excludes existing subscriptions |
| Domain | $20 | Budget |
| Warm auxiliary inference | $432 | 720 hours x $0.60 |
| Platform, storage, monitoring, transactional delivery | $100 | Monthly allowance |
| Free-account delivery | $5.00 | 25 accounts |
| Paid delivery, excluding withheld payment fees | $548.75 | Full included usage, 100 payers |
| Uncovered renderer availability | $0.00 | Minimum 120 hours; no double counting allocated GPU |
| Internal age-check processing | $12.50 | $0.10/new free/paid user, no vendor fee |
| Working buffer | $500 | Liquidity, not an expense |
| **Cash funding before receipts** | **$5918.25** | Assumes no customer receipts fund promised month-one delivery |

Internal review is not free economically: 4 minutes/account at $30/hour values age-review time at $250.00 for this cohort. Founder cash pay defaults to $0; engineering labor remains excluded. Development or legal overruns require more capital, not relaxed release gates.

## Profit versus available cash

| Payers | Revenue | All first-month modeled expense | Profit/loss | Cash after assumed hold |
|---|---:|---:|---:|---:|
| 20 | $649.80 | $5177.71 | $-4527.91 | $-4592.89 |
| 100 | $3249.00 | $6053.07 | $-2804.07 | $-3128.97 |
| 250 | $8122.50 | $7843.43 | $279.08 | $-533.17 |
| 300 | $9747.00 | $8440.21 | $1306.79 | $332.09 |
| 500 | $16245.00 | $10827.35 | $5417.65 | $3793.15 |

At the assumed plan mix, first-month expense break-even is about 237 payers; cash break-even after the modeled hold is about 281. Fractions in plan mix are expectations; actual sales mix changes these thresholds. A waitlist is not collected revenue. No sales, settlement date or profit is guaranteed.

## Stress cases at configured cohort

| Change | Funding before receipts | First-month profit |
|---|---:|---:|
| Quote-dependent $600 registration | $4568.25 | $-1454.07 |
| No internal API fee but $1 vendor fallback | $6030.75 | $-2916.57 |
| 25% renderer occupancy | $6074.81 | $-2960.63 |
| CAC $5 | $6418.25 | $-3304.07 |
| Legal budget $3,000 | $7418.25 | $-4304.07 |
| Founder pay $3,000 | $8918.25 | $-5804.07 |

The $600 registration scenario is an illustrative USD allowance for a lower-fee approved quote, not a verified EUR conversion or proof that Verotel Basic supports this visual-call business. Its public chart lists EUR 500 annual registration but excludes webcam billing on Basic and has additional recurring fees; confirm full scope.

Recommended target: roughly 60% direct contribution margin, then positive cash after overhead. A 300-500% return is no longer a requirement. At scale, retention, service quality and acquisition costs determine profit. Keep at least one month of fulfillment/refund runway; do not take restricted reserves or unearned annual subscriptions as spendable profit.

Sources: [CCBill fees](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs), [CCBill pricing](https://ccbill.com/pricing), [Verotel chart](https://www.verotel.com/en/pricechart.html), [TensorDock](https://www.tensordock.com/). Processor approval, appropriate internal age assurance and model/content suitability are not established.
