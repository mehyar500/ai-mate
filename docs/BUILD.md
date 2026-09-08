# Build the smallest useful companion

This is a proposed implementation contract, not completed software. The runtime must pass provider and state eligibility in [USA](USA.md), then measured quality/cost gates.

## Models and rates

| Stage | Exact model/service | Published rate or planning allowance |
|---|---|---|
| Conversation and summaries | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | $0.051/M input, $0.335/M output tokens |
| Text guard | `@cf/meta/llama-guard-3-8b` | $0.484/M input, $0.03/M output |
| Original curated portrait | `@cf/black-forest-labs/flux-2-klein-4b` | $0.000287/output 512px tile; 1024px four tiles $0.001148, input charges extra |
| Free recorded reply | `@cf/myshell-ai/melotts` | $0.0002/generated audio minute |
| Incoming notes and phone ASR | `@cf/deepgram/flux` | $0.0077/input audio minute |
| Phone-call speech | `@cf/deepgram/aura-2-en` | $0.03/1,000 characters |
| Paid portrait clip | fal `fal-ai/flashhead`, FlashHead Lite + bundled ElevenLabs | $0.005/output second; exact ElevenLabs model version not published |
| Memory | D1 confirmed facts + summary + recent turns | No separate embedding model in MVP |

Sources: [Cloudflare pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [MeloTTS](https://developers.cloudflare.com/workers-ai/models/melotts/), [fal schema](https://fal.ai/models/fal-ai/flashhead/api). The catalog snapshot has no video-output model; Cloudflare cannot supply this entire pipeline. Prices do not imply permission for every content category.

Preview the actual voices: MeloTTS, Aura and fal's bundled voice may sound different. Do not promise identical voice identity across channels. If users reject the mismatch, unify an approved voice pipeline before launch or remove the affected feature.

## Infrastructure

Cloudflare Workers serves the web app/API; D1 stores account-scoped memory and entitlements; R2 holds private portrait/clip assets; a Durable Object serializes each account's spending; Queues coordinates jobs; SSE reports progress. Cloudflare Realtime SFU/TURN carries phone audio. Recorded clips use private HTTP delivery, not live WebRTC transport. No user camera in MVP.

Use fal's hosted model API first for approved non-explicit clips: no personally rented idle GPU. Its custom serverless hosting has different idle/setup billing. [Model billing](https://fal.ai/docs/documentation/model-apis/pricing), [custom serverless billing](https://fal.ai/docs/documentation/serverless/pricing).

Runware custom compute is an optional beta route, requiring access and a measured container. Candidate weights: `Soul-AILab/SoulX-FlashHead-1_3B` Model_Pro, with `facebook/wav2vec2-base-960h` and the pinned model bundle's required VAE. There is no verified Runware FlashHead endpoint identifier. Budget RTX PRO 6000 at $0.000553/second; model loading classification needs confirmation. Zero active workers can mean zero compute, but storage, Workers, monitoring and held-warm capacity remain billable. [Compute offer](https://runware.ai/serverless/compute).

## A-to-Z request journey

1. Adult account gate and consent; choose one of three original characters and preview its actual voice. Optional introduction: alias, interests, conversation style and an upcoming event.
2. Confirm saved facts. First visit knows only supplied information; never scrape personal data or imply omniscience.
3. Load account-scoped profile, relevant confirmed facts, rolling summary and recent turns. Bound total prompt to 4,096 tokens, including instructions and guard-relevant context.
4. For a text/voice note, check allowance and length. Transcribe audio, guard input, call Qwen, guard output, stream text. Optionally generate a recorded MeloTTS reply up to 15 seconds. Cache the audio so replay does not regenerate it.
5. For a paid feature, show exact units/price. Approved hosted checkout creates a server-verified payment event; signed events are deduplicated. Browser redirects never grant credits.
6. Atomically reserve the call allowance or clip credit and provider budget. Duplicate requests reuse a job ID. Reject insufficient balance before inference.
7. Phone: establish audio transport, stream ASR, detect turn end, retrieve bounded memory, stream Qwen text into Aura, play audio. Barge-in cancels stale generation. Meter connected seconds; disconnect at exhaustion or inactivity timeout.
8. Clip: Qwen produces a brief script using only provider-permitted data. Send the original portrait and sanitized script to fal. Do not send the entire history or sensitive facts. Track job status, inspect output and deliver a private expiring URL.
9. Validate clip identity, lip sync, speech and policy. Charge once on successful delivery; restore user credit on failure. Successful but unusable vendor generations may still cost us. Allow at most two attempts within a job budget.
10. Save a bounded conversation summary and suggested facts. Confirm meaningful new personal facts before persistent storage. Returning greetings retrieve relevant events and the last topic.
11. Support correction/deletion, cancellation, refunds and reconciliation. Deleting a fact removes dependent summaries/cached prompts; expired assets are cleaned up.

## Memory that earns trust

Store facts with account ID, source turn, confirmation status, timestamp and optional event date/time zone. Keep an initial eight confirmed facts, a short summary and up to ten recent turns; truncate by token budget, not just turn count. Summarize every ten turns or after a call, within the text budget. Retrieval uses SQL initially.

Example: 'You mentioned an interview Tuesday. How did it go?' If the date is uncertain, ask rather than inventing an outcome. Separate preferences from inferred health, sexuality or other sensitive traits; do not silently infer/store them. Users can export, correct, forget or disable memory. No raw call recording by default. Returning continuity is useful; claiming to know everything is false and intrusive.

## Cost derivation and latency targets

Free spoken playback: 150 x 15 seconds = 37.5 minutes, about $0.0075 in MeloTTS charges. Five ASR minutes cost $0.0385. At 4,096 input and 100 output tokens per exchange, 150 text exchanges cost about $0.0364 before guards/summaries. Reserve $0.25/free account/month including memory and overhead. Paid 500 exchanges and 125 playback minutes reserve $0.60. These budgets require measurement; no unlimited context or free-user growth.

Phone planning example per connected minute: three 4,096-token prompts and 100 total output tokens cost about $0.00066; 450 spoken characters cost $0.0135; one minute ASR $0.0077. Guards, transport, summaries and buffer fit within a proposed $0.05/minute budget, subject to measurement. Thirty minutes uses approximately 368,640 input/3,000 output tokens; sixty uses 737,280/6,000. Listening time still incurs transport and possibly ASR charges.

Phone target: end-of-speech detection 250–500ms, first text 100–300ms, first audio 100–300ms, transport/playback 100–200ms. These are engineering allocations, not vendor SLAs or independently additive p95 values. Require measured end-of-user-speech to first-audible-reply p95 <=1.5 seconds. Measure barge-in separately.

A 15-second clip is output duration, not delivery time. Target median <=10 seconds and p95 <=20 seconds from submission to playable result, including first request after idle. fal's example is not a production percentile. The text endpoint determines duration from generated speech: constrain script length, meter actual output duration and trim delivery if needed; trimming does not remove provider charges. Do not advertise fast 15-second delivery before benchmarks pass.

Budget $0.15 per usable clip: $0.075 generation + $0.01 other costs, divided by 85% usable rate, plus 25% buffer = $0.125, rounded upward. Reject or restore credit if the promised deadline fails. Do not retry indefinitely. A custom Pro model may be slower even if GPU cost is lower.

## Later live video, disabled

Candidate: FlashHead Pro + local `Qwen/Qwen3-8B`, `Systran/faster-whisper-small`, `hexgrad/Kokoro-82M`, `snakers4/silero-vad`, required pinned audio encoder/VAE, WebRTC output. Commercial eligibility must include all weights, voices and dependencies. [FlashHead](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B).

Previous TensorDock scenario: two RTX 5090s at a combined $3.30/hour plus $1.20/hour auxiliary compute; at 50% billable utilization, compute alone is $4.50/30 paid minutes. Prior all-in delivery estimate $5.69 requires remeasurement. Indicative $59 clean / $129 high-risk per 30 minutes must also cover startup, support and overhead. Hourly rentals are not scale-to-zero serverless; do not promise instant calls without paying for warm capacity.

Reject the default eight-H100 `Quark-Vision/Live-Avatar` + `Wan-AI/Wan2.2-S2V-14B` route: prior delivery scenario ~$24.69/30 minutes requires roughly $360 price for 300% direct return under 18% fees plus $0.50. Keep it a historical comparison, not MVP infrastructure.

## Release evidence

Test 100 clips across the three characters, first-after-idle and concurrent requests, with actual billed seconds, duration, acceptance and p50/p95 latency. Test phone interruption/disconnect and full allowance redemption. Verify cross-account isolation, deleted memory, forged/replayed payments, duplicate jobs, provider timeout, cancellation, refund ordering and spending caps. Do not enable paid flags until these pass with approved providers. Existing offline tests validate economics only.
