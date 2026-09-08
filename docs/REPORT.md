# Affordable adult PWA: decision

Research checked September 7, 2026. Replace the expensive Pro-only assumption with **FlashHead Lite, a fixed photorealistic portrait, short generated speech chunks and WebRTC**. Target a conversational pause around one to two seconds on a warm service. No cartoon or canned motion loop is required. Do not promise arbitrary full-body action generation at this price.

## Product and offer

Free verified accounts: 150 text replies/month, max five/day; optional recorded speech up to 15 seconds per reply; five minutes incoming notes; one original adult portrait and editable memory. Pilot cap: 100 free accounts. Paid plans: 500 text replies with the same recorded-voice feature. Live voice and visual minutes are separate, charged as connected time including listening.

| Plan | Monthly price | Visual call min | Voice-only min | Portrait clips, up to 15s |
|---|---:|---:|---:|---:|
| Together | $19.99 | 20 | 10 | 2 |
| Closer | $29.99 | 45 | 20 | 5 |
| Companion | $39.99 | 75 | 30 | 8 |

Subscription optional: $14.99/30 visual minutes, $24.99/60 visual minutes, $14.99/60 voice minutes, or $14.99/10 portrait clips. All require verified accounts. There is no automatic overage, opaque cash wallet or unlimited rendering. Show exact remaining units. Restore credits for failed delivery and make cancellation simple.

This makes an hour-long visual conversation a ~$25 purchase rather than the previous $269 high-risk scenario. It is a different quality/performance configuration, not an independently measured equivalent. Call it an AI visual conversation; disclose synthetic identity. Adult content support is subject to the approved business scope, model behavior and applicable law.

## Why the cheaper approach is credible

The authors report FlashHead Lite at 96 FPS and up to three 25+ FPS streams on one RTX 4090. Budget **two**, not three. TensorDock advertises 4090 GPU pricing from $0.35/hour; our complete-node budget is $0.90/hour including an allowance for CPU/RAM and other node costs, subject to an actual US offer. At two streams and 50% occupied capacity, renderer allocation is $0.015/connected minute; auxiliary inference, transport and contingency bring the budget to $0.025. [Model evidence](https://github.com/Soul-AILab/SoulX-FlashHead), [host pricing](https://www.tensordock.com/).

The source demo batches three chunks into MP4 segments for Gradio playback. Replace that presentation path with a persistent WebRTC stream, feed short TTS chunks and retain each session's temporal cache. This removes avoidable file/segment delay; it does not remove the model's required audio context or establish production latency. [Demo source](https://raw.githubusercontent.com/Soul-AILab/SoulX-FlashHead/main/gradio_app_streaming.py).

At low traffic, stop the renderer outside announced pilot hours. Scale-to-zero is useful between sessions, not between every sentence: model reloads would ruin latency. At launch offer availability windows and a visible pre-call warm-up. Expand availability from paid demand. Do not assume both zero idle spend and guaranteed instant calls.

## Profit and limitations

At assumed 12% processing + 2% losses + $0.50/transaction, the monthly plans yield **305–317% return on direct cost** at full allowance usage. Thirty/sixty-minute visual packs yield about 335%/346%. These exclude new-account verification, company overhead and acquisition.

At 18% combined fees/losses, the middle plan yields about 254% direct return. At 18%, **500% return on total cost is mathematically impossible**: that target allows total costs of only 16.67% of revenue. At 14%, it leaves just 2.67% for all non-percentage costs. None of the proposed plans achieves 500%; do not manufacture that claim by considering GPU cost alone.

The 12% processing input is a target quote, not verified merchant pricing. If combined fees/losses are 18% and 300% direct return remains mandatory, reprice the visual packs to **$19.99/30 minutes and $34.99/60 minutes**, and the same subscription allowances to **$29.99/$44.99/$64.99**. Those are still materially below the earlier Pro design. Alternatively keep the cheaper prices and accept a smaller contribution return; do not disguise the tradeoff.

[ECONOMICS](ECONOMICS.md) includes $1/new-user verification, $1,950 annual US high-risk card registration, renderer availability and a $500 technical setup budget. At 100 payers, the modeled first month loses ~$535 before unquoted legal work/founder pay. At 500 it earns ~$8,178, a 120% return. First-month 300% company return is not achieved by this plan, despite >300% direct return. Later-month performance improves if customers renew without replacement acquisition.

Technical proof can be cheap. Commercial adult launch cannot honestly be represented as a $250 project: [CCBill's current US/Canada registration FAQ](https://ccbill.com/doc/visa-and-mastercard-payment-processing-faqs) identifies Visa $950 and Mastercard $1,000 annually. Payment reserves, age checks and legal review are separate.

## User journey and value

Introduction -> original character/voice preview -> age assurance -> optional confirmed profile -> free conversation -> transparent paid feature -> hosted checkout -> verified entitlement -> visual/voice session -> summary and user-approved memory -> useful return greeting.

First visit knows what the user shares, not everything about them. Returning conversation can recall a confirmed event and ask how it went. Users can edit or delete memory. No covert profiling, emotional pressure to pay, claims of sentience, exclusivity demands or medical promises. Offer companionship; do not advertise a proven cure for loneliness without evidence.

## Competition and demand

Candy's checked monthly offer is $13.99 with unlimited text and 100 premium tokens; the annual promotion is cheaper per month. Our subscription is not cheaper at entry, but includes explicit visual-call minutes. No verified competitor basket establishes a like-for-like saving. ChatGPT Plus's $20 reference offers broader utility; memory by itself does not differentiate us. [Candy](https://candy.ai/subscriptions), [ChatGPT](https://openai.com/chatgpt/pricing/).

A $24.99/hour AI portrait call is potentially attractive compared with many human private shows. At the previously checked Chaturbate wire rate of $0.08/token, 30 tokens/minute is $144/hour, while 6 tokens/minute is $28.80/hour; public streams can be free. These are examples, not universal rates or equivalent services. Humans provide authentic interaction that some customers will never replace. OnlyFans subscriptions and stored content are another distinct purchase. [Chaturbate support](https://support.chaturbate.com/).

[Tavus PALs](https://www.tavus.io/blog/meet-pals-ai-humans-that-finally-feel-human) and published streaming-avatar demos establish that adjacent experiences exist; they do not prove this adult stack's profitability. [RevenueCat 2026](https://www.revenuecat.com/state-of-subscription-apps/) reports weaker long-term retention for monthly AI subscriptions in its dataset. Word of mouth is a hypothesis, especially for a private product people may not share publicly.

## Decision gates

Founder: recruit 20 verified adult testers through opt-in research, no paid campaigns initially. Measure willingness to buy at the actual prices, not just enthusiasm for a demo. Test three original characters across genders; do not assume everyone wants the same mate.

Engineer: demonstrate warm end-to-end p95 <=2 seconds or report the measured miss, usable visuals >=85%, acceptable listening behavior and 60-minute identity stability. Two-stream economics requires two simultaneous full pipelines passing latency, not standalone GPU FPS. Fall back to one stream and use the stress case when it fails.

Proceed to public paid launch only after provider/merchant acceptance, reviewed state availability, bounded costs, functioning memory/deletion and meaningful renewal evidence. Proposed commercial gate: 10 of 20 pilot payers voluntarily renew after a month, with low complaint/refund rates. No assurance that everyone will want it or that organic growth will cover acquisition.

**Recommendation:** build the Lite portrait POC, not Pro, a full-body generator or a research-model collection. A cheap realistic visual conversation is a credible engineering target. Affordable access plus 300% direct return is plausible under the stated quote and load; 500% company return and guaranteed first-month profitability are not supported.
