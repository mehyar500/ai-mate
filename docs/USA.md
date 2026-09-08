# US adult launch: concrete conditional path

This plan targets verified adults, lawful consensual adult content and original fictional characters. Commercial-use licensing, provider acceptance and US law are separate requirements. No unrestricted model or host approval has been obtained by this research.

## Providers

| Platform | Job | Selection / condition |
|---|---|---|
| TensorDock, selected US host | RTX 4090 Lite renderer, custom inference | Primary POC candidate. Confirm exact US location, node price, data handling and acceptance of the complete adult AI service under provider and underlying-host contracts. |
| Cloudflare | PWA, D1/R2, account coordination, WebRTC | Infrastructure candidate; review developer/content/data terms. Self-host adult inference; do not infer hosted-model permission from infrastructure eligibility. |
| CCBill | High-risk hosted checkout | Apply with accurate AI/content flow. Obtain rates, reserves, registration and AI-content acceptance before selling. |
| Yoti | Age assurance | Obtain suitable method/price for reviewed states, server-verify proof, minimize retained data. |
| Runware custom compute | Potential future scale-to-zero alternative | Beta access, US region, streaming/metering and intended-use acceptance unconfirmed. Do not depend on it for POC. |
| Resend or approved transactional provider | Neutral account mail | Confirm whole-business eligibility; no intimate content in email. |
| fal / Stripe | Not adult traffic routes | fal prohibits explicit content; Stripe prohibits the relevant adult business. Do not route around these rules. |

Sources: [TensorDock AUP](https://docs.tensordock.com/legal-information/acceptable-use-policy-aup), [compute terms](https://docs.tensordock.com/legal-information/terms-of-service-tos), [Cloudflare developer terms](https://www.cloudflare.com/service-specific-terms-developer-platform/), [CCBill adult processing](https://ccbill.com/industries/adult-business), [Yoti](https://developers.yoti.com/age-verification/quick-start), [Runware terms](https://runware.ai/terms), [fal AUP](https://fal.ai/legal/acceptable-use-policy), [Stripe restrictions](https://stripe.com/legal/restricted-businesses), [Resend AUP](https://resend.com/legal/acceptable-use).

TensorDock's reviewed AUP prohibits exploitation, nonconsensual imagery and impersonation; it does not establish blanket approval for consensual adult business. Runware's general terms distinguish unlawful/minor content and model licenses; its creator-program advertising restrictions are a separate policy, not proof of platform-wide eligibility. Confirm the actual service rather than treating absence of a blanket ban as approval.

## Model rights

FlashHead Lite, Qwen3-8B, Kokoro and FLUX.1-schnell are commercially usable licensing candidates identified in BUILD. No general Apache-2.0 field-of-use ban is a guarantee of legality, checkpoint behavior or rights in portraits/voices. Pin checkpoint/code revisions and notices, including VAE_LTX, wav2vec2, phonemizers and any guard. No unlicensed fine-tunes, public-figure cloning, research-only sample identities or noncommercial weights.

Separate licensed capability from product capability: a talking-head model does not prove arbitrary explicit action generation. Evaluate the approved lawful adult scope before advertising it. Require original adult identity provenance and consent wherever real source assets are used.

## Release steps

1. Founder documents the exact adult content, fictional identity rules, PWA, model/data routes and states proposed for launch; obtain provider/merchant eligibility for that description.
2. Obtain a current state applicability review covering age verification, AI companions, privacy/biometrics, synthetic media, obscenity and billing. Start with an empty state allowlist until reviewed. US hosting is not a legal safe harbor or a US-only data guarantee.
3. Age-gate before adult access, including free accounts. Payment card possession is not proof of age. Fail closed on forged/expired proof; retain a minimal verification result rather than identity documents where appropriate.
4. Implement visible AI disclosure, age/consent boundaries, complaint/takedown handling, self-harm protocols, memory deletion, privacy notices and clear renewal/cancellation.
5. Test security, payments, policy handling and actual content behavior with independent review before paid release. PWA distribution does not bypass law or processor rules.

Concrete laws already relevant to the review: [New York GBS 1701](https://www.nysenate.gov/legislation/laws/GBS/1701) requires a self-harm detection/response protocol for covered companions; [1702](https://www.nysenate.gov/legislation/laws/GBS/1702) requires non-human notices at interaction start (need not exceed daily) and every three hours during continuing interaction. Use enacted law, not similarly named pending bills.

[California SB 243](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB243) includes AI disclosure, a published self-harm protocol and additional provisions, including future reporting. Its minor-specific provisions are not a blanket prohibition on adult content. Adult-only access does not remove all companion duties. This is not a completed 50-state review.

For adult-content age assurance, review each qualifying statute and enforcement status. Examples: [Texas Chapter 129B](https://statutes.capitol.texas.gov/Docs/CP/pdf/CP.129B.pdf), [Florida 501.1737](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.1737.html). Do not assume one verification method and retention design satisfies every state. Review federal synthetic-media/takedown and any recordkeeping applicability with counsel; no blanket exemption is asserted.

Position as optional companionship, not clinically proven treatment for loneliness. Do not claim the character is human, conscious, emotionally dependent on payment, or a replacement for all human contact. No unsolicited intimate notifications. Measure whether users find it helpful and whether harm/complaints emerge.

## Minimum commercial budget and ownership

CCBill's [current US/Canada FAQ](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs) lists $950 Visa and $1,000 Mastercard annual high-risk registration, with the Mastercard increase effective May 1, 2026. These costs alone exceed a $250 technical POC. Confirm applicability, fees, reserves and settlement with the actual contract. Alternative processors may differ; no cheaper approved quote is established.

Founder owns provider/merchant/state clearance and legal budget. Engineer owns evidence for identity provenance, latency/cost, deletion, age results and payment reconciliation. Feature flags stay disabled until their gates pass. Legal fees are unquoted in the forecast, not zero in reality. A private technical POC and a commercially legal adult launch are separate milestones.
