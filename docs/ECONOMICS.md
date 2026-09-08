# Adult PWA economics

USD, 2026-09-07. Generated from [config](../config/economics.json). Every cost is an assumption unless a source is expressly identified. Full allowance redemption. No adult-host approval or inference benchmark completed.

## Unit budget

Renderer: $0.90/hour / (2 streams x 50% occupied capacity x 60) = $0.0150/connected minute. Add $0.005 auxiliary and $0.0008 transport, apply 20% contingency and floor at $0.025: $0.0250/live minute.
Phone $0.015/minute; accepted 15-second portrait clip $0.10; paid text/recorded voice/memory $0.40/month; support $0.25. Free accounts $0.15/month, capped at 100. These self-hosted budgets do not use fal adult generation or hosted Cloudflare adult inference.
Payment scenario: 12% processing + 2% refunds/losses + $0.50/transaction. Obtain quotes. 300% return on cost = 75% margin; 500% = 83.33%.

## Monthly plans

| Plan | Price | Visual min | Phone min | Clips | Total direct cost | Contribution | Return on cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Together | $19.99 | 20 | 10 | 2 | $4.80 | $15.19 | 316.6% |
| Closer | $29.99 | 45 | 20 | 5 | $7.27 | $22.72 | 312.3% |
| Companion | $39.99 | 75 | 30 | 8 | $9.87 | $30.12 | 305.0% |

| Prepaid pack | Price | Direct cost | Return on cost |
|---|---:|---:|---:|
| Visual call 30 | $14.99 | $3.45 | 334.7% |
| Visual call 60 | $24.99 | $5.60 | 346.4% |
| Voice call 60 | $14.99 | $3.60 | 316.6% |
| Video messages 10 | $14.99 | $3.70 | 305.3% |

These are contribution returns before company overhead and first-user verification. Packs include $0.10 handling; do not sell them to unverified accounts. Service credits are not cash wallets. No automatic overages or reliance on unused credits.

## Company cash scenarios

Recurring fixed $100; renderer availability floor 120 hours x $0.90, adding only the portion not already allocated to calls. Startup: $500 technical budget + $1950 card registration + $0 unquoted legal expense. Legal zero means excluded/unquoted, NOT unnecessary. Founder labor $0, CAC $0, verification $1.00/new free and paid account.

| Payers | Revenue | First-month cost | First-month profit | Return | Later-month profit* |
|---|---:|---:|---:|---:|---:|
| 20 | $599.80 | $2925.22 | $-2325.42 | -79.5% | $244.58 |
| 100 | $2999.00 | $3534.11 | $-535.11 | -15.1% | $2114.89 |
| 500 | $14995.00 | $6817.42 | $8177.58 | 120.0% | $11227.58 |
| 1000 | $29990.00 | $10969.85 | $19020.15 | 173.4% | $22570.15 |

*Later month assumes the same retained users, no new acquisition/verification/setup, and excludes an annual registration accrual. Capacity is expandable: higher cohorts require more renderer hours/groups; the model allocates them through each live minute. It does not claim one GPU serves the whole cohort.

## Stress at configured payer count

| Change | Live cost/min | First-month profit | Middle-plan direct return |
|---|---:|---:|---:|
| 18% combined fees | $0.0250 | $-655.07 | 253.9% |
| One stream, 25% occupancy | $0.0790 | $-746.05 | 209.1% |
| One stream, 10% occupancy | $0.1870 | $-1245.55 | 105.9% |
| CAC $5 | $0.0250 | $-1035.11 | 312.3% |
| Legal $3,000 | $0.0250 | $-3535.11 | 312.3% |
| Founder labor $3,000 | $0.0250 | $-3535.11 | 312.3% |

Configured first-month cash after a 10% payment hold: $-835.01. Holds are cash restrictions, not expenses. Provider balances and unsettled receipts need working capital.

Price floor = (delivery + fixed transaction fee + allocated overhead) / (1/(1+target return) - percentage fees/losses). At 18%, a 500% total-cost return is impossible even with free inference. At 14%, it leaves just 2.67% of sales for all other costs; none of these offers achieves 500%. Do not relabel markup on GPU cost as company profit.

If combined fees/losses are 18%, price the same visual packs at $19.99/30 minutes and $34.99/60 minutes to retain over 300% direct return at the base delivery budget. Equivalent subscription prices are $29.99/$44.99/$64.99. These still exclude verification/acquisition and company overhead; remeasure before offering.

At the default mix, a $1 verification charge for every new payer makes 300% first-month company return unattainable even as cohort size grows under these prices. Existing-account recurring economics can improve, but must include annual registration accrual and actual retention. This forecast does not claim 300% company profit.

Technical POC budget $100-$250 can test rendering privately before merchant activation; it cannot fund a legal adult launch. CCBill currently lists Visa $950 plus Mastercard $1,000 annually for US/Canada high-risk accounts. Verify applicability and quote.

Sources: [TensorDock starting prices](https://www.tensordock.com/), [FlashHead benchmark](https://github.com/Soul-AILab/SoulX-FlashHead), [Cloudflare transport](https://developers.cloudflare.com/realtime/sfu/pricing/), [CCBill registration](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs). $0.90 complete renderer node/hour is a budget, not TensorDock's advertised GPU-only floor or a reserved US quote.
