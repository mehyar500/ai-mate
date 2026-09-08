# Asynchronous MVP economics

USD; checked 2026-09-07. Generated from [config](../config/economics.json). Proposed non-explicit launch, not measured results. A 300% return on total cost means a 75% margin. All outputs below are before income tax; founder labor and verification default to zero and must be priced before claiming economic profit.

## Allowances and unit economics

Free: 150 exchanges/month, 5/day, one curated portrait; cap 200 free accounts. Paid: 500 text exchanges/month. Text replies can also be played as free voice messages (up to 15 seconds each); free uploaded voice notes have a separate five-minute input cap. Paid voice allowance below means connected phone-call minutes, including listening; video allowance is delivered clips up to 15 seconds.

| Plan | Price/month | Phone-call min | Clips | Direct cost incl. payment | Contribution | Return on direct cost |
|---|---:|---:|---:|---:|---:|---:|
| Calls | $9.99 | 10 | 0 | $2.15 | $7.84 | 364.8% |
| Calls + Video | $19.99 | 20 | 5 | $3.90 | $16.09 | 412.6% |
| Companion Plus | $29.99 | 30 | 10 | $5.65 | $24.34 | 430.8% |

Budgets: $0.05/connected phone-call minute, $0.15/delivered clip, $0.60/payer text, free voice playback and memory, $0.25/payer support. Ordinary-processing scenario: 3% processing/platform allowance + 2% refund/loss + $0.30/transaction; no merchant approval assumed.

| Optional prepaid pack | Price | Direct cost | Return on direct cost |
|---|---:|---:|---:|
| Video pack: 8 clips / 0 phone-call min | $9.99 | $2.10 | 375.8% |
| Phone-call pack: 0 clips / 30 phone-call min | $14.99 | $2.65 | 465.8% |

These are contribution returns, not company profit. Budget full redemption; do not count unused credits as the business model. Reserve unfulfilled service costs and refunds. No annual prepaid plan or automatic overage in the pilot.

## Generation cost and speed

fal FlashHead: 15 output seconds x $0.005 = $0.075 vendor price. Add $0.01/attempt, divide by 85% usable-output rate and add 25%: $0.125; reserve at least $0.15. Rejected successful generations cost us; vendor server errors have different billing treatment. Hosted text endpoint bundles its own speech; do not charge Aura again for the same video.
Custom Runware scenario: 60 runtime + 0 warm seconds x $0.000553/GPU-second, plus $0.03/attempt, same acceptance/buffer = $0.093. This is an unbenchmarked alternative, not an available endpoint or an adult approval. Count model loading if the contract meters it. Zero workers means zero compute; held-warm and reserved workers cost money.
[fal model](https://fal.ai/models/fal-ai/flashhead), [billing](https://fal.ai/docs/documentation/model-apis/pricing), [Runware compute](https://runware.ai/serverless/compute). Fifteen-second output duration is not turnaround time. Require measured p95 <=20 seconds from submit to playable result before advertising fast delivery.

## First month: cash operating scenarios

Assume the configured plan mix, 200 free accounts, $50.00 recurring fixed cost, $500.00 setup/benchmark cost, $0.00 acquisition per payer, $0.00 founder labor and $0.00 per new free/paid user. Setup is a spending ceiling to test, not a quote for building a production app or US legal review.

| Payers | Revenue | First-month modeled cost | Profit/loss | Return on cost |
|---|---:|---:|---:|---:|
| 20 | $399.80 | $677.99 | $-278.19 | -41.0% |
| 100 | $1999.00 | $989.95 | $1009.05 | 101.9% |
| 600 | $11994.00 | $2939.70 | $9054.30 | 308.0% |

Break-even: 38 mixed-plan payers; 300% first-month return: 547 payers under these assumptions. Revenue is earned only as promised service is delivered; cash collection alone is not profit. All scenarios budget full monthly allowance consumption.

| Stress at configured payer count | Profit/loss | 300% target payer count |
|---|---:|---:|
| Paid acquisition $5 | $509.05 | Impossible at this mix and unit cost |
| Verification $1/new account | $709.05 | 8164 |
| Founder labor $3,000 | $-1990.95 | 3279 |
| No setup charge (later month, same new-payer assumption) | $1509.05 | 92 |
| High-risk fees | $729.18 | Impossible at this mix and unit cost |

An assumed 10% payment reserve reduces configured first-month available cash to $809.15; it is not an expense. Provider prepaid balances, settlement delays and refund liabilities require working capital even when profit is positive.

Formula: price floor = (delivery + fixed payment fee + allocated overhead/acquisition) / (0.25 - percentage fees/losses). If the denominator is nonpositive, 300% return is impossible. No sales or price is guaranteed. Do not rely on unquoted ordinary fees for adult business.

## Later FaceTime-style video calls

Keep disabled in the first month. FlashHead Pro on a quoted TensorDock two-5090 group plus local Qwen3-8B/Whisper/Kokoro: prior modeled $5.69/30 minutes at 50% utilization. At high-risk 18% fees + $0.50, direct 300% floor is ($5.69 + $0.50)/0.07 = about $88.46, before support/startup/overhead. Model $59/30 minutes for an approved clean service with ordinary fees, or $129/30 minutes under the high-risk fee scenario. Both require their own warm-up, support and overhead budget; validate actual cost and demand first. Quark LiveAvatar + Wan2.2-S2V-14B with eight rented H100s costs about $24.69/30 minutes; same direct floor about $359.89. Reject this as the default product. Prices are scenarios, not live offers.
