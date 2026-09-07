# Blueprint: Amorien MVP - Cloudflare & Uncensored AI Tech Stack

## 1. Cloudflare Viability for NSFW AI (Workers AI)
Can Cloudflare be the *sole* MVP provider (hosting + inference)? 
**Conclusion: No.**
While Cloudflare's Acceptable Use Policy (AUP) generally permits hosting legal adult content on its CDN and Edge compute layer (Workers/Pages) (provided it strictly complies with SESTA/FOSTA laws and doesn't involve CSAM), **Cloudflare Workers AI** relies on standard base models (e.g., Llama 3, Mistral) which are closely safety-aligned by their creators. They will frequently refuse NSFW prompts. Relying on managed serverless endpoints for consistent NSFW roleplay is unreliable without absolute control over the model weights and inference engine.

## 2. Proposed US-Compliant Hybrid Tech Stack
To ensure speed, global reach, and uncensored generation natively, a hybrid stack is safest and fastest:

*   **Edge Routing, CDN & Hosting:** Cloudflare Pages (Frontend) & Cloudflare Workers (API gateway).
*   **WebRTC & State:** Cloudflare Calls (WebRTC infrastructure) and Cloudflare Durable Objects (managing realtime WebSocket session state).
*   **Database:** Cloudflare D1 (serverless SQL for profiles/billing) and KV (caching).
*   **AI Inference Engine:** RunPod (Dedicated GPUs or Serverless Pods) or Together AI for hosting uncensored open-weight models natively and privately.

## 3. Top Uncensored AI Models for Roleplay
*   **Text (LLM):** Dolphin-2.9-Llama-3 (8B/70B) or Noromaid-v0.4 (specifically fine-tuned for high-quality, uncensored conversational roleplay).
*   **Voice (TTS):** XTTSv2 (self-hosted) or AllTalk TTS. (Note: Managed Voice APIs like ElevenLabs and OpenAI TTS strictly ban NSFW generation in their terms of service, necessitating self-hosted architecture).
*   **Generative Video:** Stable Video Diffusion (SVD) or custom AnimateDiff workflows served via a headless ComfyUI API endpoint.

## 4. Compute Cost Breakdown (Per Minute)
*   **RunPod Dedicated GPU (e.g., RTX A6000 48GB):** ~$0.79/hour.
    *   This handles concurrent Text + Voice generation. 
    *   *Baseline Cost:* **~$0.013 / minute** of active node uptime. Assuming basic model concurrency, this can handle 10-15 active users simultaneously.
*   **Video Generation (Serverless RunPod GPUs):** Scaled on-demand to avoid 24/7 idle costs.
    *   *Baseline Cost:* **~$0.004 to $0.01 / clip** depending on diffusion steps and node boot speed.
*   **Cloudflare Infrastructure:** Highly predictable, largely falling under the $5/month Workers Paid tier for MVP volume.

## 5. Subscription Pricing Calculation (MVP)
*   **Usage Assumptions:** A persistent user interacts for ~45 minutes daily.
*   **Cost Projection:** 45 mins/day * 30 days = 1,350 minutes. At ~$0.005/min (accounting for multi-tenant batching on a single GPU), compute cost is **~$6.75 per user/month**.
*   **Bandwidth & Storage:** ~$1.25 per user/mo.
*   **COGS Break-even:** ~$8.00 per user/mo.

**Recommended MVP Pricing:**
*   **Base Tier:** $19.99 / month (Unlimited Text, throttled Voice).
*   **Pro Tier:** $29.99 / month (Unlimited Voice, 50 Generative Video tokens).
*   *Margin:* 60-70% gross margin on Pro users, ensuring sustainable OPEX even with heavy compute usage.
---
## 🔒 EXECUTIVE LOCK: MVP LOGIC FLOW
*   **Infrastructure:** Cloudflare handles purely network Edge (WebRTC signaling), static React delivery (Pages), and database state (D1).
*   **Inference Engine:** Traffic explicitly bypasses Cloudflare Workers AI. Cloudflare securely routes the prompt payload to private RunPod Serverless GPU endpoints.
*   **The Models:** 
    *   *Text:* Dolphin-2.9-Llama-3 (Uncensored)
    *   *Voice:* XTTSv2 (Self-Hosted)
    *   *Video:* LivePortrait/LatentSync (Real-time Lipsync)
*   **The Economics:** ~$0.013/minute cost. Output tier is fixed at $29.99/mo (Pro Uncensored). Gross margin secured at ~65%.
