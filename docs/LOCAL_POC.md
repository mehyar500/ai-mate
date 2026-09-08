# Local companion demo

Updated September 8, 2026. **Current interaction: Text, Voice call and Video call in one window.** Calls accept typed input or microphone speech after Enable mic. Camera access remains disabled; microphone permission is limited to this origin. This is a private, non-explicit prototype.

## Run

On the configured PC:

```powershell
.\scripts\start_motion.ps1 -Background -FastFP8
.\scripts\start_local.ps1 -Background -Provider cloudflare -EnvFile C:\Users\mehya\.env
```

Open **http://127.0.0.1:8765**. The script avoids starting a duplicate server. Background logs and launch information live in ignored `.cache/local-poc/`. A foreground launch without `-Background` stops when its terminal closes. Startup warms models; the latest measured warm start took 12.69 seconds, but a cold start can take over a minute. The current motion worker runs with `-FastFP8`; this is a measured local configuration, not a guarantee on other GPUs. A running PC and server are required; this is not a public URL or boot-time Windows service.

Try **“Let’s talk in the café. How are you?”**, **“Back to the garden. Say something cheerful.”**, or **“Send a video from there.”** The selected tab controls output: Text has no media, Voice call has speech, Video call has speech and video. Opening Text keeps an existing call active, shows a persistent call-status bar and a Return to video/voice call button, and marks the background call tab with a dot. Returning changes only the view: microphone, media elements and the active reply are retained. End call stops microphone capture and playback. Ask “Send me a message saying hello from our call” to deliver a separate message to Text with an unread badge. The call stays in its selected mode. Sound, Interrupt and Replay remain explicit controls. Memory & settings contains saved facts, notes and diagnostics.

Supported settings are living room, garden, café and a full-body garden portrait. These are prepared pictures of a fictional adult character. The reviewed identity-conditioned full-body reference is now used in the prototype; photorealistic quality is still under evaluation. Wave, closer and farther commands now generate fresh LTX body video with tracked MuseTalk lip-sync and Kokoro voice. Wave/forward motion has been observed; backward direction has failed review. Ordinary messages still use the talking portrait. Arbitrary actions remain unimplemented. Within a server session, completed video poses now carry into the next video reply. The former CSS wave/cutout has been removed. It has no live view of the user.

## What was wrong, and what changed

The browser audit reproduced a real product failure: at the preview width, the old page placed video above the conversation, off screen. The user typed “show me” and the model answered that it could not display images. The existing MP4 had played successfully according to the browser, but the user could not see it from the composer. The implementation also waited for a complete phrase video, offered no contextual media routing and required manual mode/scene choices.

The current layout fits the observed 912px-high viewport without document scrolling. Text history scrolls in its tab. Call screens hide the transcript and keep a compact translucent composer below the uncropped video stage. Voice call shows a portrait and listening state. An LLM now returns a validated reply, presentation, scene and optional factual excerpts in one decision. “From there” uses recent dialogue and the active setting. The app executes only allowlisted presentation/scene changes, never model-generated code, paths, URLs or shell commands.

Video is **fragmented MP4 streamed while inference is still running**, played through MediaSource. The embedded audio is muted; a separate WAV speech track follows the video clock from its first playing event, pauses during stalls, and corrects drift over 120ms. Previously speech started only after the entire stream finished downloading, causing a delayed reply. The output is 20 FPS, encoded in roughly 200ms fragments with about 400ms initial media buffered. If MediaSource is unsupported, the app explicitly waits for the completed MP4. Autoplay failure exposes Play reply; interruptions abort both tracks. Test sound sends a short Web Audio tone to help distinguish browser/output-device problems from synthesis failures.

The new microphone path uses an AudioWorklet, mono PCM16 WAV and local faster-whisper. Energy-based turn detection keeps 200ms of pre-roll, submits after 650ms of silence and caps each turn at 25 seconds. Short clicks and silence are rejected. Echo cancellation/noise suppression are requested from the browser. Capture pauses during synthesis/playback and resumes 450ms after playback; this is half-duplex, not reliable voice barge-in. Interrupt enables an earlier turn. Mute, End call, mode changes, page exit and late permission cancellation release tracks. Raw microphone audio is held in memory, not persisted; transcripts join local history and hosted dialogue context. Device/noise robustness and phone backgrounding still need real-user testing.

