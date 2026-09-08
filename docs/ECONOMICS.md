# Local proof-of-concept economics

Checked 2026-09-07. Generated from [config](../config/economics.json). Active stage: founder-operated proof of concept and fundraising demos. No customer sales, paid engineering, production uptime or public adult service is budgeted. Existing computer and existing coding subscriptions are already owned/paid; founder living costs are outside this incremental project budget.

## Spending decision

First-demo allowance including the reserve: **$81.00**. Three-month planned expense: **$9.60**, plus one **$75.00** contingency pool = **$84.60**. Set a **$100 quarter cap**. The reserve is counted once, not every month. No cloud GPU, new paid tool or paid engineer is in this active budget. Planned funding is within the cap; stop/re-scope if actual commitments exceed it. No service purchase was made by this task.

## Why this is cheaper

Read-only local inventory found an NVIDIA RTX 4060 Ti with 16,380 MiB reported VRAM and about 47.7 GiB system RAM. Cloudflare currently handles dialogue; CPU speech and local graphics share the existing rig. Scene preparation is a separate phase. No rented GPU is used in this stage. Downloads need internet access; graphics and speech inference stay local; hosted dialogue may incur usage charges. See LOCAL_POC for measured results and limitations.
Founder screenshares a private app using synthetic demo profiles. Public material is a non-explicit product preview with no adult service access, uploads, checkout or exposed inference endpoint. Private does not waive model/host terms or applicable law; unresolved intended-content eligibility is reported as unresolved, not hidden in a demo.

## Three-month incremental costs

| Item | M1 build/demo | M2 demos | M3 demos | Total |
|---|---:|---:|---:|---:|
| Local electricity | $6.00 | $1.80 | $1.80 | $9.60 |
| 24GB cloud fallback | $0.00 | $0.00 | $0.00 | $0.00 |
| Large-GPU video experiments | $0.00 | $0.00 | $0.00 | $0.00 |
| Storage allowance | $0.00 | $0.00 | $0.00 | $0.00 |
| Incremental tools/API allowance | $0.00 | $0.00 | $0.00 | $0.00 |
| Local/free-tier web preview | $0.00 | $0.00 | $0.00 | $0.00 |
| Total planned expense | $6.00 | $1.80 | $1.80 | $9.60 |

Local power assumes 300W incremental average draw and $0.20/kWh, for 100/30/30 hours. This is an estimate, not measured power or the user's tariff. Local disk capacity and existing subscriptions are already available. Cloud fallback and large-GPU hours are zero; legacy rates remain in config only for an explicitly approved future comparison. No guaranteed video throughput or model fit is implied by the budget.

