# Scene-ready PWA: implementation contract

No app has been implemented here. This document specifies a measured prototype and release gates.

## First milestone: adult viability

Adult-content support is mandatory. Before building the product around any checkpoint, evaluate its intended lawful adult use under an accepted hosting arrangement. Existing model names are candidates, not an adult-ready deployment manifest. Do not infer adult capability from Apache/MIT licensing, a general image demo or portrait FPS.

Use a versioned evaluation rubric covering allowed adult dialogue/voice, intended adult imagery/scenes, consistent fictional adult identity, and the specific clips/call behavior to be sold. Record checkpoint revision, applicable terms, usable-output rate, inappropriate refusals of allowed requests, harmful-output handling, actual billed time and p50/p95 latency. No explicit prompts or generated media are stored in these public planning documents.

Proposed quality gate: at least 85% usable results across the founder-defined supported categories, with no unresolved severe age/consent/privacy failures. A finite test does not prove universal safety. Report modality-level results separately; approve adult images and adult video separately. Budget all rejected attempts. Model rights and provider acceptance must pass even when the images look convincing.

If Qwen, Klein or another candidate cannot support the intended adult scope, reassess the licensed checkpoint and platform before implementation. Do not remove provider safeguards, treat a noncommercial fine-tune as commercial, or replace the business with a clean-only launch. General scene generation and FlashHead talking portraits do not establish full-body explicit video generation. Until evidence exists, that capability is unresolved.

## Models and one-provider deployment

| Stage | Model | Role and constraint |
|---|---|---|
| Conversation, event extraction, summaries and scene planning | Qwen/Qwen3-8B, non-thinking mode | Candidate only: bounded dialogue and structured outputs; intended adult behavior unverified |
| Speech recognition | Systran/faster-whisper-small | Incremental ASR; audit runtime and weight licenses |
| Speech synthesis | hexgrad/Kokoro-82M | Consistent permitted preset voice across messages, calls and clips |
| End-of-turn detection | snakers4/silero-vad | Distinguish pauses from completed turns |
| Character-in-scene image/edit | black-forest-labs/FLUX.2-klein-4B | Candidate only: reference-guided editing and Apache-2.0 card do not prove required adult imagery |
| Image consistency challenger | Qwen/Qwen-Image-Edit-2511 | Evaluate only if Klein identity fails; larger/slower deployment may need a different GPU |
| Live portrait and recorded portrait clip | Soul-AILab/SoulX-FlashHead-1_3B, Model_Lite | Candidate only: portrait motion; adult scene preservation and supported framing must be tested |
| Video dependencies | VAE_LTX bundle and facebook/wav2vec2-base-960h | Pin exact revisions and all licenses |
| Screening | Local Llama-Guard-3-8B candidate plus application rules and human escalation | Generic model does not prove complete age/content safety |

