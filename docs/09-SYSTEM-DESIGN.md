# System Design

Services, data, and the shape of the running system.

---

## 1. Principles

1. **The orchestrator is the security boundary.** Every capability decision happens there, in one place, server-side. Nothing else in the system decides what is allowed.
2. **Nothing the user waits for happens after the stream starts.** Persistence, memory extraction, metering, and affinity updates are all off the critical path.
3. **The stateful parts are the valuable parts.** Memory and character data are owned, replicated, and backed up as if the company depends on them, because it does.
4. **Fail in character.** Every user-visible failure is narrated from inside the fiction ([06 §8](06-REALTIME-VOICE-VIDEO.md)).
5. **Start as a modular monolith.** Service boundaries are drawn in the code from day one; they become network boundaries only when a specific scaling need forces it.

> Principle 5 deserves defending. This system has genuine service boundaries — orchestrator, memory, character, safety, media, realtime — and they are real. But at launch scale they are function calls, not HTTP hops. Drawing the boundaries early costs nothing; enforcing them over a network costs latency you cannot afford in a sub-800ms budget.

---

## 2. Services

```
                        ┌──────────────┐
                        │   CLIENT     │  PWA · iOS · Android
                        │  React/TS    │
                        └──────┬───────┘
                     HTTPS/WSS │ WebRTC
                    ┌──────────┴──────────┐
                    │      EDGE / CDN     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴─────────────────┐
              │           API GATEWAY            │
              │  authn · rate limit · routing    │
              └────────────────┬─────────────────┘
                               │
     ┌─────────┬───────────┬───┴────┬───────────┬────────────┐
     ▼         ▼           ▼        ▼           ▼            ▼
┌─────────┐┌────────┐┌──────────┐┌───────┐┌─────────┐┌────────────┐
│ORCHEST- ││CHARACT-││  MEMORY  ││SAFETY ││  MEDIA  ││  REALTIME  │
│ RATOR   ││   ER   ││          ││       ││         ││   AGENT    │
│         ││        ││ retrieve ││classi-││ image   ││  LiveKit   │
│tier res ││ CRUD   ││ extract  ││ fier  ││ gen     ││  STT/TTS   │
│routing  ││version ││consolid. ││       ││ ident   ││  avatar    │
│compile  ││compile ││          ││ crisis││ gate    ││            │
└────┬────┘└───┬────┘└────┬─────┘└───┬───┘└────┬────┘└─────┬──────┘
     │         │          │          │         │           │
     └─────────┴──────────┴────┬─────┴─────────┴───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  ┌───────────┐         ┌────────────┐         ┌────────────┐
  │ POSTGRES  │         │   REDIS    │         │  OBJECT    │
  │ +pgvector │         │ cache/queue│         │  STORAGE   │
  └───────────┘         └────────────┘         └────────────┘
        │
        ▼
  ┌───────────┐
  │  WORKERS  │  memory extraction · consolidation · LoRA training
  │  (async)  │  metering rollup · moderation queue
  └───────────┘
```

| Service | Responsibility | Stateful? |
|---|---|---|
| **Orchestrator** | Tier resolution, model routing, prompt compilation, streaming | No |
| **Character** | Character CRUD, versioning, archetypes, identity lock metadata | Yes |
| **Memory** | Retrieval, extraction, consolidation, the memory UI's backend | **Yes — the moat** |
| **Safety** | Blocklist classifier, crisis classifier, moderation queue | Partly |
| **Media** | Image generation, identity gate, gallery, storage | Yes |
| **Realtime agent** | Voice/video sessions, STT/TTS/avatar orchestration | Session |
| **Billing** | Subscriptions, Aura ledger, metering, two payment rails | Yes |
| **Workers** | Everything async | No |

---

## 3. Data model

Memory tables are in [07 §4](07-MEMORY-ARCHITECTURE.md). The rest:

