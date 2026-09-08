# Photorealistic companion: decision report

Research checked 7 September 2026 US Eastern (8 September UTC). **Build a fictional person who looks filmed by a camera: natural skin, eyes, lighting, head and upper-body movement, with continuously generated video.** Remove the old MuseTalk/motion-loop design. Research papers call these systems “avatars”; that does not mean cartoons. No animated illustrations, puppet rig, prerecorded listening loop or mouth-only replacement satisfies this brief.

## The decision

Use **Cloudflare for the application, clean conversation and WebRTC; self-host video on TensorDock, conditional on hardware availability and intended-use approval**. The best documented heavier reproduction baseline is **Alibaba Quark LiveAvatar v1.1 + Wan2.2-S2V-14B**. First challenge its economics with **SoulX-FlashHead Pro**, which is narrower in framing but generates photorealistic video. Reject it if it looks like a talking photograph. Neither has been run in this repository.

This is a buildable research integration, not an existing turnkey service. A realistic face does not establish reliable arbitrary actions, flawless hands, perfect identity over an hour, or unlimited permissible content. A selected model must pass the user's visual standard before sale. The former $3.11/hour estimate depended on a different rendering approach and is retired.

## Which video models are actually useful?

Publisher figures below are not our measurements or equivalent hardware benchmarks.

| Model | Released evidence | Advantage | Limitation / decision |
|---|---|---|---|
| Alibaba Quark **LiveAvatar v1.1**, 14B | Code and LoRA released; real-time TPP uses five GPUs. Current repository reports 45+ fps on multiple H800s; older model card says 20 fps. | Continuous diffusion and long-duration generation; main quality reproduction baseline | Five-GPU pipeline, potentially eight-GPU rental. 48GB FP8 fit does not prove single-GPU real time. Browser conversation integration remains work. |
| **SoulX-FlashHead Pro**, 1.3B | Code/weights released; publisher reports >25 fps on two RTX 5090s with SageAttention; 10.8 fps on one 4090 | Most useful lower-cost quality challenger | Talking-head scope; no proof of broad body/action control. Public streaming demo reads a complete audio file, creates MP4 segments, and supports one GPU. Two-GPU live input/WebRTC still needs engineering. |
| **SoulX-FlashHead Lite**, 1.3B | Publisher reports 96 fps on one RTX 4090 and three real-time streams | Cheapest diffusion baseline; test one call first | Lower quality; do not assume batching, long-call stability or sufficient realism. Not the chosen paid experience without visual acceptance. |
| **GAIR LiveTalk-1.3B-V0.1** | Released Apache-2.0 weights; paper-level 24.82 fps / 0.33s first frame | Text/image/audio conditioning; promising action control | Released inference explicitly lacks streaming input/output and emits 16fps video. 20GB fit is not evidence of live service. Research challenger only. |
| **SoulX-FlashTalk-14B** | Released code/weights; README requires eight H800s for real-time inference | Larger streaming model | Four-GPU version still listed as forthcoming; poor initial cost fit. Audit all dependency licenses before adoption. |
| **StreamAvatar**, CVPR 2026 | Project reports two H800s, 928×704 at 25fps and 1.20s pipeline latency | Speaking/listening behavior and gestures | Deployable checkpoint/license not established in this review. Do not base launch on a paper. |
| **Wan2.2-TI2V-5B** | Released Apache-2.0 image/text-to-video model | Separate bounded cinematic clips | Generated playback fps is not generation speed; unsuitable as the continuous call engine without a different streaming implementation. |

