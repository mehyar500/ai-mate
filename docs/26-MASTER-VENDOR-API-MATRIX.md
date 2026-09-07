# Amorien Architecture: Master Vendor & API Matrix

## 1. WebRTC Modular Conversational AI Flow Breakdown
This calculation details the exact per-minute operational cost for an active runtime WebRTC streaming session. Metrics assume a conversational cadence of 30 seconds of user speech and 30 seconds of AI speech out of a 60-second minute window.

### Step-by-Step Cost per Minute
| Component | Preferred Vendor / Service | Unit Price Structure | Active Usage per Min | Cost per Minute (USD) |
| :--- | :--- | :--- | :--- | :--- |
| **WebRTC & Signaling** | LiveKit Cloud | $0.0016 / GB egress | ~15MB data per 1m stream | **$0.0005** |
| **STT (Speech-to-Text)**| Deepgram (Nova-2) | $0.0043 per recognized min | 1 minute stream duration | **$0.0043** |
| **LLM Inference** | Groq (Llama3-70B API) | $0.79 / 1M tokens | ~400 total tokens / min | **$0.0003** |
| **TTS (Text-to-Speech)**| Cartesia (Sonic Voice) | $0.003 per sec of generation | 30s generated audio | **$0.0900** |
| **Avatar Video Render** | Simli (or Tavus WebRTC API) | $0.05 per min of WebRTC video | 1 minute stream duration | **$0.0500** |
| **Total Modular Cost** | | | **Calculated Estimate:** | **~$0.1451 / min** |

*Note on Monolithic Alternatives: OpenAI's Realtime API (Speech-to-Speech natively) bundles STT, LLM, and TTS for approximately $0.12–$0.20 per active conversational minute. The modular approach selected above prioritizes sub-second latency and explicit control for avatar lip-sync APIs (Simli).*

## 2. Infrastructure, Memory, & Backend Data Stores

| Category | Primary Vendor | Service / Plan Type | Operational Role in Amorien |
| :--- | :--- | :--- | :--- |
| **Vector DB / Mnemonic Memory** | Pinecone | Serverless Index | Vector embeddings for agent conversational recall and swarm context-sharing. |
| **Edge Compute & Orchestration** | Cloudflare Workers / DO | Serverless Compute | WebSocket handler, low-latency API proxying, and tunnel management. |
| **Relational Database & Auth** | Supabase | Managed PostgreSQL | User state, swarm configurations (Obsidian syncs, OpenClaw records), billing locks. |
| **Fast Caching Layer** | Upstash (Redis) | Serverless Redis | Rate-limiting, ephemeral context buffers before persisting to PG/Pinecone. |
| **Media / Cold Storage** | Cloudflare R2 | Object Storage | Agent persona avatars, generated audio caching, chat history dumps. |
| **Observability (Logging/Cost)** | Langfuse | Tracing | Detailed chunk latency telemetry and LLM token cost control per subagent. |

## 3. Integrated Swarm Ecosystem Endpoints
Given Amorien features unified swarms interfacing tools:
- **Telegram Bot API:** Free ingress for Webhook-based messaging delegation.
- **Obsidian / Local File Bridge:** Handled natively vs Cloudflared reverse-tunnels pointing to local ports (zero marginal infra API cost). 
- **OpenClaw / Hermes Execution:** Self-hosted (or running natively on user endpoints); API costs are relegated to any remote execution calls (typically Docker/AWS Lambda instances, ~$0.01 per minute of code sandbox runtime).
