# Local POC on a 16GB consumer GPU

Decision: prove the smallest useful pipeline on the founder's existing PC before using any remote inference. This is the sixth active document, explicitly requested by the founder. No cloud GPU, new graphics card, dock, merchant account or public deployment is required for this experiment.

## Hardware and the hypothesis

Verified locally on September 7, 2026: NVIDIA RTX 4060 Ti, 16,380 MiB total VRAM, NVIDIA driver 595.97; 51,242,930,176 bytes system RAM (about 47.7 GiB). Windows, Ollama 0.33.3 and FFmpeg are installed. The PC has enough free disk for the small test models. This is a useful consumer-GPU prototype platform, not a guaranteed full video-inference server.

**Hypothesis:** a small quantized dialogue model plus CPU speech can leave enough VRAM for one photorealistic portrait renderer. Prepare the character/scene before the call; generate the speech-driven portrait changes during it. A new full video diffusion pass for every reply is not the first architecture to test.

System RAM and VRAM are different. 48GB RAM helps hold files, CPU speech and unloaded models; it does not turn the GPU into a 64GB GPU. CPU offload can make a model fit while making it too slow for conversation. Measure both fit and response time.

## Model and memory plan

| Job | Exact candidate | Execution plan | Evidence status |
|---|---|---|---|
| Dialogue | Qwen3-4B-Instruct-2507, Ollama `qwen3:4b-instruct-2507-q4_K_M` | 4-bit GPU weights, 4,096-token context, short replies | Benchmark results recorded below |
| Smaller dialogue comparator | Qwen2.5-1.5B-Instruct, Ollama `qwen2.5:1.5b` | Smaller GPU footprint; compare conversational quality before selecting | Neutral local short-reply benchmark succeeded |
| Speech output | Kokoro-82M ONNX v1.0, `af_sarah`, kokoro-onnx 0.6.1 | CPU ONNX Runtime, leaving GPU memory free | Local synthesis succeeded |
| Speech input | faster-whisper-small, CPU int8; tiny.en as a speed comparator | Push-to-talk before open-mic streaming | Not installed or measured in this test |
| Portrait/scene preparation | FLUX.2 Klein 4B | Load alone, prepare and validate scene, unload before dialogue/rendering | Model card reports about 13GB VRAM; local fit/quality unmeasured |
| First visual comparator | MuseTalk 1.5 | Precompute face latents; modify the face region from speech on permitted source media | Not installed or benchmarked locally; does not synthesize arbitrary body motion |
| Fresh portrait-motion challenger | SoulX-FlashHead-1_3B, Model_Lite | One stream, lowest usable resolution; profile complete dependency footprint | Not installed or measured; exact LTX VAE rights unresolved for the intended commercial use |

