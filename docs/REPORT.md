# Local proof first, commercial pilot later

Decision updated September 7, 2026: test on the founder's existing **RTX 4060 Ti with 16GB VRAM and 48GB RAM before using remote inference**. The founder is the only engineer. Build evidence for a future demonstration and funding conversations; do not finance a public commercial pilot yet.

The additional [LOCAL_POC](LOCAL_POC.md) document is the active technical plan. There are now six active product documents, as requested. It records hardware, exact candidates, benchmark commands, observed failures and successes, and acceptance targets for a realistic local portrait call.

## The cheaper approach

Keep a small instruction-following LLM on the GPU, run speech on the CPU, and use the remaining VRAM for a single portrait renderer. Prepare the character and scene before the call, then reuse valid scene/face representations while generating the speech-driven visual changes. Do not run a large image/video generation job for every conversational turn.

This can reduce the amount of work substantially, but the complete visual path is still an experiment. Loading models separately is not proof they meet latency together. The local plan measures usable responses, first speech, synchronized frames, VRAM and quality. A lip-sync prototype must be labeled as such; a prepared clip must not be presented as live generation.

Current local candidates: explicitly pinned Qwen3-4B-Instruct-2507 Q4_K_M; Kokoro-82M ONNX on CPU; faster-whisper-small int8 on CPU for later microphone work. MuseTalk 1.5 is the first constrained visual comparator; FlashHead Lite is the fresh-motion challenger with unresolved dependency rights. FLUX.2 Klein 4B is a separate scene-preparation experiment. Model and license details are in LOCAL_POC and BUILD.

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

No public adult beta, customer payments, automatic check-in service, growth funnel, custom identity system or production WebRTC scaling in this stage. Begin with founder-operated loopback tests. A later non-explicit screen share/recording can demonstrate the product interaction while separately disclosing unresolved adult capability and commercial eligibility. There is no complete PWA or FaceTime-like application in the repository yet.

## Sequence and decision criteria

1. Verify hardware/runtime and run neutral local LLM and CPU speech benchmarks. Preserve failures rather than claiming throughput alone proves usability.
2. Build the single-profile local memory/voice flow. Test save, restart, recall, correction and deletion. Add CPU microphone recognition after typed input works.
3. Test a portrait renderer alone; record peak VRAM, first-frame delay, sustained FPS and visible defects. Audit exact model/dependency/asset rights before the intended use.
4. Run dialogue and renderer together. Target warm end-of-speech to synchronized reply p95 <=2 seconds, >=20FPS and no VRAM spill during ten minutes. These are goals, not achieved results.
5. If the combined pipeline works, assemble an honest three-minute demo plus the evidence. If it fails, reduce the model, context, resolution or tested feature and document the tradeoff. Do not rent a cloud GPU automatically.

A narrow voice/memory demo may take 3–7 focused founder days; visual integration has greater uncertainty and should be timeboxed as a separate experiment. Windows/CUDA dependency compatibility, licenses and visual quality may prevent a pass. No guaranteed development date or complete visual capability is asserted.

## Business and adult requirement

Adult content remains mandatory for the eventual commercial product. Neutral local performance tests do not prove intended adult quality or legal eligibility. ADULT-01 capability, ADULT-02 commercial rights/providers, ADULT-03 access/privacy controls and ADULT-04 measured fulfillment costs remain open before paid launch. See [USA](USA.md).

Future prices remain concepts: $19.99/$29.99/$49.99 monthly, with earlier roughly 63% direct contribution hypotheses. There is no checkout, entitlement promise or revenue forecast in this local stage. The full local result must determine which features can be sold and at what measured cost. Local electricity alone is not a hosted-service cost estimate.

For funding conversations, prepare a rights/provider matrix, local cost/latency evidence, an honest demo and specific unbuilt risks. Aim for 10–15 customer-discovery interviews about value and price without delivering restricted content or collecting payment. Interest, meetings and a waitlist are not sales or guaranteed funding. Ask for funding tied to demonstrated remaining needs after the local test.

## Scope and evidence

Source revision `6d6ac63`; changes cover six product documents, planned environment settings, economics and local benchmark scripts. The founder owns implementation, evidence and spend tracking. Local component tests use synthetic neutral inputs; model weights, Python environment and generated media remain ignored. No cloud inference, deployment, payment or purchase was made.

Validation: 29 unit tests pass, covering arithmetic, invalid inputs, budget caps and generated-report consistency; Python syntax, whitespace and six-document local links pass. Local inference evidence is described in LOCAL_POC with its limitations, including a failed model selection and a corrected speech-runtime version. There is no staging or independent production review and no production migration. Rollback is a reviewed revert; the planning cap is not an implemented spend controller.
