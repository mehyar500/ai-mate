# AI Mate: video-call MVP

Continue the existing local application. Build a PWA with photorealistic companions, voice input and optional compact typed commands. Video quality, responsiveness and continuity take priority. No public service or rented GPU is provisioned.

## Current implementation

The app listens on 127.0.0.1:8765. Text, Voice and Video share local memory. The character fills the call view; a keyboard icon opens a transparent composer. Text navigation keeps the call connected and shows a return-to-call control. Camera access is disabled.

local_app/engine.py owns planning, speech, media, memory, cancellation and pose continuity:

1. Browser captures speech and detects its end, or sends a typed command.
2. CPU Whisper transcribes. The engine retrieves bounded recent context and saved facts.
3. Unambiguous supported movement commands take a direct path. Otherwise Cloudflare Qwen returns a validated reply, scene, action and optional in-app message.
4. CPU Kokoro synthesizes complete short phrases, preparing one phrase ahead.
5. MuseTalk creates new speech-driven mouth frames over the matching body source. Reviewed approach, return and wave assets avoid live diffusion for known starting poses. Other movement attempts use the experimental local generator.
6. The browser plays synchronized speech and fragmented video, then resumes the appropriate listening view. Interrupted playback preserves the displayed pose; approach/return can resume their remaining movement.
7. Completed turns update memory. Requested messages appear in Text. Generation completion is not proof the reply was heard; playback acknowledgment and recovery remain work.

Known actions are closer, farther and wave. Unsupported actions must be explained honestly. A prepared base wave cannot be applied to an unknown or near pose. Interrupted gestures retain a held frame without inventing an approach cursor. Prepared footage is disclosed; arbitrary low-latency body generation remains unsolved.

## Exact active models

| Stage | Model / configuration | Where it runs |
|---|---|---|
| Dialogue / plan | @cf/qwen/qwen3-30b-a3b-fp8 | Cloudflare, existing API key + email |
| Recognition | faster-whisper Base English, int8, eight threads | Local CPU |
| Speech | Kokoro-82M ONNX v1.0, af_sarah | Local CPU |
| Lip synchronization | MuseTalk 1.5, SD VAE ft-mse, Whisper-tiny features; optional TensorRT 11.2.1.2 FP16 decoder | Local GPU |
| Face tracking | YuNet ONNX | Local CPU |
| Reviewed body preparation | LTX-2.3 22B distilled FP8, Gemma 3 12B FP4 encoder | Offline local preparation |
| Experimental fresh actions | LTX-Video 2B 0.9.8 | Local GPU / ComfyUI |
| Reference images | FLUX.2 Klein 4B | Offline local GPU |

Pinned requirements and revisions are in config/local-poc-requirements.txt, config/local-models.json and config/local-assets.json. Installed benchmarks also include FlashHead Lite, Cloudflare Aura/Melo speech and Gateway LTX-2.5 Fast. Installation does not select them. LOCAL_POC records measured comparisons and reproduction.

Five prepared body sources are bounded by frame count/resolution, verified against reviewed manifests and primed before calls. Only source appearance is cached. Image generation and heavy video preparation run separately from calls. Unknown positions retain their captured frame instead of resetting the character.

`AI_MATE_VISUAL_DECODER=torch` is the portable default. The optional `tensorrt` selection requires a reviewed, locally built engine in `.cache/local-poc/musetalk-vae-trt/`. It verifies the engine and source-weight hashes, GPU name and exact Torch/TensorRT versions before deserialization. Missing or mismatched artifacts fail video warm-up while text/voice remain available. Revert the setting and restart to use Torch. Neither engine nor weights belong in Git; rebuild and requalify on a different GPU. LOCAL_POC records equivalence and call measurements.

Preparation now uses a 128-frame temporal VAE window for the measured 97-frame LTX clips. A same-latent comparison isolated the earlier double-image defect to temporal decoding. Isolated candidate bundles require matching review manifests before the call harness will load them. Promote the complete matching set between calls and rebuild appearance caches on restart; preserve memory and a rollback copy. LOCAL_POC records generation commands and remaining visual defects.

These are **neutral-demo selections**. LTX terms exclude the intended explicit service, and FlashHead's incorporated VAE rights remain unresolved. Hosted routes retain provider/model conditions. Commercial scope needs a separately qualified model/asset pipeline. Self-hosting does not remove license restrictions; USA records the evidence.

## Acceptance and evidence

| Requirement | Evidence / remaining work |
|---|---|
| Fast voice and visual response | Selected decoder sustained trial: end-of-speech median 2.48s / p95 2.90s, 54 spoken replies. Synthetic MediaStream includes recorder/VAD but excludes physical acoustics |
| Command behavior | Repeatable 20-command suite covering negation, unsupported action, memory and interrupted approach |
| 20–25 FPS playback | Output timestamps at 20 FPS; continuous delivery and dropped frames still need qualification |
| Synchronization within 100ms | Latest 3,685 browser clock samples: 24.74ms p95 / 51.72ms maximum; perceptual phoneme alignment and physical audio remain unqualified |
| Stable 30-minute call | TensorRT: 120 interactions, zero functional failures/reported reply stalls, all 120 clips retained; no steadily accumulating response delay |
| Realistic images and motion | Latest 5,966 frames analyzed, 120 visually sampled; previous source review retained. Hand blur, mouth artifacts, close framing and repetition remain |
| Mobile PWA calling | Layout and ManagedMediaSource selection covered; actual devices, speaker echo and background recovery pending |
| Public access and billing | Not implemented or approved |

