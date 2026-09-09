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
.\.venv\Scripts\python.exe experiments/benchmark_ltx23.py --reference-path generated/local-app/performance-near.png --action wave --framing close --return-to-reference --silent --frames 73 --seed 85 --temporal-size 128 --timeout 600
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

`qualify_call_modes.cjs` uses the same isolated qualification server with a fresh label, instead of the video-suite driver. Run `node scripts/qualify_call_modes.cjs new-modes` after starting the server with `--label new-modes`. It exercises six actual Text/Voice/Video turns, call navigation and browser playback using a silent synthetic microphone. Body commands in Text/Voice must request Video mode; negative commands must not. The validated `mode-honesty` run passed all six, with three nonzero/unclipped WAVs and all 40 generated video frames analyzed/visually inspected. Physical audio remains unverified.

Planner experiments use `experiments/benchmark_compact_planner.py --label fresh-label --variant compact --repeats 2`; `--variant sparse` preserves the original instructions and changes output defaults. The fixed baseline is read as literal text from commit `341aa93` (that commit must be available locally), never executed. Runs have at most 72 synthetic requests, no request retries, a $0.10 nominal reservation and stop after three request/adapter errors. Run outside call timing. No variant is selected in the app.

The complete comparison after the movement fix measured compact versus baseline at 0.433/0.536s median, 36 samples each; compact confused naming direction once. Sparse output measured 0.478/0.607s, also 36 each, but lost two fact corrections. Earlier failed/partial trials remain retained, including one adapter error and one timeout. Across all six trials, 252 scheduled requests had $0.017735 of known nominal token cost; one timeout's usage is unknown. Prices use the [September 9 model page](https://developers.cloudflare.com/workers-ai/models/qwen3-30b-a3b-fp8/), not an invoice. The original prompt remains selected.

Additional focused checks: `review_paused_voice.cjs` exercises corrected/negated resumed utterances; `review_voice_interruption.cjs` checks interruption continuity with synthetic capture. Their scope excludes physical echo. Existing exact commands and prerequisites remain in the scripts and historical evidence.

### Streaming motion replacement experiment

The existing call cannot represent arbitrary actions or left/right corrections. A separate **LongLive 2.0 5B / Wan2.2** experiment generates fresh image-conditioned motion with changing block prompts. All [pinned code, weights and optional decoder](../config/longlive2-benchmark.json), about 25.04GB including **MG-LightVAE v2**, are downloaded and verified. It remains outside the app because command following and visual quality fail.

