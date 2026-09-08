# MVP: one relationship, one call, one payment

Decision date: 2026-09-07. Owner: founder. US-first, reviewed state allowlist. Proposed positioning: a companion who remembers useful details and feels present in a call. Competitors already have voice/video; our advantage must be demonstrated, not declared. The [Chaturbate comparison](ECONOMICS.md#chaturbate-in-dollars) separates customer spending from performer payout; low compute cost alone is not demand evidence.

| Requirement | First testable version |
|---|---|
| MVP-1: character | Three original, clearly adult characters spanning girlfriend, boyfriend and neutral options. Fixed portrait/voice; editable name and tone. |
| MVP-2: relationship | Stream text, save user-approved facts, show/correct/delete memory. One companion/account. |
| MVP-3: call | Microphone conversation with the animated character; interruption, captions, reconnect and visible allowance. User camera unsupported initially. |
| MVP-4: videos | Paid 5–10 second talking messages from the call renderer. Separately test 5-second cinematic clips. |
| MVP-5: commerce | Free text/portrait, two paid tiers, minute top-ups and clip packs. Prices live only in [ECONOMICS.md](ECONOMICS.md). |
| MVP-6: boundaries | Adults-only, clean default, verified opt-in adult access where approved, deletion and clear AI disclosure. |

Adult support means an authorized processing route and entitlement. It does not mean minors can use clean mode, unrestricted output, or that host approval exists. If approval fails, test clean mode without selling an adult promise.

## Build order

1. **Prove the call.** One owned portrait/loop and preset voice, one 48GB GPU. Benchmark complete 30- and 60-minute sessions before polishing an app.
2. **Add relationship state.** Sign-in, text, visible memory and call screen for 10 invited adults in scheduled test windows.
3. **Prove payment.** After underwriting, sandbox checkout, renewal, cancellation, refunds, duplicate callbacks and depleted allowances. Independent security review before paid release.
4. **Test retention.** Invite 30–50 adults through founder-led, opted-in outreach. Delay paid acquisition until four-week retention and contribution are known. Adult mode and cinematic clips each need an enablement decision.

## Pass or change direction

Proposed thresholds, not existing results:

- At least 8/10 initial testers finish a call and rate voice/face consistency ≥4/5; record specific defects.
- Across ≥20 warm calls, including mobile browsers: p95 first audible reply ≤1.5s from end of user speech; sustained 25fps; audiovisual skew ≤100ms; interruption silence ≤300ms; no accumulating drift over 60 minutes.
- Delivered call cost ≤$0.055/minute at observed utilization; ≥50% contribution at full allowance after actual processor fees. Include all warm time and failures.
- In the pilot: ≥30% day-7 return and ≥20% invited-activated-to-paid conversion. Reassess after ≥30 activated people. These are internal experiment thresholds, not market benchmarks.

If GPU contention fails, compare Cloudflare speech + GPU avatar. If quality/cost still fails, launch text/voice and retain avatar calls as a test. Never fund an always-warm fleet from hypothetical utilization.

Defer native apps, marketplaces, uploaded faces/voices, full-body live generation, multiple companions, autonomous messages, gifts, vector memory and model training. Evidence requirements: [runbook](../operations/START.md).
