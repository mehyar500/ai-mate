# AI Mate: current MVP decision

Build on the existing code and deliver a PWA. The immediate goal is a convincing video call with consistent appearance, natural speech, responsive movement and low latency. The intended commercial audience is verified adults, including nudity where lawful and permitted. The running demonstration is neutral; public eligibility is unresolved.

## What works

The existing RTX 4060 Ti 16GB / 48GB RAM PC runs Text, Voice and Video through one engine. Calls accept speech or compact typed commands, preserve local memory, and can send an in-app message without ending the call. The character occupies the call view; prepared full-body and closer footage maintains position across conversation and interruption.

Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` plans replies. Whisper Base English and Kokoro `af_sarah` now use the local GPU; MuseTalk uses the selected TensorRT decoder. GPU speech releases unused allocator memory between replies. No new API key or GPU rental was needed.

The revised GPU-speech configuration completed **30 minutes / 120 commands** without failed commands, page errors or reported reply-buffer stalls. Speech-end latency was **2.04s median / 2.50s p95** across 54 replies; the two-second p95 target remains unmet. This replaces an earlier failed GPU soak, whose three allocation errors remain documented.

All **120 clips / 5,945 frames** received limited diagnostics. Visual inspection sampled 120 frames from first/final-cycle clips; hand blur and soft close-up detail remain. Six lip-sync diagnostics passed their controls at estimated offsets of 0–80ms. Browser A/V clock skew was 26ms p95. These checks do not prove physical audibility, natural anatomy or human-perceived lip sync; idle callback gaps also need better classification.

The preview now uses a **two-second wave**, removing about two seconds of nearly still footage after the gesture. Its separate 20-command qualification passed; all 829 frames received diagnostics and the complete 40-frame rendered wave was visually reviewed. The 30-minute result used the previous wave, so the revised asset has short-call evidence only. Restart completed in 29.48s with saved conversation unchanged.

An isolated H.264/Opus WebRTC experiment did not establish a whole-call speed improvement over the existing fragmented-video player. Public-network transport remains unqualified.

**174 Python and 23 JavaScript tests pass.** [LOCAL_POC](LOCAL_POC.md) contains exact model settings, comparisons, retained review pages and reproduction commands. Physical speaker/microphone tests, normal-speed visual acceptance and real mobile/PWA behavior still need device evidence.

## What is still missing

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

## Economics and next actions

The optional technical pilot is approximately **$28.93 / $14.23 / $14.23** over three months, with a **$57.38** unrounded-total forecast. It includes the existing Gateway credit purchase, ten rented GPU hours per month, local electricity and a stopped-storage allowance. These are planning assumptions under the $100 cap, not new purchases or a public-launch budget.

Under explicit cost/fee assumptions, test video packs at **$5.99/30 minutes** and **$9.99/60 minutes**, targeting roughly 52–53% contribution before fixed expenses. Validate willingness to pay and actual fulfillment costs; no guaranteed first-month profit.

CCBill is the first adult-business processor to request a quote from. Its published US/Canada annual card registration alone totals **$1,950**; actual AI-service acceptance, processing fees, reserves and payout timing require underwriting. No verified zero-upfront paid launch exists in this plan. Segpay is an alternative with specific AI-site requirements. [ECONOMICS](ECONOMICS.md) provides sources, formulas, utilization sensitivity and limits.

The latest bounded Cloudflare comparison found Gemini 3.5 Flash-Lite slower than Qwen: **0.93s versus 0.58s median**, with eight correct fixture responses each. Combined nominal usage cost was about **$0.00460**, before credit-purchase fees. Qwen remains selected. This tests neutral dialogue only; provider terms and intended-content eligibility remain separate.

Shortened Whisper encoder input, early planning during pauses and a 150ms playback buffer remain unselected after accuracy, timing or playback regressions. Preserve the standard encoder window and 350ms startup-buffer threshold. LOCAL_POC retains the comparisons.

Next: reduce endpoint/dialogue/speech delay, improve close-view quality, test actual audio/mobile behavior and compare the same workload on the capped rental if the founder elects to provision it. Keep five core documents. Founder owns provider/processor/jurisdiction decisions; independent security/correctness review and staging remain pending before public release. Work on main as authorized and preserve secrets and local memory.
