# Local companion demo

Updated September 8, 2026. One private, non-explicit companion on the founder's RTX 4060 Ti **16GB VRAM / 48GB RAM**. Text, Voice call and Video call share memory. The current result combines reviewed photographic movement with newly generated speech and lip movement. It is not unrestricted live video generation or a released native app.

## Run and try it

On this configured PC:

```powershell
.\scripts\start_local.ps1 -Background
# Needed for fresh, experimental movements and offline preparation:
.\scripts\start_motion.ps1 -Background -FastFP8
```

Open **http://127.0.0.1:8765** and wait for model warm-up. Background launch avoids duplicate servers; logs and process information stay in ignored `.cache/local-poc/`. The PC and process must stay running. This is a loopback URL, not a public deployment or Windows startup service.

In Video call, try **“Come closer.” → “Say hello.” → “Step back.”** The reviewed approach moves from full body to close view; its reverse returns to full body even after intervening conversation. Each pose has a blinking listening loop. These are a limited set of prepared movements, disclosed in Memory & settings. Wave uses experimental fresh generation and can fail framing, hand count or direction; arbitrary body commands are not implemented.

Select Call Mira (phone icon on wider screens), or Voice/Video to start microphone input. Calls have mute/end icons and automatic sound; their composer is removed. Text has the message composer and shows messages without ending an active call; Return to call restores the same media elements. “Send me a message saying hello from our call” delivers a separate in-app message with an unread badge. End call releases capture and stops playback. Memory & settings contains facts, notes, diagnostics, the prepared-footage disclosure and Test sound. Camera access is disabled.

The video fills the height when controls fit in the side space. Tall phone views trim side background without cropping the top/bottom of full-body footage; very wide gestures may extend outside that phone crop. Compact tabs and controls replace the technical overlays. At 716x854, the stage increased from 544px to 854px tall (57%); checked layouts at 320x568, 390x844, 716x854, 844x390 and 1280x720 have no horizontal overflow or overlapping header controls. Synthetic browser checks cover denied microphone permission, returning between Text and the active call, and ending the call. These checks do not qualify physical audio or Safari.

## Models actually used

| Component | Selection | Where and when |
|---|---|---|
| Conversation / bounded plan | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | Hosted JSON response; exact simple body commands bypass the network |
| Speech | Kokoro-82M ONNX v1.0 float32, `af_sarah` | CPU, four threads; new WAV per reply |
| Recognition | faster-whisper Base English int8 | CPU; opt-in microphone or synthetic WAV |
| Lip movement | MuseTalk 1.5, SD VAE ft-mse, Whisper-tiny audio encoder | Local GPU FP16; batch eight; 20 FPS output |
| Face tracking | OpenCV YuNet 2023mar | CPU; tracks supplied body footage |
| Reviewed movement / listening preparation | LTX-2.3-22B distilled FP8 with Gemma-3-12B mixed FP4 text encoder | Offline native ComfyUI graph; prompt encoder on CPU, diffusion offload on 16GB |
| Experimental new movement | LTX-Video 2B 0.9.8 distilled FP8 + T5-XXL FP8 | Local ComfyUI, eight steps; not reliable arbitrary motion |
| Reference image preparation | FLUX.2 Klein 4B | Separate GPU process; review still images before generating video |
| Delivery | FFmpeg libx264/AAC, fragmented MP4 plus synchronized WAV | CPU encoder; installed FFmpeg/NVENC driver pair is incompatible |

Pins: [models](../config/local-models.json), [assets](../config/local-assets.json), [Python dependencies](../config/local-poc-requirements.txt), [LTX-2B downloader](../scripts/download_ltx_motion.py), [LTX-2.3 downloader and SHA-256](../scripts/download_ltx23_benchmark.py). ComfyUI is pinned to `00d34d92fe0afbfbab3893ebbab2d5d70f5e9882`, with custom/API nodes disabled and 4GB VRAM reserved. The isolated environment is `.cache/comfy-env`; motion API is loopback port 8188. Do not expose this unauthenticated development service.