## Models and hardware split

| Component | Actual local selection | Resource |
|---|---|---|
| Conversation/action planner | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | Hosted, `/no_think`, bounded JSON response; no local GPU |
| Voice | Kokoro-82M ONNX v1.0 float32, `af_sarah` | CPU, four intra-op threads |
| Lip-sync | MuseTalk 1.5 + SD VAE ft-mse + Whisper-tiny encoder | GPU FP16, batch eight; 20 FPS streaming output |
| Body motion | LTX-Video 2B 0.9.8 distilled FP8 + T5-XXL FP8 | Local ComfyUI, 8 Euler steps |
| Face location | OpenCV YuNet 2023mar | CPU, per-frame movement tracking |
| Scene preparation | FLUX.2 Klein 4B, four steps, 512x640 | Separate GPU process with CPU offload; never during replies |
| Encoding | FFmpeg H.264/AAC | CPU libx264; installed FFmpeg/NVENC driver pair is incompatible |
| Speech recognition | faster-whisper Base English int8 | CPU; browser microphone or synthetic WAV through `/api/audio` |

Pinned repositories, revisions and assets are in [local-models.json](../config/local-models.json) and [local-assets.json](../config/local-assets.json). Selected Ollama digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`. The mutable tag is not enforced against this digest at startup.

The verified PC has an RTX 4060 Ti (16,380 MiB VRAM), approximately 47.7 GiB RAM and driver 595.97. Selected artifacts occupy about 25.11 GiB, excluding Python/CUDA and caches. The prior combined 9B/renderer run observed about 9.7 GiB device memory between turns; these were not sampled peaks.

## Hosted dialogue, local graphics

Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` is the running dialogue provider. `start_local.ps1 -EnvFile` reads only Cloudflare credentials from the explicitly selected private file. API key and email use `X-Auth-Key` / `X-Auth-Email`, taking priority over a token. A live authentication/planner request completed in 0.97 seconds; this is one sample. Never commit credentials.

The hosted provider receives conversation text, recent context and saved notes. Audio, pictures and video remain local. Ollama is unloaded. MiniMax and Ollama are explicit alternatives, not silent fallbacks; coding/chat subscriptions are not assumed to supply application API access.

## Memory and boundaries

Manual notes are limited to 1,200 characters. The app stores up to 50 exchanges, shows 12 and supplies four recent exchanges to the planner. It can save up to two model-selected personal facts per turn, with at most 12 retained. Each saved value must be a verbatim excerpt of the latest user message; values remain user-role data. Stable keys replace corrections. Memory shows the excerpts and allows deletion. Extraction can still misclassify a quote; these are not independently verified facts.

The selected scene persists across restart. Failed or cancelled jobs do not save a conversation or facts. Clear all cancels active work, erases local notes/facts/history and deletes reply media; prepared portraits remain. Removing a single fact does not erase that information from recent conversation. SQLite secure deletion is enabled, but storage is not encrypted by the app or guaranteed forensically erased.

The server binds only to loopback, validates Host/Origin, requires a per-boot token for API access, limits requests and generated files, and allows one inference job at a time. Streams require the same token and a known job. No public authentication, payments, age-verification service, production monitoring or independent security review has been added. This remains an R2 local prototype, not a public-release approval.

## Evidence

September 8 update: Cloudflare global-key authentication succeeded using the existing private credential file (`X-Auth-Key` plus `X-Auth-Email`). The app also supports scoped bearer tokens, but this PC uses the key/email flow. Only the four named Cloudflare settings are read from the explicitly selected file; secrets are not copied into the repository or sent to the browser. The credential file path is supplied at launch, not discovered automatically. The [Cloudflare endpoint](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/) runs [Qwen3-30B-A3B-FP8](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/).

