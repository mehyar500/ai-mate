# Local proof first, commercial pilot later

Decision updated September 8, 2026: test on the founder's existing **RTX 4060 Ti with 16GB VRAM and 48GB RAM before using remote inference**. The founder is the only engineer. Build evidence for a future demonstration and funding conversations; do not finance a public commercial pilot yet.

The additional [LOCAL_POC](LOCAL_POC.md) document is the active technical plan. There are now six active product documents, as requested. It records hardware, exact candidates, benchmark commands, observed failures and successes, and acceptance targets for a realistic local portrait call.

## The cheaper approach

Keep a small instruction-following LLM on the GPU, run speech on the CPU, and use the remaining VRAM for a single portrait renderer. Prepare the character and scene before the call, then reuse valid scene/face representations while generating the speech-driven visual changes. Do not run a large image/video generation job for every conversational turn.

The earlier batch-delivery path ran: dialogue and the portrait renderer share the GPU; speech runs on the CPU. Final selected-stack warm trials delivered speech after 1.5–2.2 seconds from typed input. The ten-minute video run delivered completed portrait replies at a median of 3.79 seconds and empirical p95 of 5.10 seconds. These server timings exclude browser playback. The visual target remains unmet: the head/body are still and generation is slightly below the 25 FPS output rate. See LOCAL_POC for sample counts, sustained-run results and rejected experiments.

Current interaction is text to voiced video; the hosted-dialogue/local-graphics adapter is implemented but awaits an API key. Installed local stack: Qwen3.5-9B Q4_K_M; Kokoro-82M float32 on CPU; faster-whisper Base English int8 on CPU; MuseTalk 1.5 with SD VAE/Whisper-tiny and YuNet; FLUX.2 Klein 4B for separate scene preparation. FlashHead remains deferred. Exact model revisions and licensing boundaries are in LOCAL_POC and BUILD.

## Budget now

No cloud GPU, new card/dock, new paid subscription, paid engineer, merchant account or public deployment is purchased. Downloads use existing internet; the models run locally. Existing disk and coding tools are already available.

| Incremental planning allowance | Month 1 | Month 2 | Month 3 |
|---|---:|---:|---:|
| Estimated extra electricity | $6.00 | $1.80 | $1.80 |
| Remote inference / new paid software / payroll | $0.00 | $0.00 | $0.00 |
| **Planned expense** | **$6.00** | **$1.80** | **$1.80** |

Power assumption: extra 300W at $0.20/kWh for 100/30/30 hours. Neither wall power nor the actual tariff has been measured. Add one $75 contingency pool for the quarter: **$84.60 total allowance, rounded to a $100 planning cap**. The reserve is not a required purchase. Founder living costs, existing internet/subscriptions and the already-owned computer are outside incremental spending. See [ECONOMICS](ECONOMICS.md).

The previous $12,096.50 scenario was a conditional funded commercial pilot and already excluded engineering payroll. It is preserved only as deferred calculator data. It is not the price of this local experiment. Required future legal, payment and public-access work is deferred by stage, not declared free or unnecessary.

## Smallest useful demonstration

One original fictional adult companion, one synthetic profile and a few permitted photorealistic scenes. The intended demo shows real dialogue, a user-confirmed fact saved locally and recalled after restart, local speech, honest scene preparation and whatever visual behavior actually passes testing. Label each part live, prepared or unimplemented.

No public adult beta, customer payments, automatic check-in service, growth funnel, custom identity system or production WebRTC scaling in this stage. Begin with founder-operated loopback tests. A later non-explicit screen share/recording can demonstrate the product interaction while separately disclosing unresolved adult capability and commercial eligibility. A local browser app is available at http://127.0.0.1:8765 after starting `scripts/start_local.ps1`. It has a manifest but has not been validated as an installed mobile PWA or a continuous FaceTime-like call.

## Current decision and next work

The original character, prepared settings, persisted user facts, typed/recorded input, speech and generated portrait replies are integrated. Synthetic HTTP tests and frame inspection demonstrate the pipeline on the existing hardware. CPU/GPU allocation therefore has evidence; a commercial experience does not yet.

The current browser revision has been tested in the actual preview: one phone-style screen, text-driven scene changes, streamed video/voice, sound control and interruption. Microphone input was removed at the founder’s request. Two final browser video samples started after 2.63 and 2.56 seconds with zero buffer waits. Mobile behavior, long sessions and subjective lip-sync quality remain unqualified. Keep this as a founder-operated local prototype.

The next technical decision is whether short portrait replies are useful despite static head/body and several seconds of delay. If they are, improve bounded incremental delivery; otherwise evaluate a licensed motion model. Do not buy a new GPU or rent remote capacity merely to hide an unmeasured bottleneck. The two-second synchronized-response goal remains a research target, not a sales promise.

## Business and adult requirement

Adult content remains mandatory for the eventual commercial product. Neutral local performance tests do not prove intended adult quality or legal eligibility. ADULT-01 capability, ADULT-02 commercial rights/providers, ADULT-03 access/privacy controls and ADULT-04 measured fulfillment costs remain open before paid launch. See [USA](USA.md).

Future prices remain concepts: $19.99/$29.99/$49.99 monthly, with earlier roughly 63% direct contribution hypotheses. There is no checkout, entitlement promise or revenue forecast in this local stage. The full local result must determine which features can be sold and at what measured cost. Local electricity alone is not a hosted-service cost estimate.

For funding conversations, prepare a rights/provider matrix, local cost/latency evidence, an honest demo and specific unbuilt risks. Aim for 10–15 customer-discovery interviews about value and price without delivering restricted content or collecting payment. Interest, meetings and a waitlist are not sales or guaranteed funding. Ask for funding tied to demonstrated remaining needs after the local test.

## Scope and evidence

Latest refinement source revision `cd38325`; the founder authorized work directly on main. Owned paths: `local_app/`, the local model/runtime configs, setup/benchmark/integration scripts, `tests/test_local_app.py`, `.env.example` and the existing active product documents/evidence. Pre-existing changes to agent contracts, routing, AGENTS.md and SOUL.md are outside this task and remain untouched.

52 offline tests pass across economics and local persistence, input validation, single-job behavior, cancellation/reset, HTTP origin/token/file boundaries and media delivery. Real model integration and a completed 30-turn/ten-minute selected-stack video run are documented in LOCAL_POC; median first video was 3.79s and empirical p95 was 5.10s. Python syntax, JavaScript syntax, dependency consistency and whitespace checks passed before the implementation commit. Model weights, generated media and memory are ignored; no secrets are included.

This is an R2 local prototype because it handles microphone and memory data. There is no independent security/correctness review, CI qualification, staging, production deployment, production migration or public-access approval. Those release requirements remain open. SQLite is a new local-only store with an explicit reset; production rollback remains a reviewed revert. The founder owns the remaining UI/microphone and commercial-release decisions before any external launch. No remote inference, payment, purchase or new paid engineer was used.
