# AI-mate MVP

Free text and recorded voice messages; paid phone calls and photorealistic video messages up to 15 seconds. Live video is a later experiment. Recommend an adult-only, non-explicit launch; explicit features require separate approvals and economics.

This is a planning repository and offline calculator, **not a working application**. No inference, checkout or latency benchmark has been completed.

Five active product documents:

1. This README: scope and repository map.
2. [REPORT](docs/REPORT.md): offer, competition and business decision.
3. [BUILD](docs/BUILD.md): models, memory, flow and release tests.
4. [ECONOMICS](docs/ECONOMICS.md): generated prices and sensitivity analysis.
5. [USA](docs/USA.md): licenses and launch eligibility.

`config/economics.json` owns assumptions; `scripts/economics.py` generates economics; `tests/` checks arithmetic. `docs/research/cloudflare-models.json` is reference data. `.env.example` lists planned integration settings, not credentials. Agent/factory records are historical coordination evidence. Superseded plans remain in Git history.

Python 3.11+, standard library only:

```powershell
python scripts/economics.py --write
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
git diff --check
```

Validate quality and costs, implement free conversation and memory, then approved checkout and paid calls/clips. Keep live video disabled until separately measured.
