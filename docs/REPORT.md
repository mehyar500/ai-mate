# AI Mate: current MVP decision

Build on the existing code and deliver a PWA. The immediate goal is a convincing video call with consistent appearance, natural speech, responsive movement and low latency. The intended commercial audience is verified adults, including nudity where lawful and permitted. The running demonstration is neutral; public eligibility is unresolved.

## Current measured demo

The RTX 4060 Ti 16GB / 48GB RAM PC runs Text, Voice and Video through one engine. Calls accept speech or compact typed commands, preserve local memory and can send an in-app message without ending the call. Reviewed full-body and closer footage preserves position through conversation, approach/return and interruption. Both known poses now have a separate right-hand wave; arbitrary fresh movement remains unsolved.

Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` plans conversation. Whisper Base English and Kokoro `af_sarah` use the local GPU; MuseTalk uses the reviewed TensorRT decoder. No new API key or GPU rental was needed.

Text and Voice now explain that body movement needs Video instead of claiming a suppressed action happened. Six real-engine/browser checks passed across all three modes, including navigation away from an active call and back. Three generated WAVs were nonzero/unclipped; all 40 new video frames were analyzed and visually inspected. The preview restarted in 30.878s with saved memory unchanged.

The current six-source configuration completed **30 minutes / 132 commands**. There were no failed commands, page errors or reported reply-buffer stalls. The call remained connected; cycle speech medians stayed between 1.77 and 1.88 seconds.

| Current sustained test | Measured result |
|---|---|
| Speech end to synchronized playback | **1.77s median / 2.53s p95**, 60 noninterrupted spoken replies; target p95 <=2s remains unmet |
| Spoken prepared movement | 1.52s median / 1.56s p95, 30 replies |
| Spoken model-planned conversation | 2.22s median / 2.57s p95, 30 replies |
| Visible playback | Approximately 19.93 FPS replies / 24.07 FPS listening; no continuous gap >250ms |
| Browser A/V clock skew | 24.11ms p95 / 34.62ms maximum, 4,003 samples |
| Offline lip-sync diagnostic | Six first/final-cycle clips estimated 0 or -40ms; injected-delay and reversed-audio controls passed |
| GPU memory | 7,306.5MiB highest sampled whole-GPU usage, 360 samples; includes other processes and is not an exact peak |

All **132 clips / 5,716 frames** received face, brightness, frame-change and decoded-audio diagnostics. Six palm/face-count flags remain. Every WAV was nonzero and unclipped. This is synthetic browser capture on localhost, excluding physical acoustics, public networks and real mobile devices. The table uses the midpoint median; raw browser JSON also retains its nearest-rank p50 of 1.56s.

A new pinned, offline body diagnostic evaluated all 5,716 sustained-call frames and all 948 frames of the prior short qualification. It retained 96 and 16 uncertain frames respectively. All flags and nearby hand frames were visually inspected: 114 sustained-call frames and 19 short-call frames. One figure remains visible where the detector reports two people; the lowering hand remains blurred. Black-frame and left/right-mirror controls passed. Its fixed skeleton cannot certify anatomy or count extra limbs.

**211 Python and 32 JavaScript tests pass.** [LOCAL_POC](LOCAL_POC.md) is the consolidated setup/test runbook; machine evidence preserves earlier successes and failures. Physical speaker/microphone tests, normal-speed visual acceptance and real mobile/PWA behavior still need device evidence.

## What is still missing

Fresh rendering fits the local GPU, but command fidelity still fails. LongLive 2.0 5B with MG-LightVAE v2 produces about 11 FPS at four steps. Reducing the original checkpoint to two steps reached **16.16 generated FPS / 1.96s first chunk**. The separately trained NVFP4-S2 checkpoint, unpacked into BF16 for this GPU, reached **15.93 FPS / 2.10s**, using **14.89GB peak tensor allocation**. Both fail right-hand-only control. S2 also drifts closer until the feet leave frame. Its 27.34s model load includes 24.85s weight conversion; warm chunk timing excludes that startup and is not command-to-correct-action latency.

RAIN was tested and rejected for full-body calls: **2.75–2.76 generated FPS**, with distorted anatomy and clothing under both moving and static body controls. Face-only controls improve appearance but remove body guidance. None of these candidates is selected in the app. All frames of their short samples were inspected; speech, live input and browser transport were absent. The original **Wan2.1-VACE-1.3B** now follows a generated right-arm raise/hold/lower trajectory in a 33-frame test, but takes **205.55s**. Transferring the **rCM Wan2.1 T2V 1.3B** generator reduces this to **26.02–26.18s / 1.26–1.27 generated FPS**, with **9.63GB peak tensor allocation**. Conditioning the unchanged background restores more of the reference patio and plants; opening padded areas keeps the hand visible but leaves a flat right-edge strip. All 132 frames across four variants were inspected and received independent pose diagnostics. These are silent offline pose tests, without language input, streaming or call acceptance. A later 256x384 test using the approximate TAEW2.1 encoder/decoder produces a one-second right-arm segment in **1.34s at two steps**; a complete 2.06-second raise/hold/lower takes **2.33s**. One step reaches **18.40 generated FPS**, but visibly damages the face and hand. Across 135 newly reviewed frames, blur and hand clipping still fail acceptance. Incremental decoding now works with isolated state and about 7.5ms warm first-frame delay on already generated latents; continuous generation remains unimplemented. The next test targets temporal continuity and responsive control, not more decoder optimization. Scope's streaming integration was excluded because its checked-in source license is noncommercial. LOCAL_POC records evidence, setup and limits. No GPU rental or paid rendering API was used for these experiments; electricity cost is unmeasured.

- Warm end-of-speech p95 <=2 seconds, including endpoint detection and actual capture.
- Reliable fresh movement outside the small supported action set.
- Natural appearance throughout every transition and stronger close-view lip quality.
- Complete perceptual review of the retained sustained-call media, including natural movement and audible speech on a real device.
- Physical speaker/microphone echo testing, perceptual A/V alignment within 100ms and real mobile PWA evidence.
- WebRTC integration and public-network qualification, Linux/GPU deployment, account isolation, public access controls and accepted billing.

The local HTTP/MSE demonstration is not a deployed WebRTC service. Prepared gestures are useful measured progress, not proof of arbitrary real-time generation or a production-ready product.

## Infrastructure decision

Keep the local rig and compare one capped **RTX 5090 32GB, 8 vCPU, 64GB RAM, 150GB disk** rental. The observed US TensorDock offer is **$0.7425/hour**, about **$7.43 for ten test hours** before extras. Its uptime warning limits this recommendation to a benchmark. The 24GB RTX 4090 alternative is $0.6395/hour with the same selected resources.

Prefer Cloudflare for the PWA/control plane and evaluate its Realtime SFU for WebRTC transport. Run continuous visual inference on a warm GPU session, preserving state across turns. Queue expensive scene/clip preparation separately. More VRAM is a capacity choice; only an identical end-to-end test can establish a speed improvement.

No GPU was purchased or rented. No host has approved this project's intended service. LTX's published restrictions exclude the intended explicit scope, so the current preparation pipeline cannot be declared the adult production stack. Model licenses, assets, host policies and processor acceptance are separate gates. [BUILD](BUILD.md), [USA](USA.md).

The pinned causal rCM candidate was audited on CPU. Its generator tensors transfer exactly, but its forward interface exposes KV-cache state without VACE control inputs, so it is rejected as a drop-in until an adapter is built and visually qualified.

## Economics and next actions

The optional technical pilot is approximately **$28.93 / $14.23 / $14.23** over three months, with a **$57.38** unrounded-total forecast. It includes the existing Gateway credit purchase, ten rented GPU hours per month, local electricity and a stopped-storage allowance. These are planning assumptions under the $100 cap, not new purchases or a public-launch budget.

Under explicit cost/fee assumptions, test video packs at **$5.99/30 minutes** and **$9.99/60 minutes**, targeting roughly 52–53% contribution before fixed expenses. Validate willingness to pay and actual fulfillment costs; no guaranteed first-month profit.

CCBill is the first adult-business processor to request a quote from. Its published US/Canada annual card registration alone totals **$1,950**; actual AI-service acceptance, processing fees, reserves and payout timing require underwriting. No verified zero-upfront paid launch exists in this plan. Segpay is an alternative with specific AI-site requirements. [ECONOMICS](ECONOMICS.md) provides sources, formulas, utilization sensitivity and limits.

Shorter planner prompts and sparse JSON reduced component latency but lost name direction or fact updates. They were rejected; the original prompt remains selected. LOCAL_POC records the bounded comparisons.

Next: reduce endpoint/dialogue/speech delay, improve close-view quality, test actual audio/mobile behavior and compare the same workload on the capped rental if the founder elects to provision it. Keep five core documents. Founder owns provider/processor/jurisdiction decisions; independent security/correctness review and staging remain pending before public release. Work on main as authorized and preserve secrets and local memory.
