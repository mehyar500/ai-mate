# Product and business decision

September 7, 2026. Free text and recorded voice; paid phone calls and personalized portrait video messages. Original fictional adult characters, realistic appearance, no cartoons or canned motion loops. Disclose that characters are synthetic. Recommend a non-explicit MVP.

## Offer

| Offer | Price | Included |
|---|---:|---|
| Free | $0 | 150 text replies/month, max 5/day; optional spoken playback up to 15 seconds each; 5 minutes incoming voice notes/month; curated portrait and editable memory |
| Calls | $9.99/month | 500 text replies with spoken playback, 10 connected call minutes |
| Calls + Video | $19.99/month | Same text/voice allowance, 20 call minutes, 5 videos |
| Companion Plus | $29.99/month | Same text/voice allowance, 30 call minutes, 10 videos |
| Video pack | $9.99 once | 8 videos up to 15 seconds; no subscription required |
| Phone-call pack | $14.99 once | 30 connected minutes; no subscription required |

Recorded voice stays free within the text allowance. Paid accounts retain five minutes of incoming notes; continuous conversation uses paid calls. Meter connected time including listening, with visible timer and balance. No automatic overages. Restore credits on failed clips. Show dollars and units instead of opaque tokens. Reserve full fulfillment costs; do not rely on unused credits. Disclose renewals, resets, pack validity and refunds before purchase.

## Why pay?

Continuity plus optional presence: remember the last conversation, talk hands-free, receive a personalized visual greeting. First-visit knowledge comes from an optional introduction, never hidden access to someone's life. Returning greetings use confirmed facts and acknowledge uncertainty. Users inspect, correct, disable and delete memory.

Memory alone is not unique. Competitors offer unlimited text; general assistants have broader utility; talking portraits can become repetitive. Voice consistency and believable conversation must earn renewal. Do not pressure distressed users to buy or make remembered facts conditional on payment.

## Profit: conditional

300% return on cost means revenue is four times total cost, a 75% margin. Full-allowance direct costs are approximately $2.15, $3.90 and $5.65 for the three plans: contribution margins of 78.5%, 80.5% and 81.2%. Company overhead still comes out of that contribution. [ECONOMICS](ECONOMICS.md) owns calculations.

Assume 200 free accounts, $50 monthly overhead, $500 setup ceiling, zero acquisition spending, no founder salary and no verification fee. At the configured plan mix, 20 payers lose $278; 100 produce about $1,009 cash operating profit; 600 produce about $9,054. Break-even is about 38 customers; 300% first-month return needs about 547. Building the app and legal review may exceed the setup ceiling substantially.

At $5 acquisition per payer, the 300% target becomes unattainable at this price/mix, even at scale. High-risk payment fees also defeat that target. Founder labor, verification, settlement delays, taxes and refunds need real funding. These are scenarios, not forecasts.

## Infrastructure choice

Cloudflare hosts the app, memory, text and audio. Hosted **fal-ai/flashhead** supplies clean portrait clips at $0.005/output second: $0.075 for 15 seconds, with a $0.15 delivered budget after retries/overhead. Its text pipeline uses FlashHead Lite and bundled ElevenLabs speech. Quality is untested; do not claim cinematic full-body realism. [Pricing](https://fal.ai/models/fal-ai/flashhead), [schema](https://fal.ai/models/fal-ai/flashhead/api).

Hosted requests avoid renting our own idle GPU. **Runware Serverless Compute** is a custom-model beta candidate: RTX PRO 6000 at published $0.000553/GPU-second, about $1.99/hour. Access, intended-use approval and speed remain unconfirmed. Held-warm/reserved workers cost money. An assumed 60 billed seconds gives about $0.093/clip including other costs and retry buffer; this is not a benchmark or a ready FlashHead endpoint. [Compute](https://runware.ai/serverless/compute), [terms](https://runware.ai/terms).

Keep live video disabled. Later test FlashHead Pro with indicative $59/30 minutes for an approved clean service or $139/30 under high-risk fees. Exclude these sales from MVP forecasts. The heavy eight-H100 LiveAvatar route is too costly for the default product.

## Competition and switching

| Alternative | Price comparison | Why switch / why stay |
|---|---|---|
| Candy AI | $13.99 monthly; advertised annual $47.88 upfront ($3.99/month equivalent); premium includes 100 tokens, not 100 videos | Our $9.99 is 28.6% cheaper than monthly; $19.99 is 42.9% dearer. Clear units may appeal; Candy offers unlimited text and an established ecosystem. No verified equivalent-video savings. |
| ChatGPT Plus | $20/month reference | Our entry is roughly half, but much narrower. Character identity and portrait clips may appeal; broader utility favors ChatGPT. |
| Human cam services | Free public streams; variable private rates | AI offers availability and predictable charges. Human agency and authentic connection cannot be replicated. |
| OnlyFans | Creator-specific subscriptions and paid content | Recorded content amortizes cheaply. Personalized clips are a different purchase; no universal savings claim. |

Sources: [Candy checkout](https://candy.ai/subscriptions), [premium inclusions](https://everai.zendesk.com/hc/en-us/articles/44102896051481-What-can-I-do-as-a-paid-user), [ChatGPT pricing](https://openai.com/chatgpt/pricing/). Recheck actual baskets before advertising comparisons.

The checked Chaturbate wire-purchase example is $0.08/token versus $0.05/token broadcaster payout. At 30 tokens/minute, a buyer spends $72/30 minutes and the performer receives $45; at 6 tokens/minute the buyer spends $14.40. A hypothetical $59 AI video call undercuts $72 by 18.1%, but is dearer than the cheaper room. Audio calls and asynchronous clips are not equivalent to human live video. Room and payment-method prices vary. [Official support](https://support.chaturbate.com/).

## Evidence and pilot

[Tavus PALs](https://www.tavus.io/blog/meet-pals-ai-humans-that-finally-feel-human) demonstrates a video-companion product, not audited profitability of this stack. [RevenueCat's 2026 report](https://www.revenuecat.com/state-of-subscription-apps/) reports twelve-month retention of 6.1% for monthly AI subscriptions versus 9.5% for non-AI in its dataset. No verified profitable case study for our exact offer was established.

Cap the pilot at 200 free users and 20 paying testers. Proposed gates: >=85% usable clips, p95 submit-to-playable <=20 seconds, phone response p95 <=1.5 seconds, costs within budget, and at least 10/20 testers renewing voluntarily after a month. These are chosen thresholds, not market benchmarks. Founder owns interviews and eligibility; engineer owns implementation and measurements. Avoid paid ads until retention supports CAC.

**Verdict:** plausible small experiment, not foolproof. Start free messages plus paid calls/clips. Resolve eligibility and reprice before launching explicit content. If quality or renewal fails, stop rather than fund full live video.
