# AI Mate: video-call MVP

Continue the existing local application. Build a PWA with photorealistic companions, voice input and optional compact typed commands. Video quality, responsiveness and continuity take priority. No public service or rented GPU is provisioned.

## Current implementation

The app listens on 127.0.0.1:8765. Text, Voice and Video share local memory. The character fills the call view; a keyboard icon opens a transparent composer. Text navigation keeps the call connected and shows a return-to-call control. Camera access is disabled.

local_app/engine.py owns planning, speech, media, memory, cancellation and pose continuity:

1. Browser captures speech and detects its end, or sends a typed command.
2. Local Whisper transcribes validated PCM (GPU FP16 on this PC; CPU int8 by default). The engine retrieves bounded recent context and saved facts.
3. Unambiguous supported movement commands take a direct path. Otherwise Cloudflare Qwen returns a validated reply, scene, action and optional in-app message.
4. Kokoro synthesizes complete short phrases, preparing one phrase ahead. This PC selects CUDA speech with unused allocator regions released after each inference. The current six-source configuration passed 132 commands over 30 minutes; CPU remains the portable default and recovery setting.
5. MuseTalk creates new speech-driven mouth frames over the matching body source. Reviewed approach, return and wave assets avoid live diffusion for known starting poses. Other movement attempts use the experimental local generator.
6. The browser plays synchronized speech and fragmented video, then resumes the appropriate listening view. Interrupted playback preserves the displayed pose; approach/return can resume their remaining movement.
7. Completed turns update memory. Requested messages appear in Text. Generation completion is not proof the reply was heard; playback acknowledgment and recovery remain work.

Known actions are closer, farther and wave. Unsupported actions must be explained honestly. Base and near waves require separate reviewed clips matched to their pose references. Neither applies to an unknown position. Interrupted gestures retain a held frame without inventing an approach cursor. Prepared footage is disclosed; arbitrary low-latency body generation remains unsolved.

In Text or Voice, a supported movement request receives a Video-mode hint after validation; a suppressed action cannot retain a success claim. Explicit negations retain the stillness response, while ordinary discussion of movement keeps conversational routing. The selected mode, scene, bounded facts and message handling remain unchanged.

Calls keep listening during silent reply preparation. If speech resumes before playback, cancel the unfinished reply and combine the original and resumed recorder audio for recognition. Keep the 650ms endpoint; combined audio is capped at the recognizer's 30 seconds. Never combine typed replacements, different calls/devices, or speech interrupting an already playing reply. Oversized/invalid combinations ask for a shorter repeated sentence. These temporary browser buffers clear on mute/end; no new storage or provider receives them. Playback interruption still requires reported echo cancellation, and the acoustic-tail cooldown remains.

The planner prompt and action validator account for ASR punctuation inside explicit negation. A proposed movement contradicted by "Please do not. Wave" is suppressed, with a stillness acknowledgement and `motion_veto` metric. The check is deliberately conservative for conflicting instructions and is not a general language parser. Negating a different movement does not block a separately requested wave.

## Exact active models

| Stage | Model / configuration | Where it runs |
|---|---|---|
| Dialogue / plan | @cf/qwen/qwen3-30b-a3b-fp8 | Cloudflare, existing API key + email |
| Recognition | faster-whisper Base English, FP16 on this PC; CPU int8 fallback, eight threads | Local GPU; explicit `AI_MATE_ASR_DEVICE` setting |
| Speech | Kokoro-82M ONNX v1.0, af_sarah, eight host threads, ONNX Runtime GPU 1.26.0 | Local GPU on this PC; CPU default elsewhere |
| Lip synchronization | MuseTalk 1.5, SD VAE ft-mse, Whisper-tiny features; optional TensorRT 11.2.1.2 FP16 decoder | Local GPU |
| Face tracking | YuNet ONNX | Local CPU |
| Reviewed body preparation | LTX-2.3 22B distilled FP8, Gemma 3 12B FP4 encoder | Offline local preparation |
| Experimental fresh actions | LTX-Video 2B 0.9.8 | Local GPU / ComfyUI |
| Reference images | FLUX.2 Klein 4B | Offline local GPU |

