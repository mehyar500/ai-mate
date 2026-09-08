# Text-to-video local demo

Updated September 8, 2026. **Current interaction: type a message, receive a spoken video reply in one phone-style screen.** No microphone or camera permission is requested; both are disabled by the page's Permissions Policy. This is a private, non-explicit prototype.

## Run

On the configured PC:

```powershell
.\scripts\start_local.ps1 -Background -Provider cloudflare -EnvFile C:\Users\mehya\.env
```

Open **http://127.0.0.1:8765**. The script avoids starting a duplicate server. Background logs and launch information live in ignored `.cache/local-poc/`. A foreground launch without `-Background` stops when its terminal closes. Startup warms models; the latest measured warm start took 12.69 seconds, but a cold start can take over a minute. A running PC and server are required; this is not a public URL or boot-time Windows service.

Try **“Let’s talk in the café. How are you?”**, **“Back to the garden. Say something cheerful.”**, or **“Send a video from there.”** Ordinary messages receive video plus voice by default. “Voice only” and “just text” change the response style through the conversation. Sound, Interrupt and Replay remain explicit controls. Memory & settings contains saved facts, notes and diagnostics.

Supported settings are living room, garden, café and a full-body garden portrait. These are prepared pictures of a fictional adult character; the separately generated full-body portrait has not passed identity-consistency review. The interactive renderer generates mouth movement and speech; it cannot wave, walk, change clothing or perform arbitrary body actions. The former CSS wave/cutout has been removed. It has no live view of the user.

## What was wrong, and what changed

The browser audit reproduced a real product failure: at the preview width, the old page placed video above the conversation, off screen. The user typed “show me” and the model answered that it could not display images. The existing MP4 had played successfully according to the browser, but the user could not see it from the composer. The implementation also waited for a complete phrase video, offered no contextual media routing and required manual mode/scene choices.

The current layout fits the observed 912px-high viewport without document scrolling. Captions/history scroll inside the same screen as the portrait and composer. An LLM now returns a validated reply, presentation, scene and optional factual excerpts in one decision. “From there” uses recent dialogue and the active setting. The app executes only allowlisted presentation/scene changes, never model-generated code, paths, URLs or shell commands.

Video is **fragmented MP4 streamed while inference is still running**, played through MediaSource. The embedded audio is muted; a separate WAV speech track follows the video clock from its first playing event, pauses during stalls, and corrects drift over 120ms. Previously speech started only after the entire stream finished downloading, causing a delayed reply. The output is 20 FPS, encoded in roughly 200ms fragments with about 400ms initial media buffered. If MediaSource is unsupported, the app explicitly waits for the completed MP4. Autoplay failure exposes Play reply; interruptions abort both tracks. Test sound sends a short Web Audio tone to help distinguish browser/output-device problems from synthesis failures.

A microphone call experiment exposed background-noise handling problems. That flow was removed at the founder's request. ASR remains installed for diagnostics but is not on the current browser interaction path.

## Models and hardware split

| Component | Actual local selection | Resource |
|---|---|---|
| Conversation/action planner | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | Hosted, `/no_think`, bounded JSON response; no local GPU |
| Voice | Kokoro-82M ONNX v1.0 float32, `af_sarah` | CPU, four intra-op threads |
| Lip-sync | MuseTalk 1.5 + SD VAE ft-mse + Whisper-tiny encoder | GPU FP16, batch eight; 20 FPS streaming output |
| Face location | OpenCV YuNet 2023mar | CPU |
| Scene preparation | FLUX.2 Klein 4B, four steps, 512x640 | Separate GPU process with CPU offload; never during replies |
| Encoding | FFmpeg H.264/AAC | CPU libx264; installed FFmpeg/NVENC driver pair is incompatible |
| Speech recognition, retained diagnostics | faster-whisper Base English int8 | CPU; no microphone capture in the current UI |

