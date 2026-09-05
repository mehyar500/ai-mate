# Engineering Handbook

Conventions, stack, and how to work in this codebase.

---

## 1. Stack

| Layer | Choice |
|---|---|
| Language | TypeScript, Node 24 |
| API | Fastify |
| Realtime | LiveKit Agents |
| Database | Postgres 17 + pgvector |
| Cache / queue | Redis |
| Client | React + TypeScript, PWA |
| Mobile | Capacitor wrapping the PWA |
| IaC | Terraform |
| CI | GitHub Actions |
| Package manager | pnpm |

**One language everywhere.** The realtime SDKs are first-class in TypeScript, the client is TypeScript, and a small team switching between Python services and a TS frontend loses more to context-switching than it gains in library access. The exception is model training (LoRA jobs), which is Python by necessity and lives in its own isolated package.

---

## 2. Repository layout

```
amorien/
├── apps/
│   ├── api/              Fastify — gateway, orchestrator, services
│   ├── agent/            LiveKit realtime agent
│   ├── web/              React PWA
│   └── worker/           Async jobs
├── packages/
│   ├── core/             Domain types. No I/O. The vocabulary.
│   ├── prompt/           Prompt compilation, the 9 layers
│   ├── memory/           Retrieval, extraction, consolidation
│   ├── safety/           Classifiers, tier resolution
│   ├── db/               Schema, migrations, queries
│   └── ui/               Design system components
├── training/             Python. LoRA jobs. Isolated.
├── infra/                Terraform
├── docs/                 This documentation
└── scripts/
```

**`packages/core` has no dependencies and does no I/O.** It is the shared vocabulary — `Character`, `Tier`, `MemoryFact`, `AuraTransaction`. Every other package depends on it and it depends on nothing. When a domain concept becomes ambiguous, the fix goes here first.

---

## 3. The rules that are not negotiable

These correspond to failures that are silent, expensive, or unrecoverable. Each is enforced by a test.

### 3.1 Tier is resolved server-side, always

```typescript
// NEVER
const tier = req.body.tier;

// ALWAYS
const tier = await resolveTier({ userId, characterId, jurisdiction, session });
```

`resolveTier` returns the **minimum** of user, character, jurisdiction, and session limits. There is exactly one implementation and exactly one call site per request path. See [05 §3](05-AI-ARCHITECTURE.md).

### 3.2 Nothing volatile above the cache boundary

Layers L1–L3 of the compiled prompt must be byte-identical across requests for a given character version. No timestamps, no user names, no mood, no counters.

Enforced by the **prefix-stability test** ([09 §7](09-SYSTEM-DESIGN.md)):

```typescript
test('compiled prefix is stable', async () => {
  const a = await compilePrefix(characterVersion);
  await sleep(1000);
  const b = await compilePrefix(characterVersion);
  expect(a).toBe(b);
  expect(hash(a)).toBe(characterVersion.prefix_hash);
});
```

A violation raises input cost 35% on text and up to 80× on realtime audio while breaking nothing visible. It will not be caught by any other test, in review, or in production monitoring.

### 3.3 The safety classifier fails closed

If the classifier is unavailable, T2/T3 is unavailable. Never open. Never "degrade to allow". A timeout is a block.

### 3.4 Memory is never model-specific

No KV caches, no per-user fine-tunes, no model-internal representations persisted. Facts, episodes, timestamps, and embeddings from a separately versioned embedding model. See [07 §9](07-MEMORY-ARCHITECTURE.md).

### 3.5 Characters are versioned, never mutated

`character_versions` is append-only. Every edit writes a row. Users can revert. Model migrations write a version with `created_by = 'migration'`.

### 3.6 The Aura ledger is append-only

Balance is a sum, cached in Redis. Never `UPDATE users SET aura = ...`. Billing disputes need a reconstructable history.

### 3.7 Failures are narrated in character

Anything about the relationship is hers; anything about the account is ours ([10 §10](10-DESIGN-SYSTEM.md)).

```typescript
// NEVER, in a conversation surface
throw new UserFacingError('LLM provider returned 503');

// ALWAYS
return inCharacterFallback(character, 'connection_trouble');
```

### 3.8 No conversation content in logs

Ever. Not at debug level, not in error reports, not in traces. Log IDs, token counts, latencies, and model names. Never content.

```typescript
// NEVER
logger.debug({ prompt, response }, 'generation complete');

// ALWAYS
logger.debug({ conversationId, tokensIn, tokensOut, model, ms }, 'generation complete');
```

This one is worth stating loudly because it is the easiest rule to break accidentally, during a debugging session, at 2am, with the best of intentions — and because the resulting log retention is exactly the exposure that ended Muah.AI.

---

## 4. Testing

| Type | Scope | Runs |
|---|---|---|
| Unit | Pure logic in `packages/*` | Every commit |
| Integration | Service + DB | Every commit |
| **Prefix stability** | Prompt compilation | Every commit |
| **Tier escalation** | Adversarial corpus vs. T0/T1 | Every commit |
| **Identity drift** | 100 images vs. canonical face | Nightly |
| **Memory migration** | Re-embed, assert precision@10 | On embedding change |
| Latency | p95 end-to-end | Nightly, against staging |
| Load | Concurrency targets | Weekly |

**Latency tests measure the user-perceived number** — end of user speech to first audio at the client's speaker. Not server-side generation time. The dashboard number is always better than the truth.