Sources: [Qwen instruct tag](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M), [Kokoro runtime](https://github.com/thewh1teagle/kokoro-onnx), [Klein card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [MuseTalk](https://github.com/TMElyralab/MuseTalk), [FlashHead](https://github.com/Soul-AILab/SoulX-FlashHead). Published speed on another GPU does not establish speed here. Model, dependency, voice and asset licenses still apply; neutral timing tests do not qualify adult output or commercial deployment.

Reserve an initial 4GB GPU budget for dialogue and runtime cache, 2GB for display/encoder/temporary buffers, and at most 10GB for the visual path. These are allocation targets, not measured renderer requirements. If the renderer exceeds its share, test a smaller dialogue model or CPU dialogue before considering any hardware purchase. Do not load the scene generator during the call. The already-installed 27B models remain untouched and are not the default because their weight size leaves much less visual headroom.

## Local call flow to test

1. **Prepare:** choose one original fictional adult identity and a permitted reference scene. Generate/validate the scene locally before the call. Cache scene assets and image/face latents only where supported. Unload the scene model and confirm VRAM is released.
2. **Warm:** load the selected small LLM and visual renderer. Run a neutral warm-up; show Ready only when both are ready. Cold start is reported separately from conversational response.
3. **Listen:** microphone audio goes to local VAD/ASR. Start with push-to-talk to isolate model delay from end-of-speech detection. No browser speech API that silently sends audio to a cloud service.
4. **Reply:** retrieve a short local memory summary and confirmed facts. Ask for a concise first sentence; start CPU speech as soon as a complete usable phrase arrives. Longer speech can follow in subsequent chunks.
5. **Render:** send audio chunks to the local portrait renderer, encode frames with the GPU's video encoder where supported, and synchronize playback. Start with local browser playback; WebRTC networking is a later measured addition.
6. **Interrupt/end:** stop queued speech and stale visual work when interrupted. Save only explicitly accepted synthetic-test facts, release model state and show cancellation/failure honestly.

Reusing a background or precomputed face representation reduces repeated work. It does not create unobserved body motion or make prerecorded media live. Display whether a segment is live, prepared earlier or unimplemented. No cartoon avatar or fake FaceTime claim. If the first renderer only lip-syncs, label it a lip-sync prototype and compare whether that constrained view satisfies the founder's intended experience.

## Measurements and acceptance

Measure first usable reply, first playable speech, first synchronized visual reply, sustained FPS, audio/video skew, dropped frames, peak VRAM, system RAM and wall power. Use at least a cold start, multiple warm runs, a longer-context run, a 10-minute conversation, interruption and a failed generation. Small-sample p95 values are provisional.

Initial full-pipeline goals: warm end-of-speech to synchronized reply p95 <=2 seconds, sustained >=20FPS at a usable portrait resolution, skew <=100ms, no memory spill/oom during a 10-minute session. These are test targets; no full-pipeline pass is claimed. Report quality alongside speed, including identity consistency and obvious visual defects. Benchmarking a short neutral response does not establish memory quality, adult capability or robust speech recognition.

The difficult part is concurrent visual rendering and dialogue, not merely loading model files. If each component runs individually but they miss latency together, reduce resolution/batch/context, move speech to CPU, serialize scene work, or test a smaller LLM. Preserve the quality tradeoff in the report. Do not convert a local failure into an automatic cloud rental.

## Reproduce the local benchmarks

The economics scripts still use Python's standard library. CPU speech has an optional isolated `.venv`; it does not modify the bundled Python environment. The model files and generated WAV/JSON results remain in ignored local directories.

```powershell
ollama pull qwen3:4b-instruct-2507-q4_K_M
# Existing bundled Python used on this PC; a normal Python 3.12 also works.
$pocPython = 'C:\Users\mehya\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $pocPython -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r config/local-poc-requirements.txt
.\.venv\Scripts\python.exe scripts/benchmark_local.py --samples 10
.\.venv\Scripts\python.exe scripts/benchmark_speech.py
.\.venv\Scripts\python.exe scripts/benchmark_voice_reply.py
```

Before speech testing, download the two files linked by the [runtime's official setup](https://github.com/thewh1teagle/kokoro-onnx#setup) into `.cache/local-poc/`: `kokoro-v1.0.onnx` and `voices-v1.0.bin`. They were downloaded for this local test. SHA-256 values are recorded in the local download manifest. Downloads use internet bandwidth; generation calls only loopback Ollama or local CPU inference. No cloud model API or GPU rental is used.

The dialogue benchmark unloads only the selected test model before its cold run, then measures ten warm neutral short replies. It rejects truncated or overlong answers rather than counting reasoning text as a completed conversation reply. It uses a 4,096-token capacity but short prompts, not a filled 4K context. Repeat with realistic context and concurrent rendering before drawing product conclusions. Generated replies and raw timing are local test data, not user conversations.

CPU speech creates five WAV files under `generated/local-speech/`. It measures whole-utterance generation, not streaming first-audio latency. Listen to those outputs locally when assessing voice quality; successful synthesis alone is not a subjective quality evaluation.

## Observed findings

The first `qwen3:4b` pull resolved to the **thinking-2507** variant. The short-reply experiment returned reasoning/truncated output, so its fast token rate was rejected as conversational-latency evidence. Pin the explicit instruct variant; a short alias plus `think=false` is insufficient evidence of actual behavior. [Ollama tag mapping](https://ollama.com/library/qwen3/tags).

The smaller Qwen2.5 1.5B comparator completed ten warm neutral replies with p50/p95 completion of about 0.10/0.13 seconds; the post-run GPU snapshot was 1,241 MiB used across the device. Its cold reply took 4.33 seconds. This is a small speed/memory comparison with short repeated prompt patterns, not proof of sufficient companion quality. Its official [model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) declares Apache-2.0.

Kokoro CPU synthesis succeeded for five neutral utterances: 2.05–4.06 seconds of audio generated in 0.38–0.62 seconds; model initialization was about 0.85 seconds. This supports moving TTS off the GPU. It does not include speech recognition, LLM, video or playback. Runtime 0.5.0 first failed on a speed-input dtype mismatch; pinning 0.6.1 resolved the observed failure.

The explicit 4B instruct checkpoint completed ten warm neutral replies with p50/p95 completion of **0.18/0.29 seconds**; first-token p95 was **0.063 seconds**. The cold reply took **1.96 seconds**. Post-run GPU usage across the device was **3,161 MiB**; this is a snapshot, not an instrumented peak. Most VRAM remained free, but no renderer ran concurrently. Median generation throughput was about 97 tokens/second on these very short replies.

The combined typed-input -> full speech waveform test used five short prompts after warm-up. With automatic CPU threading it measured p50/p95 **2.12/3.32 seconds**. Limiting ONNX intra-op threads to four and inter-op threads to one gave **1.67/2.35 seconds** in a subsequent run. This is an observed small-sample improvement, not a controlled proof that threading alone caused it. The result still misses a two-second target before adding ASR/video. It measures a complete utterance; streaming first playable audio is a different, unmeasured metric. [ONNX thread controls](https://onnxruntime.ai/docs/performance/tune-performance/threading.html).

Both successful and rejected findings are preserved in [benchmark evidence](research/local-poc-benchmarks.json). Reply quality still needs evaluation: one output described the synthetic calendar as its own, and another added emojis unsuitable for a speech-first response. These timing tests are not a memory or persona-quality pass. Next work is phrase-level audio buffering, CPU ASR and the visual renderer, followed by concurrent long-context testing. No visual renderer, scene generation, ASR, persistent-memory app or FaceTime-like session has been implemented or validated by these component tests.

## Cost and evidence for the next decision

No new hardware, cloud GPU, paid engineer, payment processor or new paid software is required for the current local tests. At an assumed extra 300W and $0.20/kWh, 100 hours costs $6; 160 hours across three months costs $9.60. The actual tariff/power have not been measured. Keep a $75 contingency pool and a **$100 total planning cap**, rather than committing to a commercial pilot now. See [ECONOMICS](ECONOMICS.md).

Only after the local combined pipeline passes should we price equivalent hosted capacity. Measure occupied GPU seconds per delivered minute, retry rate and safe simultaneous calls, then apply actual host rates and idle-capacity costs. A consumer GPU result could open cheaper hosting choices; it cannot establish their policies, concurrency, availability or commercial price without evidence.