Pinned requirements and revisions are in config/local-poc-requirements.txt, config/local-models.json and config/local-assets.json. Installed benchmarks also include FlashHead Lite, Cloudflare Aura/Melo speech and Gateway LTX-2.5 Fast. Installation does not select them. LOCAL_POC records measured comparisons and reproduction.

Isolated replacement experiments use **LongLive 2.0 5B**, **NVFP4-S2 unpacked into BF16**, **UMT5-XXL**, **Wan2.2 VAE** and **MG-LightVAE v2**, pinned in `config/longlive2-benchmark.json`: reference encoding -> changing prompt blocks -> causal diffusion -> cached decoding. Two steps improve speed but still fail right-hand isolation. **RAIN / DWPose / CLIP ViT-L / SD VAE** (`config/rain-benchmark.json`) fails full-body visual quality even with static poses. Both remain outside the engine. **Wan2.1-VACE-1.3B** now has an isolated reference/pose harness in `benchmark_vace.py`, with optional **rCM Wan2.1 T2V 1.3B** generator transfer through `vace_rcm.py`; assets are pinned in `config/vace-benchmark.json`. Its flow is reference + joint trajectories -> pose frames and optional editable-body mask -> original VACE control encoding -> four-step rCM sampling -> original VAE decode. The 26-second whole-clip result remains outside the engine: body guidance improves, but latency and scene-edge artifacts fail call acceptance. The rCM transfer preserves all 439 VACE control tensors and replaces 825 base tensors; this combination is experimental. Scope source is excluded because its checked-in license is noncommercial. Speech/playback integration follows renderer acceptance; download or successful inference alone does not select a model.

Up to six prepared body sources are bounded by frame count/resolution, verified against reviewed manifests and primed before calls. Only source appearance is cached. Reviewed clips track the unique face overlapping its previous box by at least 50%; a missing or ambiguous match fails. This prevents an off-face palm detection from stealing lip sync. Fresh generation retains the strict single-face rule. Raw detector flags remain in the separate frame review; `prepared_face_ambiguities_resolved` reports tracked disambiguations. Image generation and heavy video preparation run separately from calls. Unknown positions retain their captured frame instead of resetting the character.

The portable configuration uses Torch decoding and CPU speech. This PC explicitly selects reviewed TensorRT, CUDA recognition and CUDA Kokoro. Missing or incompatible selected backends fail rather than silently switch. TensorRT engines must match local hardware, dependencies and source hashes; rebuild and qualify after a hardware change. GPU speech releases unused arena allocations after inference; the 2GiB arena setting is not a total VRAM cap. LOCAL_POC contains installation, validation and recovery commands.

Recordings remain mono PCM16 WAV, 8–96kHz and 0.15–30 seconds. Decode and validate once, normalize/resample to 16kHz and invoke Whisper with its original VAD, beam size and 30-second padding. Raw audio stays local. Recognition warming during a pause is implemented but disabled: repeated complete-call tests did not establish a reliable gain. Earlier recognition and turn-decision experiments do not replace the 650ms endpoint or preserved resumed-speech behavior.

Preparation now uses a 128-frame temporal VAE window for the measured 97-frame LTX clips. A same-latent comparison isolated the earlier double-image defect to temporal decoding. Isolated candidate bundles require matching review manifests before the call harness will load them. Promote the complete matching set between calls and rebuild appearance caches on restart; preserve memory and a rollback copy. LOCAL_POC records generation commands and remaining visual defects.

The benchmark can also constrain the final pose with `--end-reference-path`. Both starting and final images must be reviewed app-owned PNGs; it cannot be combined with `--return-to-reference`. The selected three-second approach uses this constraint to keep the head visible, excluding a defective final guide frame. This is offline asset preparation, with no new live-call dependency or API key.

