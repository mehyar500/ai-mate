# Video-call proof before commercial launch

The founder's September 8 revision targets an **Apple-native, non-explicit companion app with Apple in-app purchases**. Responsive, realistic video is the main test. Earlier explicit-first launch requirements are superseded; any future explicit web service needs a separate scope and eligibility review.

## What runs

The existing RTX 4060 Ti 16GB / 48GB RAM PC runs one local companion. Text, Voice call and Video call share memory. Calls accept typing or an opt-in microphone, can deliver a separate message to Text, and continue across tab changes. Cloudflare plans replies; CPU Kokoro/Whisper and GPU LTX/MuseTalk produce media. No camera, signup, checkout or public deployment.

The shared flow lives in `local_app/engine.py`. Private `.env` contains implemented startup choices. [LOCAL_POC](LOCAL_POC.md) is the technical source for models, reproductions and measurements.

## Evidence and gaps

- Direct body generation took 4.50s at 384x576, 3.19s at 320x480 and 2.00s at 256x384 in warm samples. The fastest moved both hands; these times exclude the rest of the call.
- Browser approach playback began in 5.29s. Immediately returning along that generated path in reverse began in 1.82s, with new speech and zero buffer stalls. This is bounded reuse, not general fresh backward generation.
- A reviewed LTX-2.3 listening loop now supplies blinking and foliage motion at the original standing pose. A voiced greeting over it began in 2.08s with zero stalls and returned to the loop. Position-changing turns disable it to avoid snapping back. It is prepared footage, not continuous fresh diffusion.
- Fresh LTX-2.3 joint audio/video took 144.97s cold and 21.45s with cached text conditioning. Its wave looked more coherent but included unwanted subtitle-like marks. A later LTX-2B closer trial took 8.52s to playback and made her appear smaller; command accuracy remains unreliable.
- 81 Python checks pass, including idle asset/hash/HTTP boundaries, pose/return cancellation and real CPU reversal of synthetic video. Seven Node checks pass. Final checks accompany each commit.

Continuous visual presence, reliable arbitrary motion, identity/lips, acoustic device testing and sustained p95 latency remain open. This is not production-ready.

## Budget and next work

The founder is the only engineer. Electricity planning is $6/$1.80/$1.80 for three months, plus one $75 contingency: $84.60, rounded to a $100 ceiling. These power assumptions are unmeasured. No cloud GPU or Apple membership was purchased. [ECONOMICS](ECONOMICS.md) covers optional rentals and Apple-fee scenarios.

Qualify idle/streaming movement, then compare inexpensive larger GPUs if needed. Native playback and StoreKit are later implementation work; [BUILD](BUILD.md) and [USA](USA.md) define scope. Interest is not revenue; funding is not guaranteed.

The founder authorized direct main work on local engine/UI/adapters, related scripts/configuration/tests and existing product documents. Preserve SQLite memory and credentials. R2 independent security/correctness review, staging and public-release evidence remain pending, owned by the founder before launch. Rollback uses reviewed code reverts.
