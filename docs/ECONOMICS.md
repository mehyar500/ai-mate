# Adult-first PWA economics

USD; checked 2026-09-07. Generated from [config](../config/economics.json). Adult content is mandatory for launch; all prices depend on validated adult capability, approved providers and measured fulfillment cost. This is a cash-planning model with startup costs expensed at kickoff, not financial statements, a benchmark, a binding quote or a customer forecast. All included allowances are fully redeemed. Sales tax is assumed collected separately and remitted; income taxes and paid engineering are excluded.

## Decision

Budget **$12,096.50 before relying on any customer payout** for the illustrated three-month pilot, including a $1,500 unspent liquidity buffer. Under the modeled settlement timing the month-end minimum is $10,951.86; that smaller number depends on receipts arriving as assumed and does not model intramonth payment dates. Round the stronger budget up, obtain quotes, and do not spend if launch eligibility fails.

## Unit economics and monthly offer

Fully configured GPU allowances: auxiliary $0.60/hour, renderer $0.90/hour. These exceed advertised GPU-only starting rates and are not verified US offers. One stream and 50% occupied renderer capacity give $0.030/connected minute. Transport, contingency and a floor produce **$0.040/visual minute**. Warm auxiliary capacity is a separate fixed cost; incremental media/message allowances cover burst capacity and processing. Do not charge the same GPU hours twice when replacing estimates with bills.
Voice-only $0.02/minute; accepted portrait clip $0.15; photo $0.05; scene $0.10. These are cost ceilings to validate including loading, retries, rejected outputs and checks. They do not price unrestricted general video. Each paid account includes $0.50 incremental text/voice-note processing and $0.75 support allowance; human support exceeding this raises cost.
Payments: 16% processing + 2% refunds/chargeback-loss allowance + $0.50 per monthly payment, with a 10% rolling reserve. These are assumptions, not a CCBill quote. Refunds/loss allowance is conservatively modeled as withheld cash. Actual fees, chargebacks, minimums and reserves may differ.

| Plan | Price | Visual / voice minutes | Photos / portrait clips / scenes | Direct cost | Contribution | Margin |
|---|---:|---:|---:|---:|---:|---:|
| Together | $19.99 | 20 / 20 | 4 / 1 / 4 | $7.30 | $12.69 | 63.5% |
| Closer | $29.99 | 40 / 40 | 8 / 3 / 6 | $11.00 | $18.99 | 63.3% |
| Companion | $49.99 | 90 / 60 | 12 / 6 / 10 | $18.05 | $31.94 | 63.9% |

Direct contribution is before warm capacity, overhead, verification, acquisition and startup. It is not net profit. Feature entitlements cannot be sold before their adult-use license, capability and cost gates pass. Free access is capped at 25 verified pilot accounts; no unlimited free generation.

| Optional pack | Price | Direct cost | Margin |
|---|---:|---:|---:|
| Visual call 30 | $14.99 | $4.70 | 68.7% |
| Visual call 60 | $24.99 | $7.70 | 69.2% |
| Voice call 60 | $9.99 | $3.60 | 64.0% |
| Portrait videos 10 | $9.99 | $3.90 | 61.0% |

Separate general-video experiment: an 80GB node allowance of $2.50/hour costs $0.42 for two five-minute attempts. Adding $0.25 for other fulfillment yields $0.67; two 20-minute attempts instead yield $1.92. These times are illustrative, not Wan benchmarks, and producing a coherent 15-second result may require extensions. Proposed ceiling $1.25/accepted clip, proposed price $9.99, direct cost including assumed payment deductions $3.55, contribution $6.44 (64.5%). A 60% contribution target requires price at least (delivery + $0.50) / (1 - 0.18 - 0.60), or $7.95 at the ceiling. No general-video revenue, cost or entitlement is included in the forecast. Activate only after measured cost and delivery time support a separately priced offer.

## Startup purchases and review allowances

| Item | Budget | Basis |
|---|---:|---|
| Technical POC | $250.00 | Capped GPU experiments; no purchase made |
| Card registration | $1,950.00 | CCBill US/Canada Visa $950 + Mastercard $1,000 annual reference; obtain initial merchant quote |
| Legal, contracts and state review | $3,000.00 | Narrow launch allowance; not a 50-state clearance or quote |
| Independent security/privacy review | $1,500.00 | Narrow pilot review allowance, not a comprehensive audit |
| Entity/administrative setup | $300.00 | Jurisdiction-dependent allowance; avoid duplicate cost if already formed |
| Domain | $20.00 | Allowance |
| **Startup total** | **$7,020.00** | Charged once in M1 for conservative budgeting |

Technical validation and host eligibility precede larger commitments. Registration is not paid merely to keep experimenting. Annual card fees recur outside this quarter; save $162.50/month thereafter if the $1,950 annual figure applies. Legal/security overruns are possible and not covered by an unlimited guarantee.

## Fixed monthly allowances

| Item | Per month |
|---|---:|
| Cloudflare application, data and base media | $30.00 |
| GPU disks and backups | $50.00 |
| Neutral Workers AI allowance | $20.00 |
| Email and monitoring | $20.00 |
| Accounting, insurance and administration allowance | $100.00 |
| Coding tools and development API allowance | $100.00 |
| Age-assurance vendor minimum allowance | $100.00 |
| **Total excluding GPUs** | **$420.00** |