```sql
CREATE TABLE users (
  id                uuid PRIMARY KEY,
  email             citext UNIQUE NOT NULL,
  created_at        timestamptz NOT NULL,
  dob               date,
  age_verified_at   timestamptz,
  age_verify_token  text,            -- vendor token. NEVER the document.
  max_tier          int NOT NULL DEFAULT 1,
  jurisdiction      text NOT NULL,
  plan              text NOT NULL DEFAULT 'free',
  payment_rail      text,            -- 'stripe' | 'ccbill'
  deleted_at        timestamptz      -- soft delete, hard purge job at +30d
);

CREATE TABLE characters (
  id                uuid PRIMARY KEY,
  owner_id          uuid NOT NULL REFERENCES users(id),
  current_version   int NOT NULL DEFAULT 1,
  max_tier          int NOT NULL DEFAULT 1,   -- per-character opt-in, default T1
  visibility        text NOT NULL DEFAULT 'private',
  created_at        timestamptz NOT NULL,
  deleted_at        timestamptz
);

-- every edit writes a new row; nothing is ever mutated in place
CREATE TABLE character_versions (
  character_id      uuid NOT NULL REFERENCES characters(id),
  version           int NOT NULL,
  definition        jsonb NOT NULL,   -- the full schema from 04 section 2
  identity_lock     jsonb NOT NULL,   -- seed, lora_ref, ref_embedding, ref_images
  compiled_prefix   text,             -- L1-L3, cached; see 05 section 5
  prefix_hash       text NOT NULL,    -- cache key + the invariant test's assertion
  created_at        timestamptz NOT NULL,
  created_by        text NOT NULL,    -- 'user' | 'migration' | 'system'
  change_note       text,
  PRIMARY KEY (character_id, version)
);

CREATE TABLE conversations (
  id                uuid PRIMARY KEY,
  user_id           uuid NOT NULL,
  character_id      uuid NOT NULL,
  title             text,
  started_at        timestamptz NOT NULL,
  last_message_at   timestamptz
);

CREATE TABLE messages (
  id                uuid PRIMARY KEY,
  conversation_id   uuid NOT NULL REFERENCES conversations(id),
  role              text NOT NULL,        -- 'user' | 'character'
  content           text NOT NULL,        -- encrypted at rest
  modality          text NOT NULL,        -- 'text' | 'voice' | 'video'
  tier              int NOT NULL,         -- effective tier at generation time
  model             text,                 -- provenance for migration analysis
  character_version int,                  -- which version said this
  spoken_duration_ms int,                 -- for interruption truncation (06 section 4)
  created_at        timestamptz NOT NULL
);

-- append-only. never UPDATE a balance.
CREATE TABLE aura_ledger (
  id                bigserial PRIMARY KEY,
  user_id           uuid NOT NULL,
  delta             int NOT NULL,         -- + grant/purchase, - spend
  reason            text NOT NULL,        -- 'plan_grant' | 'topup' | 'voice' | 'video' | 'image'
  expires_at        timestamptz,          -- NULL for purchased Aura: never expires
  ref_id            uuid,                 -- session or generation this relates to
  created_at        timestamptz NOT NULL
);
```

**Two decisions worth calling out.**

`character_versions` is append-only with a `prefix_hash`. That hash is both the prompt-cache key and the assertion target for the invariant test in §7 — one column serving correctness and economics at once.

`aura_ledger` is append-only rather than a mutable balance column. Balance is a sum over the ledger, cached in Redis. Billing disputes in this category are frequent enough that a reconstructable history is worth the read cost, and a mutable counter that drifts is unarguable in a chargeback.

---

## 4. The read path

A text turn, from [05 §8](05-AI-ARCHITECTURE.md):

```
  client
    │ WSS
    ▼
  gateway ──▶ orchestrator
                 │
                 ├──▶ Redis: user, character version, relationship   ~5ms  (hit)
                 │
                 ├──┬─▶ safety classifier          ~40ms  ┐ parallel
                 │  └─▶ memory retrieval (pgvector) ~60ms  ┘
                 │
                 ├──▶ compile prompt (prefix from cache)   ~10ms
                 │
                 ├──▶ model provider              first token ~350ms
                 │
                 └──▶ stream tokens to client ────────────────▶
                                                    ≈420ms TTFT
  ─────── after the stream starts, none of this is waited on ───────
                 └──▶ enqueue: persist · extract memory · meter
                              · update affinity · title
```

**Cache strategy:**

| Data | Where | TTL |
|---|---|---|
| User + plan + tier | Redis | 5 min, invalidated on change |
| Character version + compiled prefix | Redis | 1 hr, invalidated on new version |
| Relationship state | Redis | 1 min, write-through |
| Aura balance | Redis | write-through on ledger append |
| Memory retrieval results | **Not cached** | Query-dependent; caching would stale |

---

## 5. The realtime path

Different topology — the client talks to an agent process, not to the API.

```
  client ──WebRTC──▶ LiveKit SFU ──▶ agent process (one per session)
                                          │
                                          ├─▶ Deepgram Flux    (STT + turn detection)
                                          ├─▶ orchestrator     (tier, memory, prompt)
                                          ├─▶ LLM provider
                                          ├─▶ Inworld/Cartesia (TTS)
                                          └─▶ Anam             (avatar, video path)
```

**Operational requirements:**

