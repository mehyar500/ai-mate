# Infrastructure Setup Runbook
**Architecture:** Namecheap (Domain) ➔ Cloudflare (DNS/Edge) ➔ RunPod (GPU Inference)
**Objective:** Establish low-latency WebRTC streaming, edge logic via Workers, and serverless GPU execution for Dolphin Llama 3, XTTSv2, and LivePortrait.

## Phase 1: Namecheap to Cloudflare Nameserver Migration
1. **Initialize Cloudflare:** Add your target domain in the Cloudflare Dashboard. Select the Free or Pro tier.
2. **Extract Nameservers:** Cloudflare will assign two nameservers (e.g., `aria.ns.cloudflare.com`, `bob.ns.cloudflare.com`).
3. **Namecheap Configuration:**
   - Log into Namecheap ➔ **Domain List** ➔ Click **Manage** next to the domain.
   - Under the **Nameservers** section, select **Custom DNS**.
   - Enter the two Cloudflare nameservers.
   - Click the **Checkmark** to save.
4. **Verification:** Wait 5-30 minutes and verify propagation in Cloudflare Dashboard (domain status will change to "Active").

## Phase 2: Cloudflare Edge Setup (Workers, D1, Calls)
### 1. API Tokens & Permissions
Create a custom Cloudflare API token at **My Profile ➔ API Tokens** with the following strict permissions:
- `Account` | `D1` | `Edit`
- `Account` | `Workers Scripts` | `Edit`
- `Account` | `Cloudflare Calls` | `Edit`
- `Zone` | `DNS` | `Edit`

### 2. D1 Database Setup (State & Memory)
- Run CLI constraint: `npx wrangler d1 create backend-db`
- Copy the resultant `database_id` and map it into your project's `wrangler.toml` under `[[d1_databases]]`.

### 3. Cloudflare Calls (WebRTC)
- Navigate to **Cloudflare Dashboard ➔ Calls**.
- Click **Create App** (e.g., "AI-Mate-RTC").
- Securely retrieve and store the provided **App ID** and **App Secret** (used in your workers to mint short-lived tokens to clients).

## Phase 3: RunPod Serverless GPU Architecture
Create three separate Serverless endpoints in RunPod for microservice isolation. Generate a single **RunPod API Key** (Account ➔ Settings ➔ API Keys) with Serverless Read/Write access.

### Endpoint 1: Language Model (Dolphin Llama 3)
- **Model:** `cognitivecomputations/dolphin-2.9-llama3-8b`
- **Compute:** 1x **RTX 4090 (24GB VRAM)** or **RTX A5000**.
- **Template:** RunPod Official vLLM image.
- **Environment Vars:** `MODEL_NAME=cognitivecomputations/dolphin-2.9-llama3-8b`, `MAX_MODEL_LEN=8192`.

### Endpoint 2: Text-to-Speech (XTTSv2)
- **Compute:** 1x **RTX 3090 (24GB VRAM)** or **RTX 4000 Ada**. XTTS heavily relies on memory bandwidth for <500ms Time-to-First-Byte (TTFB).
- **Template:** Custom serverless PyTorch image wrapper optimized for XTTS streaming.
- **Configuration:** Enable "FlashBoot" to drastically reduce cold start duration on request.

### Endpoint 3: Avatar Rendering (LivePortrait)
- **Compute:** 1x **RTX A6000 (48GB VRAM)**. LivePortrait frame rendering is VRAM intensive and easily OOMs on 24GB cards under load.
- **Template:** Custom Docker payload bundled with TensorRT/ONNX-optimized LivePortrait weights.
- **Scaling constraint:** Set maximum concurrency per worker low (1 to 2 concurrent generating sessions maximum) to preserve frame execution safety.

## Phase 4: Integration
1. Populate your local `.env` using `.env.example`.
2. Provision edge logic: `npx wrangler deploy`.
3. Test inference endpoints via RunPod dashboards and monitor cold-start latencies.