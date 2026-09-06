# August 2026 AI Companion Financials & Models

## 1. Top Real-Time Models
- **GPT-5.6 / Sora-Live:** Streaming text/audio to video. Highest fidelity but closer to ~4-5s latency.
- **Runway Gen-4 / Luma Dream Machine 2.0 (Live):** Low latency endpoints locked to LoRA identity tokens.
- **LivePortrait v2 (Open Source Winner):** Industry standard for exactly this flow. Sub-2s 30fps streaming via hosted serverless GPUs.

## 2. Cost Analysis
- **LLM Intelligence & Voice Audio:** ~$0.02 / minute
- **Real-time Image-to-Video Compute:** ~$0.05 / minute (Optimized via TensorRT FP8)
- **Total Compute Cost:** ~$0.07 / minute

## 3. Pricing Strategy
- **Pay-As-You-Go:** $0.35 / minute. ~80% profit margins. Example: 30 minutes a day = $315 revenue vs $63 infrastructure cost.
- **Premium SaaS:** $99/month for 300 minutes of Live Video time. Net profit: ~$78 per user. Exhausted minutes degrade gracefully to voice-only.