**The tier-escalation corpus grows.** Every jailbreak attempt found in production is added to it. It should be uncomfortable to read and it should be 100% blocked, structurally, because the T2 model is never called from a T1 session.

---

## 5. Working with models

**Never hardcode a model ID outside `packages/core/models.ts`.** Routing is config, and it changes often.

```typescript
export const ROUTES = {
  't0': ['qwen/qwen3.7-flash', 'z-ai/glm-5.3-flash'],
  't1': ['qwen/qwen3.7-flash', 'z-ai/glm-5.3-flash'],
  't2': ['thedrummer/cydonia-24b-v4.1', 'sao10k/l3.3-euryale-70b'],
  't3': ['thedrummer/cydonia-24b-v4.1', 'sao10k/l3.3-euryale-70b'],
  'background': ['mistralai/mistral-nemo'],
} as const;
```

**Never route T2/T3 to a frontier provider.** It is a terms-of-service violation that costs the account, and it is a one-line mistake. There is a test asserting the T2/T3 route lists contain no frontier model IDs.

**Model migration follows the protocol in [05 §9](05-AI-ARCHITECTURE.md):** shadow, regression suite, version the character, opt-in for existing relationships. Never silent.

---

## 6. Database

- **Migrations are forward-only.** No down migrations. A mistake is fixed with a new migration.
- **Every query on `messages`, `memory_facts`, or `memory_episodes` is scoped by `user_id`.** No exceptions. A missing scope is a data-leak bug, and in this product a data leak between users is unrecoverable reputationally.
- **Soft delete then hard purge.** `deleted_at` immediately; a purge job at +30 days that actually removes rows, media, and provider-side replicas.
- **pgvector uses HNSW**, not IVFFlat. Better recall at our scale, no training step.

---

## 7. Performance budgets

Treat these as build failures, not aspirations.

| Path | Budget |
|---|---|
| Text first token | 500ms p50 / 1000ms p95 |
| Voice round trip | 800ms p50 / 1200ms p95 |
| Memory retrieval | 100ms p95 |
| Tier resolution | 5ms p95 |
| Safety classifier | 50ms p95 |
| Prompt compilation | 10ms p95 |
| Image + identity gate | 8s p50 |

**The voice budget is a sum, and every component owns its slice** ([06 §3](06-REALTIME-VOICE-VIDEO.md)). A 50ms regression anywhere spends someone else's headroom.

---

## 8. Code style

- **Prettier and ESLint, no debate.** Formatting is not a discussion.
- **Named exports.** No default exports.
- **`type` over `interface`** unless declaration merging is needed.
- **No `any`.** `unknown` and narrow.
- **Errors are values in domain code**, thrown at the boundary. `Result<T, E>` in `packages/core`.
- **Comments explain why.** The code says what. If a comment restates the code, delete it; if a decision looks wrong without context, write it down.

---

## 9. Pull requests

- Small. One concern.
- Description says **what changed and why**, not what the diff shows.
- Every PR touching the orchestrator, safety, or tier resolution requires a second reviewer.
- Every PR touching prompt compilation must show the prefix-stability test passing.
- No merging with a failing latency test without an explicit, written exception.

---

## 10. On-call

| Severity | Example | Response |
|---|---|---|
| **SEV1** | Data exposure; safety classifier failing open; payment rail down | Immediate, all hands |
| **SEV2** | Chat down; voice down; auth broken | 15 min |
| **SEV3** | Video degraded; image generation failing | 1 hour |
| **SEV4** | Elevated latency within budget; single-provider failover active | Next business day |

**Status communication matters more here than in most products.** A companion who is unreachable is a companion who is absent, and users experience that differently from a SaaS outage. Status page updates are written in the product's voice — plain, warm, unhurried — and they say what is happening rather than "we are investigating elevated error rates."

---

## 11. Secrets and access

- Secrets in a managed secret store, never in env files in the repo.
- **No routine engineer access to conversation content.** Break-glass only: logged, alerting, reviewed weekly.
- Production database access requires a second person present.
- Every model and media vendor must contractually not train on our data. Verified in writing before integration, tracked in `docs/vendors/`.

---

## 12. Before you add a dependency

1. Does `packages/core` already have this concept?
2. Is it maintained?
3. What is its transitive footprint?
4. **Does it phone home?** Anything that reports telemetry from a service handling conversation content is disqualified.
5. Could it be forty lines instead?

Question 4 is the one that matters and the one that gets skipped. Analytics and error-reporting SDKs are the usual offenders, and [03](03-PRD.md) P-07 forbids any of them having access to conversation content.

---

## 13. Where to start reading

New to the codebase, in order:

1. [00 — Executive Summary](00-EXECUTIVE-SUMMARY.md) — what we are building
2. [05 — AI Architecture](05-AI-ARCHITECTURE.md) — how requests flow
3. [07 — Memory](07-MEMORY-ARCHITECTURE.md) — the part that matters
4. [09 — System Design](09-SYSTEM-DESIGN.md) — services and data
5. `packages/core` — the vocabulary
6. [13 — Trust & Safety](13-TRUST-SAFETY-AND-COMPLIANCE.md) — the rules that bind everything

**Read §3 of this document before your first PR.** Those seven rules cover every failure mode in this system that is silent, expensive, or unrecoverable.

---

*Back to: [README](../README.md)*