Targets remain warm end-of-speech p95 <=2s, at least 20 FPS with a 25 FPS target, bounded A/V skew and no accumulating session delay. Samples are not SLAs. Zero stalls do not establish correct anatomy or arbitrary movement capability.

scripts/serve_voice_video_benchmark.py and scripts/qualify_video_call.cjs run isolated qualification/soak tests on port 8766 using synthetic profiles and WAV inputs. scripts/review_call_frames.py decodes every frame and creates ordered sheets. scripts/build_call_review.py verifies complete media coverage and hashes before making an offline review page with frame stepping, audio and exportable notes. Review checkboxes remain unchecked until a reviewer records an observation. Frame heuristics and decoded-audio signal checks cannot certify perception.

Pass `qualification run-label --capture` to the browser driver to exercise the actual AudioWorklet and end-of-turn logic. The ordinary mode starts at submission and understates conversational latency. CPU ASR tuning reduced recognition median from 448ms to 407ms in the capture comparison; dialogue variability and video generation still dominate the target miss. The 650ms speech boundary remains unchanged.

Shortened Whisper encoder input and Smart Turn v3.2 are isolated experiments, not active runtime settings. LOCAL_POC records accuracy failures and the remaining candidate; do not replace the 30-second padded ASR or speech boundary solely from their compute timings.

## Next hosted experiment

Keep the 16GB rig. Recommend one US RTX 5090 32GB, 8 vCPU, 64GB RAM and 150GB disk for ten scheduled test hours. The observed TensorDock quote is $0.7425/hour; a matching 4090 configuration is $0.6395/hour. This is a benchmark recommendation, not production reliability or content approval. ECONOMICS contains the source and complete assumptions.

Transfer pinned code, permitted weights and synthetic fixtures to a compatible Linux/CUDA runtime. Keep services private and use an SSH tunnel for the founder demo. Do not upload local memory or the broad credential file. Supply only required secrets through private server configuration. Record setup time, disk, peak VRAM, CPU load and the identical suite results. Windows execution does not prove Linux/5090 compatibility.

Compare end-to-end latency, preparation, visual defects, throughput and billed time against this rig. More VRAM adds capacity; it does not itself prove faster inference. Reject a rental without enough measured benefit. No automatic expensive fallback or open-ended runtime.

## Public PWA architecture

Cloudflare is the preferred application and WebRTC transport candidate. The GPU provider runs inference; Gateway routing and WebRTC transport do not generate frames.

Browser/PWA -> authenticated Cloudflare control API -> assigned warm GPU session -> timestamped WebRTC audio/video -> browser. Account memory and entitlements live outside disposable workers. Heavy scene/clip jobs use a separate queue.

Start with one measured call slot per worker. Warm once, retain the session across turns, reserve worst-case spend before admission and release after hang-up/short disconnect grace. Scheduled workers suit early demos; scale-to-zero suits asynchronous work if the accepted provider supports it. Confirm stopped-disk charges, availability and egress. Instant cold admission cannot be promised.

The existing loopback server is single-user with a shared local token. Public use requires authenticated accounts, isolated session/memory state, short-lived media access, quotas, billing reservations, replay-safe payment webhooks, bounded retries and reconnect/cancel recovery. These are requirements, not existing protections.

Use HTTPS, request microphone access on Join, and keep captions plus clear mute/end controls. Cache only the static shell, never private conversation/media, credentials or identity documents. Test installed iOS PWA and Android Chrome, codec fallback, denied permission, network loss, locked-screen behavior and update recovery. [WebKit media requirements](https://webkit.org/blog/14735/webkit-features-in-safari-17-1/), [home-screen push](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).

## Memory and deferred features

SQLite retains editable notes, bounded verbatim facts and recent exchanges. It knows only what the user shared. Keep factual memory separate from fictional scene state. Users can inspect, correct and delete it. Preserve generated/local-app/memory.sqlite3 during updates.

Production memory needs per-account authorization and source/time metadata. Opt-in check-ins, event reminders, push and proactive media remain deferred until the call works. Never charge for unsolicited media or infer consent to retain sensitive facts. Avoid emotional pressure to pay and sensitive notification previews.

## Configuration and release gates

.env.example documents implemented fields: AI_MATE_LLM_PROVIDER, AI_MATE_LLM_MODEL, AI_MATE_ENV_FILE and AI_MATE_VISUAL_DECODER, plus Cloudflare account ID/key/email or alternative scoped token. MiniMax uses its explicit process credential. No GPU-provider, WebRTC or payment environment variable is wired yet.

The initial remote benchmark can use SSH without another inference API key. Public deployment will need scoped application/Realtime credentials, accepted GPU lifecycle access and processor-specific merchant/webhook secrets. Add exact fields with the implemented adapters; placeholders must not imply a functioning service.

The founder owns host/content/processor acceptance and jurisdiction decisions. Engineering owns isolation, verified access, spend limits and evidence. Independent security/correctness review and staging remain pending before public release. No adult capability or nationwide clearance is claimed.

Keep five core documents: REPORT for decisions, BUILD for architecture, LOCAL_POC for experiments, ECONOMICS for costs and USA for eligibility. Machine evidence belongs in docs/research/local-poc-benchmarks.json. Work on main as authorized; commit/push reviewed changes with checks, preserving secrets and memory.