These are **neutral-demo selections**. LTX terms exclude the intended explicit service, and FlashHead's incorporated VAE rights remain unresolved. Hosted routes retain provider/model conditions. Commercial scope needs a separately qualified model/asset pipeline. Self-hosting does not remove license restrictions; USA records the evidence.

## Acceptance and evidence

| Requirement | Evidence / remaining work |
|---|---|
| Fast voice and visual response | Current six-source soak: speech-end median 1.773s / p95 2.530s, 60 replies. Includes synthetic recorder/VAD; physical acoustics and public concurrency excluded. p95 target unmet |
| Command behavior | 132/132 interactions across six cycles of the expanded 22-command suite; negation, unsupported actions, memory, both wave poses and interrupted approach |
| 20–25 FPS playback | Reply output timestamps 20 FPS; continuous visible callbacks approximately 19.93 FPS replies / 24.07 FPS listening. No gap >250ms; strict >=20 FPS/25 FPS target not established |
| Synchronization within 100ms | 4,003 browser clock samples, 24.11ms p95 / 34.62ms maximum. Six SyncNet estimates 0/-40ms with controls passing. Physical/perceptual alignment remains unqualified |
| Stable 30-minute call | 132 interactions over 1,800.031 seconds, no functional/page errors or reported reply-buffer stalls. Cycle speech medians 1.77–1.88s; call stayed connected |
| Realistic images and motion | All 5,716 sustained-call frames received limited diagnostics; six face-count flags retained. Body diagnostics retained 96 uncertainties; 114 flagged/context frames were visually reviewed. Neither diagnostic certifies anatomy. Hand blur, mouth artifacts and repetition remain |
| Mobile PWA calling | Layout and ManagedMediaSource selection covered; actual devices, speaker echo and background recovery pending |
| Public access and billing | Not implemented or approved |

Targets remain warm end-of-speech p95 <=2s, at least 20 FPS with a 25 FPS target, bounded A/V skew and no accumulating session delay. Samples are not SLAs. Zero stalls do not establish correct anatomy or arbitrary movement capability.

scripts/serve_voice_video_benchmark.py and scripts/qualify_video_call.cjs run isolated qualification/soak tests on port 8766 using synthetic profiles and WAV inputs. scripts/review_call_frames.py decodes every frame and creates ordered sheets. scripts/build_call_review.py verifies complete media coverage and hashes before making an offline review page with frame stepping, audio and exportable notes. Review checkboxes remain unchecked until a reviewer records an observation. Frame heuristics and decoded-audio signal checks cannot certify perception.

Pass `qualification run-label --capture` to exercise AudioWorklet and endpoint detection. The ordinary injection mode starts at submission and understates conversational latency. Current spoken direct commands have a 1.52s median versus 2.22s for model-planned replies; this comparison includes different reply lengths and is not an isolated LLM timing measurement. Preserve the 650ms endpoint and resumed-speech handling until a complete-call comparison supports a change.

The offline OpenCV Zoo MediaPipe person/pose evaluator is pinned separately in config/body-evaluator.json. It measures joint visibility, raised wrists and projected limb discontinuities across every retained frame, preserving detector ambiguity. It adds no live inference dependency and refuses to run while the timing server is listening. LOCAL_POC has installation, controls and scope; a fixed skeleton cannot detect every extra limb, certify identity or replace visual review.

## Next hosted experiment

Keep the 16GB rig. Recommend one US RTX 5090 32GB, 8 vCPU, 64GB RAM and 150GB disk for ten scheduled test hours. The observed TensorDock quote is $0.7425/hour; a matching 4090 configuration is $0.6395/hour. This is a benchmark recommendation, not production reliability or content approval. ECONOMICS contains the source and complete assumptions.

Transfer pinned code, permitted weights and synthetic fixtures to a compatible Linux/CUDA runtime. Keep services private and use an SSH tunnel for the founder demo. Do not upload local memory or the broad credential file. Supply only required secrets through private server configuration. Record setup time, disk, peak VRAM, CPU load and the identical suite results. Windows execution does not prove Linux/5090 compatibility.

