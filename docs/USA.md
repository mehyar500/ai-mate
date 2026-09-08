# What is required for a US launch

**There is no verified “anything goes, legal everywhere” stack.** The proposed scope is original fictional adults and consensual content. Exclude minors/age ambiguity, coercion, exploitation, nonconsensual imagery and real-person impersonation. A commercial model license does not grant permission for every use.

| Decision | Evidence / action before launch |
|---|---|
| Cloudflare | [Developer terms](https://www.cloudflare.com/service-specific-terms-developer-platform/) distinguish infrastructure from model-licensor rules. Confirm the business/data flows; do not infer hosted-model adult permission. |
| TensorDock | [AUP](https://docs.tensordock.com/legal-information/acceptable-use-policy-aup) prohibits exploitation/nonconsensual imagery; [compute agreement is separate](https://docs.tensordock.com/legal-information/terms-of-service-tos). Obtain the applicable contract and written intended-use approval. A US GPU location alone does not establish legality. |
| Exclude RunPod for explicit adult traffic | [Current terms](https://www.runpod.io/legal/terms-of-service) prohibit pornography/graphic adult content. |
| Payments | [CCBill](https://ccbill.com/industries/adult-business) is an application candidate, not confirmed AI-companion approval. [Stripe](https://stripe.com/legal/restricted-businesses) prohibits the relevant adult category. Disclose the whole business; do not disguise sales. |
| Verify adults | [Yoti hosted verification](https://developers.yoti.com/age-verification/quick-start); confirm required methods/retention for each allowed state. Server-check results; card ownership is not age proof. Quote required. |
| Email | [Resend AUP](https://resend.com/legal/acceptable-use) restricts explicit messages and high-risk businesses. Neutral sign-in email still requires business eligibility confirmation. |

Start with an **empty US state allowlist**. Founder obtains a reviewed initial state list, product applicability, current enforcement, allowed verification methods and retention policy. Texas's challenged age-check requirement was [upheld](https://www.supremecourt.gov/opinions/24pdf/23-1122_3e04.pdf); relevant [Texas rules](https://statutes.capitol.texas.gov/Docs/CP/pdf/CP.129B.pdf) restrict identity retention. [Florida](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.1737.html) requires qualifying services to offer anonymous and standard options; assess [Yoti's US-partner configuration](https://developers.yoti.com/age-verification/us-partner). This is not a completed 50-state or AI-companion-law review.

Pin every deployed model/checkpoint/runtime revision, hash and license, including Quark/Wan, FlashHead VAE/audio encoders, and voice phonemizers. Exclude XTTS-v2's noncommercial weights and unlicensed fine-tunes. No raw call recording; minimize proof/log retention; allow memory/account deletion. Keep AI disclosure, consent and reporting visible. Never promise the character is human or pressure payment through emotional dependency.

Use CCBill hosted checkout with clear renewal/cancellation and nonsexual imagery. [Its AUP](https://ccbill.com/cs/client/policies/ccbill/acceptable_use.html) also requires suitable paid hosting. Validate [documented webhook origins/events](https://ccbill.com/doc/webhooks-user-guide), reconcile server-side, grant once and handle refund/renewal ordering. No browser redirect grants access; no invented universal webhook HMAC. Cancellation preserves the paid-through period.

Founder owns host/merchant/state approvals; engineer owns measured performance and licensing manifest; independent reviewer checks tenancy, forged payments/age results, replay, deletion and routing before paid release. Until then, adult/call/clip feature flags stay off.

## What the video change means legally

Quark's adapter and Wan base, FlashHead's model card and code, and GAIR LiveTalk's model card identify Apache-2.0 licensing. These are commercially usable starting points, not unlicensed models. Audit every actual checkpoint bundle, tokenizer, audio encoder, VAE, quantization modification and runtime notice at its pinned revision. Top-level metadata does not erase dependency terms. Keep original character provenance and preset-voice permissions; no public figures or sample-person assets as product identities. Sources are linked in BUILD and REPORT.

TensorDock's reviewed AUP does not contain a blanket ban on all consensual adult content; it does prohibit exploitation, nonconsensual sexual imagery and impersonation. That supports an intended-use review, not announcing approval. The separate compute agreement, resale/service terms, underlying host and merchant underwriting still apply. Obtain confirmation for the complete customer-facing synthetic companion service. If unavailable, adult launch stops; no unrestricted fallback is verified here.

HeyGen LiveAvatar is a clean-only published-price comparison. Its terms prohibit explicit content and restrict competitive benchmarking; never use it for adult failover. Aggregators do not waive upstream restrictions. Cloudflare processing locations and subprocessor terms need review: a US GPU does not make all requests and records US-only.

Before enabling any state, the founder must obtain current review of age verification, AI-companion disclosure/safety, privacy/biometric rules, subscription law and synthetic-media applicability. Texas/Florida examples above are not a complete compliance determination. Keep all MVP account holders 18+, including clean mode. A provider choice does not make every possible user request lawful.