The [upstream code](https://github.com/NVlabs/LongLive) uses Apache-2.0, while the [5B weights](https://huggingface.co/Efficient-Large-Model/LongLive-2.0-5B) use NVIDIA's Open Model License and its additional terms. [MG-LightVAE v2's model repository](https://huggingface.co/Skywork/Matrix-Game-3.0) identifies Apache-2.0. These observations do not qualify the intended adult service. The older LongLive 1.3B weights identify a noncommercial license and are not selected.

Setup is isolated: clone the exact revision in the manifest into `.cache/local-poc/LongLive2`, apply [the compatibility patch](../config/longlive2-windows.patch) with `git apply --unidiff-zero`, then install [optional imports](../config/longlive2-benchmark-requirements.txt) with `.venv/Scripts/python.exe -m pip install --no-deps --target .cache/longlive2-deps -r config/longlive2-benchmark-requirements.txt`. The patch removes an unused incompatible import and defers training imports. Do not install upstream's training environment into the app. `download_longlive2_benchmark.py` downloads/verifies the primary weights; `--light-vae-only` fetches the optional decoder. Observe an existing download's actual process/session before starting another.

`benchmark_longlive2_vae.py --label fresh-vae --vae light-v2 --latent-chunk 8 --width 384 --height 576` measures decoding synthetic repeated reference latents while the preview is idle. The original VAE lacks the expected cached method; the isolated adapter preserves causal decoder state. Both original and lightweight split decoding matched their respective ordinary 13-frame controls exactly. Three measured chunks: original **8.38–8.42 FPS / 4,322MiB peak** at 320x480; lightweight **63.25–63.43 FPS / 815MiB** at 320x480 and **42.28–42.64 FPS / 1,131MiB** at 384x576. These are decoder-only rates, not fresh motion or call FPS. Inspected reconstruction frames remain visibly softened, especially face and foliage.

With the preview deliberately stopped between calls, run `.venv/Scripts/python.exe experiments/benchmark_longlive2.py --label fresh-motion --case raise-lower --blocks 4 --repeats 2 --vae light-v2 --text-device cuda --attention-frames 32`. It requires 14GB free VRAM and separates text preparation, model loading, first decoded chunk and generation timing. It uses `weights_only=True`, native PyTorch attention and the upstream non-Triton fallback. The first attempted full run failed on missing Triton; the explicit fallback fixed execution. Restart the normal preview afterward. No private conversation or prepared motion is substituted for model input.

| Fresh motion experiment at 320x480 | Measured result | Visual decision |
|---|---|---|
| Two blocks, BF16, 16-frame history; two identical-seed runs | 61 frames; 11.05/11.67 generated FPS; first chunk 2.77/2.53s; 13.10GB peak allocation | Both hands rise; requested left arm should remain down. Soft face/fingers |
| Four blocks, BF16, 16-frame history | 125 frames in 10.86s; first chunk 2.74s; 13.11GB allocation | Both hands rise; ghosted position jumps at frames 61 and 93 |
| Four blocks, BF16, 32-frame history | 125 frames in 11.29s; first chunk 2.79s; 14.89GB allocation | Those jumps absent in this sample; both hands still rise and right arm does not fully rest down |
| Four blocks, selective FP8, 32-frame history; two identical-seed runs | 125 frames; 11.68/11.95 generated FPS; first chunk 2.62/2.42s; 11.32GB allocation | Both hands remain raised after lowering prompt; reject for live use |
| Explicit unilateral prompt, four steps, BF16, history 32 | 125 frames; 11.03 FPS; first chunk 2.82s; 14.89GB allocation | Hand stays near waist, body/background drift |
| Same prompt, original checkpoint reduced to two steps | 125 frames; 16.16 FPS; first chunk 1.96s; 14.89GB allocation | Right hand hidden/merged near waist; lowering fails |
| Trained NVFP4-S2 checkpoint unpacked into BF16, two steps | 125 frames; 15.93 FPS; first chunk 2.10s; 14.89GB allocation | Both arms rise; action timing fails; framing drifts and crops feet |

The 61-frame pair and FP8 pair are byte-identical within each pair; repeated timing is not independent quality evidence. All frames of each unique clip were visually inspected in ordered contact sheets. MP4 playback is 24 FPS, not the measured generation rate. Chunk readiness excludes speech, new-command text encoding and browser transport. Cold encoding of two prompts took 6.04s including text-model loading; later trials used the declared embedding cache. None of these short samples qualifies continuous calls or arbitrary commands.

`--precision fp8-selective` changes 270 block linears while keeping FFN output projections in BF16. The actual trained-weight microbenchmark (`benchmark_longlive2_fp8.py --label fresh-linear`) found row-wise FP8 unsupported on this GPU. Tensor-wise conversion had roughly 3.8% relative RMS error on synthetic activations, helped the FFN input projection and slowed the output projection. Whole-video tests therefore take precedence over matrix speed claims.

For the separate [S2 release](https://huggingface.co/Efficient-Large-Model/LongLive-2.0-5B-NVFP4-S2), `download_longlive2_benchmark.py --two-step-only` verifies an additional 2.95GB. Add `--checkpoint s2-dequantized --sampling-steps 2 --case unilateral-raise-lower --precision bf16` to the four-block command above. The adapter uses the pinned upstream CPU dequantizer, validates all FP4 codes/signs/scaling/cropping, and strict-loads 300 converted layers. Model loading took 27.34s including 24.85s conversion. Activations remain BF16: this is neither native NVFP4 speed nor a reproduction of published quantized quality. Five optional numerical/invalid-input tests pass. Each new configuration has one quality trial; no p95 or long-call claim follows.

### Pose-driven alternative

[RAIN](https://github.com/MatrixTeam-AI/RAIN) offers released pose-driven inference and reports about 12GiB for its demo, 8GiB after reference-model unloading. Its demonstrated desktop interface is anime face morphing, so full-body photorealistic suitability must be tested rather than inferred. The [project](https://pscgylotti.github.io/pages/RAIN/) reports 18 FPS / about 1.5s on a **4090 with TensorRT**, not this PC. [Pinned assets](../config/rain-benchmark.json) retain Apache-2.0 model-card observations for RAIN/DWPose and the separate CreativeML Open RAIL-M image-encoder terms; public-service eligibility is unresolved.

Clone the manifest revision into `.cache/local-poc/RAIN`. Install [isolated imports](../config/rain-benchmark-requirements.txt) with `.venv/Scripts/python.exe -m pip install --no-deps --only-binary=:all: --target .cache/rain-deps -r config/rain-benchmark-requirements.txt`. The app dependencies remain unchanged. `download_rain_benchmark.py` verifies 9.92GB of generator/reference/CLIP assets and `--pose-only` verifies 351MB of DWPose assets. These downloads are complete.

`benchmark_rain.py --label fresh-controls --prepare-only --frames 64 --side right` prepares a reference-aligned raise/hold/lower sequence using joint angles. Right/left controls passed bone-length and frame-bound checks, with maximum length deviation 5.55e-17. Omit `--prepare-only` for exclusive GPU rendering and restart the preview afterward. The CLIP loader verifies and removes only the redundant saved position-index buffer before strict loading.

Actual 32-frame, 512-square, four-step trials generated **2.75–2.76 FPS** with **6.63GB peak allocation**. Moving full-body controls produced detached-looking hands, merged/elongated legs and changed clothes. `--motion static` retained these defects, ruling out the moving arm as their sole cause. Adding `--pose-format face-only` improved the face/background but still changed clothing and body placement, and does not establish body control. All 96 frames across three trials were inspected; none passed. Static face-only produced zero heuristic flags despite visible defects. RAIN is set aside for full-body calls in this configuration.

The original [Wan2.1-VACE-1.3B](https://huggingface.co/Wan-AI/Wan2.1-VACE-1.3B) and [Wan inference code](https://github.com/Wan-Video/Wan2.1) identify Apache-2.0. `download_vace_benchmark.py` has verified 7.15GB of original weights and reused the cached UMT5 encoder, tokenizer and Wan2.1 VAE. [The manifest](../config/vace-benchmark.json) pins all assets. `benchmark_vace.py --label fresh-controls --prepare-only` prepares controls; after pausing the verified idle preview, omit `--prepare-only` for a 33-frame, 512-square, 30-step quality test. Restart the preview afterward. Optional RAIN pose-drawing imports are removed from the search path before loading Wan, avoiding the observed old-PEFT conflict.

`download_vace_benchmark.py --rcm-only` fetches the additional 2.84GB [rCM Wan 1.3B checkpoint](https://huggingface.co/worstcoder/rcm-Wan). Its pinned card declares Apache-2.0 and describes a Tsinghua reproduction, not an NVIDIA weight release. Add `--generator rcm --steps 4` to the benchmark. The adapter validates every base tensor, reshapes the linear patch embedding into the equivalent convolution and excludes only four named scalar training counters. Sampling follows the pinned [Apache-2.0 rCM implementation](https://github.com/NVlabs/rcm/blob/ed3cb14dd936f92cdc9f9381af7369991509b41f/rcm/inference/wan2pt1_t2v_rcm_infer.py). VACE control branches remain undistilled; this transfer has no upstream quality guarantee.

| Local 33-frame / 2.06-second pose test | Complete-clip generation | Observed result |
|---|---:|---|
| Original VACE, 30 steps | 205.55s / 0.16 FPS | Correct right-arm trajectory; reference patio changes to lawn |
| rCM, 4 steps, full mask | 26.18s / 1.26 FPS | Correct arm; different garden with umbrellas |
| rCM, `--conditioning masked-body` | 26.03s / 1.27 FPS | Reference patio/plants broadly restored; padding clips the moving hand |
| rCM, `--conditioning masked-body-open-canvas` | 26.02s / 1.27 FPS | Hand remains visible; added edge scenery and a flat right strip remain |

All 132 frames were visually inspected against the reference and evaluated with the independent body diagnostic. It detects the right arm raised in frames 6–18 and no raised left arm in every trial; black-frame and mirrored-side controls pass. This fixed skeleton misses the visually evident edge defects. Hands/faces remain soft, and the supplied trajectory raises the wrist above the prompt's stated shoulder height. No normal-speed/audio acceptance, left-hand correction, arbitrary-action planner or live streaming was tested. Peak allocated GPU memory is about 9.63GB; four-step timing includes about 7.3s control encoding, 12.9s diffusion and 5.9s decoding, excluding cached prompt preparation and roughly 2.8s model loading. Six new numerical/invalid-input checks pass. No candidate is selected in the app.

The smaller portrait experiment adds [TAEW2.1](https://github.com/madebyollin/taehv/tree/011dfc2112197741c540e0bdd5b7b67bcc930771), an approximate MIT encoder/decoder with pinned 22.64MB weights. Fetch or verify it with `.venv/Scripts/python.exe scripts/download_vace_benchmark.py --tiny-vae-only`. After pausing the verified idle preview, reproduce with `.venv/Scripts/python.exe experiments/benchmark_vace.py --label fresh-tiny-prefix --size 384 --aspect portrait --pose-profile compact --frames 17 --trajectory-frames 33 --generator rcm --steps 2 --vae tiny-both --conditioning masked-body`; always restart the preview afterward. A prefix preserves the full trajectory's timing, rather than compressing the complete movement into one second.

| 256x384, fixed seed, cached text | Inference / generated FPS | Visual result |
|---|---:|---|
| 17 frames, original VAE, 4 steps | 4.63s / 3.67 | Right hand raises; soft detail, left-edge hand clipping |
| 17 frames, tiny encoder+decoder, 4 steps | 2.27s / 7.49 | Broad control retained; moving hand smears |
| 17 frames, tiny, 2 steps | 1.34s / 12.71 | Similar action; softer face/hand |
| 17 frames, tiny, 1 step | 0.924s / 18.40 | Face/hand deformation: reject |
| 33 frames, tiny, 2 steps | 2.33s / 14.14 | Complete raise/hold/lower; blur and hand clipping remain |
| 17 frames, tiny, 2 steps, control strength 1.5 | 1.39s / 12.27 | Worse face; clipping persists: reject |

All **135 frames** including a same-latent tiny-decoder comparison were inspected. The portrait canvas removes black side padding, but does not guarantee the generated hand stays in frame. Reliable control trajectories stay bounded and the elbow is fixed; the model still deviates. The full-clip body diagnostic finds no left-arm raise and no heuristic flags despite visible defects. Peak tensor allocation is 5.45GB for tiny 17-frame tests, 6.32GB for 33 frames. Single-render timings exclude pose preparation, model loading (about 2.5-2.9s), uncached text encoding, MP4 output and playback; they are not call latency or concurrency evidence.

`benchmark_vace_decoder.py generated/local-app/audit/vace-compact-prefix-original/latents.safetensors --label fresh-decoder` checks the real retained latents with the optional tiny wrapper. It uses NTCHW [0,1] internally and applies no extra Wan latent scaling. Streaming decoding yields 17 frames, with about 7.5ms warm first-frame latency and 38ms total; state reset and cancellation/restart match exactly. Batch-versus-stream pixel MAE is 0.000161 on [0,1], below the recorded numerical limit. This measures **already generated latents**, with the idle preview resident, and proves no streaming-generation speedup. Original versus tiny decoding of the same latents differs by 0.0397 pixel MAE and needs visual judgment. No candidate passes normal-speed/audio or live-call acceptance.

Next: test generation with retained temporal state and command cancellation using the separately released causal rCM checkpoint, after verifying reference/pose compatibility. Tiny decoding is no longer the main bottleneck. No paid API or rental was used; electricity and hardware cost remain unmeasured. [Scope's VACE guide](https://docs.daydream.live/scope/guides/vace) documents experimental streaming control, but its actual [source license](https://github.com/daydreamlive/scope/blob/2aced4ded3513a76cd35f0dbfb42fbfbf5e98ab0/LICENSE.md) is CC BY-NC-SA 4.0 despite MIT package metadata; no Scope code or weights were integrated.

The pinned causal rCM checkpoint is now downloaded and hash-verified. Run `.venv/Scripts/python.exe experiments/benchmark_causal_vace_compat.py` for the CPU audit. Its 825 generator tensors transfer exactly into the VACE base while 439 VACE control tensors are retained, but the causal `WanModel.forward` exposes KV-cache state without `vace_context`, whereas `VaceWanModel.forward` exposes `vace_context` without causal KV state. The audit therefore rejects it as a drop-in runtime model. A causal VACE adapter is required before any GPU quality claim; do not select this checkpoint in the app.

Other research does not justify another large download yet: [LiveAnimate](https://github.com/liveanimate/LiveAnimate) still labels code as forthcoming; [MotionStream](https://github.com/alex4727/MotionStream) also lacks released inference in its inspected tree. [Hallo-Live](https://github.com/fudan-generative-vision/Hallo-Live) reports 20.38 FPS on two H200s. [ARDY](https://github.com/nv-tlabs/ardy) provides streaming text/spatial motion control, but its text encoder needs gated Llama access and it does not render a photorealistic person itself.

## Current evidence and decisions

| Evidence | Result and limitation |
|---|---|
| `voice-video-qualification-near-wave` | 22/22 commands; speech-end median/p95 1.556/2.277s, ten samples. 948 frames analyzed, 137 visually inspected. One palm detection flag; no functional/page errors or reported reply stalls |
| Same short call playback | Approximately 19.96 FPS replies / 24.13 FPS listening. No continuous gap over 250ms; A/V clock skew 21.59ms p95, 664 samples. Three SyncNet clips estimated 0/-40/-40ms with controls passing |
| Preview after Text/Voice movement fix | Ready in 30.878s, six sources; private memory byte-identical |
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
.\.venv\Scripts\python.exe experiments/benchmark_trt_vae.py --label fp16
.\.venv\Scripts\python.exe experiments/benchmark_trt_media.py
```

These particular build scripts retain fixed experiment paths; inspect existing outputs and their resume behavior first. Only after numerical/media review, copy `decoder.engine` and `build.json` from `audit/visual-trt-fp16` into the reviewed runtime directory, record the actual review and qualify `--decoder tensorrt-reviewed`. No script self-approves its engine. Portable Torch/CPU settings remain available.

Routine checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q local_app scripts experiments tests
node --check local_app/web/app.js
node --test tests/media-sync.test.mjs tests/microphone.test.mjs tests/call-input.test.mjs tests/playback-probe.test.cjs
git diff --check
```

Changing hardware, precision, audio backend, source footage or transport needs the relevant complete-call qualification. Keep services private, retain memory and secrets, and use the capped rental proposal in ECONOMICS only after the founder elects to provision it. A working local demonstration does not authorize a public adult service.

### MVP consolidation — September 9

Start with `./scripts/start_local.ps1 -Background` or `.venv/Scripts/python.exe -m local_app`; check with `.venv/Scripts/python.exe -m local_app --check`. Media asset validation and playback are combined in `local_app/media.py`. Speech scheduling lives in the central engine; recognition warm-up lives with the models. Five former helper modules were removed without changing their functions. README now maps the actual PWA/local demo pipeline and removes the obsolete Apple-first direction. Existing experiments remain reproducible; they are not additional app services.

Validation: 214 Python and 32 browser regression tests pass. A fresh isolated synthetic voice-command test produced a prepared wave with generated speech/lips: 40 decoded frames, non-silent audio, private memory unchanged. Cold reply took 15.79s including visual model loading; the warm repeat completed in 0.905s (0.052s ASR, 0.710s rendering). Preview was resident; this is one sample per state, not a p95, perceived latency or arbitrary-motion result. Browser playback, physical audio and perceptual sync were not tested in this run.

Cloudflare comparison through the real dialogue adapter: Qwen3-30B-A3B-FP8 passed four synthetic checks in 0.663–0.738s; Granite-4.0-H-Micro passed in 1.494–2.721s; GLM-4.7-Flash exhausted 512 output tokens after 8.239s and failed its first case. Qwen remains selected. Nine requests total; nominal cost from stored benchmark rates is $0.000701397, not a verified invoice. Cache bypass was requested; the provider returned UNKNOWN cache status. Evidence: `docs/research/local-poc-benchmarks.json`, key `mvp_consolidation_20260909`.

Benchmark programs now live in `experiments/` (42 moved files). `scripts/` retains setup, launch and qualification tools. Historical JSON evidence keeps the paths used at measurement time; current runnable commands above use the new paths. All 214 Python checks pass after the move, the Cloudflare comparison and VACE command-line entry points load, and the causal checkpoint audit still passes. Startup remains `./scripts/start_local.ps1 -Background`; no new service, key or runtime dependency was added.

Additional moved-entry-point comparisons: Llama-3.1-8B-Instruct-FP8-Fast passed four checks at 0.662–0.974s; Llama-3.2-3B-Instruct ran at 0.379–0.591s but omitted message delivery in one of four cases. Qwen remains selected. These small synthetic trials do not establish call latency or p95. Evidence key: `mvp_experiment_layout_20260909`.

### Stop-command correction — September 9

“Stop moving” now suppresses the prepared body loop across subsequent replies; a new movement releases the hold. Close-view reference and reset behavior are covered. An isolated local GPU test kept every raw lower-body frame identical while generating speech/lips (24 rendered frames, non-silent audio). First media took 8.512s including preparation; rendering alone took 0.715s. This is not a live-call latency or perceptual-sync pass. Private memory was unchanged. All 220 Python tests pass. Evidence: `generated/local-app/audit/stop-pose-smoke-raw/result.json`. Remaining priority: reduce first-response preparation and test renderer output through WebRTC with interruption.

Timing follow-up: separate load/preparation telemetry now identifies the cold bottleneck. A fresh isolated run took 8.762s to first media: 7.628s loading, 0.156s scene preparation, 0.694s rendering. Three resident repeats took 0.916/0.922/0.914s, with no reload and 0.084–0.085s preparation. This short synthetic stop command used local inference; no remote GPU/API charge was incurred, and electricity was not measured. Browser playback, arbitrary motion and p95 remain unverified. Evidence: `generated/local-app/audit/stop-pose-timing/timings.json`.

### Cloudflare WebRTC transport qualification — September 9

`experiments/benchmark_cloud_realtime.py --media both` creates a temporary SFU app with the existing Cloudflare key/email, sends synthetic CPU video and a tone between two peers through Cloudflare, then closes peers and deletes that app. No new credential file, private conversation, camera, local GPU or GPU rental is used. The default Python client header hit HTTP 403 / 1010; an explicit project User-Agent fixed API access. VP8 delivered audio but no video; MAX_BUNDLE repeatedly timed out publishing. H.264 with balanced bundling delivered 151 video frames and 323 audio frames, with both peers connected and nonzero audio amplitude. Both media types first arrived 1.593s after renegotiation, followed by a five-second sample. This is setup-to-media timing, not one-way latency, perceptual sync or an inference call benchmark. GPU/inference cost was zero; SFU billing was not measured. The temporary app deletion succeeded.

217 Python tests pass. The live app remains the local baseline; no public app or remote GPU is deployed. Next: feed real renderer frames and speech into this transport and measure playback/cancellation, preserving scene state. [Cloudflare API lifecycle](https://developers.cloudflare.com/realtime/sfu/https-api/) and [official echo example](https://github.com/cloudflare/realtime-examples/tree/main/echo). Evidence key: `cloud_realtime_transport_20260909`.

Transport timing follow-up: a 320×180 H.264 synthetic stream with an embedded frame counter measured 62.0ms median / 78.5ms p95 / 94.0ms maximum across 152 decoded frames through Cloudflare. This includes encoding, SFU transport and decode/jitter buffering on two same-host peers; it excludes generation, browser display, and real-user network variation. Setup to both media took 2.313s. Audio was nonzero, both peers connected, and temporary app deletion succeeded. This supports testing a persistent connection rather than renegotiating per reply; it does not establish call latency. SFU cost was not measured. Evidence key: `cloud_realtime_transit_20260909`.