Compare end-to-end latency, preparation, visual defects, throughput and billed time against this rig. More VRAM adds capacity; it does not itself prove faster inference. Reject a rental without enough measured benefit. No automatic expensive fallback or open-ended runtime.

## Public PWA architecture

An isolated local WebRTC prototype now sends actual MuseTalk frames and retained synthetic speech through aiortc 1.15.0, H.264 and Opus. It runs separately on port 8766 with no microphone, planner, private memory or external ICE servers. The ordinary preview still uses HTTP/MSE. LOCAL_POC records the measured transport comparison, bounded installation and incomplete receiver-quality/public-signaling qualification. It adds no runtime environment variable or provider credential.

Cloudflare is the preferred application and WebRTC transport candidate. The GPU provider runs inference; Gateway routing and WebRTC transport do not generate frames.

Browser/PWA -> authenticated Cloudflare control API -> assigned warm GPU session -> timestamped WebRTC audio/video -> browser. Account memory and entitlements live outside disposable workers. Heavy scene/clip jobs use a separate queue.

Start with one measured call slot per worker. Warm once, retain the session across turns, reserve worst-case spend before admission and release after hang-up/short disconnect grace. Scheduled workers suit early demos; scale-to-zero suits asynchronous work if the accepted provider supports it. Confirm stopped-disk charges, availability and egress. Instant cold admission cannot be promised.

The existing loopback server is single-user with a shared local token. Public use requires authenticated accounts, isolated session/memory state, short-lived media access, quotas, billing reservations, replay-safe payment webhooks, bounded retries and reconnect/cancel recovery. These are requirements, not existing protections.

Use HTTPS, request microphone access on Join, and keep captions plus clear mute/end controls. Cache only the static shell, never private conversation/media, credentials or identity documents. Test installed iOS PWA and Android Chrome, codec fallback, denied permission, network loss, locked-screen behavior and update recovery. [WebKit media requirements](https://webkit.org/blog/14735/webkit-features-in-safari-17-1/), [home-screen push](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).

## Memory and deferred features

SQLite retains editable notes, bounded verbatim facts and recent exchanges. It knows only what the user shared. Keep factual memory separate from fictional scene state. Users can inspect, correct and delete it. Preserve generated/local-app/memory.sqlite3 during updates.

Production memory needs per-account authorization and source/time metadata. Opt-in check-ins, event reminders, push and proactive media remain deferred until the call works. Never charge for unsolicited media or infer consent to retain sensitive facts. Avoid emotional pressure to pay and sensitive notification previews.

## Configuration and release gates

.env.example documents implemented fields: AI_MATE_LLM_PROVIDER, AI_MATE_LLM_MODEL, AI_MATE_ENV_FILE, AI_MATE_VISUAL_DECODER, AI_MATE_ASR_DEVICE, AI_MATE_ASR_PAUSE_WARM and AI_MATE_TTS_DEVICE, plus Cloudflare account ID/key/email or alternative scoped token. MiniMax uses its explicit process credential. No GPU-provider, WebRTC or payment environment variable is wired yet.

The initial remote benchmark can use SSH without another inference API key. Public deployment will need scoped application/Realtime credentials, accepted GPU lifecycle access and processor-specific merchant/webhook secrets. Add exact fields with the implemented adapters; placeholders must not imply a functioning service.

The founder owns host/content/processor acceptance and jurisdiction decisions. Engineering owns isolation, verified access, spend limits and evidence. Independent security/correctness review and staging remain pending before public release. No adult capability or nationwide clearance is claimed.

Keep five core documents: REPORT for decisions, BUILD for architecture, LOCAL_POC for experiments, ECONOMICS for costs and USA for eligibility. Machine evidence belongs in docs/research/local-poc-benchmarks.json. Work on main as authorized; commit/push reviewed changes with checks, preserving secrets and memory.
