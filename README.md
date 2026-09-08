# AI-mate: affordable adult companion PWA

Free bounded text and recorded voice; paid phone calls, realistic portrait calls and short portrait video messages. Adults only, with age assurance and approved high-risk payments. Default visual prototype: **self-hosted FlashHead Lite on one RTX 4090**, not the previous two-GPU Pro design.

Five active product documents:

1. This README: scope.
2. [REPORT](docs/REPORT.md): product, offers, market and decision.
3. [BUILD](docs/BUILD.md): researched models, streaming design and POC.
4. [ECONOMICS](docs/ECONOMICS.md): reproducible costs and stress cases.
5. [USA](docs/USA.md): provider eligibility and legal path.

There is no working application or validated GPU benchmark here. `config/economics.json` owns forecast inputs; `scripts/economics.py` generates the economics; `.env.example` is a planned integration contract. Catalog JSON and agent/factory records are reference/history, not additional product requirements. Earlier expensive plans remain in Git history.

Python 3.11+, no dependencies:

```powershell
python scripts/economics.py --write
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
git diff --check
```

First prove a realistic, interruptible portrait conversation for $100–$250 in technical test spending, then fund and pass the separate commercial release gates. No inference purchases, accounts or deployment are authorized by this documentation work.
