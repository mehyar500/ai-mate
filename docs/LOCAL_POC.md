# Local companion runbook

Updated September 9, 2026. This is a private, neutral demonstration on the founder's RTX 4060 Ti **16GB VRAM / 48GB RAM / i9**. It combines prepared photographic movement with newly generated speech and lips. Arbitrary realistic live movement, public access and intended adult-service eligibility remain unqualified.

[REPORT](REPORT.md) owns current results and decisions; [BUILD](BUILD.md) owns the processing flow and exact active models; [ECONOMICS](ECONOMICS.md) owns prices; [USA](USA.md) owns commercial eligibility. This runbook covers operation, reproduction and retained experiments. Historical detail remains in [machine evidence](research/local-poc-benchmarks.json), ignored local audit media and Git history through `a8b90a1`.

## Start and use the configured preview

```powershell
.\scripts\start_local.ps1 -Background
```

Open **http://127.0.0.1:8765** and wait for readiness. The process and PC must remain running. The launcher avoids duplicates and writes logs/process information under `.cache/local-poc/`; it is not a public URL or Windows startup service. A fresh checkout does not contain the private generated demonstration assets.

Select Call Mira, Voice or Video to request microphone access. Video keeps the character prominent and has mute, interrupt and end controls. The keyboard icon opens optional compact text input: Enter sends, Shift+Enter adds a line, Escape closes it. Typing also works with microphone permission denied. Text retains its separate draft while an ongoing call stays connected; Return to call restores it. Ending the call releases microphone capture. Camera access is disabled.

Try **“Come closer” → “Wave hello” → “What is my dog's name?” → “Step back.”** Supply the dog's name first. Both known poses have matching listening footage and right-hand waves. Unsupported movement must be acknowledged honestly. An interrupted movement holds the displayed pose; unknown positions cannot use a prepared wave. Repeating a gesture reuses footage rather than generating a unique body performance.

Memory & settings contains editable notes/facts, optional call captions, Test sound and diagnostics. Mira knows only what was shared. Removing a fact does not remove it from recent exchanges; Clear all removes both. **Preserve `generated/local-app/memory.sqlite3` during updates.** Never use that database as benchmark input.

The layout passed five Chromium sizes from 320x568 to 1280x720. Full-body footage keeps its head and feet in tall layouts; wide gestures may cross the phone crop. Buttons have 44px touch targets. Real iPhone/Android PWA, VoiceOver, physical speakers/microphone and acoustic echo remain unverified.

## Runtime and recovery

Exact weights, revisions and dependency versions are pinned in [local-models.json](../config/local-models.json), [local-assets.json](../config/local-assets.json) and [local-poc-requirements.txt](../config/local-poc-requirements.txt). BUILD lists every active pipeline model. The selected PC settings are:

| Setting | This PC | Portable recovery |
|---|---|---|
| Dialogue | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | Explicit alternative provider only |
| `AI_MATE_ASR_DEVICE` | `cuda`: Whisper Base English FP16, eight threads | `cpu`: same weights, int8 |
| `AI_MATE_TTS_DEVICE` | `cuda`: Kokoro-82M ONNX v1.0, `af_sarah`, eight host threads | `cpu` |
| `AI_MATE_VISUAL_DECODER` | `tensorrt`: reviewed local FP16 engine | `torch` |
| `AI_MATE_ASR_PAUSE_WARM` | `0` | Leave disabled |

Use [.env.example](../.env.example) for implemented fields. Cloudflare accepts the existing global API key plus email; both take precedence over the alternative token. Only Cloudflare credential fields are read from `AI_MATE_ENV_FILE`; process overrides win. MiniMax requires its process environment key. Never print credentials or copy the founder's broad environment file to a remote worker.

