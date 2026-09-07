# Current Plan Validation

This document summarizes the established architecture and unit economics for Amorien, answering immediate technical and financial questions while parallel agents conduct deep internet validation using frontier models.

## Technical Flow & Architecture
To achieve human-like interactions, the pipeline uses WebRTC as the transport layer.
1. **The Fast Path (Audio Native):** WebRTC -> Audio-Native Model (like GPT-4o native audio) -> WebRTC out. This bypasses text transcription entirely.
2. **The Controlled Path (Cascaded):** WebRTC -> Voice Activity Detection (VAD) -> STT -> Tiered LLM Orchestrator -> TTS -> Lip-sync/Video Generator -> WebRTC out. 
3. **Memory Layer:** Not just embedded vector search. It is an associative episodic graph. When the orchestrator receives the prompt, it retrieves relevant character history *before* the model answers. This is the primary moat.
4. **Video Realism & Instructions:** The LLM produces two streams: the text for TTS, and action tags (e.g., `[ACTION: raise_right_hand]`). The video renderer matches the audio track to lip-sync primitives while applying the action tag to the 3D/latent character rig. 

## The Latency Budget
- **Target:** < 800ms round-trip (user stops speaking -> AI voice heard). 
- Human conversational gaps are ~200ms. Anything over 1.2 seconds breaks the illusion, and >2.0s feels like an IVR phone tree. Sub-800ms is the strict limit for the "FaceTime" feel.

## Financials & The $10k Profit Target
- Text Cost: ~$0.0004 per turn 
- Voice Cost: ~$0.033 to $0.050 per minute 
- Video Cost: ~$0.145 per minute (363x the cost of text)

**The Math (Simulated):**
Because video is so expensive, unlimited video is economically fatal. You will use a metered credit system ("Aura") for compute-heavy streams.
1. **Gross Revenue per User:** $20/month base plan.
2. **COGS per User:** Assuming heavy text use and limited daily video/voice via credits, average infrastructure cost operates at ~$8/user/month.
3. **Margin:** $12 profit per user (60% margin).
4. **Volume Needed:** To reach $10,000/month pure profit: $10,000 / $12 = **~834 active paid users**. 
*(This metric scales linearly depending on the chosen margin tier).*

**Next Steps:** External validation is actively running via autonomous agents to cross-reference 2026 cutting-edge toolchains, realtime vendor pricing, and competitor GTM strategies.