Sources: [Klein 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [image-edit challenger](https://huggingface.co/Qwen/Qwen-Image-Edit-2511), [FlashHead](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B), [Qwen](https://huggingface.co/Qwen/Qwen3-8B), [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M). Commercial licensing is not a certification of lawful adult output quality. Evaluate actual approved content scope; no unlicensed fine-tunes or bypass of a provider prohibition.

Use one selected TensorDock US provider for the inference services. Keep a warm dialogue/audio pool; launch/stop the scene and renderer worker separately. Forecast one visual session per renderer until full-pipeline tests prove concurrency. Load image editing before the call, release it, then initialize FlashHead rather than assuming image and video models coexist within 24GB.

The $0.60/hour auxiliary and $0.90/hour renderer are complete-service budgets requiring offers and load testing. Warm auxiliary pool is $432/30-day month. At scale, model capacity and replication must grow with tokens/second and peak calls; a single warm pool is a pilot assumption. Cloudflare serves the PWA, account/data plane and WebRTC; payment remains a separate approved service.

## Persistent state

Keep four account-scoped records:

- User memory: confirmed facts, last conversation summary, upcoming events with source, date/timezone and confidence.
- Character identity: original adult reference images, permitted voice, appearance parameters and provenance.
- Fictional scene: location, outfit category, lighting, scene version and conversation continuity.
- Technical job: queued/preparing/validating/ready/connected/failed/cancelled/expired, entitlement reservation, spend cap and timestamps.

User facts are not character fiction. A sentence such as 'I'm in the bathroom' changes the fictional scene state, not a claim about a real person's location. The AI disclosure stays visible. The character only knows supplied/consented information.

Use a 4,096-token prompt cap, short summary, recent turns and relevant confirmed facts. Summarize after ten turns/end call. Confirm meaningful new facts before long-term storage; no covert sensitive-trait inference. Inspect/correct/forget/export controls invalidate derived summaries and cached prompts.

## Scene-to-call flow

1. User requests a call. Check age/state eligibility, account balance, character scene, host capacity and maximum generation cost.
2. Reserve a scene entitlement, not call minutes. Reuse a validated matching scene when possible; keep a small per-user cache of recent scenes with expiry.
3. If a new scene is required, send character references plus the structured fictional setting to Klein. Generate at most two candidates within the configured budget.
4. Validate original identity, adult appearance, policy and framing. Reject identity drift; a matching seed alone is not proof. Early pilot uses human-reviewed character/scene presets.
5. Warm the renderer and encode the selected scene reference. Confirm first frames and audio path before readiness.
6. Character says 'Give me a moment; I'll let you know when our call is ready.' UI shows 'Preparing your scene' and an honest estimate; do not invent a real-world cover story. Continue text while it loads.
7. Notify 'Ready to call' only after the job is ready. Keep a short configurable ready window, initially two minutes. If the user does not join, release GPU capacity; retain only the allowed scene cache.
8. User taps Join. Begin call metering only after usable media connects. Generate new synchronized portrait frames around the prepared scene. A talking portrait does not simulate arbitrary body actions.
9. On failure/deadline/cancellation, restore undelivered entitlement; record actual compute costs. Do not keep generating scenes on repeated taps or retries.
10. On hang-up, save a short summary, release reservation/capacity, expire private media according to the retention policy.

Targets to test: cached-scene preparation 1–5 seconds; a new scene on warm hardware 5–30 seconds; cold worker 30–120 seconds or longer depending on actual provider startup. These are hypotheses, not SLAs. Show the measured ETA and permit cancellation. The user's tolerated pre-call delay lets us avoid an always-on renderer.

Budget $0.10/accepted scene, $0.05/photo and $0.15/accepted portrait clip. For illustration, 60 seconds at $0.90/hour costs $0.015 of node time before loading, retries, checks and other costs. All successful-but-rejected work counts. A two-minute warm-up plus two-minute ready hold costs $0.06 at this node rate even if nobody joins; scene-budget feasibility must be measured against abandonment.

## During the visual call

Microphone -> streaming partial ASR/VAD -> concurrent memory retrieval -> Qwen first coherent phrase -> Kokoro speech -> wav2vec2 features -> FlashHead Lite -> VAE decode -> hardware H.264 encode -> synchronized WebRTC video/Opus audio.

Keep native model audio context and chunk sizes initially. Generate ahead of playback with a bounded buffer; cancel stale generations and audio/video on barge-in. Maintain independent temporal caches per session. Generate fresh listening-state portrait frames; no assumed free listening or prerecorded-loop substitution.

The [Gradio reference](https://raw.githubusercontent.com/Soul-AILab/SoulX-FlashHead/main/gradio_app_streaming.py) groups chunks into video files and starts with a completed audio file. Replace this with incremental audio and WebRTC output; removing file waits does not prove model latency. Target end-of-user-speech to synchronized reply p95 <=2 seconds on warm hardware, sustained 25FPS and limited audio/video skew. Report actual results.

FlashHead Lite's author throughput of 96FPS/4090 supports testing; it does not establish simultaneous LLM, guard, image and video performance. Use one stream until measured. Keep Pro, general Wan video and research models outside the first release.

## Opt-in check-ins and media

Ask permission separately for check-ins, web push and proactive media. Default quiet hours; respect timezone and notification revocation. Cap paid check-ins at one/day and free at one/week, counted within text limits. Scheduler retrieves a relevant confirmed event, generates one useful message, screens it and deduplicates by account/event/day.

Media suggestions consume the selected plan allowance only if the user opted into automatic included media; never trigger an overage. Cap paid proactive media at the plan's monthly totals. Free accounts receive no recurring generated video. Reuse approved assets when appropriate without claiming they were newly generated. Avoid intimate lock-screen previews: 'You have a new message' opens the authenticated app.

Cloudflare scheduled triggers/Queues and a database outbox handle delivery/retries. Notifications are not guaranteed delivery; an unread item remains in-app. No service-worker background inference or assumption that iOS keeps the app running.

## PWA guidelines and monitoring

HTTPS, install manifest, offline shell only; never cache intimate transcripts/media or age documents in the service worker. Request microphone access after a user gesture, provide captions, mute/end controls and visible balance. User camera uploads stay disabled. Test foreground Safari, installed iOS PWA and Android Chrome; detect disconnects, suspend billing and restore cleanly.

iOS web push requires an eligible home-screen web app and permission following user interaction. [WebKit documentation](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/). A PWA does not inherently add seconds of network delay, but background behavior/device codecs require tests. No App Store listing is needed for direct website access.

Internal monitoring: per-job actual cost, latency, rejection/retry rate, queue depth, active calls, paid entitlement, free-user ceiling, notification count and settlement balance. Redact sensitive payloads; separate minimal audit evidence from private conversations. Per-account and provider spend caps fail closed before new work. Monitoring compute/storage and founder incident response are budgeted; open-source tools do not eliminate operating effort.

Before paid release test age-result replay, account isolation, scene leakage, stale memory, forged payment events, duplicate jobs, abandonment, cold start, refund order and reconnection. The repo's current tests cover arithmetic only.