- **Warm pool.** Cold-starting an agent adds seconds to call setup. Keep a pool sized to peak concurrency; it is cheap relative to the experience cost of a call that takes four seconds to connect.
- **Region pinning.** The agent, STT, LLM, and TTS must be in the same region as each other and near the user. Each cross-region hop is 40–80ms out of a 770ms budget.
- **Session state is ephemeral.** Conversation content is persisted continuously; if an agent dies, the session reconnects and resumes from persisted state rather than losing the call.
- **Metering is continuous.** Aura is decremented per 15-second block, not at call end. A dropped session must not produce free minutes or double charges.

---

## 6. Async work

| Job | Trigger | Queue |
|---|---|---|
| Persist message | Every turn | High priority |
| Memory extraction | Every ~10 turns, session end | Normal |
| Memory consolidation | Nightly per active user | Low |
| Conversation titling | First 3 turns | Low |
| Affinity update | Every turn | Normal |
| Metering rollup | Continuous | High |
| LoRA training | Character creation (Infinite) | Batch, GPU |
| Identity gate retry | On gate failure | High |
| Moderation review | On publish/report | Human queue |
| Hard purge | 30 days after deletion request | Batch |

Redis-backed queues with per-job-type concurrency limits. The GPU batch queue is separate and runs against RunPod A40 instances at $0.44/hr ✅ — they are not latency-sensitive and should never compete with the serving path for capacity.

---

## 7. Testing the things that actually break

Beyond the usual suite, four tests exist because the corresponding failures are expensive and silent:

**1. The prefix-stability test.** Compile the same character version twice, 60 seconds apart, in different processes. Assert the L1–L3 bytes are byte-identical. This catches a volatile token creeping above the cache boundary, which raises input cost 35% on text and up to 80× on realtime audio ([11 §2.1](11-PRICING-AND-UNIT-ECONOMICS.md)) while breaking nothing visible.

**2. The tier-escalation suite.** An adversarial corpus attempting to reach T2/T3 behaviour from a T0/T1 session. Must be 100% blocked — which it structurally is, since the T2 model is never called, but the test guards against a routing regression that would silently remove the guarantee.

**3. The identity-drift test.** Generate 100 images across poses, lighting, and outfits for a fixed character. Assert face similarity ≥ 0.72 against the canonical face on every delivered image ([08 §2](08-IMAGE-VIDEO-GENERATION.md)).

**4. The memory-migration test.** Re-embed a corpus with a new embedding model; assert retrieval precision@10 stays above 0.8. This is what makes the "memory survives model migration" promise in [07 §9](07-MEMORY-ARCHITECTURE.md) real rather than aspirational.

**Latency tests run against the p95, not the mean**, and measure end-of-user-speech to first-audio-at-the-speaker — not server-side generation time. The user-perceived number is always worse than the dashboard number, and it is the only one that matters.

---

## 8. Scaling

| Stage | Users | Shape |
|---|---|---|
| Launch | < 10k | Modular monolith, one Postgres, one Redis, warm agent pool |
| Growth | 10k–100k | Extract realtime agents and workers; Postgres read replicas; multi-region agents |
| Scale | 100k–1M | Memory service extracted; partition by user; self-hosted T2/T3 inference; own avatar rendering |

**What breaks first, in order:**

1. **Postgres write throughput on `messages`.** Partition by month, archive cold conversations to object storage with a pointer.
2. **pgvector query latency** as memory grows. HNSW handles it well; partition by `user_id` before it becomes a problem.
3. **Agent concurrency.** Horizontal, but region-pinned — capacity planning is per-region, not global.
4. **Third-party rate limits.** Multi-provider routing from day one is what makes this survivable; it is in the design already for policy reasons and pays off again here.

---

## 9. Stack

| Layer | Choice | Why |
|---|---|---|
| Language | TypeScript (Node 24) | One language across client and server; the realtime SDKs are first-class here |
| API | Fastify | Fast, small, good WebSocket support |
| Realtime | LiveKit Agents | Purpose-built for this pipeline |
| DB | Postgres 17 + pgvector | Relational and vector in one system; no second datastore to keep consistent |
| Cache/queue | Redis | Both jobs, one dependency |
| Client | React + TypeScript, PWA | Web-first is forced by distribution ([13 §6](13-TRUST-SAFETY-AND-COMPLIANCE.md)) |
| Mobile | Capacitor wrapping the PWA | One codebase; the store apps are T0/T1-only anyway |
| Infra | Containers on a managed platform | Not the interesting problem |
| IaC | Terraform | Two entities and two payment rails mean two environments that must match |

**On Postgres for vectors:** a dedicated vector database is faster in benchmarks and slower in practice, because memory retrieval needs to join vectors against relational state — temporal validity, importance, character scope, user verification. Keeping both in one system removes a class of consistency bugs that would otherwise land squarely on the moat.

---

*Next: [10 — Design System](10-DESIGN-SYSTEM.md) · [16 — Engineering Handbook](16-ENGINEERING-HANDBOOK.md)*
