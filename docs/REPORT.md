# AI Mate: current MVP decision

Build on the existing code and deliver a PWA. The immediate goal is a convincing video call with consistent appearance, natural speech, responsive movement and low latency. The intended commercial audience is verified adults, including nudity where lawful and permitted. The running demonstration is neutral; public eligibility is unresolved.

## What works

The RTX 4060 Ti 16GB / 48GB RAM PC runs Text, Voice and Video through one engine. Calls accept spoken input or optional compact typed commands, preserve local memory and can send a separate in-app message while the call continues. Full-body and closer views have prepared listening motion.

Cloudflare Qwen plans replies, CPU Whisper/Kokoro handle recognition and speech, and local MuseTalk produces speech video over prepared body footage. Reviewed approach/return actions maintain position through conversation and interruption. The local preview has been restarted with the replacement approach, close listening loop and right-hand wave.

A same-latent decoder comparison removed the pronounced double-image defect by increasing the temporal window from 32 to 128 frames. The latest approach stops in a wider near view with the whole head visible. Its matching listening loop has one bilateral blink per 5.21 seconds. This improves prepared footage; it does not solve arbitrary live video generation.

The optional TensorRT decoder now runs in the preview. It reduced SD VAE batch time from **235ms to 120ms**, and four identical speech/motion renders finished **31–37% sooner**. All 259 paired frames were compared and the four worst pairs inspected. This is a measured renderer improvement on the existing GPU; the source appearance and supported actions are unchanged.

The selected decoder with four-thread Kokoro completed a **30-minute call / 120 commands**, covering movement, negation, memory, unsupported requests, interruption and in-app messaging. There were zero functional failures, browser errors or reported reply stalls. Across 54 uninterrupted spoken replies, end-of-speech median/p95 was **2.48/2.90s**, including synthetic browser capture and endpoint detection. The two-second target remains unmet. Cycle medians showed no steadily accumulating delay.

All **120 clips / 5,966 frames** were retained and analyzed, with nonzero unclipped audio and zero limited heuristic flags. Six contact sheets covering 120 frames were inspected across the first and last cycles. Those recordings retain hand blur, soft mouth detail and the previous close-view crown cropping. Browser A/V clock skew was **24.74ms p95 / 51.72ms maximum** across 3,685 samples; that does not establish perceptual lip sync.

Kokoro now uses eight CPU threads: median synthesis improved **687ms → 547ms** across the same five texts/15 samples, with correct readback. The updated 20-command call passed without reported stalls, but spoken p95 was **3.22s**; no overall latency gain is established. The new setting needs sustained-call qualification. Supertonic 3 was tested and remains unselected because long-count readback failed and its slower delivery adds video frames.

The new framing passed **20/20 commands**, including interruption and return, with no reported reply stalls. Spoken end-of-speech median/p95 was **2.46/2.90s**, across nine replies; this does not establish a speed gain. All **991 frames / 20 clips** were analyzed, and 80 approach/near-speech frames inspected visually. Whole-head framing improves; hand/skin softness, imperfect lips and a slightly worse loop boundary remain. A sustained call with the latest speech setting and footage is still required.

An offline review page provides recorded playback, exact frame stepping and exportable notes. Its browser test detects decoded speech audio and passes desktop/mobile-width layout checks. Physical sound, real mobile use and full visual acceptance remain unqualified. **148 Python and 17 Node tests pass.**

Exact revisions, benchmark commands, media hashes and continuing results are in [LOCAL_POC](LOCAL_POC.md) and its machine evidence. Keep all private conversation outside benchmark artifacts.

## What is still missing

- Warm end-of-speech p95 <=2 seconds, including endpoint detection and actual capture.
- Reliable fresh movement outside the small supported action set.
- Natural appearance throughout every transition and stronger close-view lip quality.
- Complete perceptual review of the retained sustained-call media, including natural movement and audible speech on a real device.
- Physical speaker/microphone echo testing, perceptual A/V alignment within 100ms and real mobile PWA evidence.
- WebRTC output, Linux/GPU deployment, account isolation, public access controls and accepted billing.

The local HTTP/MSE demonstration is not a deployed WebRTC service. Prepared gestures are useful measured progress, not proof of arbitrary real-time generation or a production-ready product.

## Infrastructure decision

Keep the local rig and compare one capped **RTX 5090 32GB, 8 vCPU, 64GB RAM, 150GB disk** rental. The observed US TensorDock offer is **$0.7425/hour**, about **$7.43 for ten test hours** before extras. Its uptime warning limits this recommendation to a benchmark. The 24GB RTX 4090 alternative is $0.6395/hour with the same selected resources.

Prefer Cloudflare for the PWA/control plane and evaluate its Realtime SFU for WebRTC transport. Run continuous visual inference on a warm GPU session, preserving state across turns. Queue expensive scene/clip preparation separately. More VRAM is a capacity choice; only an identical end-to-end test can establish a speed improvement.

No GPU was purchased or rented. No host has approved this project's intended service. LTX's published restrictions exclude the intended explicit scope, so the current preparation pipeline cannot be declared the adult production stack. Model licenses, assets, host policies and processor acceptance are separate gates. [BUILD](BUILD.md), [USA](USA.md).

## Economics and next actions

The optional technical pilot is approximately **$28.93 / $14.23 / $14.23** over three months, with a **$57.38** unrounded-total forecast. It includes the existing Gateway credit purchase, ten rented GPU hours per month, local electricity and a stopped-storage allowance. These are planning assumptions under the $100 cap, not new purchases or a public-launch budget.

Under explicit cost/fee assumptions, test video packs at **$5.99/30 minutes** and **$9.99/60 minutes**, targeting roughly 52–53% contribution before fixed expenses. Validate willingness to pay and actual fulfillment costs; no guaranteed first-month profit.

CCBill is the first adult-business processor to request a quote from. Its published US/Canada annual card registration alone totals **$1,950**; actual AI-service acceptance, processing fees, reserves and payout timing require underwriting. No verified zero-upfront paid launch exists in this plan. Segpay is an alternative with specific AI-site requirements. [ECONOMICS](ECONOMICS.md) provides sources, formulas, utilization sensitivity and limits.

An additional 24 synthetic Cloudflare calls compared Qwen, Llama 3.1 8B FP8 Fast and Llama 3.2 3B. Their median planner times were 0.603s / 0.596s / 0.421s. The 3B model missed one requested message; the 8B median improvement was negligible. Keep Qwen until a larger correct comparison establishes a better choice.

The shorter Whisper input is rejected: a harder 36-fixture comparison found repeated punctuation in 17 outputs and worse tail latency, despite unchanged normalized word-error rate. The scorer now checks that defect explicitly. Smart Turn v3.2 remains an unselected experiment.

Next: reduce endpoint/dialogue/speech delay, improve close-view quality, test actual audio/mobile behavior and compare the same workload on the capped rental if the founder elects to provision it. Keep five core documents. Founder owns provider/processor/jurisdiction decisions; independent security/correctness review and staging remain pending before public release. Work on main as authorized and preserve secrets and local memory.
