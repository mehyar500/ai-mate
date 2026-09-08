# US distribution: native app first, separate web alternative

## Current Apple direction — September 8

The founder now prioritizes a non-explicit native companion app with Apple in-app purchases. This supersedes the earlier explicit-first launch requirement. The existing local demo stays private and fully clothed.

Apple guideline 1.1.4 excludes overtly sexual/pornographic material. Clothing alone is not a safe-harbor test: a bikini does not guarantee approval, and erotic presentation or revealing sheer clothing can still conflict with that rule. The incidental mature-UGC provision is not general permission for a primarily sexual AI service. Use a non-explicit product, honest review notes and consistent server-side behavior. Apple decides approval. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/).

Use StoreKit in-app purchases for the proposed digital subscriptions/credits; Apple Pay is a different product. Implement server-verified transactions, restored entitlements and revocation/refund handling before charging. The US storefront permits external purchase links under current guidelines, but the founder's selected path remains Apple billing. Model and hosting terms still apply independently. [Payment guidelines](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase).

“Apple approved design” can only describe an actual approval. The current web UI follows relevant design guidance with large touch targets, clear call controls and optional captions; it has not undergone App Review or iOS accessibility/device testing. Cloudflare model selection, an age gate or paying Apple's commission does not authorize otherwise excluded content. [Design guidance](https://developer.apple.com/design/tips/), [App Review](https://developer.apple.com/app-store/review/).

## Deferred explicit web-service review