CUDA speech uses ONNX Runtime **1.26.0** in `.cache/ort-gpu-deps`, with existing Torch CUDA 12.8/cuDNN 9 libraries. Unused speech arena memory is released after inference. The 2GiB arena setting is not a total VRAM cap. Runtime version/location and actual GPU provider are checked; mismatches fail explicitly. Revert the corresponding setting and restart between calls. No automatic model/provider fallback masks a failed selection.

The TensorRT decoder uses the same SD VAE predictions, batch eight. `.cache/local-poc/musetalk-vae-trt/{decoder.engine,build.json}` must match reviewed engine/source hashes, GPU, Torch and TensorRT versions. Rebuild/requalify on another GPU; do not assume Windows engine portability. A failed visual warm-up leaves text/voice available.

Current render settings: **384x576, 20 FPS**, 256x256 face region, face shift **-0.05**, six Whisper context steps, face-appearance encode stride two. FFmpeg uses CPU libx264 because this PC's installed NVENC/driver combination is incompatible. The client consumes 200ms fMP4 fragments after at least 350ms is buffered. A separate WAV follows the video clock and pauses during stalls; the video's embedded audio is muted. Unsupported MSE waits for the finished file; autoplay rejection exposes Play reply. A/V clock checks do not prove physical audibility.

Microphone capture keeps the **650ms endpoint pause**. Speech resumed before playback cancels/recombines an unfinished spoken turn, capped at 30 seconds. It never combines typed replacements, different devices/calls or already-playing replies. Playback interruption depends on reported echo cancellation and retains the observed video timestamp. End/mute clears temporary recording buffers.

## Prepare graphics separately from calls

Heavy image/video preparation must run while call inference is idle. ComfyUI is a separate installation, pinned to `00d34d92fe0afbfbab3893ebbab2d5d70f5e9882`, in `.cache/local-poc/ComfyUI` with `.cache/comfy-env`. Its launcher disables custom/API nodes, reserves 4GB VRAM and binds only to loopback 8188:

```powershell
.\scripts\start_motion.ps1 -Background -FastFP8
```

LTX-2.3 22B distilled FP8 and its Gemma-3-12B mixed-FP4 encoder require about **39GB of weights**, beyond other caches/environments. [The downloader](../scripts/download_ltx23_benchmark.py) pins sizes/hashes and requires 45GB free workspace disk. Prompt encoding runs on CPU; diffusion offloads on 16GB. The smaller experimental LTX-Video 2B/T5 path has a [separate pinned downloader](../scripts/download_ltx_motion.py). Downloading a model does not select it or establish commercial permission.

Prepared assets in `generated/local-app/`:

| Files | Purpose |
|---|---|
| `fullbody.png` | Original full-body identity/reference |
| `performance.json`, `performance-closer.mp4`, `performance-farther.mp4`, `performance-near.png` | Matched approach, reverse return and near reference |
| `performance-wave.json/.mp4` | Base-pose gesture |
| `performance-near-wave.json/.mp4` | Separate near gesture; requires `pose: near` |
| `idle-fullbody.json/.mp4`, `idle-near.json/.mp4` | Matching silent listening loops |

Manifests must explicitly record local review and match every required reference/video hash. A broken optional gesture disables only that gesture. Appearance warm-up covers at most **six sources, 144 frames each, 384x576**. Only source appearance is cached; generated mouths and user speech are not. Sequential face correspondence resolves the palm false positive in reviewed near-wave footage. Raw detector flags remain in frame reviews; fresh generation keeps strict single-face detection.

Use isolated candidate bundles; inspect each reference before generating from it. The current approach is three seconds from seed 96 with a reviewed end reference; the final corrective guide frame was excluded. The return reverses that approach. Base wave is two seconds. Near wave is 2.125 seconds from seed 85, without speeding up motion. A 128-frame temporal VAE window removed the earlier double-image defect. Fingers, mouth detail and transition seams still need improvement.

