# AI-mate: realistic companion calls

**Current direction, September 8: a non-explicit companion experience intended for an Apple-native app and Apple in-app purchases.** Realistic, responsive video calls are the priority. The founder's revised goal supersedes the earlier explicit-content-first launch requirement. Any later explicit web product requires a separate scope and eligibility review; it is not a hidden native-app mode.

**Current stage: a running, non-explicit local prototype on the founder's RTX 4060 Ti, 16GB VRAM and 48GB RAM.** Text, Voice call and Video call share conversation and memory. Calls accept typing or opt-in microphone input; an active call continues when viewing Text. Video supports three bounded body commands with uneven quality. Camera access is disabled. Public access, billing and the intended adult commercial experience remain unqualified.

On this configured PC, run `./scripts/start_local.ps1 -Background` and open **http://127.0.0.1:8765**. Wait for model warm-up. Cloudflare handles dialogue; graphics, speech and transcription run locally. The central `local_app/engine.py` loads three non-secret startup choices from private `.env`; process/launcher overrides win. Cloudflare credentials stay in the explicitly selected private file, using API key plus email here. Setup, model choices, measured performance and limitations are in [LOCAL_POC](docs/LOCAL_POC.md). `.env.example` documents only implemented configuration.

Six active product documents, including the newly requested local POC plan:

1. This README: scope.
2. [REPORT](docs/REPORT.md): small demo scope, founder build path and funding evidence.
3. [BUILD](docs/BUILD.md): models, scene flow, memory, PWA and measurements.
4. [ECONOMICS](docs/ECONOMICS.md): generated costs, funding and sensitivity.
5. [USA](docs/USA.md): commercial licenses, hosting, US release conditions and age assurance.
6. [LOCAL_POC](docs/LOCAL_POC.md): local hardware allocation, benchmark commands, measured findings and the visual-call experiment.

Use the existing computer and loopback services for graphics and speech; dialogue uses the configured provider. Model downloads use internet access. TensorDock/Cloudflare are deferred deployment candidates; no payment processor is needed for this unpaid stage. Self-hosting does not override licenses or establish nationwide legality.

`local_app/` contains the loopback server, inference adapters and browser interface. `scripts/` contains setup, benchmarks and synthetic integration checks; `config/` pins models and runtimes; `tests/` covers economics and local data/HTTP behavior. Weights, generated media and private memory stay ignored locally. The interface has a web manifest but is not a validated mobile PWA or continuous FaceTime app. Earlier plans remain in Git history; agent/factory files are historical coordination material.

Python 3.11+, standard library:

```powershell
python scripts/economics.py --write
python -m unittest discover -s tests -v
python -m compileall -q scripts tests local_app
git diff --check
```

The local three-month forecast is $9.60 estimated electricity plus one $75 contingency pool, or $84.60; round the ceiling to $100. Existing hardware, storage and tools are already available. No paid engineers, customer revenue or cloud credits are assumed. The previous commercial-pilot model remains deferred calculator data. A demo must distinguish measured functionality from prepared media and unbuilt features.