September 8 remote-provider clarification: "NSFW" is not a sufficiently precise content category for provider selection. Non-explicit romance, factual sexual-health Q&A, suggestive imagery and explicit sexual generation need separate review. One Cloudflare bill does not replace model-specific conditions. [Cloudflare terms](https://www.cloudflare.com/service-specific-terms-developer-platform/) retain third-party terms for Workers AI and AI Gateway; routing also does not establish US-only processing.

Runpod's current terms prohibit pornography/graphic adult content; self-hosting weights there does not waive the restriction. Pruna's general terms do not list a blanket consensual-adult ban, but explicitly retain third-party conditions, and its P-Video documentation links LTX's license: this is not an explicit-content workaround. Inworld's developer AUP restricts suggestive/mature tools, so its TTS is deferred for the proposed mature scope. Published filter controls are not permission to bypass contractual limits. These findings leave remote neutral clip tests feasible, not an approved NSFW launch. [Runpod](https://www.runpod.io/legal/terms-of-service), [Pruna terms](https://docs.api.pruna.ai/terms), [P-Video license reference](https://docs.api.pruna.ai/guides/models/p-video), [Inworld AUP](https://inworld.ai/aup/).

The material below applies only if a separate explicit web scope is later chosen. It does not describe the native MVP or establish permission for it.

**Current stage is a founder-operated private prototype and fundraising demonstration, with no customer billing or public adult access.** The founder can show a non-explicit product preview using synthetic profiles. The commercial launch conditions below remain deferred requirements; they are not waived by calling something a demo.

No merchant registration or processor integration is purchased now because payments are disabled. No public age-service subscription is purchased because the prototype is not a public adult service. Do not accept payments through a prohibited route or expose an adult beta to avoid those costs. Before any external restricted-content session, determine the applicable access, age, content, consent and provider conditions; manual invitations alone do not establish an exemption. A public preview does not prove adult capability or legal clearance.

The founder may perform source/terms research and build an internal synthetic-data prototype without automatically buying the previous paid-launch legal/security packages. If the intended activity requires specialist advice or permission that is not available within the cap, stop that activity or obtain separately funded advice. The current $100 local planning cap is not a universal compliance budget, legal opinion, insurance policy or authorization to receive investment funds. Local neutral benchmarks do not qualify intended adult output; see [LOCAL_POC](LOCAL_POC.md).

The launch scope is original fictional adults, lawful consensual adult content, clear AI disclosure and verified access. Models' commercial licenses, provider policies, card-network rules and US law are distinct. None of the providers has approved this project yet.

**Adult-service eligibility is a selection criterion, not a post-launch check.** Request acceptance for the actual explicit-content service, including generation, storage, private delivery, visual calls and billing. Do not describe it merely as a generic chatbot to obtain approval. A host accepting stored content does not automatically approve model APIs or every underlying provider.

An explicit web service would require its own accepted scope, rights, hosting, access controls and payment route. The founder has now explicitly chosen a non-explicit native direction first. There is no hidden explicit-mode switch, and removed planning-only environment flags were never functioning access controls.

## What self-hosting does and does not permit

Self-hosting a commercially licensed checkpoint can avoid a managed inference API's separate content policy. It does not waive the checkpoint license, incorporated use policy, training/asset rights, hosting agreement or applicable law. "Open weights" does not mean public domain, and an absent license is not permission. Buying hardware changes ownership of the machine, not these rights.

| Exact checkpoint | Published licensing basis | What this establishes |
|---|---|---|
| Qwen/Qwen3-8B | [Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE) | Commercial use grant without a blanket adult-content prohibition in that license; intended behavior remains untested |
| black-forest-labs/FLUX.2-klein-4B | [Apache-2.0 model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) | Commercial image/editing candidate; card addresses unlawful/nonconsensual uses and says its prose does not modify the released license |
| Wan-AI/Wan2.2-I2V-A14B | [Apache-2.0 model card](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B) | Commercial recorded-video candidate; no verified adult-quality, fast-delivery or project-eligibility evidence |
| hexgrad/Kokoro-82M | [Apache-2.0 model card](https://huggingface.co/hexgrad/Kokoro-82M) | Commercial speech candidate; specific voice, dependency and source-asset rights still require review |

These are royalty-free licensing candidates subject to their conditions, not warranties that all outputs are lawful or non-infringing. A license cannot authorize a third party's likeness or copyrighted material it does not own. Preserve attribution/notices as required; pin exact revisions, obtain an auditable dependency/voice/asset manifest and avoid unlicensed reuploads. The model evidence/exclusions in BUILD and below distinguish eligibility from demonstrated capability.

## Conditional US legal path

**There is no hosting location or model choice that guarantees we cannot be sued. This review does not clear a nationwide launch.** A lawful adult service may be possible within reviewed content and jurisdictions, but age verification alone does not establish legality. Qualified US counsel needs to evaluate the actual supported content, synthetic-media rights, applicable state access rules and the complete delivery/payment flow.

Federal law prohibits commercial distribution of legally obscene material, including through interactive computer services; the Miller test matters even when viewers are adults. Do not equate "consensual and over 18" with automatic protection for every output. [DOJ federal obscenity overview](https://www.justice.gov/criminal/criminal-ceos/citizens-guide-us-federal-law-obscenity).

The FTC began enforcing covered-platform duties under TAKE IT DOWN in May 2026, including a notice process and removal within 48 hours of a valid request. The law addresses qualifying nonconsensual intimate imagery, including digital forgeries. Counsel must assess platform coverage and the precise handling/identical-copy obligations for our service. Build reporting, access revocation and deletion handling; do not assume "no user uploads" resolves every duty. [FTC enforcement notice](https://www.ftc.gov/news-events/news/press-releases/2026/05/ftc-begins-enforcing-take-it-down-act).

Use original fictional adult identities and permitted voices, disable user face/camera uploads, review age/consent controls, keep private material isolated and make AI disclosures visible. Review any applicable 18 USC 2257/2257A recordkeeping duties with counsel, especially if real performers or source footage enter the pipeline; no blanket exemption is asserted. Enable only reviewed states, with accepted age methods and a documented incident/takedown process. Contracts, legal review and insurance can manage particular risks; they do not provide lawsuit immunity.

## Processor shortlist

| Processor | Public evidence | Decision |
|---|---|---|
| CCBill | PSP pricing describes no monthly fee, while high-risk registration is separate. Current US/Canada FAQ lists Visa $950 + Mastercard $1,000 annually. Processing, reserve and other fees require a quote. | Baseline budget; apply for full AI/visual-call scope |
| Segpay | Supports subscriptions/digital purchases; public FAQ lists registration but differs from CCBill's updated Mastercard figure. AI-site guidance restricts user uploads. | Alternative quote; reconcile current card fees and product rules |
| Verotel Basic | Public chart: EUR 500 annual registration, 15.5% non-recurring; recurring adds 1.5%; 10% six-month reserve. Basic lists no webcam billing. | Possible lower-upfront option only if AI visual calls and all fees are expressly accepted |
| Stripe/fal | Relevant adult content/business restrictions | Not adult payment/inference routes |

Sources: [CCBill pricing](https://ccbill.com/pricing), [current registration FAQ](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs), [Segpay FAQ](https://segpay.com/csfaq/), [Segpay AI/UGC guidance](https://gethelp.segpay.com/docs/Content/ComplianceDocs/UserGeneratedContent.htm), [Verotel chart](https://www.verotel.com/en/pricechart.html), [Stripe](https://stripe.com/legal/restricted-businesses), [fal](https://fal.ai/legal/acceptable-use-policy).

No verified zero-upfront processor for this exact business was found. Free technical setup does not waive registration. Deferred fees may reduce initial cash but remain costs. Do not disguise visual calls as another category to qualify for a cheaper plan. No account application or communication has been sent by this task.

## One inference provider

TensorDock US host is the primary custom-model candidate; Cloudflare is the app/storage/WebRTC provider. Confirm complete content scope, underlying-host agreement, data routes, storage, log handling and intended US region. TensorDock's AUP restricts exploitation/nonconsensual content and impersonation, but lack of a blanket consensual-adult ban is not written acceptance. [AUP](https://docs.tensordock.com/legal-information/acceptable-use-policy-aup), [compute terms](https://docs.tensordock.com/legal-information/terms-of-service-tos), [Cloudflare developer terms](https://www.cloudflare.com/service-specific-terms-developer-platform/).

Runware custom compute is an alternative requiring access, model/container support, US-region and adult-business acceptance; do not treat a model-upload API as support for every streaming container. US-only inference does not guarantee Cloudflare/payment/notification processing is US-only.

## September 7 model and host exclusions

| Option | Current finding | Decision |
|---|---|---|
| Runpod | March 24, 2026 terms expressly prohibit pornography/graphic adult content. | Exclude under published terms; do not assume renting raw GPUs changes the contract. [Terms](https://www.runpod.io/legal/terms-of-service). |
| Lightricks/LTX-2.3 | Community license incorporates its AUP; March 30, 2026 AUP covers hosted and on-premises products and prohibits explicit sexual content/erotic chats. License also has a $10M annual-revenue threshold and competition restrictions. | Exclude for the explicit scope under published terms. Free weights or local execution do not waive these terms. [License](https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE), [AUP](https://static.lightricks.com/legal/ltx-acceptable-use-policy.pdf). |
| MiniMaxAI/MiniMax-H3 | August 2026 community license excludes the US, EU, UK and South Korea from its territory, including relevant outputs; separate authorization route exists. | Not a default US deployment option. No separate authorization obtained. [License](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE). |
| ReadyArt/Serenity-12B | Adult-focused June 2026 model card has an Apache tag but also explicitly states personal/noncommercial use. | Exclude pending an unambiguous commercial grant; do not resolve conflicting text in our favor. [Card](https://huggingface.co/ReadyArt/Serenity-12B). |
| dphn/Dolphin3.0-Mistral-24B | Public repository has no declared license tag or separate license file in the checked metadata. | Exact fine-tune license unresolved; base-model rights alone are insufficient evidence. [Card](https://huggingface.co/dphn/Dolphin3.0-Mistral-24B). |
| Sao10K/L3.3-70B-Euryale-v2.3 | Roleplay training is documented, but repository tags `llama3` while its stated base is Llama 3.3; no separate license file found. | Defer: resolve applicable Meta and fine-tune terms; 70B is also outside the cheap baseline. No adult-quality benchmark established here. [Card](https://huggingface.co/Sao10K/L3.3-70B-Euryale-v2.3). |

TensorDock remains a candidate, not an approved adult host. Its AUP also has a written-permission provision for selling/reselling or exploiting the service; confirm how that applies to this commercial application. No account application, provider contact or paid inference was performed. Small model downloads and neutral local benchmarks are documented separately in LOCAL_POC. This review establishes documented terms and unresolved questions, not a legal opinion that a particular output or nationwide service is lawful.

## Can age assurance be internal?

Possibly for a reviewed jurisdiction and accepted method. Paying Yoti is not universally mandatory. But 'we built it ourselves' does not establish compliant verification, and a checkbox, entered birthdate, payment card or generic LLM selfie estimate is not a proven substitute.

Texas Chapter 129B expressly discusses verification performed by the commercial entity or a third party, and specifies digital ID or qualifying verification methods. It also restricts retained identifying information. [Current statute](https://statutes.capitol.texas.gov/Docs/CP/pdf/CP.129B.pdf). Assess current application/enforcement with counsel; do not copy statutory warning text without reviewing rulings.

Florida's published statute requires qualifying services to offer both anonymous and standard verification choices and meet the linked requirements. An in-house ID upload alone does not establish both options. [Florida 501.1737](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.1737.html).

Proposed internal pilot route, only after acceptance: secure separate verification intake; supported identity/digital-proof method; authenticity and binding checks appropriate to that method; restricted human review for uncertainty; no age documents in AI chat, analytics, notifications or model prompts. Delete identifying evidence according to applicable requirements; retain only permissible minimal verification status. The method, data retention and evidence rules need state/merchant review before implementation.

No homemade face-age model is certified here. NIST documents variable age-estimation performance; an estimate around the adult threshold needs appropriate assurance, not a universal pass. [NIST evaluation](https://www.nist.gov/news-events/news/2024/05/nist-reports-first-results-age-estimation-software-evaluation).

The canonical budget now reserves $100/month for an age-service minimum and $1.25/new unique account ($1 assumed check plus a 25% retry provision). These are procurement allowances, not [Yoti tariffs](https://www.yoti.com/business/age-verification/). The three-month scenario has 185 new verified accounts and $231.25 variable checks. An accepted internal method could save these vendor amounts, but security, fraud, appeals and development remain work. Four minutes of review per account values founder effort at $370 across the quarter; cash pay defaults to zero. If a required method or anonymous option is unavailable, integrate an accepted service or do not enable that jurisdiction.

## Other release duties

Start with an empty state allowlist; enable reviewed states only. Assess companion-AI disclosure/safety, synthetic-media rights/takedowns, applicable adult recordkeeping, privacy/biometrics, subscriptions and taxes. Original characters and no user face/camera uploads simplify but do not eliminate obligations.

Covered New York companions have self-harm protocols and non-human notification duties. California SB 243 includes AI disclosure and published self-harm protocols among other duties. Age verification alone does not satisfy these laws. [NY 1701](https://www.nysenate.gov/legislation/laws/GBS/1701), [NY 1702](https://www.nysenate.gov/legislation/laws/GBS/1702), [CA SB 243](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260SB243).

Keep character story separate from factual user memory. Be transparent that scenes and care-like interactions are generated fiction; do not claim clinical treatment, sentience or literal private knowledge. Check-ins/media require opt-in and easy revocation; no sensitive push previews or emotional pressure to pay.

Pin model/checkpoint/runtime/voice licenses and provenance. Klein 4B and Qwen Image Edit are licensing candidates for scene work, not proof of every requested adult output. Respect usage terms and demonstrate the approved scope; do not substitute unlicensed or noncommercial weights.

Founder owns eligibility, contracts and legal budget; engineer owns memory isolation, spend caps and verified controls; independent reviewer checks billing/privacy boundaries. Hosted checkout, reconciled server events, straightforward cancellation and refunds precede paid launch. No guaranteed first-month revenue or zero-cost commercial launch is asserted.
