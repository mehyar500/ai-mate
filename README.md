# Amorien

An adult-only AI companion for a US-first pilot: persistent text, a consistent fictional face, and paid voice/avatar calls. Clean by default; adult features only for verified adults in approved states.

**State:** one MVP plan, current research and an offline cost calculator. No production app or live inference is delivered here. Earlier prototype work remains separate and needs review against this plan.

**Choice:** Cloudflare for the web app, data and WebRTC; a dedicated GPU for the character. TensorDock is the conditional GPU candidate. Reusable motion plus lip-sync powers calls; full video generation is a separate short-clip job.

| Read | Purpose |
|---|---|
| [MVP](docs/product/MVP.md) | Scope, build order and success criteria |
| [Experience](docs/design/EXPERIENCE.md) | Onboarding, calls and recovery |
| [Architecture](docs/architecture/STACK.md) | One implementation plan |
| [Models](docs/research/MODELS.md) | Exact choices, licenses and evidence |
| [Economics](docs/product/ECONOMICS.md) | Tiers, 30/60-minute costs and Chaturbate dollar comparison |
| [Boundaries](docs/trust/BOUNDARIES.md) | US eligibility, providers and billing |
| [Start here](docs/operations/START.md) | Tests and environment setup |

Python 3.11+, no dependencies or API keys needed:

```sh
python scripts/economics.py --json
python -m unittest discover -s tests -v
```

[.env.example](.env.example) lists planned integration settings; it does not provision services. The [86-model Cloudflare snapshot](docs/research/cloudflare-models.json) is reference data, not another plan.

The overlapping proposals and simulated demo remain in Git history at `ba5513891072ea5488497bec5016cc7638720688`. This is the replacement baseline for **main**, per the founder's instruction. Work: [issue #1](https://github.com/mehyar500/ai-mate/issues/1). [MIT](LICENSE) covers this repository, not third-party models.
