# Start and test

This repository runs an offline calculator and catalog collector. App deployment, GPU images, auth and payment adapters are **not implemented** here. Do not confuse a populated environment template with working integrations.

## Run what exists

Python 3.11+, standard library only; no package installation:

```sh
python scripts/economics.py --json
python scripts/economics.py --utilization 0.2 --json
python scripts/economics.py --write
python -m unittest discover -s tests -v
python scripts/snapshot_cloudflare.py
```

The last command makes public documentation requests and overwrites the catalog snapshot; inspect the diff before committing. The others are offline. Keep financial assumptions in `config/economics.json`, then regenerate the pricing doc.

Copy `.env.example` to ignored `.env` locally. Empty secrets are intentional. These names define the planned adapter contract, not existing handlers or universal vendor variable names. In Workers, deploy runtime secrets through secret bindings, and configure `AI`, `DB`, `ASSETS_BUCKET` and `ACCOUNT_SESSION` as resource bindings. D1/DO/R2 bindings are not API keys. Do not ship a management token in frontend code.

| Settings | Source/use |
|---|---|
| Cloudflare account/API token | Deployment and optional REST tests; scope to required account/resources. Workers AI binding needs no separate model-provider key. |
| SFU app ID/secret, TURN key/token | [Realtime app](https://developers.cloudflare.com/realtime/sfu/get-started/) and [TURN credentials](https://developers.cloudflare.com/realtime/turn/generate-credentials/); mint short-lived client grants server-side. |
| GPU base URL/shared session secret | Our GPU controller deployment. TensorDock provisioning stays manual initially, so its management API key is not required at runtime. |
| CCBill account/subaccount/form/salt/Data Link | Merchant-issued settings; [billing contract](../trust/BOUNDARIES.md). No fabricated webhook secret. |
| Yoti API key/SDK ID | Hosted [Age Verification Service](https://developers.yoti.com/age-verification/quick-start); bearer auth and `Yoti-SDK-Id`. |
| Resend API key/from address | Transactional sign-in mail; verified sender domain. [Key handling](https://resend.com/docs/knowledge-base/how-to-handle-api-keys). |
| Session secret and Turnstile keys | Server authentication/abuse controls; public site key only may reach browser. |

## Next implementation handoff

1. Founder: choose test region, approve GPU spend cap, obtain applicable host agreement/quote and model artifact licenses. Configure no adult traffic before approvals.
2. Engineer: build a small Python GPU proof with one owned character, first over local playback then Cloudflare WebRTC. Record actual model revisions, GPU/driver versions, input/output tokens, speech characters, warm/load seconds, failures, VRAM and end-to-end timestamps.
3. Test 20 calls including 30/60-minute sessions, cold start, interruption, mobile Safari/Chrome, TURN-only network, renderer failure, lost connection, user cancellation and exhausted allowance. Use synthetic test conversations, not customer intimate data.
4. Compare Kokoro/Qwen3-TTS and local/Cloudflare speech. Include shared-GPU contention. Cap any clip experiment by wall time/spend; never extrapolate real-time generation from output fps.
5. Only after [MVP thresholds](../product/MVP.md) pass: build Workers app, durable ledger and hosted auth/age/checkout adapters. Establish package manager, lockfiles and real CI commands then; no invented `npm run` commands today.
6. Security reviewer: adversarial tenancy/payment/age/routing/deletion checks and staging evidence. Founder: approve public paid pilot, geography, processor terms and content scope. Turn on features individually.

For the experiment, track activation, day-7 return, paid conversion, refund rate, cost/connected minute, GPU billable utilization and p95 turn latency. No raw-content analytics. Keep scheduled beta hours until utilization justifies continuous availability.

Rollback: disable adult/call/clip flags independently, stop new reservations, drain/cancel sessions, reconcile/refund unused entitlements, then revert the deployment. Never erase billing records as a rollback. Documentation rollback is a revert of the reset commit; the original proposals remain in history.