Open weights do not automatically establish commercial rights. MuseTalk's model grant, dependency licenses, LTX's community license/use policy, voice and reference-image provenance each matter. [BUILD](BUILD.md) retains model comparisons and primary sources; [USA](USA.md) contains unresolved release conditions. No public or adult deployment is approved.

## Central flow and visual continuity

`local_app/engine.py` owns all modalities, job cancellation, pose state and memory:

```text
typed input / opt-in mic -> local ASR if needed
    -> direct supported command OR Cloudflare conversation plan
    -> Text: text only; Voice call: new Kokoro speech
    -> Video call:
         base + closer -> reviewed approach -> near
         near + farther -> reviewed reverse -> base
         conversation at base/near -> corresponding listening footage
         other supported action -> experimental LTX-2B generation
       -> track face -> new MuseTalk lips -> streamed video + synchronized speech
    -> successful server completion: conversation, facts, message and generated pose
    -> completed browser playback: switch to the matching listening loop
```

Scene changes require a current visual request. Talking about a garden does not reset a close view to the garden portrait. The planner receives the trusted current pose; it cannot execute code, paths, URLs or shell commands.

Prepared assets must have an explicit local review flag and matching reference/video hashes. Fixed files: `performance.json`, `performance-closer.mp4`, `performance-farther.mp4`, `performance-near.png`, plus `idle-fullbody.json/.mp4` and `idle-near.json/.mp4`. They are private generated artifacts, not in Git. Preparation scripts default to unreviewed. Missing/changed/unreviewed assets fall back to the experimental renderer or held portrait; a fresh checkout does not contain the demonstration clips.

Listening footage continues while a reply buffers, pauses when the reply actually plays, and resumes in the correct pose afterward. Longer speech loops the prepared body instead of freezing its last frame; physical action clips never loop. Text/Voice navigation and backgrounding pause hidden idle playback. A bounded appearance cache reuses decoded source frames, face tracking and VAE appearance latents for at most two short reviewed clips. User speech and generated mouth frames are not cached there.

Successful fresh video captures its final decoded frame as the next reference. Unknown positions disable known-pose loops. The older one-shot reverse cache remains only for an unprepared approach followed immediately by a return. Failed/cancelled generation cannot commit a new pose. Restart clears transient pose/return files and starts at the base pose while preserving conversation. **The server tracks the last generated pose, not the exact frame seen during interrupted playback; mid-motion interruption continuity is still open.**

## Measured results and failures

These are individual local samples, not p95, guarantees or comparable measurements of every configuration. [Machine-readable history](research/local-poc-benchmarks.json) preserves settings and rejected trials. Raw synthetic traces and reviewed contact sheets stay in ignored `generated/local-app/audit/`.

| Test | Observed result | Limit |
|---|---|---|
| Prepared approach → greeting → return | Browser starts 1.72s / 2.16s / 1.83s, zero stalls; unmuted audio ended; matching idle resumed | Prepared movement, newly synthesized speech/lips; not fresh diffusion |
| Synthetic spoken “Come closer” through real audio API | ASR 0.445s; server complete 3.085s | No physical mic/speaker or browser round trip in this sample |
| LTX-2.3 approach, 97 frames, seed 70, silent | 146.429s cold wall time; reviewed approach succeeded | Offline preparation; slight camera drift, soft face remain |
| LTX-2.3 close idle | Generic prompts were static or zoomed/pulled back; rejected. Blink-only guided 97 frames took 28.482s with cached prompt | Selected 3.792s loop visibly repeats over long sessions |
| LTX-2.3 joint audio/video wave | 144.974s cold / 21.445s with cached text conditioning | Coherent wave but unwanted subtitle-like marks; too slow for live replacement |
| Direct LTX-2B body-only generation | Warm 4.50s at 384x576; 3.19s at 320x480; 2.00s at 256x384 | Excludes speech/lips/browser. Fastest raised both hands; backward test moved forward |
| OmniAvatar-1.3B, Wan2.1 / UMT5 / Wav2Vec2 dependencies | Two short clips took 60.5–67.5s and did not wave | Rejected configurations |

