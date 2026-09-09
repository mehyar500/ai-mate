# Local companion demo

Updated September 9, 2026. One private, non-explicit companion on the founder's RTX 4060 Ti **16GB VRAM / 48GB RAM**. Text, Voice call and Video call share memory. The current result combines reviewed photographic movement with newly generated speech and lip movement. It is not unrestricted live video generation or a released native app.

## Run and try it

On this configured PC:

```powershell
.\scripts\start_local.ps1 -Background
# Needed for fresh, experimental movements and offline preparation:
.\scripts\start_motion.ps1 -Background -FastFP8
```

Open **http://127.0.0.1:8765** and wait for model warm-up. Background launch avoids duplicate servers; logs and process information stay in ignored `.cache/local-poc/`. The PC and process must stay running. This is a loopback URL, not a public deployment or Windows startup service.

In Video call, try **“Wave hello.” → “Come closer.” → “Say hello.” → “Step back.”** The reviewed approach moves from full body to close view; its reverse returns after intervening conversation. Each pose has a blinking listening loop. The preview was restarted with the replacement approach, close loop and base-pose right-hand wave on September 9 UTC. These prepared movements are disclosed in Memory & settings. A wave from other positions still uses experimental generation and can fail framing, hand count or direction; arbitrary body commands are not implemented.

Select Call Mira (phone icon on wider screens), or Voice/Video to start microphone input. Calls have mute/end icons and automatic sound. The keyboard icon opens an optional compact transparent input: Enter sends a command to the current voice/video call, Shift+Enter adds a line, and Escape hides it. Typed commands also work with the microphone muted or denied; sending during a reply stops it before submitting. Text has a separate draft and shows messages without ending an active call; Return to call restores the same media elements. “Send me a message saying hello from our call” delivers a separate in-app message with an unread badge. End call releases capture and stops playback. Memory & settings contains facts, notes, diagnostics, the prepared-footage disclosure and Test sound. Camera access is disabled.

The video fills the height when controls fit in the side space. Tall phone views trim side background without cropping the top/bottom of full-body footage; very wide gestures may extend outside that phone crop. Compact tabs and controls replace the technical overlays. Buttons have at least 44px touch targets; optional call captions are in settings and last for the current page session. At 716x854, the stage increased from 544px to 854px tall (57%). Five Chromium layouts from 320x568 to 1280x720 passed overflow/control-overlap checks. Synthetic calls passed microphone-denial handling, caption visibility across Text/call navigation, unmuted audio completion and ending the call. These checks do not qualify physical audio, VoiceOver or Safari.

## Models actually used

| Component | Selection | Where and when |
|---|---|---|
| Conversation / bounded plan | Cloudflare `@cf/qwen/qwen3-30b-a3b-fp8` | Hosted JSON response; exact simple body commands bypass the network |
| Speech | Kokoro-82M ONNX v1.0 float32, `af_sarah` | CPU, four threads; new WAV per reply |
| Recognition | faster-whisper Base English int8 | CPU, eight threads; opt-in microphone or synthetic WAV |
| Lip movement | MuseTalk 1.5, SD VAE ft-mse, Whisper-tiny audio encoder | Local GPU FP16; batch eight; 20 FPS output |
| Face tracking | OpenCV YuNet 2023mar | CPU; tracks supplied body footage |
| Reviewed movement / listening preparation | LTX-2.3-22B distilled FP8 with Gemma-3-12B mixed FP4 text encoder | Offline native ComfyUI graph; prompt encoder on CPU, diffusion offload on 16GB |
| Experimental new movement | LTX-Video 2B 0.9.8 distilled FP8 + T5-XXL FP8 | Local ComfyUI, eight steps; not reliable arbitrary motion |
| Reference image preparation | FLUX.2 Klein 4B | Separate GPU process; review still images before generating video |
| Delivery | FFmpeg libx264/AAC, fragmented MP4 plus synchronized WAV | CPU encoder; installed FFmpeg/NVENC driver pair is incompatible |

Pins: [models](../config/local-models.json), [assets](../config/local-assets.json), [Python dependencies](../config/local-poc-requirements.txt), [LTX-2B downloader](../scripts/download_ltx_motion.py), [LTX-2.3 downloader and SHA-256](../scripts/download_ltx23_benchmark.py). ComfyUI is pinned to `00d34d92fe0afbfbab3893ebbab2d5d70f5e9882`, with custom/API nodes disabled and 4GB VRAM reserved. The isolated environment is `.cache/comfy-env`; motion API is loopback port 8188. Do not expose this unauthenticated development service.

Open weights do not automatically establish commercial rights. MuseTalk's model grant, dependency licenses, LTX's community license/use policy, voice and reference-image provenance each matter. [BUILD](BUILD.md) defines the current architecture; comparisons are recorded below and [USA](USA.md) contains source-based release conditions. No public or adult deployment is approved.

## Central flow and visual continuity

`local_app/engine.py` owns all modalities, job cancellation, pose state and memory:

```text
typed input / opt-in mic -> local ASR if needed
    -> direct supported command OR Cloudflare conversation plan
    -> calls: short speech phrases; prepare one CPU TTS phrase ahead
    -> Text: text only; Voice call: new Kokoro speech
    -> Video call:
         base + closer -> reviewed approach -> near
         near + farther -> reviewed reverse -> base
         base + wave -> reviewed right-hand gesture -> base
         conversation at base/near -> corresponding listening footage
         other supported action -> experimental LTX-2B generation
       -> requested action once, then continue the destination pose/loop phase
       -> track face -> new MuseTalk lips -> one fMP4/WAV stream per phrase
    -> successful server completion: conversation, facts, message and generated pose
    -> completed browser playback: switch to the matching listening loop
```

Scene changes require a current visual request. Talking about a garden does not reset a close view to the garden portrait. The planner receives the trusted current pose; it cannot execute code, paths, URLs or shell commands.

Prepared assets must have an explicit local review flag and matching reference/video hashes. Fixed files: `performance.json`, `performance-closer.mp4`, `performance-farther.mp4`, `performance-near.png`, optional `performance-wave.json/.mp4`, plus `idle-fullbody.json/.mp4` and `idle-near.json/.mp4`. They are private generated artifacts, not in Git. Preparation scripts default to unreviewed. Missing/changed/unreviewed assets fall back to the experimental renderer or held portrait; a fresh checkout does not contain the demonstration clips.

Listening footage continues while a reply buffers, pauses when the reply actually plays, and resumes in the correct pose afterward. Ambient reply video now ends with speech instead of forcing a whole idle-loop duration; deliberate approach/return clips still finish their movement. Longer speech loops the prepared body instead of freezing its last frame; physical action clips never loop. Text/Voice navigation and backgrounding pause hidden idle playback. A bounded appearance cache reuses decoded source frames, face tracking and VAE appearance latents for five short reviewed clips. User speech and generated mouth frames are not cached there.