Example: create another near-wave candidate using the currently reviewed near reference. These commands perform local generation and preserve existing assets:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_ltx23.py --reference-path generated/local-app/performance-near.png --action wave --framing close --return-to-reference --silent --frames 73 --seed 85 --temporal-size 128 --timeout 600
```

Use the returned local MP4 path as `SOURCE.mp4` below, and a fresh lowercase label:

```powershell
.\.venv\Scripts\python.exe scripts/review_motion_frames.py SOURCE.mp4 --label new-source
.\.venv\Scripts\python.exe scripts/prepare_performance.py SOURCE.mp4 --action wave --pose near --duration 2.125 --candidate-label new-near-wave
```

Preparation intentionally writes an unreviewed manifest. Review the source and prepared clip frame by frame, normal-speed motion, direction and seams before recording a truthful review. Qualify that candidate with the call suite below. Promote only the matching assets between calls, keep a rollback copy, and restart to rebuild the appearance cache. Never change the memory database. New reference images use `prepare_local_scene.py --scene fullbody --candidate`; they also require review before promotion.

For new listening footage, `prepare_idle_loop.py SOURCE.mp4 --pose near --performance-label new-bundle` uses the matching candidate near reference. `retime_idle_motion.py` can slow background motion while preserving a separately selected bilateral blink interval; it does not choose or validate the blink. Keep retimed footage within 144 frames, inspect interpolation/seam artifacts, and record the output review. Exact selected generation/retiming settings and hashes remain in machine evidence.

## Repeatable call qualification

Use `.venv\Scripts\python.exe`, FFmpeg on PATH, and Node with Playwright available. On this PC:

```powershell
$env:NODE_PATH='C:\Users\mehya\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
```

The isolated server uses **127.0.0.1:8766**, synthetic notes/audio and the existing hosted dialogue credentials. It never copies live conversation. The unchanged core suite has 20 commands; `--near-wave` adds a near gesture and following memory reply. The 30-minute soak runs six cycles: **120 core or 132 expanded interactions**. Use a fresh label to preserve earlier evidence.

Terminal one, using the reviewed `near-wave` bundle already retained on this PC:

```powershell
.\.venv\Scripts\python.exe scripts/serve_voice_video_benchmark.py --trial qualification --label new-call --performance-label near-wave --near-wave --decoder tensorrt-reviewed --asr-device cuda --tts-device cuda
```

Terminal two:

```powershell
node scripts/qualify_video_call.cjs qualification new-call --capture
```

For a new candidate, replace `--performance-label near-wave` with its reviewed bundle label. For the sustained test, use `--trial soak` and Node's `soak` argument with the same fresh label. The driver waits up to 90 seconds for startup, alternates synthetic speech and text, exercises real AudioWorklet/VAD/ASR/planning/TTS/render/playback, and closes the server through its completion marker. Three failed soak turns stop it early while preserving failures. An observation timeout does not mean the job stopped: inspect the actual process before restarting.

`--capture` measures from the last synthetic speech block above the detector's energy floor to both audio/video playback. Default WAV injection excludes capture/endpoint waiting. Deliberate interruptions are excluded from response percentiles. Neither mode measures physical acoustics or public/mobile networks. Frame callbacks measure continuous visible playback, resetting on actual pause/seek/source/visibility changes.

After timing and both processes finish:

```powershell
.\.venv\Scripts\python.exe scripts/review_call_frames.py --trial qualification --label new-call
.\.venv\Scripts\python.exe scripts/build_call_review.py --trial qualification --label new-call
.\.venv\Scripts\python.exe scripts/review_lip_sync.py --source voice-video-qualification-new-call --label new-sync --device cuda
```

Use the corresponding `soak` names for a sustained run. Each review page checks retained media coverage/hashes and supports playback, exact frame stepping, flags and browser-local notes/export. Serve **only the synthetic audit directory**, never the live database folder:

```powershell
.\.venv\Scripts\python.exe -m http.server 8771 --bind 127.0.0.1 --directory generated/local-app/audit/voice-video-qualification-new-call
```

Choose a free port. Review checkboxes stay unchecked until someone actually records the observation. Generated audio can be nonzero, unclipped and unmuted yet remain inaudible at the physical speakers.

SyncNet v2 is installed as an offline evaluator under `.cache/local-poc/syncnet-evaluator`; [its manifest](../config/syncnet-evaluator.json) records model, dependency, code hashes and research scope. `download_syncnet_evaluator.py` restores the pinned assets without changing app packages. It compares actual decoded timestamps and the app's separate WAV, uses 40ms offset resolution and calibrated injected-delay/reversed-audio controls. It is not a human-perception or commercial-license certificate.

The new OpenCV Zoo MediaPipe [person](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/person_detection_mediapipe) and [pose](https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/pose_estimation_mediapipe) diagnostic is CPU-only and offline. Both directories state Apache-2.0; code, licenses and weights are hash-pinned in [body-evaluator.json](../config/body-evaluator.json). It estimates person presence, joint confidence, raised wrists and abrupt projected limb changes. Its fixed skeleton cannot count extra limbs or certify identity/anatomy. Run after timing; inspect flags visually:

```powershell
.\.venv\Scripts\python.exe scripts/download_body_evaluator.py
.\.venv\Scripts\python.exe scripts/review_body_motion.py --source voice-video-qualification-new-call --label new-body
```

Additional focused checks: `review_paused_voice.cjs` exercises corrected/negated resumed utterances; `review_voice_interruption.cjs` checks interruption continuity with synthetic capture. Their scope excludes physical echo. Existing exact commands and prerequisites remain in the scripts and historical evidence.

## Current evidence and decisions

| Evidence | Result and limitation |
|---|---|
| `voice-video-qualification-near-wave` | 22/22 commands; speech-end median/p95 1.556/2.277s, ten samples. 948 frames analyzed, 137 visually inspected. One palm detection flag; no functional/page errors or reported reply stalls |
| Same short call playback | Approximately 19.96 FPS replies / 24.13 FPS listening. No continuous gap over 250ms; A/V clock skew 21.59ms p95, 664 samples. Three SyncNet clips estimated 0/-40/-40ms with controls passing |
| Preview after near-wave promotion | Ready in 30.883s, six sources; private memory byte-identical |
| Earlier `voice-video-soak-speech-arena` | 30 minutes / 120 commands without failures. Speech-end 2.043/2.500s, 54 samples. 5,945 frames analyzed. Predates shortened base wave, near wave and new tracking |
| `voice-video-soak-near-wave` | 30 minutes / 132 commands, no failures. Speech-end midpoint median/p95 1.773/2.530s, 60 samples. Approximately 19.93/24.07 FPS reply/listening; no continuous gap >250ms. A/V skew 24.11ms p95, 4,003 samples. Six SyncNet estimates 0/-40ms with controls passing; all 5,716 frames analyzed |

The body evaluator completed 948 short-call and 5,716 sustained-call frames. It retained 16/96 flags respectively: repeated person-count ambiguity and a projected-limb change during hand lowering. All flags plus hand context were visually inspected (19/114 frames); one figure is visible on the two-person flags, and hand blur persists. Black-frame and mirrored-raise controls passed. Detailed joint outputs and review selections remain in `body-near-wave` and `body-near-wave-soak`; these diagnostics are not anatomy or perceptual acceptance.

All paths above are under `generated/local-app/audit/`. Metrics are measured samples, not SLAs. Browser summary JSON uses nearest-rank percentiles; this sustained run's nearest-rank p50 is 1.564s, while the midpoint median is 1.773s. Targets remain p95 <=2s from speech end, >=20 FPS with a 25 FPS target, <=100ms perceptual sync and stable 30-minute state. Physical audio, real mobile, natural motion, arbitrary movement and public eligibility are still open. REPORT is the current acceptance summary.

Keep these selected improvements: local GPU recognition; validated PCM decoding; same-voice CUDA speech with allocator cleanup; reviewed TensorRT VAE; phrase output with one speech phrase ahead; six-source appearance priming; reviewed body footage and constrained pose continuity.

| Rejected or deferred experiment | Why it is not selected |
|---|---|
| Recognition warm-up during pauses | Component median improved, but complete-call p95 varied 2.13–2.56s; disabled |
| Short Whisper encoder windows / earlier turn decisions | Harder tests exposed punctuation/latency or unfinished-utterance risks; preserve normal padding and endpoint |
| 150ms video buffer / batch-16 rendering | Playback regressions; keep 350ms threshold and batch eight |
| CUDA graphs | About 0.85% isolated gain; insufficient demonstrated benefit |
| Supertonic-3, Tiny/Moonshine ASR | Accuracy/quality or integrated-benefit gaps; no replacement selected |
| FlashHead Lite 1.3B | Local 31-second throughput demonstrated around 5GB tensor allocation, but imperfect mouth/framing and no arbitrary body commands |
| Cloudflare Aura speech / Gemini 3.5 Flash-Lite planner | No demonstrated whole-call advantage over selected Kokoro/Qwen |
| Gateway LTX-2.5 Fast | About 31.8s to local availability for a five-second clip; two tests cost $0.90 total. Different text-generated identity; unsuitable for immediate calls |
| Local aiortc WebRTC prototype | H.264/Opus transport works in isolation, but no full-call speed advantage or public-network qualification demonstrated |

Experiment settings, sample counts, failures, official source links and hashes remain in machine evidence. Detailed older narrative is retrievable from Git; no audit media is removed by this consolidation. Independent public-release review and staging remain pending.

## Rebuild dependencies on a new machine

Installed baseline: Python **3.12**, Torch **2.11.0+cu128**, FFmpeg. Use an actual Python 3.12 executable to create the environment; Windows' bare `python` may be an unavailable Store alias.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r config/local-poc-requirements.txt
.\.venv\Scripts\python.exe scripts/download_local_models.py --assets-only
.\.venv\Scripts\python.exe scripts/download_local_models.py --models asr-base-en musetalk sd-vae whisper-tiny klein
```

