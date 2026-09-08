# Text-to-video local demo

Updated September 8, 2026. **Current interaction: type a message, receive a spoken video reply in one phone-style screen.** No microphone or camera permission is requested; both are disabled by the page's Permissions Policy. This is a private, non-explicit prototype.

## Run

On the configured PC:

```powershell
.\scripts\start_local.ps1 -Background
```

Open **http://127.0.0.1:8765**. The script avoids starting a duplicate server. Background logs and launch information live in ignored `.cache/local-poc/`. A foreground launch without `-Background` stops when its terminal closes. Startup warms models; the latest measured warm start took 12.69 seconds, but a cold start can take over a minute. A running PC and server are required; this is not a public URL or boot-time Windows service.

Try **“Let’s talk in the café. How are you?”**, **“Back to the garden. Say something cheerful.”**, or **“Send a video from there.”** Ordinary messages receive video plus voice by default. “Voice only” and “just text” change the response style through the conversation. Sound, Interrupt and Replay remain explicit controls. Memory & settings contains saved facts, notes and diagnostics.

Supported settings are living room, garden and café. These are prepared pictures of an original fictional adult character. The app generates mouth movement and speech; it cannot wave, walk, change clothing or perform arbitrary body actions. It must describe that limitation instead of claiming an unsupported action happened. It has no live view of the user.

## What was wrong, and what changed

The browser audit reproduced a real product failure: at the preview width, the old page placed video above the conversation, off screen. The user typed “show me” and the model answered that it could not display images. The existing MP4 had played successfully according to the browser, but the user could not see it from the composer. The implementation also waited for a complete phrase video, offered no contextual media routing and required manual mode/scene choices.

The current layout fits the observed 912px-high viewport without document scrolling. Captions/history scroll inside the same screen as the portrait and composer. An LLM now returns a validated reply, presentation, scene and optional factual excerpts in one decision. “From there” uses recent dialogue and the active setting. The app executes only allowlisted presentation/scene changes, never model-generated code, paths, URLs or shell commands.

Video is now **fragmented MP4 streamed while inference is still running**, played through MediaSource with synchronized H.264/AAC tracks. The output is 20 FPS, encoded in roughly 200ms fragments with about 400ms initial media buffered. If MediaSource is unsupported, the app explicitly waits for the completed MP4. Autoplay failure exposes Play reply; connection failures retry; interruptions abort playback and cancel generation. Prepared images remain visible during loading.

A microphone call experiment exposed background-noise handling problems. That flow was removed at the founder's request. ASR remains installed for diagnostics but is not on the current browser interaction path.

## Models and hardware split

| Component | Actual local selection | Resource |
|---|---|---|
| Conversation/action planner | Qwen3.5-9B, Ollama `qwen3.5:9b-q4_K_M` | GPU, thinking off; temporary default until a hosted provider is configured |
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

- **52 offline tests pass**, covering prior economics/local boundaries plus action validation, verbatim-fact restrictions, corrections, persistence, scene persistence, missing-provider credentials and media bytes arriving before a job finishes.
- Eight real Qwen planner turns correctly handled two personal facts, a lesson-day correction, recall, photo selection, contextual video selection and returning to text. Planner times were 0.87–1.90 seconds in this small synthetic sample.
- Browser audit verified contextual image display, actual video playback, visible controls and no document scroll at the observed viewport. An intermediate 25 FPS stream began after 3.10 seconds with no buffer waits.
- The first 20 FPS browser trial began after 2.36 seconds and completed server rendering at 4.33 seconds, with one buffer-wait event. Initial buffering was then increased. Three final warm replies began after **2.63, 2.56 and 2.34 seconds**, with **zero buffer waits**, while server completion took **4.64, 4.07 and 3.89 seconds**. These are samples, not a p95 claim.
- The final streaming cancellation check received 4,096 bytes while the job was still rendering and cancelled in **0.329 seconds**. Conversation/notes/facts remained unchanged; cancelled media was removed.
- Older 30-turn/ten-minute stability runs are preserved in [benchmark evidence](research/local-poc-benchmarks.json). They used the previous batch-delivery path and do not qualify this new streaming path for long calls.

Current browser captures and synthetic traces are under ignored `generated/local-app/audit/`. Real browser playback is now checked; subjective listening quality, measured phoneme alignment, mobile Safari, lengthy calls and public concurrency remain unqualified. Synthetic memory test data was isolated from the user's saved profile.

## What is still missing for FaceTime

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