Sources: [Quark code](https://github.com/Alibaba-Quark/LiveAvatar), [Quark weights](https://huggingface.co/Quark-Vision/Live-Avatar), [FlashHead](https://github.com/Soul-AILab/SoulX-FlashHead), [FlashHead weights](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B), [public streaming implementation](https://github.com/Soul-AILab/SoulX-FlashHead/blob/main/gradio_app_streaming.py), [LiveTalk code](https://github.com/GAIR-NLP/LiveTalk), [LiveTalk weights](https://huggingface.co/GAIR/LiveTalk-1.3B-V0.1), [FlashTalk](https://github.com/Soul-AILab/SoulX-FlashTalk), [StreamAvatar](https://streamavatar.github.io/), [Wan clips](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B).

This is the relevant deployment shortlist, not a claim to inventory every 2026 model. The full saved Cloudflare hosted catalog has 86 entries, including 18 deprecated entries, and no video-generation output model. Its image, speech and language models cannot substitute for the live renderer. AI Gateway access to another company does not bring that company's compute or terms inside Cloudflare.

## What it costs us and what customers would pay

At 50% billable utilization, one call per GPU group, full-stream speech charges and 25% contingency:

| Clean conversation + video | Our cost: 30 / 60 minutes | What this means |
|---|---:|---|
| FlashHead Lite / one 4090 | $1.63 / $3.26 | Only if the visual quality is acceptable; not a promise of premium realism |
| FlashHead Pro / two 5090s | $5.07 / $10.14 | Assumed $3.30/hour whole node, not a quote; strongest economical test |
| Quark / five H100s billed | $15.63 / $31.26 | Assumes five separately billable cards on suitable interconnect are obtainable |
| Quark / eight H100s billed | $24.07 / $48.14 | Conservative allocation case; $18.50/hour node assumption |

H100 numbers use TensorDock's advertised starting rate, not a verified US cluster quote or demonstrated H800-equivalent throughput. Exact formulas, low-utilization losses and customer comparisons are in [ECONOMICS](ECONOMICS.md).

**Recommended commercial decision:** test Pro first against Quark's visual reference. If Pro passes, test **$49.99/60 minutes and $89.99/120 minutes**, with $24.99/30-minute top-ups. At its modeled $0.169/minute clean-call cost, the subscriptions contribute approximately 53.0% and 54.6% before fixed costs. Do not publish these until the benchmark and fee quote pass.

If only the heavy Quark route meets the quality requirement, model **$99/30 minutes and $179/60 minutes**, with $89/30-minute top-ups. These deliver roughly 53% contribution in the conservative clean scenario, but are a premium niche hypothesis. They are not competitive mass-market girlfriend prices. If testers will not pay, stop that offer; do not conceal costs with an unlimited tier or quietly replace the video with loops. Adult local speech changes the cost and must be measured separately.

Free remains one static photorealistic character image, 900 clean text exchanges/month (30/day) and a voice sample. No free video minutes. Free ongoing speech is deferred until acquisition/retention evidence justifies its subsidy. Paid text: 2,000 exchanges/month. Optional five bounded clips for $9.99 only after a delivered-cost/speed test.

## Compare like with like

| Choice | Customer price / value | Why prefer it | Why choose something else |
|---|---|---|---|
| ChatGPT Plus | $20/month; general assistant and voice | Broad utility, established conversation, already subscribed | Reviewed documentation does not establish this persistent photorealistic partner product |
| ChatGPT Pro | Starts at $100/month on reviewed pricing page | Higher usage and general capabilities | Different product; do not invent a per-minute equivalent or OpenAI's internal profit |
| Our Pro-model target | $49.99/60 or $89.99/120 | Persistent original character, editable memory, predictable private allowance | 150% / 350% more than Plus; simulated person, limited scope and unproved quality |
| Our heavy-model scenario | $99/30 or $179/60 | Higher-cost visual quality if users prefer it | 395% / 795% more than Plus; not universally cheaper than human private shows |
| Human private show, Chaturbate | Example 6 tokens/min = $0.48 buyer/min; 30 tokens/min = $2.40 buyer/min | A real person's agency, presence and spontaneous interaction | Availability, boundaries and private-session expense vary; public viewing can be free |

At full use, the $89.99/120 target is $0.75/min: **56.2% more than the lowest $0.48 human example, but 68.8% cheaper than $2.40/min**. The $179/60 heavy case is $2.98/min: **24.3% more than the $2.40 example**. It is 58.6% cheaper than a $7.20/min example. These use the published wire token valuation with a $250 funding minimum; card purchases may differ. Performer payout is $0.05/token, not the customer's $0.08 reference. See the full dollar table.

[ChatGPT pricing](https://learn.chatgpt.com/docs/pricing), [voice capabilities](https://learn.chatgpt.com/docs/features/voice), [Chaturbate buyer valuation](https://support.chaturbate.com/hc/en-us/articles/360036511091-How-do-I-buy-tokens), [performer payout](https://support.chaturbate.com/hc/en-us/articles/360037125852-How-do-I-convert-my-tokens). Preference claims are hypotheses, not survey findings. Test repeat use, willingness to pay and cancellation after the novelty wears off.

## Managed realistic video comparison

**HeyGen LiveAvatar is unrelated to Alibaba Quark LiveAvatar.** It offers managed realistic video and transport. Its website lists Business $475/6,000 credits and up to 60-minute sessions; Avatar Only/LITE consumes one credit/minute. Fully used, rendering is about $0.079/min; at only 1,000 used minutes it is $0.475/min. Adding our hosted conversation and contingency gives roughly $7.82 versus $37.51 per hour respectively. Provider transport may replace our SFU, so these conservative illustrations retain a small transport allowance rather than claim an exact bill.

The website's credits differ from its FAQ (5,000 + 10 on the older Scale plan); confirm the purchasable contract. Starter/Essential website sessions are capped at 5/20 minutes, so they do not meet 30–60-minute calls. The advertised $0.01/min is a top-volume tier, not startup pricing. FULL mode uses two credits/minute and includes the voice stack; do not add our voice costs to that mode.

Adult explicit content is prohibited. Terms also restrict comparative benchmarking and competitive uses; treat this as a published-price reference, and obtain permission before a comparative product trial. It is not the adult fallback. [Website](https://www.liveavatar.com/), [credit FAQ](https://docs.liveavatar.com/docs/faq/credits), [terms](https://www.heygen.com/terms).

## What to do next

One capped technical proof: reproduce Quark, then assess Pro against the same approved original character and 30/60-minute conversation. No training, marketplace, native app or enormous model menu. [BUILD](BUILD.md) defines the implementation and pass/fail criteria; [USA](USA.md) defines the still-unresolved host, licensing and merchant decisions. This repository currently supplies a plan and offline economics, not a functioning call service.
