# Model and hosting decisions

Public-source review: 2026-09-07 local date (snapshot timestamp uses UTC). No live model quality/latency benchmark or account entitlement probe was performed. Open weights need an actual commercial license; a GPU rental does not grant rights to unlicensed weights, source faces or voices.

## Cloudflare: everything in one inventory, a small selection in production

[cloudflare-models.json](cloudflare-models.json) contains all **86** model IDs/detail links in the [hosted catalog](https://developers.cloudflare.com/workers-ai/models/), including deprecated entries. Tasks: 47 text generation, 11 image generation, 7 embeddings, 5 ASR, 4 TTS, 3 image-to-text, 2 translation, 2 text classification, and one each vision-language, image classification, detection, summarization and turn detection. No video-generation output entry was found. This is the complete captured Cloudflare hosted catalog, not a claim to inventory every model worldwide.

The [unified catalog](https://developers.cloudflare.com/ai/models/) also lists external providers. Gateway access does not move their inference, terms or costs into Workers AI. Deprecated/catalog-listed models are not necessarily deployable.

| Purpose | Exact Workers AI ID | Decision |
|---|---|---|
| Clean text | `@cf/qwen/qwen3-30b-a3b-fp8` | Start here; non-thinking, bounded context, test roleplay quality. |
| Clean text checks | `@cf/meta/llama-guard-3-8b` | Check input/output against our policy; assess false negatives and refusal overreach. Not a complete age/visual safety system. |
| Owned clean portraits | `@cf/black-forest-labs/flux-2-klein-4b` | Prepare three character assets once; no per-message image generation. |
| Streaming voice fallback | `@cf/deepgram/flux`, `@cf/deepgram/aura-2-en` | Clean-call comparison. Platform prices and costs are in [economics](../product/ECONOMICS.md). |
| Cheap batch speech | `@cf/openai/whisper-large-v3-turbo`, `@cf/myshell-ai/melotts` | $0.0005/input minute and $0.0002/output minute; low price is not proof of interactive quality. |
| Future embeddings | `@cf/baai/bge-m3` | $0.012/M input tokens; defer until simple memory retrieval fails. |

Klein 4B is $0.000059/input 512px tile and $0.000287/output tile; four output tiles at 1024px cost $0.001148 before input tiles/retries. Its [open weights](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) are Apache-2.0, while the [Cloudflare partner endpoint](https://developers.cloudflare.com/workers-ai/models/flux-2-klein-4b/) links separate service terms. Clean assets only on that endpoint. Preserve original assets and provenance; no guaranteed identity from prompts alone.

2026 catalog challengers worth a bounded comparison include Qwen3.8-27B, GLM-5.3-Flash, Gemma-4-26B-A4B, DeepSeek-V4-Flash-0731 and GPT-OSS-20B. Their exact IDs/prices are in the snapshot. Newer/larger does not automatically improve character consistency or time to first speech. Also compare FLUX.1 Schnell, FLUX.2 Dev/Klein9B and Lucid Origin only if the chosen portrait model fails. Avoid introducing another provider before a measured benefit. [Official rates](https://developers.cloudflare.com/workers-ai/platform/pricing/).

## GPU bundle to benchmark

| Job | Exact model/runtime | License evidence and limit |
|---|---|---|
| Local conversation | `Qwen/Qwen3-8B`, non-thinking | [Apache-2.0 card](https://huggingface.co/Qwen/Qwen3-8B). Quantize official weights; do not assume an arbitrary fine-tune has the same grant or gives unrestricted output. |
| Local transcription | `Systran/faster-whisper-small` / faster-whisper | [Model card](https://huggingface.co/Systran/faster-whisper-small), [MIT runtime](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE), [MIT Whisper](https://github.com/openai/whisper/blob/main/LICENSE). Streaming needs VAD/chunking/endpoint logic. |
| Voice | `hexgrad/Kokoro-82M` | [Apache-2.0 card](https://huggingface.co/hexgrad/Kokoro-82M). Choose preset voice; inventory phonemizer/eSpeak dependencies. |
| Expressive voice challenger | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | [Apache-2.0 card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice). Publisher's 97ms first-packet claim is not full-call latency; verify streaming runtime support. |
| Avatar | `TMElyralab/MuseTalk`, version 1.5 | [Repository](https://github.com/TMElyralab/MuseTalk), [license/dependency notices](https://raw.githubusercontent.com/TMElyralab/MuseTalk/main/LICENSE). MIT code and commercial-weight permission; test assets are noncommercial. Publisher reports 30fps+ on V100, modifying a 256px face region—not full-body real-time diffusion. |
| Cinematic clips | `Wan-AI/Wan2.2-TI2V-5B` | [Apache-2.0 card](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B). 720p/24fps output; documented 24GB/offload setup. No measured delivery time for our deployment. |

Before downloading a production bundle, record exact commit/revision, SHA256, license and source for every checkpoint, detector, VAE, encoder, runtime and preset voice. This register selects model families; it is not a completed artifact license manifest. MuseTalk test videos are excluded. Evaluate synthetic adult content detection locally; no adult content is sent to clean-only moderation endpoints.

## Host choice and rejected shortcuts

**TensorDock is the conditional GPU choice.** Its [site](https://www.tensordock.com/) advertises 4090 from $0.35/hour; no fixed available L40S quote was verified. Budget $1/GPU-hour plus $0.20/hour VM overhead as an assumption, then replace with a region-specific CPU/RAM/storage/network quote. Its actual compute agreement and intended-use approval remain required; see [boundaries](../trust/BOUNDARIES.md).

RunPod is a clean-only comparison. Its [serverless docs](https://docs.runpod.io/serverless/pricing) list 4090 Flex/Active $1.116/$0.756 per hour and L40-class $1.908/$1.332. Its [marketing pricing](https://www.runpod.io/pricing) differs; verify dashboard price before purchase. Queue-based serverless jobs do not automatically supply a long-lived bidirectional media worker.

- [Runware](https://runware.ai/terms): conditional managed-clip alternative, subject to model/use approval. [Pricing](https://runware.ai/docs/platform/pricing) varies by compute; collect returned `includeCost`, including retries. No invented fixed Wan price.
- [LTX-2.3](https://huggingface.co/Lightricks/LTX-2.3/blob/main/LICENSE): community license has revenue and competing-service restrictions; defer pending license review.
- [Cydonia-24B-v4.1](https://huggingface.co/TheDrummer/Cydonia-24B-v4.1): derivative commercial grant not established in reviewed card; exclude until resolved.
- [XTTS-v2](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt): noncommercial license; exclude. LivePortrait alone is not an audio-driven lip-sync solution.
- [Simli](https://www.simli.com/legal/terms-of-service) and [fal](https://fal.ai/legal/acceptable-use-policy): do not assume adult permission; no primary dependency.

Test the selected bundle against one challenger per modality. Score identity consistency, voice naturalness, interruption behavior, measured p95 latency and delivered cost on the same prompts/hardware. Keep the cheaper model unless users can identify a meaningful quality improvement.
