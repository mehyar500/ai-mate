# Local proof-of-concept economics

Checked 2026-09-07. Generated from [config](../config/economics.json). Active stage: founder-operated proof of concept and fundraising demos. No customer sales, paid engineering, production uptime or public adult service is budgeted. Existing computer and existing coding subscriptions are already owned/paid; founder living costs are outside this incremental project budget.

## Spending decision

First-demo allowance including the reserve: **$81.00**. Three-month planned expense: **$9.60**, plus one **$75.00** contingency pool = **$84.60**. Set a **$100 quarter cap**. The reserve is counted once, not every month. No cloud GPU, new paid tool or paid engineer is in this active budget. Planned funding is within the cap; stop/re-scope if actual commitments exceed it. No service purchase was made by this task.

## Why this is cheaper

Read-only local inventory found an NVIDIA RTX 4060 Ti with 16,380 MiB reported VRAM and about 47.7 GiB system RAM. Test dialogue and CPU speech locally, then evaluate the portrait renderer within the remaining VRAM. Scene preparation is a separate phase. No rented GPU is used in this stage. Downloads need internet access; inference stays local. See LOCAL_POC for measured results and limitations.
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

Use localhost; no domain, remote deployment, hosted model API or new subscription is needed for local tests. Existing Ollama and the isolated CPU speech runtime use downloaded weights. A future eligible web preview could use Cloudflare Free, but it is not needed or deployed now. [Cloudflare pricing](https://developers.cloudflare.com/workers/platform/pricing/).

## Sensitivity and stop rules

| Scenario | Quarter expense | With one contingency pool | Within $100 cap? |
|---|---:|---:|---|
| Baseline | $9.60 | $84.60 | Yes |
| Local power draw doubles | $19.20 | $94.20 | Yes |
| New optional tools at $10/month | $39.60 | $114.60 | No — reduce hours/scope |
| Electricity only, no contingency | $9.60 | $9.60 | Yes |

The $100 cap is a planning limit, not an implemented account control or permission to purchase. Do not move tests to a cloud provider because a local model fails to fit. Change model size, quantization, context, processing order or the tested feature, and document the effect. Stop at the cap. No cloud credits or future funding are assumed.

## Costs postponed by the stage change

Customer billing and card registration: $0 now because there is no checkout or payment acceptance. Public age-service minimums: $0 now because there is no public adult access. Paid launch legal/security packages, company-formation purchases, insurance and production support are not automatically incurred for this private prototype. They have not been declared unnecessary for a real launch. Any required advice or third-party access clearance must fit new approved funding or stop that activity. Never take payments through an incompatible processor or call a public adult beta a private demo.

## Future price hypotheses only

The existing commercial calculator remains available for later planning; its funded-pilot scenario is deferred, not an immediate requirement or committed fundraising target. Its assumptions are not mixed into the local budget. Full-inclusion feature quality and costs remain unvalidated.

| Future monthly offer | Price to test | Earlier direct contribution hypothesis |
|---|---:|---:|
| Together | $19.99 | 63.5% |
| Closer | $29.99 | 63.3% |
| Companion | $49.99 | 63.9% |

Show prospective users clearly labeled price concepts; record qualified interest and objections without charging. Interview responses and investor meetings are not revenue. This stage deliberately has zero revenue, so its expense is a small planned loss. Its return is evidence: local inference measurements, a future demo, license findings and demand signals. Public launch/fundraising legal work and guarantees of investment are outside this budget. See [LOCAL_POC](LOCAL_POC.md), [REPORT](REPORT.md), [BUILD](BUILD.md) and [USA](USA.md).
