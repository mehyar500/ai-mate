# AI-mate: scene-ready adult PWA

A fictional adult companion with editable memory, opt-in check-ins, bounded free text/recorded voice, paid calls, and scene preparation before visual calls. Target roughly 60% direct contribution margin and positive cash after overhead, not a 300–500% return.

Five active product documents:

1. This README: scope.
2. [REPORT](docs/REPORT.md): offer, launch budget and development estimate.
3. [BUILD](docs/BUILD.md): models, scene flow, memory, PWA and measurements.
4. [ECONOMICS](docs/ECONOMICS.md): generated costs, funding and sensitivity.
5. [USA](docs/USA.md): processor options and internal age-assurance limits.

One inference provider: a selected TensorDock US host, subject to business approval. Cloudflare serves the web/control plane and media transport; an approved processor handles payments. One provider does not mean one model or one GPU.

This is documentation and an offline calculator, not a working app. No production account, paid inference, deployment or processor approval has been created. Earlier plans remain in Git history. Catalog JSON and agent/factory files are reference/history.

Python 3.11+, standard library:

```powershell
python scripts/economics.py --write
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
git diff --check
```

Keep the first private POC within $250 technical spending after funding authorization. A commercial adult pilot has separate startup and working-capital needs; the baseline 100-payer funding budget is about $5,918, including unquoted review allowances and excluding paid engineering labor.
