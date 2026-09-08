# Launch boundaries and payments

Checked 2026-09-07. Requirements and unresolved commercial decisions, not legal clearance.

Both people and characters are adults. Permit original fictional adults and consensual scenarios. Exclude minors/age ambiguity, coercion, exploitation, nonconsensual imagery, real-person impersonation and uploaded faces/voices. Check input and output; model refusal behavior is not an enforcement system.

| Provider | Finding and decision |
|---|---|
| Cloudflare | Infrastructure and model terms differ. Preferred application host; confirm intended use, data and each model's terms. |
| TensorDock | AUP prohibits child exploitation/nonconsensual material; compute agreement is separate. Conditional GPU candidate; obtain applicable agreement and written use-case approval before adult processing. |
| RunPod | Current terms prohibit pornography/graphic adult content. Clean benchmark alternative only. |
| Vast.ai | Current terms prohibit obscene content. No adult-use assumption. |
| Stripe | Adult prohibition includes AI content for sexual gratification. Exclude for this mixed adult business; no disguised clean sales. |
| CCBill | Adult-business processor candidate; AI-companion eligibility still needs underwriting. |
| Resend | Prohibits sexually explicit email and reserves high-risk-business discretion. Conditional candidate for neutral sign-in mail only; obtain eligibility confirmation. |

Sources: [Cloudflare](https://www.cloudflare.com/service-specific-terms-developer-platform/), [TensorDock AUP](https://docs.tensordock.com/legal-information/acceptable-use-policy-aup) and [terms](https://docs.tensordock.com/legal-information/terms-of-service-tos), [RunPod](https://www.runpod.io/legal/terms-of-service), [Vast](https://vast.ai/terms), [Stripe](https://stripe.com/legal/restricted-businesses), [CCBill](https://ccbill.com/industries/adult-business).

Email source: [Resend AUP](https://resend.com/legal/acceptable-use). Sending only neutral messages does not itself establish business eligibility.

Founder selects initial US states with qualified review. Default allowlist empty and adult mode off. Verify adult eligibility for free and paid accounts under the selected policy. Yoti hosted age verification uses account-bound server-created sessions and authoritative server retrieval, not browser callbacks. Store only policy-permitted proof/status, never ID images. A state retention rule can override the proposed reference/expiry storage. Quote required. [Yoti quick start](https://developers.yoti.com/age-verification/quick-start).

## US launch is state-specific

The Supreme Court upheld the challenged Texas age-verification requirement in June 2025; that is not nationwide approval of this product or a specific verification method. [Official opinion](https://www.supremecourt.gov/opinions/24pdf/23-1122_3e04.pdf).

| Example requiring review | Concrete implication |
|---|---|
| [Texas Chapter 129B](https://statutes.capitol.texas.gov/Docs/CP/pdf/CP.129B.pdf) | Relevant verification provisions prohibit retaining identifying information after access. Review proof storage and current enforcement; do not copy separately litigated health-warning language blindly. |
| [Florida 2026 §501.1737](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.1737.html) | Qualifying services must offer anonymous and standard age-verification options. A single generic selfie flow is not a US-wide solution. |

Maintain a launch-state table with source, effective/enforcement status, product applicability, allowed verification methods, retention and review date before enabling any state. These examples are not a 50-state legal review. Assess AI-companion-specific duties as well as adult-site rules. A US GPU location does not determine which customer-state laws apply; confirm US compute availability, data flows, merchant entity and tax setup separately.

Yoti documents a [US partner flow for Florida](https://developers.yoti.com/age-verification/us-partner). Evaluate that configuration and the permitted standard methods together before allowing Florida; a generic API key alone does not configure compliance.

## Billing contract

Use hosted FlexForms. CCBill requires approved URLs, nonsexual checkout imagery, clear recurring terms and suitable hosting; its AUP excludes free web hosting. Budget paid Workers and confirm the arrangement. [Merchant AUP](https://ccbill.com/cs/client/policies/ccbill/acceptable_use.html).

Create purchase intents with account, SKU, currency, amount and unique key. Use documented dynamic-pricing digests, not an invented universal HMAC webhook secret. Initial-sale `dynamicPricingValidationDigest` does not authenticate every lifecycle event. Validate trusted-edge source addresses, account/subaccount and schema; persist an event inbox; reconcile status server-to-server before grants. If verification is unavailable, keep new grants pending and alert operations.

Apply verified transactions once to an append-only ledger. Distinguish payment, renewal, cancel, expire, refund and chargeback. Cancellation preserves the paid period. Replays cannot replenish twice; old success events cannot restore refunded access. Redirects grant nothing. Reconcile daily and after outages. [Dynamic pricing](https://ccbill.com/doc/dynamic-pricing-user-guide), [webhooks](https://ccbill.com/doc/webhooks-user-guide), [Data Link](https://ccbill.com/doc/datalink-user), [subscription API](https://ccbill.com/doc/ccbill-api-guide).

## Privacy and release

No raw call recording; discard transient media at session end. Proposed retention: chats 30 days, approved memories until deletion, clips 7 days. Support immediate user deletion; separately define required billing retention. Test deletion of derived data/backups. Logs contain timings, costs, errors and opaque IDs, never intimate content or credentials.

Workers AI says it does not train/improve models with content without explicit consent; this does not extend automatically to external Gateway providers. Adult speech stays local unless another provider explicitly permits it. Review direct Deepgram opt-out settings if used later. [Cloudflare data](https://developers.cloudflare.com/workers-ai/platform/data-usage/), [Deepgram terms](https://deepgram.com/terms), [opt-out](https://developers.deepgram.com/docs/the-deepgram-model-improvement-partnership-program).

Independent security review before paid release must cover cross-account access, forged age/payment results, replay/refund races, fail-closed routes, cancellation, deletion and abuse controls. Founder owns commercial/jurisdiction decisions; engineer owns tests; reviewer owns evidence. This reset supplies no deployment or merchant approval.