- One isolated Cloudflare planner reply: **1.13s**. One full browser reply: **2.60s to playback**, **3.77s server completion**, no buffer waits. These are samples, not p95 or continuous-motion measurements.
- Replay observation: video clock **0.122068s**, unmuted WAV clock **0.127626s** (about **6ms** apart). Both finished without a browser media error. This does not confirm physical speaker output or phoneme quality.
- Cancellation with Cloudflare: bytes arrived while rendering at **2.596s**, cancellation completed in **0.369s**, and prior conversation was preserved.
- **54 Python tests and three JavaScript transport tests pass**. The latter cover initial synchronization, buffer stalls, blocked audio and cancellation while audio is starting. Earlier benchmark entries below used the previous provider/playback revision.

- **52 offline tests pass**, covering prior economics/local boundaries plus action validation, verbatim-fact restrictions, corrections, persistence, scene persistence, missing-provider credentials and media bytes arriving before a job finishes.
- Eight real Qwen planner turns correctly handled two personal facts, a lesson-day correction, recall, photo selection, contextual video selection and returning to text. Planner times were 0.87–1.90 seconds in this small synthetic sample.
- Browser audit verified contextual image display, actual video playback, visible controls and no document scroll at the observed viewport. An intermediate 25 FPS stream began after 3.10 seconds with no buffer waits.
- The first 20 FPS browser trial began after 2.36 seconds and completed server rendering at 4.33 seconds, with one buffer-wait event. Initial buffering was then increased. Three final warm replies began after **2.63, 2.56 and 2.34 seconds**, with **zero buffer waits**, while server completion took **4.64, 4.07 and 3.89 seconds**. These are samples, not a p95 claim.
- The final streaming cancellation check received 4,096 bytes while the job was still rendering and cancelled in **0.329 seconds**. Conversation/notes/facts remained unchanged; cancelled media was removed.
- Older 30-turn/ten-minute stability runs are preserved in [benchmark evidence](research/local-poc-benchmarks.json). They used the previous batch-delivery path and do not qualify this new streaming path for long calls.

Current browser captures and synthetic traces are under ignored `generated/local-app/audit/`. Real browser playback is now checked; subjective listening quality, measured phoneme alignment, mobile Safari, lengthy calls and public concurrency remain unqualified. Synthetic memory test data was isolated from the user's saved profile.

## What is still missing for FaceTime

### Full-body motion decision (September 2026)