Successful fresh video captures its final decoded frame as the next reference. Unknown positions disable known-pose loops. The older one-shot reverse cache remains only for an unprepared approach followed immediately by a return. Cancelled generation cannot commit its endpoint. Interrupt reports the displayed frame timestamp; the engine separately preserves that observed pose. Restart clears transient pose/return files and starts at the base pose while preserving conversation. Voice now triggers this interruption flow when echo cancellation is reported; actual acoustic behavior and playback recovery after browser closure remain open.

## Measured results and failures

The tables distinguish individual samples from repeated suites. Different configurations and capture boundaries are not directly comparable; none is a performance guarantee. [Machine-readable history](research/local-poc-benchmarks.json) preserves settings and rejected trials. Raw synthetic traces and reviewed contact sheets stay in ignored `generated/local-app/audit/`.

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

### Reviewed wave and repeatable command coverage - September 9

The new right-hand wave is a prepared LTX-2.3 clip from the verified full-body reference: 97 frames, seed 83, 384x576 at 24FPS, generated in **154.781s**. A separate review manifest binds the footage to the reference SHA-256. It is selected only from the base pose; an interrupted gesture retains the displayed frame without incorrectly treating it as approach progress. Startup now primes five appearance sources in **16.735s**, using 1,831MiB of Torch allocation before speech rendering.

Five real ASR/Cloudflare/Kokoro/MuseTalk browser interactions started in **2.09-2.66s**, with no buffer stalls. Every one of their **278 decoded frames** passed the limited face-count/luma/pixel-change diagnostics. All **81 rendered wave frames** were visually inspected in sequence: one raised right hand, body and feet retained, with hand blur, face softness and background deformation still visible. This is a neutral demo asset, not approved adult-generation infrastructure.

`config/video-call-qualification.json` defines 20 commands covering motion, negation, memory update/recall, unsupported motion, interrupted approach/resumption and in-app messaging while switching views. The initial run produced 20 media clips / **984 decoded frames**, with zero heuristic flags. Two harness assertions incorrectly rejected completed-render/partial-playback interruption and the Text-view active-call banner; corrected assertions are used in the extended run. Initial response p95 was approximately **2.83s**, excluding physical capture and endpoint detection.

Reproduce in two terminals, using a fresh trial directory (existing evidence is deliberately not overwritten):

```powershell
.\.venv\Scripts\python.exe scripts/serve_voice_video_benchmark.py --trial qualification
# In a second terminal with Playwright available on NODE_PATH:
node scripts/qualify_video_call.cjs qualification
.\.venv\Scripts\python.exe scripts/review_call_frames.py --trial qualification
```

Use `soak` in all three commands for six cycles / 120 interactions across 30 minutes. For a repeat, append `--label new-run` to the Python commands and `new-run` after the Node trial argument; labels preserve prior evidence. Drivers alternate fixed synthetic WAV and typed input; recognition, hosted planning, speech synthesis, GPU rendering and browser playback are real. Default injection excludes physical capture and endpoint wait. The `--capture` mode below includes the actual browser recorder and detector. Neither tests physical acoustics or mobile/internet transport. Frame diagnostics create ordered sheets covering every decoded frame, but cannot certify anatomy, identity or perceptual lip synchronization. The live user's database is never copied into these trials.

Prepare new footage in an isolated bundle using `prepare_performance.py <local-output-path> --action wave --duration 4.05 --candidate-label new-wave`. Preparation writes an unreviewed manifest; inspect source and rendered output before accepting it. The seed-83 result above used the original 32-frame decoder window. The revised decoder and replacement footage are described below.

### Removing double images from prepared motion — September 9

