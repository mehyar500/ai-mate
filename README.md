# AI-mate: adult-first companion PWA

**Lawful consensual adult content is a mandatory launch requirement. If the intended adult experience cannot be delivered within accepted model, host and payment terms, the product does not launch.** This decision supersedes earlier suggestions to launch a non-explicit substitute.

**Current stage: a local proof of concept on the founder's RTX 4060 Ti, 16GB VRAM and 48GB RAM. No remote inference before local validation.** The founder is the only engineer. Keep a $100 planning cap for the quarter, including a $75 contingency pool; estimated additional electricity is $9.60 for 160 hours. Public adult access and customer billing are deferred.

Six active product documents, including the newly requested local POC plan:

1. This README: scope.
2. [REPORT](docs/REPORT.md): small demo scope, founder build path and funding evidence.
3. [BUILD](docs/BUILD.md): models, scene flow, memory, PWA and measurements.
4. [ECONOMICS](docs/ECONOMICS.md): generated costs, funding and sensitivity.
5. [USA](docs/USA.md): commercial licenses, hosting, US release conditions and age assurance.
6. [LOCAL_POC](docs/LOCAL_POC.md): local hardware allocation, benchmark commands, measured findings and the visual-call experiment.

Use the existing computer and loopback services only for current inference. Model downloads use internet access. TensorDock/Cloudflare are deferred deployment candidates; no payment processor is needed for this unpaid stage. Self-hosting does not override licenses or establish nationwide legality.

This repository contains documentation, an offline calculator and local component benchmark scripts, not a working PWA or validated visual-call app. Local model tests use synthetic neutral prompts. No production account, paid inference, deployment or processor approval has been created. Earlier plans remain in Git history. Catalog JSON and agent/factory files are reference/history.

Python 3.11+, standard library:

```powershell
python scripts/economics.py --write
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
git diff --check
```

The local three-month forecast is $9.60 estimated electricity plus one $75 contingency pool, or $84.60; round the ceiling to $100. Existing hardware, storage and tools are already available. No paid engineers, customer revenue or cloud credits are assumed. The previous commercial-pilot model remains deferred calculator data. A demo must distinguish measured functionality from prepared media and unbuilt features.
