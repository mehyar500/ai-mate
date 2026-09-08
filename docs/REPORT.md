# Video-call proof before commercial launch

The founder's September 8 revision targets an **Apple-native, non-explicit companion app with Apple in-app purchases**. Responsive, realistic video is the main test. Earlier explicit-first launch requirements are superseded; any future explicit web service needs a separate scope and eligibility review.

## What runs

The existing RTX 4060 Ti 16GB / 48GB RAM PC runs one local companion. Text, Voice call and Video call share memory. Calls accept typing or an opt-in microphone, can deliver a separate message to Text, and continue across tab changes. Cloudflare plans replies; CPU Kokoro/Whisper and GPU LTX/MuseTalk produce media. No camera, signup, checkout or public deployment.

The shared flow lives in `local_app/engine.py`. Private `.env` contains implemented startup choices. [LOCAL_POC](LOCAL_POC.md) is the technical source for models, reproductions and measurements.

## Evidence and gaps

- Direct body generation took 4.50s at 384x576, 3.19s at 320x480 and 2.00s at 256x384 in warm samples. The fastest moved both hands; these times exclude the rest of the call.
- Reviewed approach → greeting → return began browser playback in **1.72s / 2.16s / 1.83s**, with zero stalls and completed unmuted audio. The final-build approach/return check took **2.61s / 2.68s**, also with no stalls. Prepared transitions now survive intervening conversation, with a blinking listening loop at both full-body and close positions.
- New speech and lips are generated over prepared footage. A bounded source-appearance cache reduces repeated tracking/encoding; long replies loop the body instead of freezing. The scene guard now prevents garden descriptions from discarding a close view.
- A **13.092s** spoken count took **9.97s to start / 23.489s server completion**, with two stalls before caching. A warm-cache repeat took **9.54s / 19.680s**, with no stalls; rendering improved from 15.943s to 11.182s. That starting delay remains unacceptable for a call. Another 6.155s reply began in 4.23s with no stalls. These are samples, not p95 or universal two-second latency.
- LTX-2.3 successfully prepared the approach in 146.429s cold. Several close-idle prompts failed review before a blink-only guided clip worked. Its fresh joint audio/video remains too slow for live replacement; arbitrary LTX-2B commands still fail direction/framing. Prepared motion is disclosed.
- **89 Python / seven Node checks pass**. A real streaming cancellation completed in 0.328s, preserving conversation and the listening pose and removing cancelled media. Unmuted browser completion is not confirmation of physical speaker output.

Longer replies now retain visual motion, but short loops repeat and approach frames have visible blur. Reliable arbitrary motion, interruption-aware pose continuity, identity/lips, acoustic device testing and sustained p95 latency remain open. This is not production-ready.

## Budget and next work

The founder is the only engineer. Electricity planning is $6/$1.80/$1.80 for three months, plus one $75 contingency: $84.60, rounded to a $100 ceiling. These power assumptions are unmeasured. No cloud GPU or Apple membership was purchased. [ECONOMICS](ECONOMICS.md) covers optional rentals and Apple-fee scenarios.

Next: reduce whole-reply speech preparation, repair interrupted-playback pose state, then qualify sustained call latency and compare larger GPUs if necessary. Native playback and StoreKit are later implementation work; [BUILD](BUILD.md) and [USA](USA.md) define scope. Interest is not revenue; funding is not guaranteed.

The founder authorized direct main work on local engine/UI/adapters, related scripts/configuration/tests and existing product documents. Preserve SQLite memory and credentials. R2 independent security/correctness review, staging and public-release evidence remain pending, owned by the founder before launch. Rollback uses reviewed code reverts.
