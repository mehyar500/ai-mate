# Low-cost visual conversation: build contract

Research-backed architecture, not implemented or benchmarked. Adults-only PWA; approved self-hosted inference is the default for adult traffic. Retain non-explicit mode through the same controls. Do not send adult conversations to fal or assume Cloudflare hosted-model permission.

## Model selection

| Function | Selected model | License/evidence and limitation |
|---|---|---|
| Realistic portrait | Soul-AILab/SoulX-FlashHead-1_3B, Model_Lite | Apache-2.0 model card; authors report 96 FPS/4090. Start 512px, 25 FPS; quality must be evaluated. |
| Video decoder | VAE_LTX from the FlashHead bundle | Pin exact artifact, upstream license and notices; not interchangeable with Pro's VAE_Wan. |
| Audio features | facebook/wav2vec2-base-960h | Required by published pipeline; pin weights/license. |
| Dialogue and summaries | Qwen/Qwen3-8B, non-thinking mode | Apache-2.0; cap context/output. Commercial license does not prove adult dialogue quality or policy fit. |
| Speech recognition | Systran/faster-whisper-small | CTranslate2 runtime and Whisper-derived weights; audit both; test streaming partial transcripts. |
| Speech synthesis | hexgrad/Kokoro-82M | Apache-2.0 model; permitted preset voices only. CPU first if latency passes. |
| Turn detection | snakers4/silero-vad | MIT project; distinguish end-of-turn from brief pauses. |
| Policy classification | Local meta-llama/Llama-Guard-3-8B candidate plus explicit product rules | Separate Meta license review; benchmark taxonomy and false positives. No claim that a generic guard provides complete adult/age safety. |
| Original portrait assets | black-forest-labs/FLUX.1-schnell, offline curated | Apache-2.0 card; original fictional adults, provenance checked. Visual identity prepared before calls. |

