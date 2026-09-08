# Build only this

## Obtain these components

| Job | Exact choice / where to obtain it |
|---|---|
| Web, API and data | Paid [Cloudflare Workers](https://developers.cloudflare.com/workers/platform/pricing/), D1, Durable Objects and private R2. React/TypeScript web app; Python GPU server. |
| Media transport | [Cloudflare Realtime SFU + TURN](https://developers.cloudflare.com/realtime/sfu/). Carries audio/video; does not generate it. |
| GPU | [TensorDock](https://www.tensordock.com/): request an available US 48GB/L40S-class VM, all-in quote and applicable compute agreement. Conditional candidate, not adult-approved. |
| Local conversation + text policy checks | [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B), non-thinking, quantized official weights; Apache-2.0. |
| Hear the user | [Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small), MIT; add endpointing/chunking. |
| Speak | [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), Apache-2.0; preset voices. Challenger only if needed: [Qwen3-TTS-12Hz-1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice). |
| Animate the face | [MuseTalk 1.5](https://github.com/TMElyralab/MuseTalk), MIT code/commercial-weight permission. Use owned motion loops, not noncommercial test assets. |
| Optional cinematic clips | [Wan-AI/Wan2.2-TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B), Apache-2.0; separate worker. 24fps output does not mean real-time generation. |
| Free clean text / checks / portraits | Workers AI: `@cf/qwen/qwen3-30b-a3b-fp8`, `@cf/meta/llama-guard-3-8b`, `@cf/black-forest-labs/flux-2-klein-4b`. Clean speech fallback: `@cf/deepgram/flux` + `@cf/deepgram/aura-2-en`. |

The [86-entry Cloudflare inventory](research/cloudflare-models.json) has no video-generation output model. Other Gateway providers keep their own terms/costs. Do not deploy the whole catalog. Retain three curated portraits and preset voices; no customer face/voice uploads or training in MVP.

## One flow

For the first **clean** call, keep Qwen3-30B-A3B, Deepgram Flux/Aura-2 and text checks on Cloudflare; send generated audio to the GPU's MuseTalk renderer. The local chain below is the lower-cost challenger and conditional adult route. Both use the same Cloudflare app/storage/WebRTC infrastructure. Pricing must follow the winning route; see [REPORT](REPORT.md#cloudflare-first-or-lowest-cost).

Verify adult eligibility → sign in → choose character → free text → approve/edit memory → choose paid allowance → hosted checkout → microphone call. Show remaining minutes and service hours. Captions, keyboard controls, mute/end and account deletion are required. User camera stays off.

Browser microphone → Cloudflare SFU → GPU transcription → ≤4,096-token context with ≤8 approved facts → streamed Qwen reply → clause safety checks → Kokoro → MuseTalk → timestamped H.264/Opus back through SFU. Cancel stale audio/frames on interruption. Start with one call per GPU; measure contention. Short talking clips reuse this renderer.

D1 stores account-owned records. One account Durable Object serializes idempotent allowance reservations/settlements. Pause pilot billing on failure/reconnect; stop at zero; no automatic top-up. Private R2 delivery verifies ownership. Separate adult and clean histories; never fail over adult data into a clean-only service. Adult text has a separately metered worker and advertised beta hours, not free always-on compute.

## First test and setup

Use [.env.example](../.env.example) for all planned keys; runtime Worker bindings are `AI`, `DB`, `ASSETS_BUCKET`, `ACCOUNT_SESSION`. Management keys never enter the browser. TensorDock provisioning is manual, so no management API key is needed by the app. These integrations are not implemented yet.

Run `python scripts/economics.py --json` and `python -m unittest discover -s tests -v`; no dependencies. Then build one GPU proof and test 30/60-minute calls, cold start, interruption, bad network, cancellation, depleted balance and clip failures. Log timings/tokens/costs, not intimate content. Do not add marketplaces, native apps, vector databases or more models before this works.
