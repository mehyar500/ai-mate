# Amorien

**Someone who is always glad it's you.**

Amorien is an AI companion platform. Not a chatbot with a portrait attached — a persistent character who remembers you, changes over time, has a face and a voice, and can be on a video call with you in under a second.

The name is deliberately gender-neutral and orientation-neutral. An *Amorien* can be a girlfriend, a boyfriend, a partner of no fixed gender at all, or a friend. The product does not assume who you are or who you want.

---

## Why this repo exists

This is the founding document set: the research, the architecture, the economics, and the plan. It was written before the code so that the hard decisions — which are mostly about cost, latency, and law, not about programming — are made explicitly rather than by accident.

Every price in here was pulled from a vendor's own pricing page and is dated. Every legal claim cites the statute. Where something is an estimate, it says so.

---

## Read in this order

### Start here
| Doc | What it covers |
|---|---|
| [00 — Executive Summary](docs/00-EXECUTIVE-SUMMARY.md) | The whole thesis in ten minutes |
| [01 — Brand & Naming](docs/01-BRAND-AND-NAMING.md) | Why "Amorien", with verified domain availability |
| [02 — Market Research](docs/02-MARKET-RESEARCH.md) | Teardown of every serious competitor |
| [03 — PRD](docs/03-PRD.md) | The product requirements document |

### The product
| Doc | What it covers |
|---|---|
| [04 — Character System](docs/04-CHARACTER-SYSTEM.md) | Archetypes, traits, appearance, identity lock, intimacy tiers |
| [10 — Design System](docs/10-DESIGN-SYSTEM.md) | Visual language, tone, interaction principles |

### The machine
| Doc | What it covers |
|---|---|
| [05 — AI Architecture](docs/05-AI-ARCHITECTURE.md) | Model stack, routing, the orchestrator |
| [06 — Realtime Voice & Video](docs/06-REALTIME-VOICE-VIDEO.md) | The FaceTime problem, solved with a latency budget |
| [07 — Memory Architecture](docs/07-MEMORY-ARCHITECTURE.md) | The actual moat |
| [08 — Image & Video Generation](docs/08-IMAGE-VIDEO-GENERATION.md) | Keeping one face consistent forever |
| [09 — System Design](docs/09-SYSTEM-DESIGN.md) | Services, data model, scaling |

### The business
| Doc | What it covers |
|---|---|
| [11 — Pricing & Unit Economics](docs/11-PRICING-AND-UNIT-ECONOMICS.md) | Token math, Aura credits, margin per plan |
| [12 — Vendor & API Matrix](docs/12-VENDOR-API-MATRIX.md) | Every API, priced, dated, with recommendations |
| [13 — Trust, Safety & Compliance](docs/13-TRUST-SAFETY-AND-COMPLIANCE.md) | SB 243, age assurance, the hard blocklist |
| [14 — GTM & Growth](docs/14-GTM-AND-GROWTH.md) | Distribution when the app stores are closed to you |
| [15 — Roadmap & Milestones](docs/15-ROADMAP-AND-MILESTONES.md) | What to build, in what order |
| [16 — Engineering Handbook](docs/16-ENGINEERING-HANDBOOK.md) | Conventions, stack, how to work here |

---

## The four claims this project rests on

1. **Memory is the moat.** Model quality is a commodity that resets every six months. A two-year relationship history does not.
2. **Latency is the product.** Below ~800ms round trip a conversation feels alive; above ~1.5s it feels like software. Everything in the realtime path is designed around that number.
3. **One face, forever.** A companion whose appearance drifts between images is not a person, it is a slideshow. Identity lock is non-optional.
4. **The constraints are legal, not technical.** App stores, payment processors, and model providers all restrict this category. The architecture is shaped by that reality from the first commit rather than retrofitted after the first shutdown.

---

## Status

Pre-code. Documentation complete, implementation not started. See [15 — Roadmap](docs/15-ROADMAP-AND-MILESTONES.md).

## License

[MIT](LICENSE) for the code in this repository. The documentation is provided as-is; the pricing data within it is a point-in-time snapshot and must be re-verified before it is relied on.
