# AI Mate: current MVP decision

Build on the existing code and deliver a PWA. The immediate goal is a convincing video call with consistent appearance, natural speech, responsive movement and low latency. The intended commercial audience is verified adults, including nudity where lawful and permitted. The running demonstration is neutral; public eligibility is unresolved.

## What works

The existing RTX 4060 Ti 16GB / 48GB RAM PC runs Text, Voice and Video through one engine. Calls accept speech or compact typed commands, preserve local memory, and can send an in-app message without ending the call. The character occupies the call view; prepared full-body and closer footage maintains position across conversation and interruption.

Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` plans replies. Whisper Base English uses optional local GPU FP16 recognition; Kokoro `af_sarah` uses eight CPU threads. MuseTalk generates new mouth frames over reviewed body footage, with the selected TensorRT decoder. No new API key or GPU rental was needed.

The latest 20-command run passed with no functional failures, browser errors or reported reply stalls. Across nine uninterrupted spoken replies, end-of-speech median/p95 was **2.03/2.63s**. This includes synthetic browser capture and the 650ms endpoint. The two-second p95 target remains unmet; nine samples cannot establish sustained performance.

The recognition change removes redundant audio decoding and its full-process garbage collection. Across 119 fixed recordings, CPU and GPU FP16 retained the same normalized words as their previous paths, including the same four existing word errors in the harder corpus. Isolated GPU recognition reached a 31ms median on ordinary speech; that is not whole-call latency. GPU wake-up after inactivity remains measurable.

The latest improvement changes MuseTalk's face crop, preserving audio timing. Offline SyncNet checks flagged roughly 160–200ms of mouth lag in earlier full-body replies. A controlled 12-clip comparison used the same two speech recordings in both views: the selected crop scored 0–40ms offset in all four comparisons, with successful injected-delay controls. Three eligible speech clips from the subsequent real-pipeline call scored 0–80ms. These are model estimates at 40ms resolution, not human perceptual acceptance. Small faces, soft skin and mouth edges remain limitations.

All **20 clips / 978 frames** from that call were retained and analyzed, with nonzero unclipped audio and no limited heuristic flags. A/V clock skew was **24.24ms p95 / 28.71ms maximum** across 598 samples. The preceding crop comparison covered all **828 frames**, with **120 face crops** visually inspected. Clock agreement and frame heuristics do not establish natural anatomy.

Before this crop adjustment, all six paused-speech cases passed, preserving negations and corrections while cancelling three unfinished replies. Their **276 frames** passed limited diagnostics and twenty were inspected. The preceding configuration also passed a **30-minute / 120-command** call with zero functional failures, page errors or reported reply stalls. Across 54 spoken replies, end-of-speech median/p95 was **2.114/2.609s**. Cycle medians showed no accumulating delay. All **5,952 frames** were analyzed; 120 wave/approach/near-speech frames from the first and last cycles were inspected. A/V clock skew was **26.19ms p95 / 45.69ms maximum** across 3,667 samples. The new crop has the 20-command evidence above; it has not received another 30-minute run.

The preview restarted successfully with private memory unchanged. **162 Python and 23 Node tests pass.** The retained review page supports playback, exact frame stepping and notes. Physical sound and real mobile/PWA behavior still need device evidence. The economics generator now matches the document's existing GPU-recognition description; cost formulas are unchanged.

[LOCAL_POC](LOCAL_POC.md) records reproducible commands, model settings, rejected experiments and machine evidence. Private conversation is excluded from benchmarks.

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

Shortened Whisper encoder input, early planning during pauses and a 150ms playback buffer remain unselected after accuracy, timing or playback regressions. Preserve the standard encoder window and 350ms startup-buffer threshold. LOCAL_POC retains the comparisons.

Next: reduce endpoint/dialogue/speech delay, improve close-view quality, test actual audio/mobile behavior and compare the same workload on the capped rental if the founder elects to provision it. Keep five core documents. Founder owns provider/processor/jurisdiction decisions; independent security/correctness review and staging remain pending before public release. Work on main as authorized and preserve secrets and local memory.
