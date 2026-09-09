# AI Mate — local video-call MVP

Run on the existing RTX 4060 Ti (16GB VRAM, 48GB system RAM). The immediate deliverable is a working local web demo. The deployment direction is a PWA with a separate GPU service; Apple distribution is deferred.

## Start

On this configured Windows PC:

```powershell
./scripts/start_local.ps1 -Background
```

Open **http://127.0.0.1:8765**. For foreground logs, run `.venv/Scripts/python.exe -m local_app`. To check the running service without changing conversation history, run `.venv/Scripts/python.exe -m local_app --check`.

Configuration lives in `.env`; `.env.example` lists implemented options. Credentials stay in the private file selected by `AI_MATE_ENV_FILE`. Model weights and generated media are local and ignored by Git. Full setup instructions are in [LOCAL_POC](docs/LOCAL_POC.md).

## One call pipeline

Voice or text input → `server.py` → `engine.py` → dialogue plan → speech → body motion and lip sync → browser playback. The engine owns turn state, memory commits, cancellation and model orchestration.

| Location | Responsibility |
| --- | --- |
| `local_app/server.py`, `__main__.py` | Loopback HTTP and launch/health command |
| `local_app/engine.py` | Single conversation and media coordinator |
| `local_app/core.py`, `conversation.py` | Memory and dialogue provider |
| `local_app/models.py`, `speech_runtime.py` | Transcription and speech inference |
| `local_app/visual.py`, `motion.py`, `trt_decoder.py` | GPU rendering adapters |
| `local_app/media.py` | Reviewed clips and playback continuity |
| `local_app/web/` | Text, voice call and video call UI |
| `config/` | Model and runtime pins |
| `scripts/` | Setup, launch and qualification tools |
| `experiments/` | Optional model comparisons and renderer benchmarks; not app services |
| `tests/` | Regression checks |

Cloudflare currently supplies configured dialogue. Transcription, speech and graphics run locally. Moving graphics to a GPU provider will require an explicit inference API; this local Python process cannot run inside a Cloudflare Worker. Public WebRTC transport and multi-user deployment are still unqualified.

## What works and what needs work

The demo supports shared conversation memory, voiced video replies and a small set of reviewed approach, return and wave clips. These are prepared body movements with generated speech/lips. Arbitrary live body generation, reliable left/right corrections, natural transitions and physical-device audio quality have not passed acceptance. New models stay experimental until they improve the actual call.

Technical validation uses clothed, neutral footage. Commercial model licensing, hosting and release requirements remain separate unresolved decisions.

## Verify

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe -m compileall -q local_app scripts experiments tests
node --test tests/media-sync.test.mjs tests/microphone.test.mjs tests/call-input.test.mjs tests/playback-probe.test.cjs
git diff --check
```

Five core documents: [local setup and evidence](docs/LOCAL_POC.md), [current report](docs/REPORT.md), [architecture and models](docs/BUILD.md), [economics](docs/ECONOMICS.md), and [US release requirements](docs/USA.md). Historical experiment evidence stays available for reproducibility. Use the current measured report for costs rather than assuming profitable public calls from local generation speed.