Use localhost; no domain or remote deployment is needed. The active Cloudflare dialogue adapter uses existing credentials and may incur usage charges, which are not measured in this electricity-only baseline. Ollama is an optional local alternative; CPU speech uses downloaded weights. A future eligible web preview could use Cloudflare Free, but it is not needed or deployed now. [Cloudflare pricing](https://developers.cloudflare.com/workers/platform/pricing/).

## Sensitivity and stop rules

| Scenario | Quarter expense | With one contingency pool | Within $100 cap? |
|---|---:|---:|---|
| Baseline | $9.60 | $84.60 | Yes |
| Local power draw doubles | $19.20 | $94.20 | Yes |
| New optional tools at $10/month | $39.60 | $114.60 | No — reduce hours/scope |
| Electricity only, no contingency | $9.60 | $9.60 | Yes |

The $100 cap is a planning limit, not an implemented account control or permission to purchase. The founder now permits considering inexpensive cloud/larger-GPU approaches if local latency remains unacceptable. Compare measured benefit before purchasing; no rental is currently provisioned. No cloud credits or future funding are assumed.

## Costs postponed by the stage change

Customer billing and card registration: $0 now because there is no checkout or payment acceptance. Public age-service minimums: $0 now because there is no public adult access. Paid launch legal/security packages, company-formation purchases, insurance and production support are not automatically incurred for this private prototype. They have not been declared unnecessary for a real launch. Any required advice or third-party access clearance must fit new approved funding or stop that activity. Never take payments through an incompatible processor or call a public adult beta a private demo.

## Future price hypotheses only

### Apple billing sensitivity — September 8

Use **30%** as the conservative commission assumption. Apple's subscription guidance describes 70% proceeds in a subscriber's first year and 85% after one paid year, before applicable taxes. Approved eligible Small Business Program participants can receive the 15% commission rate earlier; do not assume enrollment. [Subscriptions](https://developer.apple.com/app-store/subscriptions/), [Small Business Program](https://developer.apple.com/app-store/small-business-program/).

| Customer price | After 30% Apple fee | After 15% fee | Service-cost ceiling for 60% contribution on customer price, at 30% fee |
|---|---:|---:|---:|
| $19.99 | $13.99 | $16.99 | $2.00 |
| $29.99 | $20.99 | $25.49 | $3.00 |
| $49.99 | $34.99 | $42.49 | $5.00 |

Formula: contribution = price × (1 − commission) − all variable service costs. These ceilings exclude fixed overhead, tax/refunds and acquisition, so they are not net-profit promises. Earlier roughly 63% web contribution estimates cannot be carried into Apple billing unchanged. Use quotas and prepaid top-ups only after measuring service cost; never promise unlimited generated video against these ceilings.

### Optional GPU benchmark budget, not provisioned

Current [Runpod pricing](https://www.runpod.io/pricing) lists a 24GB RTX 4090 Pod at $0.74/hour, 32GB RTX 5090 at $0.99/hour, and 48GB L40S at $1.09/hour. Ten test hours are **$7.40/$9.90/$10.90 GPU compute**, plus storage and applicable charges. Its Serverless 4090 tier lists $1.10/hour: **$0.55 for a continuously occupied 30-minute call**, before other costs and startup. Rates/availability are quotes to recheck at provisioning; the marketing blog and live price table differ, so use the table rather than combining them.

Flex can scale to zero, but startup, execution and the idle timeout are billed; persistent storage still costs money. An 80GB standard network volume at $0.07/GB/month adds **$5.60/month**. Zero idle GPU time does not mean a zero-dollar account. [Billing rules](https://docs.runpod.io/serverless/pricing). A capped 10-hour, 80GB experiment would therefore start around $13–$17 using those Pod quotes, before incidental charges. No machine has been rented and no model has demonstrated the target call speed there.

[Modal](https://modal.com/pricing) lists L4 at $0.000222/s, A10 at $0.000306/s and L40S at $0.000542/s: **$0.7992/$1.1016/$1.9512 per GPU-hour**. CPU, RAM and storage are additional; explicit region selection lists a 1.15–1.75 multiplier. Free credits are not assumed. These are alternative benchmark costs, not confirmation of content-policy or US deployment eligibility.

More system RAM helps keep weights available for offloading; it does not turn the 4060 Ti into a faster GPU. Benchmark a rental before buying a card. For scale, an always-running $0.74/hour worker costs about **$533 per 30 days**, so low utilization can erase subscription margin. Public prices need measured GPU occupancy per delivered call, startup behavior, rejected generations, support/refunds and demand data.

The existing commercial calculator remains available for later planning; its funded-pilot scenario is deferred, not an immediate requirement or committed fundraising target. Its assumptions are not mixed into the local budget. Full-inclusion feature quality and costs remain unvalidated.

| Future monthly offer | Price to test | Earlier direct contribution hypothesis |
|---|---:|---:|
| Together | $19.99 | 63.5% |
| Closer | $29.99 | 63.3% |
| Companion | $49.99 | 63.9% |

Show prospective users clearly labeled price concepts; record qualified interest and objections without charging. Interview responses and investor meetings are not revenue. This stage deliberately has zero revenue, so its expense is a small planned loss. Its return is evidence: local inference measurements, a future demo, license findings and demand signals. Public launch/fundraising legal work and guarantees of investment are outside this budget. See [LOCAL_POC](LOCAL_POC.md), [REPORT](REPORT.md), [BUILD](BUILD.md) and [USA](USA.md).
