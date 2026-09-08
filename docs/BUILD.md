# Founder video-call demo and future native app

A single-user local app is implemented under `local_app/`. This document separates that running prototype from the deferred commercial design below. Reproduction and results live in [LOCAL_POC](LOCAL_POC.md).

## Active scope: local demo with optional remote inference

The local app binds to `127.0.0.1:8765`. Text has the composer; Voice and Video calls request microphone access when started, with mute/end icons and automatic sound playback. Opening Text keeps an existing call connected. Video uses the full height when controls fit beside it; tall phones trim side background to retain head-to-toe framing. Camera access is disabled. `local_app/engine.py` owns the shared turn flow, cancellation and memory. Cloudflare Qwen selects a bounded plan; CPU Kokoro makes speech; LTX body video and MuseTalk lips run on the local GPU. Picture fragments and a synchronized WAV reach the browser during rendering. Exact timings, failures and candidate comparisons live in LOCAL_POC.

Cloudflare is configured using API key plus email. MiniMax and Ollama remain optional adapters. Three startup settings are read from private `.env`; the model adapters pin the actual graphics/voice choices. No production payment flags or pretend deployment controls are configured.

The founder now permits remote models while minimizing credentials: prefer Cloudflare's combined AI catalog and add one GPU provider only if continuous video needs it. Cloudflare-listed Pruna motion/avatar models are the next clip candidates; they are not integrated or quality-qualified. The billing-read check works with existing key/email, but prepaid Gateway credits are unavailable. LOCAL_POC records model IDs, access evidence and the benchmark sequence; USA records content restrictions. Streaming speech/pose continuity remain engine work regardless of provider.

September 8 API trials keep Qwen selected: Granite was cheaper but slower, while GLM-4.7-Flash did not complete the current bounded planner format. Kokoro remains the voice; Aura-1, Aura-2 and Melo were benchmarked with synthetic prompts. FlashHead Lite is installed only in an isolated Windows test and reaches short-run real-time throughput, with stronger close-up than full-body speech quality. None of these benchmark adapters is automatically promoted. LOCAL_POC records every measured configuration and its limits.

The engine loads hash-matched, reviewed LTX-2.3 approach/return clips and listening loops for full-body and close views. Ordinary speech applies new MuseTalk lips to the appropriate loop; longer replies repeat its body footage. The browser keeps idle motion visible during buffering and selects the destination loop after playback. A bounded cache reuses source appearance, never generated user speech. Unknown poses use held frames. These prepared movements improve latency for a limited set of actions; arbitrary real-time generation remains unresolved.

Use the founder's existing RTX 4060 Ti (16,380 MiB reported VRAM) and about 47.7 GiB system RAM. This is an inventory result, not an inference benchmark. Run a loopback-only server and browser UI with a synthetic profile, local SQLite/file memory and an explicit reset/delete control. No public model endpoint, user signup, customer payment, camera upload or production scheduler.

Installed components include optional local dialogue `qwen3.5:9b-q4_K_M` (Cloudflare is active), Kokoro-82M ONNX v1.0 float32 (`af_sarah`), faster-whisper Base English int8, MuseTalk 1.5, SD VAE ft-mse, Whisper-tiny audio features, YuNet face detection and FLUX.2 Klein 4B for offline scene preparation. Image generation runs separately and exits before the conversation server starts. Exact revisions/assets are in `config/local-models.json` and `config/local-assets.json`. Other models in the research catalog below are deferred candidates, not the app's runtime.

SQLite stores an editable 1,200-character memory and at most 50 exchanges. The UI restores the last 12; the model receives the last four plus saved facts. Memory persistence, correction and reset are exercised in tests. It additionally retains up to 12 model-selected verbatim personal-fact excerpts, with two updates per turn and review/delete controls. It does not know facts the user has not shared. Prepared scenes stay visibly labeled; no automatic check-ins, pushes, subscriptions or WebRTC have been implemented.

Job metrics report ASR, first text, first completed media and total time; video reports rendering throughput and PyTorch memory. The UI now measures first browser playback and buffer waits; lip-sync skew, wall power and total-device peak allocation remain unmeasured. Keep synthetic benchmark evidence separate from private conversation data. Short clips can have a gap between phrases; this is not a continuous video-call implementation.