This sets up core inference, not the separate ComfyUI installation or reviewed private footage. Optional GPU speech uses the [pinned Windows/Python wheel](../config/speech-gpu-benchmark-requirements.txt):

```powershell
.\.venv\Scripts\python.exe -m pip install --target .cache/ort-gpu-deps --no-deps --only-binary=:all: --require-hashes -r config/speech-gpu-benchmark-requirements.txt
```

TensorRT installation/build comparison is separate and hardware-specific:

```powershell
.\.venv\Scripts\python.exe -m pip install --target .cache/tensorrt-deps --no-deps -r config/tensorrt-benchmark-requirements.txt
.\.venv\Scripts\python.exe scripts/benchmark_trt_vae.py --label fp16
.\.venv\Scripts\python.exe scripts/benchmark_trt_media.py
```

These particular build scripts retain fixed experiment paths; inspect existing outputs and their resume behavior first. Only after numerical/media review, copy `decoder.engine` and `build.json` from `audit/visual-trt-fp16` into the reviewed runtime directory, record the actual review and qualify `--decoder tensorrt-reviewed`. No script self-approves its engine. Portable Torch/CPU settings remain available.

Routine checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q local_app scripts tests
node --check local_app/web/app.js
node --test tests/media-sync.test.mjs tests/microphone.test.mjs tests/call-input.test.mjs tests/playback-probe.test.cjs
git diff --check
```

Changing hardware, precision, audio backend, source footage or transport needs the relevant complete-call qualification. Keep services private, retain memory and secrets, and use the capped rental proposal in ECONOMICS only after the founder elects to provision it. A working local demonstration does not authorize a public adult service.
