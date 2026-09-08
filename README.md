# Amorien

**Five active product documents, including this page.** Everything else is code, configuration, reference data or agent operating records.

1. [Decision report](docs/REPORT.md) — what we can build, what differs from ChatGPT, and whether it can make money.
2. [Prices and comparisons](docs/ECONOMICS.md) — costs, customer prices, Chaturbate payouts and percentage savings.
3. [Build](docs/BUILD.md) — exact models, infrastructure, onboarding and first test.
4. [US launch](docs/USA.md) — commercial licenses, provider eligibility, payment and age checks.

Status: plan and tested offline calculator; realistic live calls have **not** been demonstrated. No production deployment or adult-provider approval exists yet.

Run `python -m unittest discover -s tests -v`. Change assumptions in [config/economics.json](config/economics.json), then run `python scripts/economics.py --write`. Planned keys are in [.env.example](.env.example); actual `.env` stays private. Superseded plans remain in Git history.