Primary sources: [FlashHead](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B), [bundle files](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B/tree/main), [Qwen](https://huggingface.co/Qwen/Qwen3-8B), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M), [FLUX](https://huggingface.co/black-forest-labs/FLUX.1-schnell). Audit every actual runtime/weight/voice at its pinned revision. No unlicensed fine-tune or blanket permission claim.

Adult scope means the approved lawful adult product, not removing all controls. Test consent, age ambiguity, impersonation, self-harm and forbidden content handling. Off-the-shelf model behavior and realistic explicit imagery are not established here; do not sell an untested capability.

## Alternatives evaluated

| Candidate | Advantage | Decision |
|---|---|---|
| FlashHead Lite | Released streaming model, one consumer GPU, fresh portrait motion | First POC |
| FlashHead Pro | Higher-quality candidate | Later comparison; two-5090 author real-time configuration is unnecessary for first test |
| MuseTalk 1.5 | Released commercially usable lip-sync, author 30+ FPS/V100; edits 256px face region | Backup if Lite quality fails; typically relies on prepared source motion. Does not independently generate a new responsive body. No canned-loop default. |
| EmbodiedHead | Explicit listening/speaking design and live demo | Watchlist: production license/deployable bundle not established in reviewed page |
| lycui/AvatarForcing (arXiv 2603.14331) | Released checkpoints, one-step streaming research | Commercial license not established in reviewed card; do not confuse with the separate TaekyungKi project |
| Wan2.2-TI2V-5B | Apache-2.0 general video candidate | Optional later asynchronous scenes; no one-to-two-second live/full-body claim |
| Quark LiveAvatar/large diffusion clusters | More extensive generation | Exclude from cheap POC |

Sources: [MuseTalk](https://github.com/TMElyralab/MuseTalk), [EmbodiedHead](https://03skyboy.github.io/EmbodiedHead/), [AvatarForcing](https://huggingface.co/lycui/AvatarForcing), [Wan](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B). MuseTalk test assets are research-only even though its model is commercially usable; audit its VAE/detector dependencies separately.

## PWA and US topology

HTTPS PWA on Cloudflare Workers; D1 holds account-scoped memory/entitlements, R2 private assets, Durable Objects serialize spending. Cloudflare Realtime SFU/TURN carries Opus audio and H.264 video. Client microphone only; no camera upload or visual understanding in POC. Cache the shell, not intimate transcripts/media, in the service worker.

Place the renderer and auxiliary inference together in one selected US region. Avoid serial cross-country hops. Start with one US host near the recruited cohort; test both coasts before expanding. WebRTC/PWA does not intrinsically add seconds of latency. Device, RTT, inference and buffering determine response time. [WebKit WebRTC](https://webkit.org/blog/7763/a-closer-look-into-webrtc/), [Safari 26 web apps](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/).

Require a user tap to start media, microphone permission, reconnection and a browser fallback. Test installed PWA and ordinary Safari/Chrome separately. Suspend billing on detected media loss; terminate idle/disconnected sessions after a short grace period. Do not promise reliable background/locked-screen video. Use wake-lock where supported, without assuming availability.

## Streaming logic and latency

1. Prepare character portrait encoding once. Allocate per-session temporal state; never share memory or frame caches between users.
2. VAD and partial ASR run while the user speaks. Retrieve confirmed profile/last topic concurrently. Do not wait for a completed recording upload.
3. After turn end, run bounded non-thinking Qwen. Send the first coherent short phrase to Kokoro while the next phrase is generated.
4. Generate enough speech samples for the model's native chunk and audio context; TTS can create a second of audio faster than a second of wall time. Avoid arbitrary chunk shortening until quality is tested.
5. Pass chunk audio through wav2vec2 and FlashHead Lite, decode, hardware-encode frames and push directly to WebRTC with synchronized timestamps.
6. Keep next-chunk work ahead of playback with a short bounded buffer. On interruption cancel stale audio/video by generation ID and reset state as needed.
7. During listening generate fresh silent portrait frames at a tested cadence; measure mouth artifacts. Budget continuous rendering rather than assuming free listening or a talking duty-cycle discount.
8. End at allowance exhaustion, persist a short summary, release capacity, and reconcile billed/fulfilled seconds.

The [reference Gradio implementation](https://raw.githubusercontent.com/Soul-AILab/SoulX-FlashHead/main/gradio_app_streaming.py) reads a complete audio file and groups three chunks into MP4 segments. It is not our production transport. The proposed integration removes file/segment waits, but still must implement incremental audio, per-session state and cancellation. FPS measures throughput, not first response or two-session p95 latency.

Warm latency allocation: endpointing/ASR finalization 200–350ms; first phrase 100–250ms; TTS/audio preparation 100–250ms; first video chunk 250–550ms; encoding/network/playout 100–250ms. Total working budget ~0.75–1.65s, with an end-to-end p95 goal <=2s. These are allocations, not measured percentiles or guarantees. Test one stream first, then two under simultaneous speech. If the model requires more lookahead or load adds queue delay, publish the observed number and reduce admission.

Use native chunk sizes first. Do not upscale to 1080p or regenerate backgrounds per turn. Avoid long thinking traces and unbounded conversation prompts. Prefer 512px with good lighting/compression to expensive sharpening that cannot restore missing detail. No client-side neural-renderer dependency in the first PWA.

## Capacity and short clips

Author maximum is three Lite streams; forecast two at 50% occupied capacity. A $0.90/hour complete renderer then allocates $0.015/minute. Add $0.005/min auxiliary inference, $0.0008 transport and 20% contingency: approximately $0.025/min. Auxiliary costs are budgets, not evidence that the LLM, guard and two renderers fit/run fast on the same 4090. Use a separate measured auxiliary service if needed and update cost.

Clip generation reuses portrait and voice; priority is below live jobs. Fifteen output seconds = 375 frames at 25 FPS; 96 FPS implies ~3.9 seconds renderer-only on an otherwise idle benchmark GPU, not end-to-end latency. Budget $0.10 per usable clip including auxiliary work, retries and overhead; target p95 <=15 seconds after warm admission, max two attempts. If live demand prevents that, show the wait before purchase. This is a speaking portrait, not unrestricted action video.

## Memory and billing

4,096-token total prompt cap; short summary, up to eight confirmed facts and recent turns truncated by tokens. Facts have source/date and optional event timezone. First visit uses optional introductions only. Users confirm, correct, export and delete memory; deletions invalidate derived summaries. Never claim omniscience or infer sensitive traits covertly.

CCBill hosted checkout is the adult candidate. Server-validate documented events, deduplicate and reconcile; no browser redirect grants credits or invented universal HMAC. Reserve entitlement before inference; meter delivered connected time; restore on failed delivery; show price and timer. Independent review must cover cross-account access, replay, forged age proof, duplicate jobs, refunds and cancellation before release.

## Small proof of concept

Stage 1: 20–40 rented renderer hours plus auxiliary experiments, storage and network; $100–$250 technical cap, not permission to spend now. Use original clothed adult test portraits to measure the rendering mechanics privately before merchant activation. No training, no public payment collection, no app-store submission.

Stage 2: one character, microphone, editable memory and live portrait in an HTTPS browser; measure 100 turns and several 30/60-minute calls. Compare one versus two streams, cold start, simultaneous speech, listening, barge-in, iPhone Safari/PWA and Android.

Stage 3: after host/merchant/state gates, 20 verified adult pilot customers. Acceptance: >=85% usable visual ratings; end-to-end warm p95 <=2s; clip p95 <=15s; full-redemption costs within budget; no severe privacy/billing failures. If it misses, report the measured price/latency and decide whether users accept it before scaling. No fake claims of tested explicit performance.

Do not use perpetual idle GPUs in the forecast: 120 scheduled renderer hours/month cost $108 at the node assumption. The calculator adds any uncovered floor rather than double-counting allocated usage. Scale to zero outside pilot hours and show warm-up before charging; reserve warm capacity only from proven demand.
