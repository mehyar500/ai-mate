# Audio & Core LLM Pod: Architecture Consensus

**Date:** September 5, 2026
**Target:** <200ms Time-to-First-Audio (TTFA) for FaceTime-like AI Companion
**Pod Members:** 
- **Alex** (LLM Backbone Architect)
- **Sam** (Acoustic Engineer)
- **Jordan** (Low-Latency Networker)

---

## 1. The Debate: Cascade vs. Native Audio-to-Audio

We simulated an intense 50-turn debate regarding the core architecture for the FaceTime-like Companion. Here are the core findings:

### Why Cascade Pipelines (STT -> LLM -> TTS) Are Dead
- **Latency Floor:** Even with streaming STT (e.g., Whisper-v3-Turbo) and chunked TTS, a cascade pipeline fundamentally requires Voice Activity Detection (VAD) buffering. You lose ~300ms just waiting for a pause to chunk the audio, plus another ~150-250ms for LLM TTFT (Time to First Token), plus ~100ms for TTS vocalization. Best case scenario is ~550ms.
- **The Prosody Loss:** Cascade pipelines crush acoustic data into cold text. STT completely strips tone, breathing, pacing, and emotional state. The TTS then has to blindly guess the tone based purely on semantic context, leading to a jarring, unnatural "bot" feel.
- **Barge-in Clunkiness:** Handling interruptions (barge-in) in cascade requires killing the TTS process and flushing the LLM context mid-stream, which creates a noticeable stutter and conversational reset.

### The Shift to Native Audio-to-Audio (End-to-End)
- **Zero-Shot Empathy:** Native models (like GPT-4o's underlying Omni architecture, Moshi 2.0, or Llama-3-Audio) map direct acoustic tokens to acoustic tokens (Speech-to-Speech without text intermediates). Tone is preserved and mirrored. 
- **Continuous Duplexing:** Native models can predict overlapping speech patterns. They don't need a hard VAD "silence" trigger to start generating; they can backchannel (say "mhm", "yeah") *while* the user is talking.

## 2. The Ultimate <200ms Voice Pipeline

Based on the pod's consensus, we must adopt a ground-up **Continuous Audio-Token Stream** architecture.

### A. The Protocol Layer (Jordan's Domain)
- **Transport:** **WebRTC** (strictly UDP) over custom ingest PoPs (Points of Presence) routed via Anycast. Do not use WebSockets (TCP head-of-line blocking adds upwards of 150ms in lossy mobile environments).
- **Codec:** **Opus (at 48kHz, 20ms frames)**. We bypass traditional large audio chunking and send ultra-small packets continuously.
- **Transport Fallback:** **WebTransport** (HTTP/3 / QUIC) for environments where WebRTC UDP punch-through fails, maintaining multiplexed UDP streams.

### B. The Edge / Client Layer (Sam's Domain)
- **Client-Side AEC:** Hardware-accelerated Acoustic Echo Cancellation (AEC) and automatic noise suppression (ANS) *must* be done on the native OS layer before transmission. If the base model hears itself echoing back from the user's speakers, it will enter a feedback hallucination loop.
- **No Client VAD:** The client streams audio constantly (Full-Duplex). Let the model learn silence rather than relying on brittle client-side VAD gates.

### C. The Core AI Architecture (Alex's Domain)
- **Audio Tokenizer:** We utilize a continuous neural audio codec (highly optimized EnCodec or SoundStream variant). Incoming Opus packets are decoded directly in C++, tokenized into discrete acoustic tokens, and fed into the LLM context window at ~50 tokens/second.
- **Model Backbone:** A custom sparse-MoE (Mixture of Experts) multimodal transformer (approx. >70B parameters, heavily quantized to INT8/FP8 for H100 inference speed). 
- **Generation:** The model auto-regressively predicts *both* semantic text (for memory logging) and acoustic tokens simultaneously.
- **Early-Exit Audio Generation:** As soon as the first 2-3 acoustic tokens are generated, they are fed to the neural vocoder and pushed out via WebRTC. 
- **Time-to-First-Audio:** ~120-150ms network + inference time total.

## 3. Summary of Implementation

1. **Client (iOS/Android):** WebRTC -> Opus Audio (continuous full-duplex).
2. **Ingest Edge:** Terminate WebRTC locally, forward to GPU cluster via direct gRPC stream.
3. **Inference (GPU):** 
   - Neural Codec maps PCMA/Opus -> Acoustic Tokens.
   - MoE Model predicts Next Audio Token.
   - Vocoder translates Acoustic Token -> Opus Stream.
4. **Delivery:** Stream directly to WebRTC track. 
5. **Barge-in:** Handled purely by the model's attention mechanism shifting when new loud acoustic tokens interrupt its output generation.

---
*Consensus passed unanimously.*