A paired experiment decoded the **same sampled latent** with temporal windows of 32 and 128 frames, holding all other decoder inputs fixed. The larger window removed the pronounced double images at the inspected approach frames. It is now the preparation-script default for the measured 97-frame clips. This changes offline source quality; it does not accelerate dialogue or establish arbitrary live movement. ComfyUI documents the [temporal window and compression handling](https://docs.comfy.org/built-in-nodes/VAEDecodeTiled); [issue 11767](https://github.com/Comfy-Org/ComfyUI/issues/11767) reports similar artifacts, but the local paired experiment is the evidence for this change.

| Replacement | Preparation and review |
|---|---|
| Approach and return | Seed 70, 97 source frames; select 72 frames / 3 seconds and reverse for return. Paired generation plus both decoders: 83.09s. |
| Close listening | Seed 94, matching new close reference; 77.87s preparation. Select source seconds 1.75–4.00 and retime to an 89-frame / 3.708s loop with one bilateral blink. |
| Right-hand wave | Seed 84, 97 frames / 4.042s; 28.65s with warm generation caches. Seed 83 at the new window was rejected because the face tracker missed frame 28. |

All 291 selected source frames and all 89 final listening frames were visually inspected in ordered sheets. Every approach/return/wave transcode frame was compared with its reviewed source. The largest transcode mean absolute pixel difference was 3.11/255; this is a correspondence check, not an anatomy score. Close-loop background flow measured 0.15 pixels/s mean versus 0.46 in the previous loop, with different generated content. Hand blur, soft skin, close-view crown cropping, subtle loop seams and imperfect mouth shapes remain. Normal-speed motion and perceptual lip-sync acceptance remain separate from frame diagnostics.

The paired job fit this 16GB card. Partial device sampling peaked at 15,376MiB used, including the preview and desktop; it is not model-only VRAM or a complete peak trace. Preparation timings have different cache states and must not be ranked as live response speeds. Release idle ComfyUI model caches before measuring calls.

Reproduce the paired comparison and keep new candidates separate from the running app:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_ltx23.py --action closer --silent --frames 97 --seed 70 --temporal-size 128 --compare-decode --timeout 600
.\.venv\Scripts\python.exe scripts/review_motion_frames.py <local-source.mp4> --label source-review
.\.venv\Scripts\python.exe scripts/prepare_performance.py <reviewed-source.mp4> --candidate-label new-bundle
# Review approach/return and the new performance-near.png before preparing matching idle.
# prepare_idle_loop.py accepts --performance-label new-bundle; its manifest remains unreviewed.
# Once all matching manifests are reviewed, qualify the bundle without using private memory:
.\.venv\Scripts\python.exe scripts/serve_voice_video_benchmark.py --trial qualification --label new-call --performance-label new-bundle
node scripts/qualify_video_call.cjs qualification new-call --capture
.\.venv\Scripts\python.exe scripts/review_call_frames.py --trial qualification --label new-call
```

Use `--temporal-size 32` to reproduce historical preparation. Longer clips or other resolutions need their own memory and visual qualification. Candidate labels never select assets in the live server automatically; promote the matching set only between calls, retain a rollback copy and restart to rebuild appearance caches.

The `qualification temporal128 --capture` run passed all 20 commands without reported reply stalls. Across nine uninterrupted spoken replies, end-of-speech playback was **2.706s median / 3.421s p95**. Across 19 mixed typed/spoken replies, Send-to-playback was 1.81s median / 2.75s p95. Browser A/V clocks differed by 27.355ms p95 / 38.780ms maximum (635 samples). Every one of the 20 clips / **1,014 frames** was retained and decoded, with zero limited heuristic flags and nonzero unclipped audio. Visual review covered all 81 frames of one rendered wave and 60 transition/close-speech frames, confirming removal of the earlier double image in the inspected region. It did not qualify physical audio, perceptual lip sync or all-frame anatomy.

After the test, the idle preview call was ended and eight matching asset files replaced with a rollback copy in ignored `audit/live-before-temporal128/`. The memory database was unchanged during promotion. The restarted server loaded five appearance sources in **18.071s**; the page was refreshed to the full-body Call Mira screen. No public deployment, credential, provider or memory-schema change was made. Roll back by stopping the preview between calls, restoring those eight files, reverting the code if needed and restarting. Never restore or overwrite private memory as part of an asset rollback.

### Thirty-minute call and smaller planners - September 9

A 1,800.056-second call completed **120 interactions** (six fixed 20-command cycles), with zero functional assertion failures, browser errors or reported buffer stalls. The call remained active through the final turn. Six deliberate interruptions were excluded from first-response percentiles.

| Input boundary | Samples | Median | p95 | Maximum |
|---|---:|---:|---:|---:|
| Mixed typed / injected WAV | 114 | 1.89s | 2.82s | 5.64s |
| Typed submission | 60 | 1.855s | 2.58s | 4.55s |
| Injected WAV, including ASR | 54 | 2.215s | 2.83s | 5.64s |

Cycle medians were 2.13 / 2.28 / 1.89 / 1.85 / 1.99 / 1.89 seconds. This run shows no steady growth in response delay; it is one sequential user on this PC, not a concurrency or mobile qualification. Spoken end-of-speech latency still adds physical capture and the approximately 0.65s endpoint wait. Raw callback-gap counters include intentional source changes and idle pauses, so they are not presented as playback stalls.

Normal 50-turn retention deleted 70 older clips before the post-run review. The **50 retained clips / 2,469 decoded frames** had zero limited heuristic flags, 20FPS decoded timestamp spacing, nonzero speech RMS and no clipped audio samples. The other 70 clips cannot be retrospectively inspected; this is not a complete every-frame pass. The harness now archives only its synthetic media per turn. Windows browser closure also produced one ConnectionAbortedError while returning the final cancellation response; disconnect handling is corrected and regression tested.

The subsequent `qualification --label sync` run completed all 20 commands with zero failures/stalls and retained every clip: **997 decoded frames**, zero heuristic flags. Its response p50/p95 was **1.83s/3.05s** across 19 non-interrupted replies. **619 audio/video clock samples** measured 11.19ms median, 27.94ms p95 and 31.86ms maximum absolute skew while speech was playing. This passes the browser-clock target, not perceptual phoneme alignment or physical speaker latency. The server closed cleanly. Validation: 130 Python tests, 17 Node tests, compileall and Node syntax checks passed; independent public-release review remains pending.

After the soak, 24 sequential synthetic calls compared three Cloudflare models using the same real planner prompt/schema and memory, negation, message and unsupported-action cases. Rates are from the [Cloudflare table](https://developers.cloudflare.com/workers-ai/platform/pricing/), checked September 9 UTC. These are complete planner times, not first tokens or whole-call times:

| Exact model | Samples | Median / maximum | Failed cases | Listed total cost |
|---|---:|---:|---:|---:|
| @cf/qwen/qwen3-30b-a3b-fp8 | 8 | 0.603s / 1.268s | 0 | $0.000608 |
| @cf/meta/llama-3.1-8b-instruct-fp8-fast | 8 | 0.596s / 0.828s | 0 | $0.000638 |
| @cf/meta/llama-3.2-3b-instruct | 8 | 0.421s / 0.692s | 1 message delivery | $0.000623 |

Keep Qwen: 8B did not show a meaningful median gain; 3B sacrificed a requested behavior. These small samples do not establish tail reliability or adult-service permission. Reproduce with `benchmark_cloud_comparison.py dialogue --model <exact-model> --repeats 2 --label <new-label>` in the virtual environment. Runtime selection and credentials were unchanged.

### End-of-speech measurement and ASR comparison — September 9

`qualify_video_call.cjs --capture` supplies synthetic speech to a virtual MediaStream while retaining the actual AudioWorklet, energy detector, turn submission, ASR, planner and playback. The measurement begins at the last 128-sample input block above the detector's minimum energy floor and ends when both audio and video have started. This includes the 650ms endpoint wait; it still excludes physical microphone/speaker latency and acoustic echo. Deliberate interruption is excluded from response percentiles.

| Capture-inclusive run | Commands | Spoken samples | End-of-speech p50 / p95 | Browser A/V p95 / maximum |
|---|---:|---:|---:|---:|
| Base English, four CPU threads | 20 | 9 | 2.85s / 3.39s | 24.43ms / 30.72ms |
| Base English, eight CPU threads | 20 | 9 | 3.09s / 3.83s | 24.36ms / 32.01ms |

Both runs passed all commands without reported stalls. Actual recognition median fell from 447.5ms to 406.5ms across ten audio submissions; normalized words matched. Hosted planner timing and reply lengths varied, so the second run establishes no overall call improvement. Retain eight threads for the measured ASR benefit; do not shorten the speech boundary without pause/cutoff testing. The two-second target remains unmet.

All 40 clips were retained: 986 + 1,003 decoded frames, zero face-count/dark-frame/abrupt-change flags, and nonzero unclipped audio. Manual spot review found blurred hands, close-view mouth artifacts and pronounced double images during approach. A source/render comparison confirms that approach source frames 48 and 50 already contain the double image before MuseTalk. The heuristics missed this defect. Replace/review the prepared source; faster transport cannot repair it. These runs are not full visual, perceptual lip-sync or physical-audio acceptance.

The separate ASR corpus contains 80 utterances across US female, US male and UK female synthetic voices, including 20 with seeded 15dB white noise, plus three non-speech probes. Whole-utterance results on this CPU:

| Recognizer | Threads | Median / p95 | Word error rate |
|---|---:|---:|---:|
| Whisper Base English int8 | 4 | 313ms / 330ms | 0% |
| Whisper Base English int8 | 8 | 268ms / 286ms | 0% |
| Whisper Tiny English int8 | 4 | 172ms / 180ms | 1.42% |
| Whisper Tiny English int8 | 8 | 138ms / 144ms | 1.42% |
| Moonshine Tiny Streaming | Native default | 283ms / 531ms | 3.13% |
| Moonshine Small Streaming | Native default | 1,089ms / 1,727ms | 1.42% |

No tested recognizer lost a critical negation. Tiny substitutes “T” for “tea”; the scorer also counts UK “favourite” as an error, although that spelling is harmless. Both Moonshine models emitted a word for digital silence when called directly; the application's existing energy guard rejects that silence before inference. Moonshine was tested through its whole-utterance API, without incremental overlap; these results do not reject every possible streaming configuration. The corpus is synthetic English, not a human/accent/noisy-room qualification.

Tiny's official converted checkpoint is pinned in config/local-models.json. Optional Moonshine SDK **0.1.5** and its isolated dependencies are pinned in config/moonshine-benchmark-requirements.txt; downloaded English models use CDN revision **quantized_26_08_21**, with exact URLs and SHA-256 manifests retained locally. The [upstream license](https://github.com/moonshine-ai/moonshine/blob/main/LICENSE) grants the English/streaming models under MIT; other assets and dependencies need their own review. Neither candidate changes the active app model.

Reproduce using fresh labels/directories:

```powershell
.\.venv\Scripts\python.exe scripts/serve_voice_video_benchmark.py --trial qualification --label capture-new
# In another terminal; set NODE_PATH as in the existing qualification instructions:
node scripts/qualify_video_call.cjs qualification capture-new --capture
.\.venv\Scripts\python.exe scripts/review_call_frames.py --trial qualification --label capture-new
.\.venv\Scripts\python.exe scripts/download_local_models.py --models asr-tiny-en
.\.venv\Scripts\python.exe scripts/benchmark_call_asr.py --label cpu-comparison
```

For the optional Moonshine comparison, create `.cache/moonshine-env`, install its pinned requirements there, and run `benchmark_moonshine_asr.py --model tiny-streaming --download-only` with that environment's Python, followed by the same command without `--download-only`; repeat for `small-streaming`. It consumes the fixed `asr-calls-cpu-comparison` corpus. Existing results cause an error rather than overwrite evidence. Model discovery/download and benchmarking are separate; no microphone or cloud inference is used.

Finally, 16 bounded synthetic Qwen planner calls compared fresh HTTPS with connection reuse: eight calls each, median **517ms / 458ms**, all four cases passed. The roughly 60ms difference does not resolve the call bottleneck; production transport is unchanged. `benchmark_dialogue_connection.py` records sanitized timing and token usage. Neural rendering, reply preparation and end-of-turn detection remain the main optimization work. ASR alternatives, connection reuse and model installation are separate from provider/content approval.

### Full ASR-to-video check — September 9

The real local recognizer, configured Cloudflare Qwen planner, Kokoro voice and MuseTalk renderer were exercised together through browser playback. Only physical microphone capture was replaced with fixed generated WAVs; an isolated database held the synthetic fact "My dog is named Maple." No private conversation was read or modified.

| Selected build, one warm call | ASR | ASR + complete plan | First browser playback | Stalls |
|---|---:|---:|---:|---:|
| Greeting | 0.396s | 1.065s | 2.52s | 0 |
| Recall dog's name | 0.393s | 0.975s | 2.20s | 0 |
| Contextual approach request | 0.411s | 0.935s | 2.19s | 0 |

All transcripts matched the fixed prompts, memory recall returned Maple, and the approach reached the near pose with unmuted audio completion. Peak Torch allocation was 2,739MiB, not total device memory. The existing 16GB card fits this path. These three samples are not p95; physical microphone, endpoint detection, mobile Safari, internet transport, long calls and concurrent users remain unmeasured. The current microphone waits about 0.65s of silence before submission, so end-of-speech latency is longer than the table.

A 0.15s starting-buffer experiment caused a 0.05–0.09s stall in each of three trials. Keep 0.35s. Baseline timing was 2.60/2.35/2.01s; varying hosted replies mean the selected run is not a claimed speed percentage. The selected change fixes repeated audio-end seeks during a longer silent body gesture: seven ended events became one. iPhone ManagedMediaSource selection is implemented and unit checked with remote playback disabled; no real iPhone performance claim follows from those checks.

Reproduce in a fresh audit directory with `serve_voice_video_benchmark.py --trial selected`, then `review_voice_video_playback.cjs selected`. Existing trial directories cause an error to preserve evidence. Each trial uses four hosted plans including warm-up; all prompts/history are synthetic. Three completed trials made twelve such requests; billing usage was not captured, so these are not declared free. Files remain under `generated/local-app/audit/voice-video-{baseline,revised,selected}`; machine-readable summary is in research/local-poc-benchmarks.json.

### Preparing appearances before calls — September 9

Same synthetic approach/count/browser workflow, current mouth crop:

| Configuration | First browser playback from Send | Total phrase gaps | Within-phrase stalls | Server completion |
|---|---:|---:|---:|---:|
| Batch 8, previous preparation | 2.56s | 1.03s | 0 | 15.63s |
| Batch 4 | 2.53s | 1.00s | 0 | 15.87s |
| Batch 8, two views prerendered | 1.67s | 0.03s | 0 | 12.16s |
| Batch 8, four source appearances primed | **1.61s** | **0.03s** | **0** | **11.10s** |

Batch 4 was rejected as noise. The selected implementation tracks/encodes verified source appearances during startup, caches four bounded clips instead of two, and generates speech-conditioned mouths anew. It does not precompute user replies. Priming four sources took **13.514s** before admission; subsequent face tracking took about 4ms per phrase. Loaded Torch allocation was 1,829MiB; peak rendering allocation was 2,742MiB, excluding other processes/display/driver usage. This is not a 16GB capacity bottleneck. Prepared movement and facial/arbitrary-command limitations remain.

The browser completed three unmuted phrases without errors. Engine startup now primes sources; `visual_warmup` reports source count, time and allocation. Reproduce with `serve_phrase_benchmark.py --action closer --prime-reviewed`, then `review_phrase_playback.cjs phrases-approach-primed`. `--prewarm-reviewed` retains the two-clip experiment; `--batch-size 4` retains the rejected comparison. These exclude physical capture, real ASR/dialogue, internet transport and concurrency. Startup is longer; warm replies are faster.

New primary research: [OmniMate](https://arxiv.org/html/2607.23023v1) reports 27.64FPS and 3.49s time to first frame with H100 hardware/pipeline parallelism; downloadable inference weights were not located in the checked paper. [InteractiveAvatar](https://arxiv.org/html/2606.22905v1) describes state/history switching and separates DiT/VAE across GPUs; it is an architectural lead, not an installed package. [Omni-LiveAvatar](https://github.com/Aoko955/Omni-LiveAvatar) reports H200 streaming but explicitly has not released code/checkpoints. [MotionStream](https://joonghyuk.com/motionstream-web/index.html) reports 29FPS/0.4s on H100 with motion controls, not a complete speech-driven companion. None proves a drop-in 16GB solution. The tested FlashHead Lite remains a practical next streaming comparison, with body-command and dependency-license gaps.

### Speech pipeline — September 8 measured revision

The engine now preserves the full planned reply across short phrases (first target 72 characters, later 120), prepares one CPU TTS phrase ahead while rendering, performs a body command once, and advances the prepared loop's source time. Punctuation/word boundaries are preserved. Cancellation joins in-flight TTS before clearing media; incomplete replies do not commit memory. Each completed phrase closes its own fMP4 response. Previously the response stayed open until the whole job finished, causing an 8.34s stall in the first segmented experiment; that regression is fixed and covered by an HTTP test.

| Same 215-character count | First browser playback | Server complete | Stalls within clips | Largest gap between clips |
|---|---:|---:|---:|---:|
| Whole reply, batch 8 | 4.10s | 14.89s | 0 | N/A |
| Three phrases, batch 8 — selected | 2.33s | 14.71s | 0 | 0.576s |
| Three phrases, batch 16 — rejected | 2.36s | 14.58s | 3 / 0.94s | 0.018s |
| Three phrases plus approach, batch 8 | 2.66s | 15.63s | 0 | 0.987s |

These are single local samples with **synthetic ASR and planner**, real Kokoro/MuseTalk/HTTP/MSE, and unmuted Chromium audio. Add real recognition and dialogue time for a real call. They are not p50/p95 or directly comparable with earlier differently loaded runs. Local Whisper recovered 1–25 in every concatenated speech output. Contact sheets retained full-body framing and the close destination, but the prepared approach visibly blurs/ghosts, the close source crops the crown, and mouth artifacts remain. Gap time is now reported separately from buffer stalls; faster start does not establish seamless playback.

Reproduce in two terminals: `.\.venv\Scripts\python.exe scripts/serve_phrase_benchmark.py [--whole | --batch-size 16 | --action closer]`, then `node scripts/review_phrase_playback.cjs <whole|phrases|phrases-b16|phrases-approach>` with Playwright on `NODE_PATH`. This dedicated loopback server uses port 8766, a separate synthetic database and reviewed media copies; it never reads the live conversation, makes a cloud call or opens a physical microphone. It shuts down after browser completion or a 150s observation window. `review_phrase_outputs.py` produces transcripts and contact sheets. Audit media stay local; sanitized results/hashes are in the machine evidence.

### Interruption continuity — September 8 measured revision

The browser freezes the current picture immediately and sends only the registered job/part and presented timestamp to authenticated `/api/cancel`. The engine copies a bounded, app-owned fMP4 prefix before cancellation deletes media, then selects the last decoded frame at that timestamp on CPU. Container-average frame rate was inaccurate for fragmented clips; decoded timestamps select the frame, while the renderer's 20fps source clock selects the motion offset. No client image, path or URL is accepted. Stale jobs cannot roll back newer state; reset wins over an in-flight capture, and new replies wait until capture finishes. Transient snapshots are removed; the retained PNG is deleted on replacement, reset or restart.

For the reviewed approach/return pair, the engine preserves progress between base and near. An ordinary reply speaks from that captured pose; a later approach or return uses the corresponding remaining source segment. Other generated actions preserve their displayed image but have no guaranteed reversible body trajectory. Failed capture stops the reply and reports that its position was not saved. Stopping a server-completed reply does not retroactively erase its already-saved text; delivery-aware memory remains future work. No new API key, environment variable or database migration is needed.

| Actual browser trial | Saved movement position | CPU capture | Following behavior |
|---|---:|---:|---|
| Interrupt approach → speak → return | 0.8s into source | 0.136s | Speech retained the pose; return began at 2.2s of the reverse clip and reached base |
| Interrupt approach → speak → continue | 1.6s into source | 0.094s | Speech retained the pose; approach resumed at 1.6s and reached near |

Both in-flight approaches cancelled successfully. Browser-held versus engine-saved images differed by 1.33 / 1.41 channel levels on a 0–255 scale, consistent with small decoder/color differences; this is a position check, not a realism score. In the second trial, following speech started in 1.46s and the resumed long approach reply in 1.84s, with zero within-clip buffer waits and a 0.68s total inter-phrase gap. These two samples use synthetic ASR/plans with real Kokoro, MuseTalk, HTTP and Chromium. Physical audio, natural barge-in, every interruption position and sustained p95 remain unqualified. Visual review still shows soft mouths, body morphing and close framing that crops the crown. Two initial harness attempts accidentally awaited the complete submit promise and stopped in phrase 2; they did not qualify mid-motion interruption.

Reproduce with `serve_phrase_benchmark.py --interruption`, then `node scripts/review_interruption_playback.cjs`; repeat using `--interruption --trial middle` and `node scripts/review_interruption_playback.cjs middle`. `review_interruption_outputs.py` computes the saved-frame differences and artifact hashes. The same synthetic-only port 8766 isolation applies.

Latest listening review: two raw calm LTX-2.3 candidates held both eyes shut for roughly one second and were rejected unchanged. `retime_idle_motion.py` slows the full frame to half speed while compressing the manually selected blink interval separately to about 0.25s. The reviewed 5.208s prepared result is now active: side-background mean optical flow fell from 1.153 to 0.473px/s (59%), with a brief bilateral blink. This is a measured improvement, not a natural-motion certificate: minor scene morphing, seam movement and repetition remain. The source, settings, reviewed hash and rollback backup are recorded in machine evidence; `prepare_idle_loop.py --candidate` never replaces active footage automatically.

`benchmark_listening_timing.py` used the same synthetic 1.035s greeting. Old-padding-equivalent playback lasted 5.25s; the corrected ambient path lasts 1.05s, removing 4.2s of unnecessary silent reply playback. Warm rendering took 0.83s with first 4KB at 0.345s. The old-equivalent render had a cold appearance cache, so its 1.655s render is not a controlled attribution of all speed gains to this change. Speech creation was 0.279s; LLM, ASR and browser delay are excluded.

`benchmark_cloud_speech.py` makes at most six synthetic requests using the existing Cloudflare authentication, without reading conversation. [Aura-2 English](https://developers.cloudflare.com/workers-ai/models/aura-2-en/) (`@cf/deepgram/aura-2-en`, `luna`) lists $0.03/1,000 input characters. First 4KB arrived in 0.278–0.395s; complete WAVs took 0.750–0.818s for 16 characters, 1.851–1.873s for 62, and 6.014–7.264s for 215. Six listed costs total $0.01758; an earlier 16-character request with an unknown-length WAV header failed local parsing, adding a nominal $0.00048. These are computed list prices, not an invoice. The parser now measures actual PCM length. Cloud speech is **not selected**: first bytes are not usable synchronized video, and long complete-file latency is still poor. Streaming audio would require incremental speech features/rendering, not just changing the provider.

### Cloudflare comparison — September 8 follow-up

The founder authorized API quality/latency comparisons. `benchmark_cloud_comparison.py` uses synthetic notes and the actual dialogue adapter, with bounded requests/tokens and no runtime switch. Eight samples per successful model covered recall, negated movement, in-call message delivery and an unsupported cartwheel. These are whole-response times, not token-stream latency:

| Model | Completion samples | Quality finding |
|---|---:|---|
| `@cf/qwen/qwen3-30b-a3b-fp8` | 0.455–0.771s | Correct recall, no negated movement, message delivered; remains selected |
| `@cf/ibm-granite/granite-4.0-h-micro` | 1.289–2.108s | Same basic decisions, cheaper tokens but slower in this sample |
| `@cf/zai-org/glm-4.7-flash` | 6.854s truncated; second sample timed out at 30s | Not compatible with the current 512-token/no-think adapter settings; not a general model-quality verdict |

Qwen and Granite both incorrectly said “Let me try that” for a cartwheel while choosing no action. A capability prompt correction makes the selected Qwen explain the limit; two follow-up samples returned the correct explanation. This fixes the observed case, not every possible unsupported request. The harness now stops testing a failed model for the entire run; its initial version repeated GLM once in the second round.

Three identical texts (16/62/215 characters), with one new sample per voice:

| Speech model / voice | Short / normal / long complete audio | Long output duration | Long sample list cost |
|---|---|---:|---:|
| Local Kokoro `af_sarah`, four CPU threads, warm | 0.307 / 0.683 / 2.153s | 13.092s | Local electricity |
| `@cf/deepgram/aura-1`, `luna` | 0.747 / 0.538 / 2.435s | 13.363s | $0.003225 |
| `@cf/deepgram/aura-2-en`, `luna` | 0.736 / 1.886 / 7.269s | 18.000s | $0.006450 |
| `@cf/myshell-ai/melotts`, default English voice | 0.974 / 1.473 / 2.005s | 10.545s | $0.000035 |

All twelve WAVs contained non-silent, unclipped signal. Local Whisper recovered the count through 25 for Kokoro/Aura; Aura-1's “birdsong” became “birds on,” and Melo's count transcription repeated 20. These are ASR flags, not proof of which model introduced an error or a subjective listening score. Kokoro stays selected: the cloud alternatives do not consistently beat it, and voice preference is untested. `review_cloud_speech.py` reproduces the local comparison. [Cloudflare list pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) determines nominal costs; the failed GLM timeout has unknown billed usage.

The 86-entry [Workers AI catalog](https://developers.cloudflare.com/workers-ai/models/) is only the Cloudflare-hosted subset. The broader [AI catalog](https://developers.cloudflare.com/ai/models/) lists 235 entries on September 8, including third-party video. Our earlier Workers AI inventory therefore did not cover every model reachable through Cloudflare.

### Remote inference with fewer credentials — September 8

Prefer **one Cloudflare credential, at most one additional GPU credential** if continuous rendering requires it. Cloudflare's [unified REST endpoint](https://developers.cloudflare.com/ai-gateway/usage/rest-api/) accepts `{model, input}` at `/accounts/{account}/ai/run`; its documented third-party examples use Unified Billing without individual provider keys. This is a proposed benchmark route, not a new app renderer.

| Role | Exact Cloudflare model ID | Decision |
|---|---|---|
| Dialogue | `@cf/qwen/qwen3-30b-a3b-fp8` | Keep the measured active route |
| Remote speech | `@cf/deepgram/aura-1` | Already compared; Kokoro remains selected |
| Cheap motion candidate | `pruna/p-video` | Compare 720p draft and standard, same fictional reference and command |
| Spoken avatar clip | `pruna/p-video-avatar` | Compare against local FlashHead; completed clips are not proof of streaming calls |
| Alternative motion | `lightricks/ltx-2-5-fast`, `bytedance/seedance-2.0-fast` | Secondary candidates after price/terms checks |
| Additional speech candidate | `inworld/tts-1.5-mini` | Defer: its AUP restricts suggestive/mature applications; advertised latency is not measured here |

Sources: [P-Video](https://developers.cloudflare.com/ai/models/pruna/p-video/), [avatar](https://developers.cloudflare.com/ai/models/pruna/p-video-avatar/), [LTX](https://developers.cloudflare.com/ai/models/lightricks/ltx-2-5-fast/), [Seedance](https://developers.cloudflare.com/ai/models/bytedance/seedance-2.0-fast/), [Inworld AUP](https://inworld.ai/aup/). Cloudflare routing preserves underlying model terms; no NSFW approval is established. See USA for content exclusions and ECONOMICS for per-clip versus continuous-video costs.

The founder funded $10 in prepaid credits for Gateway **`default`**. Existing **API key + email** works for both the [credit-balance GET](https://developers.cloudflare.com/api/resources/ai_gateway/subresources/billing/) and LTX third-party inference. Reproduce with `.\.venv\Scripts\python.exe scripts/check_cloud_gateway.py`; it writes only sanitized status to the local audit folder. It reads no conversation and never purchases credits, changes billing or follows redirects. The read-only checker tests billing only; the separate video benchmark proves third-party key/email compatibility. No extra provider key or runtime environment variable was added.

[Unified Billing](https://developers.cloudflare.com/ai-gateway/features/unified-billing/) adds 5% to credit purchases; rare negative balances can still be collected later. The founder purchased credits; no GPU was rented. The benchmark makes one bounded synthetic request per case, keeps provider safety filtering, refuses existing cases and disables automatic retry. Measure request-to-playable time, identity, command execution and audio sync. Do not upload private history or mistake provider inference time for call latency. Continuous calls retain local rendering while remote candidates are unqualified.

### Funded Gateway video test — September 8 evening (September 9 UTC)

| Trial | Result | Request time | Recorded generation cost |
|---|---|---:|---:|
| `pruna/p-video`, 5s, 720p draft | HTTP 400 input-mapping errors; no clip | 1.04–2.77s | No observed deduction |
| `lightricks/ltx-2-5-fast`, 5s, 720x1280/24fps, audio | Two completed text-to-video requests | 31.107 / 31.204s | $0.45 each |

The three Pruna diagnostics tested documented flat parameters, provider nesting and both. Errors alternated between missing `input` and missing `prompt`; the live dashboard schema matches the published flat request. Stop this route pending adapter correction. No safety rejection was reported. LTX's first completed result was missed by the initial response parser; its Gateway log confirmed completion/cost but logging-off prevented payload recovery. The corrected parser preserves the nested v4 response; a separate review trial supplies the usable clip. Both charges are counted.

The reviewed LTX clip is 720x1280 H.264/AAC, 5.042s, 3.18MB; download took 0.635s after generation. Sampled frames show a full-body right-hand raise, wave and lowering, with stable clothing/framing. CPU Whisper recovered “Hi, good to see you.” This text-only test created a different fictional woman: Mira identity conditioning, fine lip-sync, physical speakers and repeatability remain unqualified. At about 31.8s to local availability it fits a prepared message, not a two-second call. Provider inference cost reconciled to **$0.90 used / $9.10 credits remaining**; immediate balance reads lagged. Credit-balance values are cents, while log costs are dollars. Account pricing also shows LTX 1080p at $0.15/s, so the $0.09/s comparison applies to 720p.

Reproduce once per case with `scripts/benchmark_cloud_video.py motion-draft`, `ltx-smoke` or `ltx-review`; these are paid tests with existing-output guards, not runtime routing. `scripts/review_cloud_video.py ltx-review` downloads the returned clip for decoding from the observed HTTPS Google Storage host, without Cloudflare headers or redirects. Local evidence lives under `generated/local-app/audit/cloud-video/`; URLs, account details and credentials are not committed. Model sources are linked above. No new API key, automatic top-up, payment setting or live provider switch was made.

### Local mouth tuning — September 8 evening

`benchmark_visual_quality.py` compared four face/audio settings on near and full-body idle footage; `--motion` adds legacy/new approach and return comparisons. The selected crop moves its face midpoint from −0.04 to −0.10 of detected face height, reducing exaggerated mouth openings in sampled frames. MuseTalk's two-frame left context is now six Whisper steps at 20fps, matching [upstream preprocessing](https://github.com/TMElyralab/MuseTalk/blob/main/musetalk/utils/audio_processor.py), instead of the previous four. Crop-sensitive source caches prevent reuse of old face latents. Teeth, motion blur and the crude mouth blend remain visible; this is a modest correction, not photorealistic lip-sync qualification.

The isolated browser approach/count trial (`serve_phrase_benchmark.py --action closer --quality-review`, then `review_phrase_playback.cjs phrases-approach-quality`) began at **2.56s from Send**, finished server work in 15.63s, completed all three unmuted audio phrases and had zero within-phrase stalls / 1.03s total phrase gaps. ASR/planning were synthetic. `benchmark_visual_graph.py` produced identical pixels but changed batch-eight neural time only from 0.2902s to 0.2877s median (0.85%); CUDA graphs were rejected. Source/quality contact sheets and raw timings remain in the local audit folder.

### FlashHead Lite local trial

`Soul-AILab/SoulX-FlashHead-1_3B/Model_Lite` now runs locally in an isolated benchmark using PyTorch SDPA, four denoising steps, 384x576, 24 generated frames per 0.96s chunk. The full-body greeting used 5,014MiB peak tensor allocation; its first chunk took 1.424s and later chunks 0.790–0.856s. The close reference with a 3.262s synthetic Aura-1 sentence took 0.937s for the first chunk and 0.790–0.878s thereafter, producing 5.76s in 4.993s including encoding. Model/reference setup was 4.0–4.5s, excluded from chunk times. This establishes short-run local throughput, not end-to-end call latency or sustained p95.

Reviewed output: the full-body mouth barely reacts; the close reference has visible mouth/head motion and smoother whole-face changes, but mouth shapes remain imperfect and the framing clips the crown as the source does. Neither test follows arbitrary body commands. **Not selected in the app.** Next compare longer speech, silence, identity drift and action transitions before adding a persistent renderer. The [authors' 4090 results](https://github.com/Soul-AILab/SoulX-FlashHead) are separate from these measurements. Apache top-level licensing does not settle the bundled LTX VAE/dependency rights for public use.

A follow-up 32-chunk run used the complete 13.092s Kokoro count and then silence: 30.72s of video generated/encoded in 25.592s, 0.929s first chunk, 0.793s median / 0.863s maximum later chunks, about 5GB peak tensor allocation. Sampled frames retained identity through the end and returned to a quiet expression; mouth shapes still look imperfect. This is a 31-second throughput check, not a 30-minute call or a lip-sync acceptance test. Reproduce after the speech review with `benchmark_flashhead.py --reference performance-near --audio kokoro-long --chunks 32`; insufficient output duration now fails instead of truncating the input sentence.

### Faster speech-video decoder — September 9

A batch-eight profile isolated SD VAE decoding at **234ms**, versus **56ms** for MuseTalk UNet and **4ms** for pixel transfer. A locally built TensorRT FP16 decoder reduced the isolated decode median from **235ms to 120ms** across 12 synthetic conditions. Raw decoded pixel differences averaged about 0.068/255, with a maximum of 2/255.

Four identical audio/body-source comparisons rendered in **1.52 / 1.58 / 0.615 / 0.621s**, versus Torch **2.41 / 2.28 / 0.957 / 0.963s**: a 31–37% render-time reduction. All **259 encoded frames** were compared; the largest whole-frame mean difference was 0.126/255. All four worst-pair images were inspected, and partial batches 1–8 remained finite and close to Torch. This preserves existing appearance, including its mouth/hand defects; it does not certify natural lip sync. Torch allocation counters exclude TensorRT's external memory allocations.

The experimental and integrated capture trials both passed **20/20 commands** with no reported reply stalls. End-of-speech median/p95 was **2.50/3.44s** and **2.48/2.92s** respectively (nine uninterrupted spoken inputs each); mixed Send-to-playback median/p95 was **1.49/2.77s** and **1.60/2.48s** (19 inputs each). Keep both runs: hosted variability changes the tail, and neither meets the two-second target. Integrated A/V clock skew was 25.11ms p95 / 32.55ms maximum over 614 samples. This measures browser clocks, not phoneme alignment or audible speakers.

Every frame in both trials was analyzed: **1,005 experimental / 994 integrated**, with no heuristic flags, nonzero audio and no clipped samples. Forty transition/close frames per trial were manually inspected; remaining perceptual defects persist. All 20 integrated render records report `tensorrt`. The selected preview restarted successfully in **29.47s**, including five-source warm-up, with unchanged private memory. Its own 30-minute trial, physical audio and mobile checks remain pending.

Reproduce on the configured local environment:

```powershell
.\.venv\Scripts\python.exe -m pip install --target .cache/tensorrt-deps --no-deps -r config/tensorrt-benchmark-requirements.txt
.\.venv\Scripts\python.exe scripts/benchmark_visual_kernels.py --label baseline
.\.venv\Scripts\python.exe scripts/benchmark_trt_vae.py --label fp16
.\.venv\Scripts\python.exe scripts/benchmark_trt_media.py
```

These commands use isolated synthetic audit folders and refuse overwriting completed runs. The media comparison uses retained speech from the documented `qualification temporal128 --capture` trial. Install dependencies only into the optional target directory; the existing Torch environment is unchanged. The NVIDIA Windows libraries require approximately 2.25GB to download. The fixed engine is approximately 101MB and built in 38.2s on this rig; installation and cold preparation are additional.

After inspecting the comparisons and experimental call suite, copy only `decoder.engine` and `build.json` from `audit/visual-trt-fp16/` into `.cache/local-poc/musetalk-vae-trt/`, then mark that copied manifest `reviewed: true` with the review scope. Keep the original experiment record. Qualify the normal runtime using `serve_voice_video_benchmark.py --trial qualification --label trt-reviewed --performance-label temporal128 --decoder tensorrt-reviewed`, then `qualify_video_call.cjs qualification trt-reviewed --capture` and `review_call_frames.py --trial qualification --label trt-reviewed`. Set `AI_MATE_VISUAL_DECODER=tensorrt` only after that passes; restart between calls. Setting `torch` and restarting rolls back without touching memory.

Only load engines built from the pinned local VAE. NVIDIA describes engines as executable, platform/GPU-dependent artifacts; hashes and a local review record are provenance checks, not a sandbox for third-party binaries. [NVIDIA runtime documentation](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/python-api-docs.html), [installation](https://docs.nvidia.com/deeplearning/tensorrt/latest/installing-tensorrt/install-pip.html). The optional runtime changes no model/content license, hosting eligibility or API credential.

## Playback, microphone and memory

The browser consumes about 200ms MP4 fragments with about 400ms initial media buffered. Its embedded audio stays muted; a separate WAV follows the video clock, pauses during stalls and corrects drift above 120ms. If MediaSource is unsupported, playback waits for the finished file. Autoplay rejection exposes Play reply. Interrupt aborts both tracks. These paths have Node tests, but mobile Safari and lengthy calls remain unqualified.

Microphone capture uses AudioWorklet, mono PCM16 WAV, 200ms pre-roll, a 650ms silence boundary and a 25s turn cap. During playback, a browser reporting echo cancellation permits voice interruption after 240ms of above-threshold audio. The energy detector is not a speech/noise classifier. `call-input.mjs` holds one utterance while the authenticated stop preserves the displayed pose and releases the previous render. Cleanup has a 10s bound after the stop response; stale call/microphone generations, rejected cancellation and timeout discard pending audio. Valid short words below the early-onset threshold also stop before submission. Browsers without reported echo cancellation retain manual Interrupt and resume listening 450ms after playback. Raw capture stays in memory; the transcript enters local history and hosted dialogue context.

The isolated voice-interruption trial fed generated PCM through the actual browser recorder, energy detector and local ASR, then real Kokoro/MuseTalk media. Cancellation arrived **445ms after fixture playback started**, including **75ms pose capture**; fixture leading silence is included, so this is not pure detector latency. The next transcript was exactly “Actually, tell me the name of my dog.” It continued from the held pose and then returned to full body. Three inputs produced exactly three submissions; ending the call produced no extra submission. The held browser image versus engine-saved pose differed by **1.34/255 mean channel levels**, a continuity check rather than a quality score. Echo cancellation was simulated and planning was deterministic; no physical microphone, acoustic echo test, iPhone, cloud request or new body generation was involved. Existing source blur remains.

Reproduce with `.\.venv\Scripts\python.exe scripts/serve_phrase_benchmark.py --interruption --voice-interruption --prime-reviewed`, then `node scripts/review_voice_interruption.cjs`. Both use synthetic-only port 8766 and ignored `generated/local-app/audit/speech-interruption-voice-primed/`; the live conversation is untouched. See machine history for exact results.

SQLite keeps editable notes, up to 50 exchanges (12 shown, four sent as recent context) and up to 12 bounded verbatim fact excerpts. Users can inspect, correct and delete saved information. It knows only what was shared; automatic check-ins, calendar integrations and push notifications are unimplemented. Preserve `generated/local-app/memory.sqlite3` during normal updates.

Private `.env` loads only `AI_MATE_LLM_PROVIDER`, `AI_MATE_LLM_MODEL`, `AI_MATE_ENV_FILE` and `AI_MATE_VISUAL_DECODER`; process/launcher overrides win. This PC selects `C:\Users\mehya\.env` for Cloudflare account ID, API key and email (`X-Auth-Key` / `X-Auth-Email`). A scoped token is an alternative. Secrets never reach browser/artifacts. Hosted dialogue receives text, recent context and saved notes; images, video and raw audio stay local. MiniMax/Ollama are explicit alternatives; subscriptions are not presumed API entitlements. [.env.example](../.env.example) contains only implemented configuration.

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

FlashHead reproduction uses source revision `9bc03de06bb0de82cd6bc477804512ae06144bf2` in `.cache/local-poc/SoulX-FlashHead`, with [Windows patch](../config/flashhead-windows.patch) applied using `git apply --unidiff-zero` in that source checkout. Install [isolated dependencies](../config/flashhead-benchmark-requirements.txt) with pip `--target .cache/flashhead-deps --no-deps`, reusing the configured Torch/scientific runtime. `download_flashhead_benchmark.py` downloads about 8.2GB of pinned, SHA-verified Lite/VAE/Wav2Vec2 weights. Run `benchmark_listening_timing.py` to create the synthetic greeting, then `benchmark_flashhead.py`. The close trial additionally needs `benchmark_cloud_comparison.py speech`, then `benchmark_flashhead.py --reference performance-near --audio cloud-aura1-normal --chunks 6`. Downloads and scripts do not select the model automatically. No private conversation is benchmark input.

Checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q local_app scripts tests
node --check local_app/web/app.js
node --test tests/media-sync.test.mjs tests/microphone.test.mjs tests/call-input.test.mjs
git diff --check
# Idle ready server, synthetic cancellation check preserving existing conversation:
.\.venv\Scripts\python.exe scripts/verify_streaming.py
```

R2 independent security/correctness review, staging, end-of-speech p95, complete long-call visual review, real microphone/speaker interruption, iPhone qualification, browser-close recovery and public concurrency remain pending. The founder owns those gates before any public launch. No SQLite migration; rollback is a reviewed code revert and restart, preserving memory, credentials and reviewed assets.

Checks for this revision: 137 Python tests and 17 Node tests, Python compilation, JavaScript syntax and whitespace checks. Regression coverage includes reviewed asset hashes, interruption/pose continuity, cancellation failures, authentication/origin, microphone lifecycle and synchronized playback. Existing layout checks cover five viewports and 44px touch targets; actual iPhone keyboard behavior remains unqualified. Synthetic benchmark servers use disposable memory. No memory schema or provider credential changed. The optional non-secret decoder setting and decoder telemetry are documented above; new tests reject unreviewed, tampered, missing and runtime-mismatched engines.

## Cost and next decision

TensorRT changes no rented-GPU charges or proven concurrency. Do not convert its render-time saving into a billing or profit claim. The optional three-month technical-pilot forecast is **$57.38 under a $100 planning cap**, including local power, the existing Gateway funding and ten optional 5090 test hours per month with a disk allowance. Power and stopped-storage assumptions are unmeasured; no GPU has been rented. The electricity-only baseline remains available in the calculator's historical output.

Use the bounded demo to test whether people value the conversation and continuity before buying capacity. [ECONOMICS](ECONOMICS.md) contains the PWA rental, session-cost and pricing assumptions. Device testing and intended-content model/hosting/payment qualification remain required. No profit, legal immunity or universal two-second latency is promised.
