# Decision report — 7 September 2026

**Build a convincing talking character first. Do not promise unlimited actions or live full-body video.** A consistent face, natural speech, interruption and useful memory are feasible to prototype. Their quality and cost together are not proven.

## What we offer versus ChatGPT

| | ChatGPT | Proposed Amorien |
|---|---|---|
| Product | General assistant with live voice and other tools | One persistent fictional adult companion with an animated face |
| Monthly price | Plus $20; Pro starts at $100 | Close $24.99/60 call minutes; Together $49.99/180 minutes |
| Cheaper than Plus? | Reference price | **No: Close is 24.95% more; Together 149.95% more** |
| Usage comparison | Plan- and app-dependent voice allowances; not sold as our monthly avatar-minute bundle | Explicit monthly connected-call minutes |
| Our intended difference | Reviewed voice documentation does not establish an equivalent persistent photorealistic companion offering | Consistent character, visible editable relationship memory and approved adult mode |

[Official ChatGPT prices](https://learn.chatgpt.com/docs/pricing), [voice documentation](https://learn.chatgpt.com/docs/features/voice). These describe customer pricing, not OpenAI's internal cost or profit; those were not established. API prices are a different product. Do not turn ChatGPT's subscription into an invented per-minute rate or claim we beat its intelligence/voice quality.

## Cloudflare-first or lowest-cost?

**Start the clean prototype with Cloudflare text, speech and safety models, plus one GPU solely for MuseTalk.** This matches the preference for fewer model services and isolates the hardest test: the face. Move speech/language onto the GPU only if measured quality, utilization and savings justify it. Adult traffic requires a separately permitted local route; Cloudflare infrastructure permission does not authorize every hosted model.

| Call implementation | Estimated 30 / 60 min cost | Pricing implication |
|---|---:|---|
| Cloudflare voice + static portrait | $0.93 / $1.86 | Cheap voice product; not animated FaceTime |
| Cloudflare voice + GPU face | $2.43 / $4.86 | At current $24.99/$49.99 plans, contribution falls to 45.1%/44.1% |
| Local language/voice + GPU face | $1.55 / $3.11 | Current plans model 52.1%/54.6%, but shared-GPU performance is unproven |

If the Cloudflare-heavy route wins, **$29.99/60 minutes and $59.99/180 minutes** would model 51.2%/50.4% contribution under the same assumptions. These are conditional alternatives, not additional tiers. The $59.99 option is 30.6% cheaper than the lowest listed Chaturbate private category and 86.1% cheaper than the 30-token example at full use; the $29.99 option is actually 4.1% more expensive than the cheapest category. Do not advertise savings universally. Keep the existing prices only if the lower-cost route passes its test.

## Why choose one over another?

These are hypotheses to validate with users, not survey findings.

| Choice | Why someone might prefer it | Why they might choose something else |
|---|---|---|
| Amorien | Same fictional character, explicit editable memory, predictable private-call allowance, permitted customization | Simulated relationship, animation defects, limited actions and beta hours; less general utility |
| ChatGPT | Broad assistance, established voice experience, $20 Plus entry price; may already be subscribed | The reviewed product is not the same photorealistic fictional partner experience |
| Human performer | Real person's presence, agency, spontaneous movement and interaction | Private time can be expensive; availability and individual boundaries vary |

Our strongest hypothesis is persistent personalized companionship, not replacing human performers or beating ChatGPT on general intelligence. Ask testers which experience they would pay for after trying both; measure repeat use and cancellations, not just visual novelty.

## Where the price advantage could exist

Against **Chaturbate private shows**, Together's fully used allowance is about **42% cheaper than the 6-token/minute category** and **88% cheaper than a 30-token/minute example**, using the published wire token valuation. See the [dollar tables and funding caveat](ECONOMICS.md). Public viewing can be free, and real performers offer something an AI cannot reproduce merely by lowering price.

Our modeled 60-minute call costs **$3.11 at 50% billable GPU utilization**, or **$7.61 at 20%**. Proposed recurring contribution is roughly **52–55% at full allowance** in the baseline; this is before fixed costs, acquisition and tax, not net profit. A warm worker with few users can lose money. Launch scheduled beta hours, not an always-on fleet.

## What “realistic FaceTime” actually means

Use precomputed original character motion, streamed speech and lip-sync. The character can listen, speak, smile and interrupt naturally if the implementation succeeds. This does **not** establish arbitrary body movements, physical interaction, live undressing, or unrestricted requests. Offer cinematic actions as separate bounded clips only after testing speed, identity, licensing and permitted content.

**Next decision:** fund one capped GPU benchmark. Admit ten verified adult testers only after 30/60-minute tests show stable identity, p95 response ≤1.5s, ≥25fps, ≤100ms audiovisual skew and cost ≤$0.055/minute. If those fail, keep avatar calls experimental and test voice/text. Exact components: [BUILD](BUILD.md). Launch eligibility: [USA](USA.md).