The $100 age-service minimum and $1.25/new unique user are procurement allowances, not Yoti prices: $1/check plus 25% retry provision. An accepted internal method could reduce vendor spend, but has development, privacy and review costs. No provider quote or insurance coverage is bound. Cloudflare's $20 neutral inference allowance is not a quoted token tariff; adult conversations stay on the approved private route. Warm dialogue/audio GPU adds $432 per 30-day pilot month. GPU disk costs persist when compute is stopped; a running idle VM is billable.

## Three months from kickoff

Scenario: M1 builds with no paying customers and 120 auxiliary GPU hours; M2 has 50 payers; M3 has 150. M3 keeps 40 of M2's 50 and adds 110, illustrating 20% monthly churn. New paid users are separate from the initial 25 free users; no free-to-paid conversion or repeated renewal verification is assumed. Plan mix: 25% Together, 50% Closer, 25% Companion. Counts/mix are planning expectations, not demand evidence. M2/M3 only happen if development and all release gates pass; timing may slip.
Settlement assumption: eligible proceeds arrive 1 model month(s) later; reserve release is outside this quarter. Month 3 receivables and restricted reserves are not available cash.

| Item | M1 build | M2 pilot | M3 pilot | Three months |
|---|---:|---:|---:|---:|
| Active payers | 0 | 50 | 150 | — |
| New unique age checks | 25 | 50 | 110 | 185 |
| Gross revenue | $0.00 | $1,624.50 | $4,873.50 | $6,498.00 |
| One-time startup | $7,020.00 | $0.00 | $0.00 | $7,020.00 |
| Fixed non-GPU overhead | $420.00 | $420.00 | $420.00 | $1,260.00 |
| Auxiliary GPU | $72.00 | $432.00 | $432.00 | $936.00 |
| Paid service delivery | $0.00 | $274.38 | $823.13 | $1,097.50 |
| Uncovered renderer availability | $0.00 | $36.75 | $0.00 | $36.75 |
| Free service delivery | $5.00 | $5.00 | $5.00 | $15.00 |
| Age checks | $31.25 | $62.50 | $137.50 | $231.25 |
| Customer acquisition | $0.00 | $0.00 | $0.00 | $0.00 |
| Founder cash pay | $0.00 | $0.00 | $0.00 | $0.00 |
| Processing/refund/loss allowance | $0.00 | $317.41 | $952.23 | $1,269.64 |
| Total modeled expense | $7,548.25 | $1,548.04 | $2,769.86 | $11,866.14 |
| Profit / loss | $-7,548.25 | $76.46 | $2,103.64 | $-5,368.14 |
| New restricted reserve | $0.00 | $162.45 | $487.35 | $649.80 |
| Cash payouts received | $0.00 | $0.00 | $1,144.64 | $1,144.64 |
| Cash paid out, excluding withheld fees | $7,548.25 | $1,230.62 | $1,817.63 | $10,596.50 |
| Net cash change | $-7,548.25 | $-1,230.62 | $-672.99 | $-9,451.86 |

Quarter reconciliation: profit $-5,368.14 minus restricted reserves $649.80 minus unsettled eligible proceeds $3,433.92 = cash change $-9,451.86. The $1,500 buffer is capital kept available, not an expense or reserve fee.
The quarter has 185 new age checks. Four minutes of founder review per account at $30/hour adds $370.00 of unpaid economic labor value, excluded from cash expenses. Baseline acquisition cost is zero only as an organic-founder-distribution assumption; it is not evidence users arrive free.

## Funding and downside cases

| Scenario | Three-month expense | Profit / loss | Funding with no payouts + buffer |
|---|---:|---:|---:|
| Baseline | $11,866.14 | $-5,368.14 | $12,096.50 |
| No paying users; retain scheduled pilot capacity | $9,478.25 | $-9,478.25 | $10,978.25 |
| CAC $20 per new payer | $15,066.14 | $-8,568.14 | $15,296.50 |
| Visual delivery $0.08/min; photos/scenes/clips double | $12,553.64 | $-6,055.64 | $12,784.00 |
| Two auxiliary GPUs throughout | $12,802.14 | $-6,304.14 | $13,032.50 |
| Founder cash pay $3,000/month | $20,866.14 | $-14,368.14 | $21,096.50 |
| Legal/security quotes total $9,000 | $16,366.14 | $-9,868.14 | $16,596.50 |

Stress cases change one factor at a time and can combine. No-sales operation is a downside budget, not a reason to keep spending after failure. At 160 new paid users, $20 CAC adds $3,200. Founder pay and hired engineering are separate: illustrative 160–320 hours at $75/hour adds $12,000–$24,000 if outsourced. Neither the hourly rate nor effort is a quote. Unlimited investigations, legal defense, hardware purchase and a full national launch are outside this pilot budget.

## Operating break-even and release decision

Weighted revenue is $32.49/payer and direct contribution $20.65 before fixed costs. At the configured 100 active-payer snapshot, ongoing expense is $2,040.57, revenue $3,249.00, and operating contribution after modeled overhead $1,208.43; this snapshot excludes new-user verification, acquisition and startup recovery.
No guarantee of first-month profit is possible. With zero M1 revenue, its startup/build expense is a loss in this planning model. A profitable recurring month does not repay startup automatically and can still precede payment settlement. Target about 60% direct contribution, measure retention and CAC, then require cash runway for already-promised usage. Do not treat a reserve or prepaid annual liability as profit.

Sources: [TensorDock advertised rates](https://www.tensordock.com/), [CCBill registration reference](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs), [CCBill pricing](https://ccbill.com/pricing), [Yoti age-service overview](https://www.yoti.com/business/age-verification/). Actual full-node offers, processor terms, vendor minimums, adult model performance and licensing acceptance remain unresolved. See [BUILD](BUILD.md) and [USA](USA.md).
