# AI Mate: current MVP decision

Build on the existing code and deliver a PWA. The immediate goal is a convincing video call with consistent appearance, natural speech, responsive movement and low latency. The intended commercial audience is verified adults, including nudity where lawful and permitted. The running demonstration is neutral; public eligibility is unresolved.

## What works

The RTX 4060 Ti 16GB / 48GB RAM PC runs Text, Voice and Video through one engine. Calls accept spoken input or optional compact typed commands, preserve local memory and can send a separate in-app message while the call continues. Full-body and closer views have prepared listening motion.

Cloudflare Qwen plans replies, CPU Whisper/Kokoro handle recognition and speech, and local MuseTalk produces speech video over prepared body footage. Reviewed approach/return actions maintain position through conversation and interruption. The local preview has been restarted with the replacement approach, close listening loop and right-hand wave.

A same-latent decoder comparison removed the pronounced double-image defect by increasing the temporal window from 32 to 128 frames. The replacement sources were reviewed on the existing 16GB card. Close listening now uses one bilateral blink per 3.71-second loop with quieter background motion. This improves prepared footage; it does not solve arbitrary live video generation.

An earlier Torch-based **30-minute call completed 120 interactions** across six repetitions of the 20-command suite, with zero functional failures or reported buffer stalls. Across 114 non-interrupted responses, median playback start was **1.89s**, p95 **2.82s**. Spoken-fixture p95 was **2.83s**, excluding physical capture and the approximately 0.65s endpoint wait. The two-second target is not met. Cycle medians did not show steadily accumulating delay.

The suite covers movement, negation, memory updates, unsupported commands, interrupted movement and in-app messaging. Normal application retention removed 70 old clips before the long-call frame audit; its remaining 50 clips contain 2,469 inspected frames. Future benchmark runs archive synthetic media per turn, without increasing live-user retention. The long call therefore establishes session behavior, not complete frame-by-frame quality acceptance.

The optional TensorRT decoder now runs in the preview. It reduced SD VAE batch time from **235ms to 120ms**, and four identical speech/motion renders finished **31–37% sooner**. All 259 paired frames were compared and the four worst pairs inspected. This is a measured renderer improvement on the existing GPU; the source appearance and supported actions are unchanged.

Both TensorRT call trials passed **20/20 commands** without reported reply stalls. End-of-speech median/p95 was **2.50/3.44s** experimentally and **2.48/2.92s** through the normal runtime. Each includes nine uninterrupted spoken fixtures through browser capture/VAD; hosted variability makes these small samples unsuitable for a latency guarantee. The two-second target remains unmet. The latest trial recorded **25.11ms p95 / 32.55ms maximum** browser A/V clock skew across 614 samples. All **994** rendered frames were analyzed; 40 transition/close frames were manually inspected. Physical audio, perceptual lip sync and complete visual acceptance remain unqualified. Hand blur, close-view cropping and mouth artifacts remain. **137 Python and 17 Node tests pass.** The new decoder has not yet completed its own 30-minute trial.

Exact revisions, benchmark commands, media hashes and continuing results are in [LOCAL_POC](LOCAL_POC.md) and its machine evidence. Keep all private conversation outside benchmark artifacts.

## What is still missing

- Warm end-of-speech p95 <=2 seconds, including endpoint detection and actual capture.
- Reliable fresh movement outside the small supported action set.
- Natural appearance throughout every transition and stronger close-view lip quality.
- Complete retained-media review across a sustained call, including natural movement and audible speech on a real device.
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

Next: run the retained-media sustained trial with the selected decoder, reduce remaining endpoint/dialogue/speech delay, qualify actual audio/mobile behavior and compare the same workload on the capped rental if the founder elects to provision it. Keep the five core documents concise. Founder owns provider/processor/jurisdiction decisions; independent security/correctness review and staging remain pending before public release. Work on main as authorized and preserve secrets and local memory.