Pinned repositories, revisions and assets are in [local-models.json](../config/local-models.json) and [local-assets.json](../config/local-assets.json). Selected Ollama digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`. The mutable tag is not enforced against this digest at startup.

The verified PC has an RTX 4060 Ti (16,380 MiB VRAM), approximately 47.7 GiB RAM and driver 595.97. Selected artifacts occupy about 25.11 GiB, excluding Python/CUDA and caches. The prior combined 9B/renderer run observed about 9.7 GiB device memory between turns; these were not sampled peaks.

## Hosted dialogue, local graphics

**Preferred next configuration: hosted conversation, CPU speech, local GPU video.** A MiniMax adapter is implemented behind `AI_MATE_LLM_PROVIDER=minimax`. It uses the official text endpoint and defaults to `MiniMax-M2.7`; `MiniMax-M2.7-highspeed` is an optional model setting. It has not been live-tested because no MiniMax/OpenAI API key was configured in this project's environment. No paid request was made. The current server therefore still uses Qwen locally.

Set these **process environment variables** before launching the server: `AI_MATE_LLM_PROVIDER`, optional `AI_MATE_LLM_MODEL`, and private `MINIMAX_API_KEY`. Missing credentials fail clearly before an external request. The app does not read `.env` or `.env.example`; the latter lists settings, not loaded configuration. With a working hosted provider selected, stop the old server and unload Qwen with `ollama stop qwen3.5:9b-q4_K_M`, then relaunch. This removes the resident local LLM from the graphics GPU.

Hosted dialogue sends text, recent context and saved notes to that provider. Audio, pictures and video remain local. No silent cloud fallback is used. The UI discloses the selected provider. A paid chat/coding subscription is not assumed to supply an application API key. Codex SDK is a separate agent integration; this app does not proxy Codex tokens or expose coding-agent tools to conversation inputs. [Official Codex authentication](https://learn.chatgpt.com/docs/auth), [MiniMax text API](https://platform.minimax.io/docs/api-reference/text-post).

MiniMax currently lists M2.7 at $0.30/M input tokens and $1.20/M output; highspeed is $0.60/$2.40. An example with 2,000 input and 300 billed output tokens is $0.00096 per turn, or about $0.35 for 360 turns. This excludes extra reasoning tokens, retries, taxes and every non-LLM cost; it is not a measured call bill or latency guarantee. [Official pricing](https://platform.minimax.io/docs/guides/pricing-paygo).

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

**Current experiment: OmniAvatar-1.3B**, with Wan2.1-T2V-1.3B, UMT5-XXL, Wan VAE and Wav2Vec2-base-960h. It accepts a reference image, speech and movement prompt. [Upstream](https://github.com/Omni-Avatar/OmniAvatar) is pinned to `1536bf31abaec74364fb7d5883470d5b23ffa7f8` by `scripts/benchmark_omniavatar.py`. The runner removes unnecessary NCCL setup for exactly one GPU and conditionally imports sequence-parallel helpers; its imports pass on Windows. It uses CPU offload and starts at 256×384, 81 frames and 10 denoising steps. Weights are still downloading; **no successful body-motion generation, latency or quality result is claimed yet**. The checkpoint being 1.3B does not include the large text encoder and is not a total VRAM estimate.

The isolated environment `.cache/omni-env` reuses the installed CUDA PyTorch through `app-runtime.pth`; its older Transformers/NumPy dependencies are pinned in `config/omniavatar-requirements.txt`. Do not install those dependencies into the app's `.venv`. Example after downloads finish, with the app stopped to free GPU/RAM:

```powershell
.cache/omni-env/Scripts/python.exe -X utf8 scripts/benchmark_omniavatar.py --image generated/local-app/fullbody.png --audio PATH_TO_SHORT_TEST_WAV
```

The runner records wall time and peak CUDA allocation in its ignored upstream cache. Its generated clips must be visually reviewed before integration. A failed/import-only run does not qualify as a working demo.

Research alternatives: the [ComfyUI OmniAvatar node](https://github.com/CallMe1101/ComfyUI_OmniAvatar) exposes image/audio/prompt inputs but does not establish this GPU's speed. [StreamDiffusionV2](https://github.com/daitomanabe/streamdiffusionv2) offers single-GPU causal video-to-video streaming and a lightweight VAE option; it requires a driving video and has no measured 4060 Ti result here. [Vidu Q3](https://www.vidu.com/vidu-q3) documents native audiovisual clips up to 16 seconds; this is not evidence for local weights, continuous live generation or the claimed “S3 July” release. None of these links establishes unrestricted adult-use eligibility.

A photorealistic full-body generator has **not yet met call latency on this 16 GB RTX 4060 Ti**. Earlier wording claimed this was impossible without measuring it; that conclusion was unsupported. Candidate differences matter:

* **SoulX-FlashHead Lite** is the best local low-latency talking-avatar candidate, but it remains a head/upper-body model. Its published 96 FPS result is on an RTX 4090, not this card. [Repository](https://github.com/Soul-AILab/SoulX-FlashHead)
* **Tencent MimicMotion 1.1** accepts pose guidance and can create body actions such as waving, walking and sitting, but its own README reports about 20 minutes for a 35-second clip on an RTX 4090 and approximately 16 GB VRAM. It is a prepared-clip generator, not a FaceTime renderer. [Repository](https://github.com/Tencent/MimicMotion)

A possible fallback is a library of actual generated action clips, selected by commands and voiced locally. This is not implemented and would support only the prepared actions. It must not be presented as arbitrary instant body generation.

**New primary evaluation target: LongCat-Video-Avatar 1.5.** Its September 2026 model card describes audio-text-to-video and audio-image-text-to-video, full-body temporal stability, identity consistency, 8-step distillation and INT8 inference, with model weights under MIT. The INT8 checkpoint is four shards totaling approximately 16 GB before the base model, Whisper-large-v3 and runtime overhead. The published quick start uses a separate Python 3.10/PyTorch 2.6/FlashAttention environment and two distributed processes. It is therefore a serious full-body candidate, but it has not been installed or benchmarked on this 16 GB card. Do not route production traffic to it until a local smoke test proves VRAM, first-frame latency, audio synchronization and cancellation. [LongCat-Video-Avatar 1.5 model card](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.5)

**Lower-memory evaluation target: OmniAvatar 1.3B.** Its official project publishes a Wan2.1 1.3B base, an OmniAvatar 1.3B audio/body adapter and a dedicated `inference_1.3B.yaml`; it is the smaller full-body route to test first on this 16 GB card. The base still includes an approximately 5.7 GB diffusion checkpoint, 11.4 GB T5 encoder and 0.5 GB VAE, so CPU offload and a separate environment are required. Downloading the checkpoints is now supported by `scripts/download_omniavatar.py`; no inference is claimed until the files finish and the model is benchmarked. [OmniAvatar repository](https://github.com/Omni-Avatar/OmniAvatar) · [1.3B weights](https://huggingface.co/OmniAvatar/OmniAvatar-1.3B)

A responsive phone-shaped interface and incremental lip-sync are progress, but they do not create natural head/body movement or full-duplex conversation. The current demo is explicitly text input with generated audiovisual replies. Long-lived WebRTC tracks, acoustic echo handling, semantic turn detection, real barge-in, browser/mobile recovery and a motion-capable portrait model still require work. Switching the LLM alone does not add those capabilities.

For a public motion-model evaluation, **SoulX-FlashHead Model_Lite** is the next credible candidate: the code/model card declare Apache-2.0 and the authors report up to 96 generated FPS on one RTX 4090. Those results are not measurements on this 4060 Ti; first-frame delay, VRAM, voice alignment and quality need a separate test. The Pro variant's reported 10.8 FPS on one 4090 is unsuitable as this machine's assumed realtime path. Audit its VAE/audio dependencies and asset rights separately. [Repository](https://github.com/Soul-AILab/SoulX-FlashHead), [weights](https://huggingface.co/Soul-AILab/SoulX-FlashHead-1_3B).

**LiveTalking** is a useful integration reference for MuseTalk, WebRTC and interruption. Its Apache code license does not automatically clear all selectable model weights; do not treat its Wav2Lip option as commercially interchangeable with MuseTalk. No LiveTalking or FlashHead installation is claimed here. [Project](https://github.com/lipku/LiveTalking). Existing component/provider/public release questions remain in [USA](USA.md); self-hosting does not establish blanket legal permission.

## Reproduce

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
git diff --check
# With an idle ready server; preserves existing conversation:
.\.venv\Scripts\python.exe scripts/verify_streaming.py
```

No cloud GPU, new hardware or paid engineer was purchased. Existing electricity planning remains an unmeasured 300W increment at $0.20/kWh ($6 per 100 hours). Optional hosted model usage adds to that budget. Local electricity is not a public-service unit cost; see [ECONOMICS](ECONOMICS.md).