**Tested and rejected for the current goal: OmniAvatar-1.3B**, with Wan2.1-T2V-1.3B, UMT5-XXL, Wan VAE and Wav2Vec2-base-960h. [Upstream](https://github.com/Omni-Avatar/OmniAvatar) is pinned to `1536bf31abaec74364fb7d5883470d5b23ffa7f8` by `scripts/benchmark_omniavatar.py`. The Windows runner removes unnecessary NCCL setup and Linux shell-copy/export commands. All weights downloaded successfully. Two 256×384, 2.56-second clips exported with audio: **67.5s cold / 31s denoising / 3.96 GiB peak model allocation** at 10 steps; **60.5s cold / 27s denoising / 3.86 GiB** at 8 steps with stronger text guidance. Both ignored the wave command: reviewed frames show arms staying down. This is a measured failure of these configurations, not proof all full-body models are impossible on 16 GB. See [benchmark evidence](research/local-poc-benchmarks.json).

**Current experiment: LTX-Video 2B 0.9.8 distilled FP8 and T5-XXL FP8**, installed in native ComfyUI pinned to `00d34d92fe0afbfbab3893ebbab2d5d70f5e9882`. The two pinned weight files total 9.35 GB; see `scripts/download_ltx_motion.py`. The isolated `.cache/comfy-env` uses loopback port 8188, disables custom/API nodes and reserves 4 GB for the speech renderer. [Official workflow](https://comfyanonymous.github.io/ComfyUI_examples/ltxv/), [LTX source](https://github.com/Lightricks/LTX-Video).

Flow: Cloudflare decision -> CPU Kokoro WAV -> fresh LTX body video at 384x576/24 FPS -> per-frame YuNet tracking -> MuseTalk mouth synthesis on moving frames -> H.264 fragments and synchronized WAV in the browser. Face appearance is encoded every two frames (50ms reuse at 20 FPS); body tracking and audio-driven mouth synthesis still update every frame. Body clips cap at about four seconds; longer speech holds the final body frame. Short speech no longer truncates the action: the video finishes, with natural LTX frames after speech and its brief lip-sync tail end. Commands select bounded graph parameters, never model-authored code, URLs or paths. Cancellation targets only the application's own Comfy prompt. A live cancellation test completed in 0.078s while Comfy was generating, preserving conversation and removing app media. ComfyUI is an unauthenticated trusted loopback development service; do not expose it publicly.

| Measured sample | Delay | Finding |
|---|---:|---|
| LTX cold wave, VP9, 384x576, 49 frames | 11.486s | Real arm movement, framing drift |
| LTX warm wave, VP9 | 7.176s | Encoding was expensive |
| LTX H.264 wave, same dimensions/frames | 3.645s | Material encoding improvement |
| LTX H.264, 256x384, 57 frames | 2.948s | Faster, visibly softer face |
| Integrated moving speech, full appearance encoding | 7.14s first playback; 9.11s completion | One 0.54s stall |
| Integrated moving speech, two-frame appearance reuse | 5.80s first playback; 6.94s completion | Zero stalls, audio/video both ended |

The optimized sample measured 0.752s to text, 3.28s for LTX and 2.428s for moving lip-sync. Resident GPU memory between replies was 12,588 MiB of 16,380 MiB. These are individual samples with differing seeds/speech durations, not controlled p95 or long-call measurements. Unmuted browser playback is not confirmation of physical speaker output or phoneme accuracy.

**Quality is not accepted.** Review source images first, then first-frame likeness, hands/feet, body proportions and scene geometry, then consecutive motion and speech. The old close-up/full-body assets differ in identity. `prepare_local_scene.py --scene fullbody --candidate` now creates a separate identity-conditioned 768x1152 candidate for review without replacing active media. The first candidate took 22.24s including model loading; its still image has more headroom and a closer facial likeness. Its cold motion test took 7.414s after ComfyUI was unloaded for image generation: the raised hand stays in frame, but framing drifts and feet begin cropping. It was subsequently promoted for prototype testing after the three-second guided-wave review; the original asset is retained in the ignored audit directory.

Reviewed motion raises hands and visibly moves legs, but framing drifts, hands crop out, one-arm prompts can raise both arms, and a backward-step prompt moved forward. Still needed: reliable direction, continuity during interruptions/restarts, broader command following, natural idle movement, better identity/hand stability, lower first-playback latency and sustained browser/audio recovery testing. This is discrete audiovisual generation, not seamless FaceTime.

OmniAvatar's two completed runs were rejected above. Alternatives remain unmeasured on this GPU: [StreamDiffusionV2](https://github.com/daitomanabe/streamdiffusionv2) needs driving video; [LongCat-Video-Avatar 1.5](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5) has larger memory requirements; [SoulX-FlashHead](https://github.com/Soul-AILab/SoulX-FlashHead) targets head/upper-body movement. [Vidu Q3](https://www.vidu.com/vidu-q3) is hosted clip generation, not established local continuous generation. None establishes unrestricted adult-use eligibility; see [USA](USA.md).

Validation: local review and 65 offline Python checks pass; independent security review, staging, long-call soak, mobile and public concurrency qualification remain unavailable. No SQLite migration. Roll back by reverting this code change and restarting; preserve private conversation data and prepared assets.

## Continuity and guided actions: latest evaluation

The backend keeps a private PNG of the last decoded frame of a successfully completed video. The next video reply uses it as its reference; an ordinary spoken reply no longer resets the body to the original portrait. Failed/cancelled replies do not replace it, and Reset removes it. It is session-local: restart discards it while preserving conversation. It describes the last **generated** pose, not necessarily the frame the user saw if they interrupted playback early; interruption-aware continuity remains incomplete.

The browser holds the actual last visible frame on a canvas while waiting, then replaces it when the new video starts. This is a still hold, not continuous idle animation. Full-body media uses `contain` on mobile to avoid extra CSS cropping. Its video area now sits above the composer; older messages are behind an accessible Show messages toggle, and the lower dark overlay no longer hides the feet. The actual browser screenshot was checked, including both feet above the controls and expanding/collapsing the transcript. A repeat command in this layout began playback at 5.66s with no stalls and completed server-side at 6.14s. A real two-reply test observed 6.10s first playback for the movement and 2.29s for the following same-pose reply, with zero stalls. The last/first frame pair retained body placement; mean pixel difference outside an expanded face region was 2.453/255. This is one transition, not a long-call identity test. Fragmented MP4 frame-count estimates initially broke pose capture; decoding to the final real frame fixed the reproduced failure.

Wave generation now uses native `LTXVAddGuide` and `LTXVCropGuides` to target the starting pose again at the end. A 73-frame trial showed one hand raising and lowering with a stable background and visible feet. The shorter 49-frame guided trial stayed still and was rejected; waves now allow at least 73 frames (about three seconds). With `-FastFP8`, three fresh seeds all moved and returned to neutral; two warm server execution samples were 4.081s and 3.996s. Hand count, finger detail and occasional hand cropping remain inconsistent. This is not a controlled FP8 speed comparison or proof of reliable arbitrary commands. [Official multiple-guide workflow](https://comfyanonymous.github.io/ComfyUI_examples/ltxv/).

Two FLUX Klein attempts to create a closer destination image failed still-image review: they mostly retained the original scale. Those destination images were not used to claim successful approach/backward guidance.

Cloudflare intermittently echoed a JSON schema rather than a filled plan. The prompt now requests concrete values and shows an example plan; five live samples returned valid plans in 0.578-1.469s. A later hosted request still took 22.064s, causing a 28.54s first-playback outlier. Exact simple motion commands now use a bounded local command path; contextual requests, questions, conditions and negations still go to the model. `decision_source` records that distinction. The live direct-command sample reached text in 0.001s and browser playback in 5.81s with zero stalls; a complete 3.05s action contained 0.961s of speech and finished server-side in 6.281s. Its reviewed frames showed one hand raising/lowering, both feet visible and a neutral final pose. This removes a hosted dependency for those exact commands; it is not a fallback promise for arbitrary dialogue. [Cloudflare JSON-mode limitations](https://developers.cloudflare.com/workers-ai/features/json-mode/).

## Call modes: verified September 8

Validation: 69 Python tests and seven Node audio/microphone tests passed, along with Python compilation, JavaScript syntax and `git diff --check`. Browser checks covered 716x854 and 390x844 layouts, latest-message scrolling, silent Text replies, Voice call delivery, Video call playback, microphone activation/muting and End call during a pending reply. The temporary viewport override was restored. Tests and raw synthetic evidence do not replace the outstanding independent review and production gates.

Text-only completed in **0.74s** with no media sources. A Voice call acknowledged and delivered a separate in-app message in **1.05s to playback**, with zero stalls; Text showed an unread badge, opening it preserved the call, and the message persisted in SQLite. The first message test had failed semantically (the model spoke the requested text without delivering it); the plan contract now includes an explicit message field and an example. Three isolated live planner probes covered two positive requests and a negated request successfully. These are samples, not reliability guarantees.

Video call microphone activation reached **Listening** in the preview and Mute released capture. A synthetic spoken wave passed through the real `/api/audio` endpoint: **0.494s ASR**, **4.107s body generation**, **1.613s lip rendering**, **6.661s total server time**. Silence returned `no_speech` without changing conversation. This does not establish an acoustic microphone-to-speaker round trip. The separate typed wave reached browser playback in **5.78s**, zero stalls. Reviewed frames showed a raised/lowered hand, full body, stable overall framing and a return to neutral; face detail and fingers remain soft. Evidence: `generated/local-app/audit/call-modes-asr.json` and `call-mode-wave-review.jpg` (private ignored artifacts).

A subsequent return-to-call test preserved both media source URLs and the playback position. It also exposed a stale planner action: asking for a garden-walk description incorrectly reused wave, taking **12.31s to playback / 18.171s to finish**. New validation requires a cue in the latest user turn for one of the three supported actions, or an explicit contextual repeat, and the prompt defaults ordinary conversation to none. An isolated live test with four previous waves then chose none in **1.053s**. The repeated browser request then reached playback in **2.60s**, zero stalls, finishing in **6.88s**; the planner also changed to the garden portrait, so this is not a controlled A/B benchmark. During a replay, Text-to-Return navigation preserved the same video source and advanced from **0.430s to 1.145s** without pausing or ending playback. This bounded guard is not a complete intent parser.

The 650ms microphone turn boundary adds to end-of-speech response latency. Hands-free capture is half-duplex; headphones, quiet-room testing, microphone denial/disconnection and real-user noise testing remain necessary qualification work. A seamless live body stream, reliable backward walking, identity consistency over long sessions, arbitrary actions, browser mobile/background behavior and physical speaker confirmation remain open. Do not label this production-ready.

Persistence adds an optional `call_messages` table linked to existing turns without rewriting existing conversation rows. Messages commit with successful replies, prune with their parent turns, and clear with conversation reset. Rolling back code leaves that extra table unused; preserve the database. Microphone access remains same-origin on loopback, camera denied, with existing Origin/Host/token checks. R2 review and staging/public deployment evidence are still absent; this build stays local.

### Renderer research and the next experiment

[LTX-2.3 FP8](https://huggingface.co/Lightricks/LTX-2.3-fp8) supplies a **22B distilled, eight-step CFG=1** joint audio/video model. It is the next quality candidate for avoiding a separately pasted lip renderer. [Lightricks' desktop app](https://github.com/Lightricks/LTX-Desktop) now supports local Windows CUDA with **at least 16 GB VRAM** and also advertises newer LTX 2.5 Fast; it lists **160 GB free disk** and describes newer weights as gated. [Official inference](https://github.com/Lightricks/LTX-2) offers FP8 and CPU/disk offloading. Hardware compatibility is not evidence of two-second latency: offloading can add PCIe transfer time, and neither candidate has been benchmarked on this rig. Model weights use a [community license](https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE), not the code repository's Apache license. No new license agreement was accepted and no public/adult clearance is claimed.

[StreamDiffusionV2](https://arxiv.org/abs/2511.07399) is worth evaluating for continuous generation, but its headline first-frame/FPS figures use **four H100 GPUs**. [Scope's integration](https://github.com/daydreamlive/scope/blob/main/src/scope/core/pipelines/streamdiffusionv2/docs/usage.md) provides a practical implementation to inspect. It is not a demonstrated synchronized, identity-preserving talking companion on the 4060 Ti. Do not replace measured local numbers with its paper's hardware results.

A second latency approach is a reviewed library of genuinely generated neutral-to-neutral body actions, with live speech rendering and fresh generation for uncached actions. That can remove repeated body diffusion from common commands, but it must be labelled and measured as reuse, preserve framing/identity, and reject cache hits when the current pose differs. It is a proposed experiment, not implemented success. Gate every candidate on a reviewed reference image, first/last-frame continuity, complete visible action, synchronized speech, multiple seeds/turns, cancellation and measured warm/cold delays before making it the default.

## Reproduce

### Central engine and current configuration

`local_app/engine.py` owns startup, turn state, the selected response mode, model sequencing, cancellation, pose continuity and successful memory/message commits. `server.py` is the loopback HTTP transport and retains an `Application` alias for existing integration scripts. Model-specific inference remains in `conversation.py`, `models.py`, `motion.py` and `visual.py`; there is one turn flow rather than separate text/microphone implementations.

```text
typed input ----------------------┐
microphone WAV -> Whisper base.en ─┴-> memory + explicit mode
    -> bounded direct command OR Cloudflare Qwen filled plan
    -> Text: reply
    -> Voice call: Kokoro speech
    -> Video call: Kokoro speech -> optional LTX body action -> MuseTalk lips
    -> stream picture + synchronized WAV -> hold final picture between turns
    -> successful completion: memory, in-app call message and last pose
```

The video tab remains the main experiment. A browser check found a blank picture after an ended video had sat idle. The client now captures its last decoded frame into the existing canvas at completion, hides the ended video surface and keeps a reviewed portrait underneath if capture fails. This is a held image between generated replies, not continuous live movement. A fresh reply hides that held frame only when playback starts.

After restart from the private `.env` without launcher overrides, Cloudflare and the local models became ready in **12.422s**. A fresh cold wave reached browser playback in **8.99s**, finished server-side in **9.47s**, and had zero buffer stalls. The unmuted WAV reached its end; the 384x576 final picture remained visible after playback and a Text/Return-to-call round trip. A streaming cancellation check then received bytes during rendering in **2.131s**, cancelled in **0.336s**, preserved conversation/notes/facts and removed only its cancelled media. These checks validate the engine move and frame retention; they do not meet the target latency.

Private `.env` now contains implemented startup configuration instead of hypothetical production flags. The engine reads only `AI_MATE_LLM_PROVIDER`, `AI_MATE_LLM_MODEL` and `AI_MATE_ENV_FILE`; environment/launcher overrides take precedence. The existing Cloudflare adapter reads account ID, API key, email or alternative API token from the explicitly selected credential file. API key plus email remains the selected authentication flow. Secrets are never loaded into the browser. MiniMax credentials remain process variables. Custom local values were preserved and the former local file was backed up privately as `.env.before-engine`. Deployment, payment and legal requirements stay in the product documents; deleting unused flags neither implements nor removes access controls.

### Direct renderer comparison, September 8

Same reviewed garden reference, seed 50, three-second/73-frame clips, eight distilled steps. The direct runner uses Diffusers 0.40.0 and existing LTX 2B 0.9.8 FP8 checkpoint weights cast to BF16; ComfyUI uses its fast FP8 kernels. Both wave tests condition the starting and ending pose. Tokenization/config-only assets are pinned to official `Lightricks/LTX-Video-0.9.5` revision `e58e28c39631af4d1468ee57a853764e11c1d37e`, whose transformer/VAE architecture matches this checkpoint. Precision, latent handling, VAE tiling and decode settings differ: this is a practical pipeline comparison, not an isolated framework performance claim.

| Candidate | Measured body time | Reviewed finding |
|---|---:|---|
| ComfyUI FP8, 384x576 | 6.809s cold execution; 4.349s warm | Hand raised/lowered, but the other hand also moved |
| Direct BF16, 384x576 | 4.720s first render+encode; 4.496s warm | One hand raised/lowered; full body; soft face/fingers |
| Direct BF16, 320x480 | 3.192s warm render+encode | Wave retained; softer details |
| Direct BF16, 256x384 | 2.005s warm render+encode | Both hands raised; rejected for exact one-hand following |
| Direct closer, 384x576 | 4.107s render+encode | Approached, but framing/background shifted |
| Direct backward, 384x576 | 4.107s render+encode | Came forward and crouched; failed command |

Direct cold setup was **13.948s**, including **8.287s** to load/encode the first T5 prompt; subsequent benchmark prompts are cached by prompt/config hash. Peak direct allocated CUDA memory was about **6.4 GiB**, with the app's lip renderer still resident separately. The 320 first sample was 4.082s with idle Comfy weights still resident; only its second warm sample is shown above. None of these numbers includes LLM, speech, lip rendering, browser startup or network delivery. A Comfy repeat uses a unique input node so it reruns diffusion instead of returning a fully cached video.

Speech assembly was separately tested over the reviewed generated 320 and 256 clips: Kokoro took **0.390s** for 1.863s of speech; first 4KB of the voiced video appeared after **0.799/0.700s** of assembly, and rendering completed in **2.861/2.764s**. Body generation was excluded from that test. The audio peaked at 0.470, RMS -22.67 dBFS, and local ASR recovered the exact test sentence. This establishes a non-silent generated track, not the founder's physical speaker output. Reviewed 320 output retained a complete visible wave; facial detail remains limited. Do not add these separate samples and claim a measured end-to-end latency.

**Decision:** keep the existing app backend while the direct pipeline remains an independently reproducible candidate. Its low-resolution speed gain is real in these samples; dependable backward motion, identity and audio/visual quality remain unsolved. Larger joint audio/video LTX-2.3 weights are downloading, have not completed verification/inference and are not selected. Its [weight license](https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE) has revenue and directly competing-service conditions; code licensing and self-hosting do not establish public/adult commercial clearance.

Reproduce benchmark candidates separately from user calls, keeping other GPU inference idle:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_direct_ltx.py --prepare-config --return-to-reference
.\.venv\Scripts\python.exe scripts/benchmark_direct_ltx.py --width 320 --height 480 --return-to-reference
.\.venv\Scripts\python.exe scripts/benchmark_direct_ltx.py --width 256 --height 384 --return-to-reference
.\.venv\Scripts\python.exe scripts/benchmark_video_assembly.py
.\.venv\Scripts\python.exe scripts/benchmark_ltx_motion.py --frames 73 --seed 50 --return-to-reference
# Optional ~39GB pinned candidate download; no automatic renderer selection:
.\.venv\Scripts\python.exe scripts/download_ltx23_benchmark.py
.\.venv\Scripts\python.exe scripts/benchmark_ltx23.py
```

Run the Comfy benchmark with the existing motion service; the direct runner does not call or import ComfyUI. Review source images first, then the private MP4/contact sheets and JSON in `generated/local-app/audit`. The direct-renderer checkpoint passed 71 Python and seven Node checks; the later return-motion changes pass 77 Python and seven Node checks. Independent R2 review, staging and public qualification remain outstanding. Rollback is a reviewed code revert; keep SQLite memory and private credentials intact.

### Return motion and continuous-presence findings — September 8

The engine now keeps one private, completed approach clip. An immediate request to move back in the same scene reverses that trajectory on CPU, then generates the current reply's voice and lips. A paired browser test measured **5.29s** to first approach playback and **1.82s** for the return, with no stalls. Server completion was 6.174s/2.700s; reversing the body clip took 0.160s. The reviewed return restored the full-body position with both shoes visible. This is disclosed motion reuse, not a new diffusion result or a benchmark of arbitrary backward commands.

The cache is consumed once, invalidated by another completed video turn or scene change, and cleared on reset/startup. Failed turns retain the prior valid cache; cancellation cannot publish a new one. Files stay within the private media directory. Tests cover these transitions, bounded input/duration, cancellation and a real CPU FFmpeg reversal with synthetic frames. Memory is preserved.

Continuous presence remains **unresolved**. Three 384x576 LTX-2B idle trials used a reviewed pose: 73-frame/end-guided (4.816s), 97-frame/end-guided (5.978s), and 97-frame/no-end-guide (5.813s). The first two barely moved; the third walked forward and shifted framing. All were rejected for background listening. No failed idle clip is selected by the app. The visible held frame remains a static fallback, not blinking, hair movement or a continuous generated call. The internal benchmark prompt is not a public command or an enabled idle worker.

The revised commercial direction is non-explicit Apple-native distribution; the current Windows browser app remains the test harness. StoreKit, device playback, public serving and independent review are outstanding. Optional larger-GPU experiment budgets are in ECONOMICS; no GPU has been rented. LTX-2.3 remains a candidate until download verification, inference and output review pass.

The configured environment is Python 3.12 with PyTorch 2.11.0+cu128. Dependencies are pinned in [requirements](../config/local-poc-requirements.txt). For a fresh environment, install Python 3.12, Ollama and FFmpeg, then:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r config/local-poc-requirements.txt
ollama pull qwen3.5:9b-q4_K_M
.\.venv\Scripts\python.exe scripts/download_local_models.py --assets-only
.\.venv\Scripts\python.exe scripts/download_local_models.py --models asr-base-en musetalk sd-vae whisper-tiny klein
```

Prepare scenes with the conversation server stopped; unload Qwen first. Each image process exits and releases GPU memory. Review the results before use.

```powershell
ollama stop qwen3.5:9b-q4_K_M
.\.venv\Scripts\python.exe scripts/prepare_local_scene.py
.\.venv\Scripts\python.exe scripts/prepare_local_scene.py --scene garden
.\.venv\Scripts\python.exe scripts/prepare_local_scene.py --scene cafe
.\scripts\start_local.ps1 -Background
```

Checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q local_app scripts tests
node --check local_app/web/app.js
node --test tests/media-sync.test.mjs tests/microphone.test.mjs
git diff --check
# With an idle ready server; preserves existing conversation:
.\.venv\Scripts\python.exe scripts/verify_streaming.py
```

No cloud GPU, new hardware or paid engineer was purchased. Existing electricity planning remains an unmeasured 300W increment at $0.20/kWh ($6 per 100 hours). Optional hosted model usage adds to that budget. Local electricity is not a public-service unit cost; see [ECONOMICS](ECONOMICS.md).