The paired-motion demonstration is a real improvement, but the requested quality is not accepted: loops repeat, scene identity differs across older portraits, fingers and mouth detail remain soft, and new movements can ignore instructions. A 13.092s spoken count before appearance caching took **9.97s to playback**, **23.489s server completion**, and stalled twice; short greetings alone do not qualify long calls. Later cache measurements are recorded in the machine evidence and REPORT.

Output files contain speech, local ASR recovered synthetic test sentences, and the browser completed unmuted playback without media errors. Physical speaker output and subjective phoneme/voice quality still need device testing. Jobs record first text, per-chunk speech generation time, rendering stages, cache hits and completion; the browser separately measures first playback and stalls.

Latest listening review: `benchmark_ltx23.py --idle-style calm` produced candidates in 143.227s (129 frames, seed 80) and 83.033s (97 frames, seed 81). Both kept the eyes closed for roughly one second despite a short bilateral-blink prompt. `review_idle_motion.py` measures side-strip optical flow and creates eye contact sheets; lower flow is not visual acceptance. Neither candidate is active. The fast-foliage/wink complaint remains open; whole-clip slowdown would further lengthen the blink.

`benchmark_cloud_speech.py` makes at most six synthetic requests using the existing Cloudflare authentication, without reading conversation. [Aura-2 English](https://developers.cloudflare.com/workers-ai/models/aura-2-en/) (`@cf/deepgram/aura-2-en`, `luna`) lists $0.03/1,000 input characters. First 4KB arrived in 0.278–0.395s; complete WAVs took 0.750–0.818s for 16 characters, 1.851–1.873s for 62, and 6.014–7.264s for 215. Six listed costs total $0.01758; an earlier 16-character request with an unknown-length WAV header failed local parsing, adding a nominal $0.00048. These are computed list prices, not an invoice. The parser now measures actual PCM length. Cloud speech is **not selected**: first bytes are not usable synchronized video, and long complete-file latency is still poor. Streaming audio would require incremental speech features/rendering, not just changing the provider.

## Playback, microphone and memory

The browser consumes about 200ms MP4 fragments with about 400ms initial media buffered. Its embedded audio stays muted; a separate WAV follows the video clock, pauses during stalls and corrects drift above 120ms. If MediaSource is unsupported, playback waits for the finished file. Autoplay rejection exposes Play reply. Interrupt aborts both tracks. These paths have Node tests, but mobile Safari and lengthy calls remain unqualified.

Microphone capture uses AudioWorklet, mono PCM16 WAV, 200ms pre-roll, a 650ms silence boundary and a 25s turn cap. It pauses during synthesis/playback, resumes 450ms afterward, and requests browser echo cancellation/noise suppression. This is half-duplex, not natural speech barge-in. Raw capture stays in memory; the transcript enters local history and hosted dialogue context.

SQLite keeps editable notes, up to 50 exchanges (12 shown, four sent as recent context) and up to 12 bounded verbatim fact excerpts. Users can inspect, correct and delete saved information. It knows only what was shared; automatic check-ins, calendar integrations and push notifications are unimplemented. Preserve `generated/local-app/memory.sqlite3` during normal updates.

Private `.env` loads only `AI_MATE_LLM_PROVIDER`, `AI_MATE_LLM_MODEL` and `AI_MATE_ENV_FILE`; process/launcher overrides win. This PC selects `C:\Users\mehya\.env` for Cloudflare account ID, API key and email (`X-Auth-Key` / `X-Auth-Email`). A scoped token is an alternative. Secrets never reach browser/artifacts. Hosted dialogue receives text, recent context and saved notes; images, video and raw audio stay local. MiniMax/Ollama are explicit alternatives; subscriptions are not presumed API entitlements. [.env.example](../.env.example) contains only implemented configuration.

## Reproduce or extend

Current environment: Python 3.12, PyTorch 2.11.0+cu128, FFmpeg. Core setup commands for a fresh Python environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.\.venv\Scripts\python.exe -m pip install -r config/local-poc-requirements.txt
.\.venv\Scripts\python.exe scripts/download_local_models.py --assets-only
.\.venv\Scripts\python.exe scripts/download_local_models.py --models asr-base-en musetalk sd-vae whisper-tiny klein
```

Ollama is optional and unloaded on this PC; the active dialogue route is Cloudflare. ComfyUI and its isolated environment are separately installed; the app launcher does not install them. Large downloads require adequate disk space: LTX-2.3 and its prompt encoder add about 39GB, excluding other models/environments. Downloads do not select a runtime automatically.

Prepare/review references while other GPU inference is idle. Never replace active assets during a call. The approach and close-idle sequence uses the installed benchmark:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_local_scene.py --scene fullbody --candidate
# Review the candidate before promoting it to the active fullbody.png.
.\.venv\Scripts\python.exe scripts/benchmark_ltx23.py --action closer --frames 97 --seed 70 --silent --timeout 300
.\.venv\Scripts\python.exe scripts/review_local_video.py <local-source.mp4>
.\.venv\Scripts\python.exe scripts/prepare_performance.py <reviewed-approach.mp4>
# Review the forward/reverse clips and performance-near.png before marking the manifest reviewed.
.\.venv\Scripts\python.exe scripts/benchmark_ltx23.py --action idle --frames 97 --seed 75 --silent --framing close --reference-path generated/local-app/performance-near.png --return-to-reference
.\.venv\Scripts\python.exe scripts/prepare_idle_loop.py <reviewed-close-idle.mp4> --pose near
# Review the prepared loop and seam, then mark its manifest reviewed and restart.
```

Base idle uses `--action idle --frames 97 --seed 61 --return-to-reference` with the full-body reference and default `prepare_idle_loop.py` pose. Source images must be reviewed before inference; scripts never certify their own outputs. Exact generation settings and SHA-256 values are in machine evidence.

For independent fresh-motion comparisons use `benchmark_direct_ltx.py`, `benchmark_ltx_motion.py`, `benchmark_video_assembly.py` and `benchmark_omniavatar.py`. [Hallo-Live](https://github.com/fudan-generative-vision/Hallo-Live) reports 20.38 FPS / 0.94s on **two H200s**; [LightX2V](https://github.com/ModelTC/LightX2V) provides quantization/offload paths. Neither establishes those speeds or command quality on this 4060 Ti.

Checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q local_app scripts tests
node --check local_app/web/app.js
node --test tests/media-sync.test.mjs tests/microphone.test.mjs
git diff --check
# Idle ready server, synthetic cancellation check preserving existing conversation:
.\.venv\Scripts\python.exe scripts/verify_streaming.py
```

R2 independent security/correctness review, staging, sustained p50/p95, real microphone/speaker testing, interruption continuity and public concurrency remain pending. The founder owns those gates before any public launch. No SQLite migration; rollback is a reviewed code revert and restart, preserving memory, credentials and reviewed assets.

## Cost and next decision

The three-month local plan is **$9.60 estimated incremental electricity + $75 contingency = $84.60**, rounded to a $100 ceiling. Power assumptions are unmeasured; hosted dialogue usage adds cost. No paid engineer, rented GPU, hardware or Apple membership has been purchased.

Use the bounded demo to test whether people value the conversation and continuity before buying capacity. [ECONOMICS](ECONOMICS.md) includes optional larger-GPU trials and Apple's 30% baseline / conditional 15% program scenario. Native SwiftUI, StoreKit, device testing and model/hosting clearance remain future work. No profit, legal immunity, App Store acceptance or universal two-second latency is promised.
