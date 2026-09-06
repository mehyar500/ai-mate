# Amorien: PWA-first distribution, iOS and payments

## Decision

Launch Amorien as a **Progressive Web App (PWA)** first. Users visit the website in Safari and use Share → Add to Home Screen. Defer a native App Store app until customer demand and revenue justify its development and review costs.

Use an approved CCBill web checkout for the adult offering, subject to written merchant underwriting approval for the actual AI content, business and jurisdictions. No accounts, payments or production infrastructure are created by this document.

This decision supersedes earlier suggestions that an unrestricted native iOS experience, provider acceptance, legal compliance or margins were already validated. Previous cost estimates remain hypotheses, not measured production costs. No provider guarantees immunity from suspension.

## PWA launch

- Serve the web app over HTTPS with a manifest, icons and an appropriate service worker. Never cache private conversations, credentials or payment responses in a public/offline cache.
- Explain iPhone installation through Safari's Add to Home Screen flow.
- Request microphone, camera and notification permissions only when needed.
- Test WebRTC, interruptions, backgrounding, reconnects, audio routing, installation and notifications on physical iPhones. Do not promise native-equivalent background calling.
- Website payments do not incur an App Store commission. Processor fees, reserves, refunds, chargebacks, taxes and operating costs still apply.
- A PWA has no App Store listing or guaranteed App Store discovery.

## Payment and entitlement flow

```text
Web / installed PWA
  -> approved CCBill hosted checkout
  -> provider-authenticated, replay-safe server notification
  -> D1 subscription and payment-event ledger
  -> Worker checks entitlement, age eligibility and usage allowance
  -> authorized model session
```

1. Create checkout on the server using an approved product/price configuration. Keep credentials out of the browser.
2. Associate payment with an internal account identifier; do not trust client-supplied prices or plan privileges.
3. Activate access only after server-side verification using the processor's documented notification/verification mechanism, not the checkout return URL.
4. Process events idempotently. Handle duplicates, retries and out-of-order delivery, with reconciliation against provider records.
5. Store provider, external subscription ID, account ID, plan, status, expiry/paid-through date, cancellation state and usage allowance. Keep billing entitlements separate from age/content eligibility.
6. Handle renewal, cancellation, failed payments, refunds and chargebacks. Explain where the user must cancel and prevent accidental duplicate subscriptions.
7. Use hosted payment collection; do not store card details. Define data retention, access controls and deletion procedures.

## Apple content restrictions

Apple App Review Guideline 1.1.4 prohibits overtly sexual or pornographic material, including explicit descriptions as well as imagery. Paying elsewhere or verifying age does not override that restriction. A private one-to-one experience is not automatically exempt.

Do not wrap the unrestricted PWA in a native shell, hide features from reviewers, or enable prohibited features after approval. Guideline 4.2 also requires more than a repackaged website.

A later native app must offer a genuinely App-Store-compliant companion experience. Enforce that boundary on the server, including conversation history, generated media, notifications and shared-account data. Keep the adult experience web-only; do not assume native links promoting it will be approved. Apple review remains a launch gate.

## Apple billing by storefront

- **US storefront:** Guideline 3.1.1(a), as consulted for this decision, allows buttons, external links and calls to action to other purchase methods without the external-link entitlement required in certain other regions. This is not permission for prohibited content or a universal exemption for embedded payment mechanisms.
- **Other storefronts:** Review the applicable regional rules and agreements. Do not apply US permissions globally.
- **Multiplatform access:** Guideline 3.1.3(b) permits access to subscriptions/content acquired on another platform under its conditions, including the stated IAP availability condition. It is not a blanket way to avoid IAP obligations.
- **Apple IAP:** Eligible developers enrolled in the App Store Small Business Program can receive a 15% commission rate. Do not assume every sale incurs 30%, or that reduced rates apply automatically.
- An AI companion is not a human-to-human service qualifying automatically for the person-to-person payment exception.

If native IAP is added, use StoreKit with server-verified transactions and App Store Server Notifications. Map Apple and web purchases into the same entitlement ledger. Track purchase channel and direct cancellation to that channel. Recheck current Apple rules before submission or expansion to another storefront.

## Competitor evidence

- Replika's cancellation documentation describes both in-app and web subscriptions and platform-specific cancellation.
- Kindroid's subscription help describes web subscription management alongside mobile purchasing.
- These sources support a multi-channel billing pattern. They do not establish any competitor's private Apple review arrangements or prove that explicit features are permitted in its native app.

## Economics and unresolved approvals

Do not set subscription allowances from the earlier unbenchmarked per-minute estimates. Measure full session cost, including GPU idle time, concurrency, voice/video generation, memory, transport, storage, support and abuse prevention.

Contribution per subscriber = collected revenue less payment fees, usage costs, refund/chargeback provision and other variable costs. Operating profit additionally subtracts fixed costs, acquisition spend and compensation. Processor reserves affect cash flow even when not an expense.

Before paid launch, obtain or validate:
- Processor approval, fee schedule, reserve requirements and permitted AI-content scope.
- Host AUP acceptance and commercial model/voice/likeness rights.
- Jurisdiction-specific legal advice, appropriate age assurance, privacy notices and consent, content restrictions and incident handling. FOSTA-SESTA is not itself a universal age-verification API mandate.
- Security and billing tests, cancellation/refund flow and accurate customer disclosures that companions are AI.

## Delivery checklist and ownership

- Founder: approve PWA-first scope; approve spending only after quotes.
- Engineering: implement installation, authentication, verified billing ledger and server-side usage/content gates.
- Legal/compliance and providers: resolve licensing, merchant approval, content, privacy and jurisdiction gates.
- QA: test physical iPhones, payment sandbox events, access expiry, duplicate events, refunds and account deletion.
- Later native release: separate decision, storefront review, content-boundary tests and billing implementation.

**Current status:** distribution decision documented; no implementation, provider approval, legal sign-off or profitability guarantee implied.

## Sources

Official policy pages were consulted during the preceding discussion; recheck them at launch because terms change.

- Apple App Review Guidelines, especially 1.1.4, 3.1.1(a), 3.1.3(b), 3.1.3(d) and 4.2: https://developer.apple.com/app-store/review/guidelines/
- Apple Small Business Program: https://developer.apple.com/app-store/small-business-program/
- Replika cancellation help: https://help.replika.com/hc/en-us/articles/360032500012-How-to-cancel-your-subscription
- Kindroid subscriptions: https://kindroid.ai/v2/docs/subscriptions/