The first demo proves the interaction and selected measured components. Adult commercial capability, provider acceptance and full live visual calling remain separately unresolved. The sections below retain the model/license evidence and future paid-service contract; their always-on capacity, 25-user free cohort and paid entitlements are **deferred**, not current POC requirements. Source requirements ADULT-01 through ADULT-04 apply only to a separately approved explicit web launch.

## Distribution decision: native, non-explicit first

The revised founder goal targets an Apple-native client and Apple in-app purchases. Keep the current Windows browser prototype for model/latency experiments; native SwiftUI playback, microphone permissions, StoreKit transactions and device testing are future implementation work. Model/hosting rights remain required for the actual experience. [USA](USA.md) defines the content boundary; [ECONOMICS](ECONOMICS.md) includes Apple's fee. No native app, StoreKit entitlement service or approval exists yet. Current design work follows Apple's guidance on touch targets, readable controls, undistorted media and accessible text alternatives: 44px web controls, optional captions, keyboard-accessible settings and a persistent call/Message distinction. Native 44pt targets, Dynamic Type, VoiceOver, safe areas, audio interruption and real iPhone tests remain acceptance work. [Apple design guidance](https://developer.apple.com/design/tips/).

For any deferred explicit web scope, use a versioned evaluation rubric covering permitted dialogue/voice, imagery/scenes, consistent fictional adult identity, and the specific clips/call behavior to be sold. Record checkpoint revision, applicable terms, usable-output rate, inappropriate refusals of allowed requests, harmful-output handling, actual billed time and p50/p95 latency. No explicit prompts or generated media are stored in these public planning documents.

Proposed quality gate: at least 85% usable results across the founder-defined supported categories, with no unresolved severe age/consent/privacy failures. A finite test does not prove universal safety. Report modality-level results separately; approve adult images and adult video separately. Budget all rejected attempts. Model rights and provider acceptance must pass even when the images look convincing.

The following adult evaluation and public-service capacity material is a deferred alternative, not the native MVP. If that separate scope is later pursued, reassess licensed checkpoints, hosting and payments for it. Current neutral demos do not prove explicit capability or eligibility.

## Model evidence checked September 7, 2026

This catalog is a source-based availability and terms review, not a claim that every listed model was released in 2026. RealVisXL and Magnum are older releases still available. Separate neutral local dialogue/speech benchmarks are recorded in LOCAL_POC. No reviewed source establishes this project's complete adult experience, delivery cost or US deployment eligibility. Author claims, general demonstrations and a measured product acceptance test are different evidence levels. An NSFW label alone does not specify the supported content or quality.

| Component / exact model | Evidence found | License and decision |
|---|---|---|
| Images: SG161222/RealVisXL_V5.0 and RealVisXL_V5.0_Lightning | Author explicitly states photorealistic SFW/NSFW support; Lightning has a lower-step configuration. Stronger adult-specific evidence than the previous image shortlist, but still an author claim. | OpenRAIL++ metadata; audit exact merge/dependency permissions. Compare image quality and identity continuity before selecting either. [Standard](https://huggingface.co/SG161222/RealVisXL_V5.0), [Lightning](https://huggingface.co/SG161222/RealVisXL_V5.0_Lightning). |
| Dialogue challenger: anthracite-org/magnum-v4-12b | Published prose-oriented fine-tune and training configuration; no reviewed adult-quality benchmark. | Apache-2.0 declaration; [base Mistral-Nemo](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407) also declares Apache-2.0. Dataset provenance and intended behavior remain unverified. [Card](https://huggingface.co/anthracite-org/magnum-v4-12b). |
| Current general dialogue challenger: Qwen/Qwen3.8-27B | Official August 2026 release with general text/vision evaluations; no adult-product evaluation found. | Apache-2.0; larger than the existing Qwen3-8B budget baseline. Do not infer an adult-content qualification from general benchmarks. [Card](https://huggingface.co/Qwen/Qwen3.8-27B). |
| Scene editing: black-forest-labs/FLUX.2-klein-4B | Reference editing and approximately 13GB VRAM documented; intended adult output remains unverified. | Apache-2.0. Retain as an editing comparator, not the sole proof of adult images. [Card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B). |
| General recorded video: Wan-AI/Wan2.2-I2V-A14B | Official image-to-video demonstrations, 480P/720P. No reviewed adult-quality benchmark. | Apache-2.0; official single-GPU example requires at least 80GB VRAM. Separate offline-video cost experiment, not a live-call renderer. [Card](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B). |
| Smaller general video: Wan-AI/Wan2.2-TI2V-5B | 720P/24FPS output, consumer-GPU support; author reports five seconds of video in under nine minutes without specific optimization. | Apache-2.0. Output FPS is not generation FPS; fast delivery remains unproven. [Card](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B). |
| Portrait renderer: Soul-AILab/SoulX-FlashHead-1_3B, Model_Lite | General streaming portrait demonstrations; author reports 96FPS on RTX4090. No adult demonstration established in this review. | Apache-2.0 at top level, but bundled LTX VAE rights require separate resolution. Conditional research candidate only. [Card](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B). |
| Lip-sync comparator: TMElyralab/MuseTalk, version 1.5 | General lip-sync examples and author-reported 30FPS+ on V100. Alters a 256px face region in supplied media; does not create arbitrary body motion. | MIT code; authors expressly permit commercial use of trained model, with separate dependency terms. Supplied test media are noncommercial. Not a substitute for the requested fresh-motion experience without a scope decision. [Repository](https://github.com/TMElyralab/MuseTalk). |
| 2026 speech challengers: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice and Qwen/Qwen3-ASR-0.6B | Published speech generation/recognition; these do not establish adult dialogue quality or a complete low-latency call. | Apache-2.0 cards. Compare against Kokoro/faster-whisper; use permitted preset voices. [TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice), [ASR](https://huggingface.co/Qwen/Qwen3-ASR-0.6B). |

The research shortlist broadens to RealVisXL for image evaluation, Magnum for dialogue comparison, and Wan2.2 for separately measured recorded video. None is promoted to an approved deployment. Keep Qwen/Qwen3-8B, Systran/faster-whisper-small, hexgrad/Kokoro-82M, snakers4/silero-vad, facebook/wav2vec2-base-960h and meta-llama/Llama-Guard-3-8B as the existing budget/auxiliary candidates. Qwen/Qwen-Image-Edit-2511 remains a larger identity-editing comparator. Exact revisions, voices and dependency terms must pass before use.

Audit snapshot: RealVisXL V5.0 revision `ac93e0dda1f6d448cae19bbfab8c5e720a5e48bc`; Magnum v4 12B `3200513f4a737a1f7fa41145c373ac55f886ae35`. Their public repository metadata declares a license but neither repository lists a separate license file. [SDXL's base license](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md) permits hosted use subject to its restrictions; that alone does not resolve every fine-tune or merged component's rights. Do not substitute a random reupload or assume that permission to sell outputs authorizes every form of model hosting.

FlashHead Lite requires special attention: its authors identify an LTX-Video VAE dependency, while Lightricks' current policy expressly restricts explicit content. The exact VAE provenance and applicable historical/current terms have not been established; do not automatically apply a top-level Apache tag to that component or assume a policy applies retroactively. This is an unresolved release gate. Excluded models and terms are listed in [USA](USA.md).

## Deferred commercial deployment hypothesis

Use one selected TensorDock US provider for the inference services. Keep a warm dialogue/audio pool; launch/stop the scene and renderer worker separately. Forecast one visual session per renderer until full-pipeline tests prove concurrency. Load image editing before the call, release it, then initialize FlashHead rather than assuming image and video models coexist within 24GB.

The $0.60/hour auxiliary and $0.90/hour renderer are complete-service budgets requiring offers and load testing. Warm auxiliary pool is $432/30-day month. At scale, model capacity and replication must grow with tokens/second and peak calls; a single warm pool is a pilot assumption. Cloudflare serves the PWA, account/data plane and WebRTC; payment remains a separate approved service.

For the first capacity experiment, use separate auxiliary and visual workers at one accepted US host. Benchmark Qwen3-8B plus ASR/TTS first; do not assume that an additional 8B guard and image model fit in the same 24GB device alongside all runtime caches. If capacity requires a second auxiliary GPU, the three-month stress budget explicitly doubles that cost. Large Wan recorded-video trials use a separate 80GB worker at an assumed $2.50/hour. No paid application traffic is routed yet.

Cloudflare's neutral managed candidate is `@cf/qwen/qwen3-30b-a3b-fp8` for product FAQs or public structured operations only. Do not send companion conversations or derived intimate memory to this route. A privacy-preserving route is a data boundary, not permission to evade terms: the product and each service still need to be eligible. Budget $20/month for this neutral use until actual token billing is measured. [Official model listing](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/), [developer service terms](https://www.cloudflare.com/service-specific-terms-developer-platform/).

A controller may deallocate unused visual workers after the ready window/session ends, leaving only approved encrypted disk/cache storage. Verify the host's actual stop/delete billing behavior and capacity availability before promising scale-to-zero. Running VMs cost money while idle. Prepaid-balance monitoring must reserve enough to fulfill already-purchased usage; a zero balance or unavailable replacement GPU is a service interruption, not a free operating mode.

Owned workstation comparison is an illustrative capital scenario in REPORT, not the launch architecture. Do not purchase hardware or rent compute from these planning settings. Actual node quotes, US region, complete license manifest and account acceptance remain required.

## Persistent state

Keep four account-scoped records:

- User memory: confirmed facts, last conversation summary, upcoming events with source, date/timezone and confidence.
- Character identity: original adult reference images, permitted voice, appearance parameters and provenance.
- Fictional scene: location, outfit category, lighting, scene version and conversation continuity.
- Technical job: queued/preparing/validating/ready/connected/failed/cancelled/expired, entitlement reservation, spend cap and timestamps.

User facts are not character fiction. A sentence such as 'I'm in the bathroom' changes the fictional scene state, not a claim about a real person's location. The AI disclosure stays visible. The character only knows supplied/consented information.

Use a 4,096-token prompt cap, short summary, recent turns and relevant confirmed facts. Summarize after ten turns/end call. Confirm meaningful new facts before long-term storage; no covert sensitive-trait inference. Inspect/correct/forget/export controls invalidate derived summaries and cached prompts.

Token sizing example, not a measured conversation: two model replies/minute, each reading 2,000 input tokens and producing 60 output tokens, gives 4,000 input/120 output tokens per minute, or 240,000 input/7,200 output for an hour. At the 4,096-token input cap that input total becomes 491,520/hour. Memory updates, checks and retries add work. Self-hosted bills are GPU time/capacity, not an external per-token tariff; measure prefill/decode throughput, queue delay and peak concurrency rather than multiplying this example by an invented API price.

## Scene-to-call flow

1. User requests a call. Check age/state eligibility, account balance, character scene, host capacity and maximum generation cost.
2. Reserve a scene entitlement, not call minutes. Reuse a validated matching scene when possible; keep a small per-user cache of recent scenes with expiry.
3. If a new scene is required, send character references plus the structured fictional setting to the image model that passes evaluation. Klein is the existing reference-editing baseline; RealVisXL is a comparator, not a verified drop-in reference editor. Generate at most two candidates within the configured budget.
4. Validate original identity, adult appearance, policy and framing. Reject identity drift; a matching seed alone is not proof. Early pilot uses human-reviewed character/scene presets.
5. Warm the renderer and encode the selected scene reference. Confirm first frames and audio path before readiness.
6. Character says 'Give me a moment; I'll let you know when our call is ready.' UI shows 'Preparing your scene' and an honest estimate; do not invent a real-world cover story. Continue text while it loads.
7. Notify 'Ready to call' only after the job is ready. Keep a short configurable ready window, initially two minutes. If the user does not join, release GPU capacity; retain only the allowed scene cache.
8. User taps Join. Begin call metering only after usable media connects. Generate new synchronized portrait frames around the prepared scene. A talking portrait does not simulate arbitrary body actions.
9. On failure/deadline/cancellation, restore undelivered entitlement; record actual compute costs. Do not keep generating scenes on repeated taps or retries.
10. On hang-up, save a short summary, release reservation/capacity, expire private media according to the retention policy.

Targets to test: cached-scene preparation 1–5 seconds; a new scene on warm hardware 5–30 seconds; cold worker 30–120 seconds or longer depending on actual provider startup. These are hypotheses, not SLAs. Show the measured ETA and permit cancellation. The user's tolerated pre-call delay lets us avoid an always-on renderer.

Budget $0.10/accepted scene, $0.05/photo and $0.15/accepted portrait clip. These are existing hypotheses and do not price general Wan video. For illustration, 60 seconds at $0.90/hour costs $0.015 of node time before loading, retries, checks and other costs. All successful-but-rejected work counts. A two-minute warm-up plus two-minute ready hold costs $0.06 at this node rate even if nobody joins; scene-budget feasibility must be measured against abandonment.

Keep general recorded video in a separate queue and price contract. At an illustrative $2.50/hour, two five-minute attempts cost $0.42 compute, while two 20-minute attempts cost $1.67. Add loading, checks, rejected jobs and delivery costs; longer output may need more generation or extensions. The proposed $1.25 accepted-clip ceiling and $9.99 sale price are experiments, not Wan performance claims. No output or delivery-time guarantee is established; general-video sales are excluded from the three-month forecast. Never apply the $0.15 portrait budget to arbitrary video.

## During the visual call

Microphone -> streaming partial ASR/VAD -> concurrent memory retrieval -> Qwen first coherent phrase -> Kokoro speech -> wav2vec2 features -> FlashHead Lite -> VAE decode -> hardware H.264 encode -> synchronized WebRTC video/Opus audio.

Keep native model audio context and chunk sizes initially. Generate ahead of playback with a bounded buffer; cancel stale generations and audio/video on barge-in. Maintain independent temporal caches per session. Generate fresh listening-state portrait frames; no assumed free listening or prerecorded-loop substitution.

The [Gradio reference](https://raw.githubusercontent.com/Soul-AILab/SoulX-FlashHead/main/gradio_app_streaming.py) groups chunks into video files and starts with a completed audio file. Replace this with incremental audio and WebRTC output; removing file waits does not prove model latency. Target end-of-user-speech to synchronized reply p95 <=2 seconds on warm hardware, sustained 25FPS and limited audio/video skew. Report actual results.

FlashHead Lite's author throughput supports technical investigation; it does not establish simultaneous LLM, guard, image and video performance or adult eligibility. Use one stream until measured and licensed for the intended service. General Wan video remains a separate recorded-video experiment; it does not inherit the portrait call's latency or cost assumptions.

## Opt-in check-ins and media

Ask permission separately for check-ins, web push and proactive media. Default quiet hours; respect timezone and notification revocation. Cap paid check-ins at one/day and free at one/week, counted within text limits. Scheduler retrieves a relevant confirmed event, generates one useful message, screens it and deduplicates by account/event/day.

Media suggestions consume the selected plan allowance only if the user opted into automatic included media; never trigger an overage. Cap paid proactive media at the plan's monthly totals. Free accounts receive no recurring generated video. Reuse approved assets when appropriate without claiming they were newly generated. Avoid intimate lock-screen previews: 'You have a new message' opens the authenticated app.

Cloudflare scheduled triggers/Queues and a database outbox handle delivery/retries. Notifications are not guaranteed delivery; an unread item remains in-app. No service-worker background inference or assumption that iOS keeps the app running.

## PWA guidelines and monitoring

HTTPS, install manifest, offline shell only; never cache intimate transcripts/media or age documents in the service worker. Request microphone access after a user gesture, provide captions, mute/end controls and visible balance. User camera uploads stay disabled. Test foreground Safari, installed iOS PWA and Android Chrome; detect disconnects, suspend billing and restore cleanly.

iOS web push requires an eligible home-screen web app and permission following user interaction. [WebKit documentation](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/). A PWA does not inherently add seconds of network delay, but background behavior/device codecs require tests. No App Store listing is needed for direct website access.

Internal monitoring: per-job actual cost, latency, rejection/retry rate, queue depth, active calls, paid entitlement, free-user ceiling, notification count and settlement balance. Redact sensitive payloads; separate minimal audit evidence from private conversations. Per-account and provider spend caps fail closed before new work. Monitoring compute/storage and founder incident response are budgeted; open-source tools do not eliminate operating effort.

Before paid release test age-result replay, account isolation, scene leakage, stale memory, forged payment events, duplicate jobs, abandonment, cold start, refund order and reconnection. Current offline tests cover arithmetic plus local memory, cancellation and HTTP boundaries. They do not qualify those future production controls.
