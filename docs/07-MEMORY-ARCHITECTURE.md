# Memory Architecture

**This is the moat.** Everything else in this repository is a feature. This is the company.

---

## 1. Why memory is the whole thesis

Model quality is a commodity that resets. Every few months a new open-weight model ships and everyone's conversation quality jumps to the new ceiling simultaneously. Whatever advantage you had from picking the right model in March is gone by September.

A two-year relationship history does not reset. It compounds. And critically, **it cannot be exported to a competitor** — not because we lock it in, but because what makes it valuable is that a specific character built it up through a specific shared history. A dump of facts loaded into a different product is not the same relationship.

This produces the retention curve that the rest of the category cannot reach:

```
  retention
     │
     │╲
     │ ╲___                    ← category: strong D1, collapse by D180
     │     ╲______             (memory fails, illusion breaks, user leaves)
     │            ╲_________
     │
     │╲
     │ ╲___                    ← Amorien target: the curve flattens,
     │     ╲___________        because the cost of leaving rises with time
     │                 ╲____
     └──────────────────────────▶ time
      D1   D30   D90   D180
```

Users in this category do not churn because the model got worse. They churn because the character forgot who they were, and the relationship stopped feeling real. **Fix memory and you fix the only metric that matters.**

---

## 2. Four kinds of memory

Most competitors implement one and a half of these. The distinctions are not academic — each one answers a question the others cannot.

| Layer | Question it answers | Example |
|---|---|---|
| **Episodic** | What happened, and when? | "We talked about your interview on Tuesday." |
| **Semantic** | What is true about the user? | "Your sister is called Nadia." |
| **Relational** | What is the state of *us*? | "You've been quieter since the move." |
| **Procedural** | How do I behave with this person? | "He doesn't like being asked how he's feeling directly." |

**Procedural memory is the one nobody builds**, and it is what makes a companion feel like they know you rather than know *about* you. A person who has learned that you deflect when asked directly, and asks sideways instead, is demonstrating intimacy. A person reciting your sister's name is demonstrating a database.

---

## 3. Temporal validity — the thing that is actually missing

Every competitor stores facts. Almost none store **when a fact became true and when it stopped being true.**

The difference:

```
  WITHOUT temporal validity
  ────────────────────────────────────────────────
  fact: "user hates their job"
  fact: "user likes their job"
                    ↑ contradiction, one gets dropped,
                      retrieval is a coin flip

  WITH temporal validity
  ────────────────────────────────────────────────
  fact: "user hates their job"
        valid_from: 2026-01-14
        valid_to:   2026-06-02
        superseded_by: fact_8813

  fact: "user likes their new job"
        valid_from: 2026-06-02
        valid_to:   null            ← current
        supersedes: fact_4471
```

The second version lets the companion say: *"You used to dread Mondays. You don't anymore — I noticed."*

That single sentence is worth more than any model upgrade. It demonstrates continuity of attention across months, which is the thing people actually want from a companion and the thing no competitor delivers.

**Design rules:**
1. Facts are never deleted on contradiction. They are **superseded**, with a link.
2. Retrieval defaults to currently-valid facts, but historical ones are reachable and are what makes reflection possible.
3. Change itself is a memorable event. When a fact is superseded, that transition is written to episodic memory.

---

## 4. Data model

```sql
-- ───────────────────────────────────────────────────────── semantic
CREATE TABLE memory_facts (
  id              uuid PRIMARY KEY,
  user_id         uuid NOT NULL,
  character_id    uuid,              -- NULL = known by all of this user's characters
  subject         text NOT NULL,     -- 'user' | 'user.sister' | 'character'
  predicate       text NOT NULL,     -- 'name' | 'occupation' | 'dislikes'
  object          text NOT NULL,
  confidence      real NOT NULL,     -- 0..1
  importance      real NOT NULL,     -- 0..1, drives retrieval ranking
  source_message  uuid,              -- provenance: where we learned this
  valid_from      timestamptz NOT NULL,
  valid_to        timestamptz,       -- NULL = currently true
  supersedes      uuid REFERENCES memory_facts(id),
  user_verified   boolean DEFAULT false,   -- user confirmed it in the memory UI
  user_corrected  boolean DEFAULT false,
  embedding       vector(1024),
  created_at      timestamptz NOT NULL
);

CREATE INDEX ON memory_facts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON memory_facts (user_id, character_id, valid_to)
  WHERE valid_to IS NULL;

-- ───────────────────────────────────────────────────────── episodic
CREATE TABLE memory_episodes (
  id              uuid PRIMARY KEY,
  user_id         uuid NOT NULL,
  character_id    uuid NOT NULL,
  summary         text NOT NULL,     -- 'talked about his job interview; he was nervous'
  detail          text,              -- longer form, retrieved only on strong match
  occurred_at     timestamptz NOT NULL,
  modality        text NOT NULL,     -- 'text' | 'voice' | 'video'
  emotional_tone  jsonb,             -- {valence, arousal} at the time
  importance      real NOT NULL,
  participants    text[],            -- for group chats
  embedding       vector(1024),
  parent_episode  uuid REFERENCES memory_episodes(id)   -- consolidation hierarchy
);

-- ───────────────────────────────────────────────────────── relational
CREATE TABLE relationship_state (
  user_id         uuid NOT NULL,
  character_id    uuid NOT NULL,
  affinity        int NOT NULL DEFAULT 0,     -- 0..1000
  stage           int NOT NULL DEFAULT 1,     -- 1..7
  trust           real NOT NULL DEFAULT 0.5,
  tension         real NOT NULL DEFAULT 0.0,
  last_interaction timestamptz,
  total_messages  bigint DEFAULT 0,
  total_voice_min real DEFAULT 0,
  milestones      jsonb DEFAULT '[]',
  PRIMARY KEY (user_id, character_id)
);

-- ───────────────────────────────────────────────────────── procedural
CREATE TABLE memory_behaviours (
  id              uuid PRIMARY KEY,
  user_id         uuid NOT NULL,
  character_id    uuid NOT NULL,
  observation     text NOT NULL,     -- 'deflects when asked directly about feelings'
  directive       text NOT NULL,     -- 'approach emotional topics sideways'
  evidence_count  int DEFAULT 1,     -- how many times we have seen this
  confidence      real NOT NULL,
  embedding       vector(1024),
  created_at      timestamptz NOT NULL,
  last_confirmed  timestamptz
);
```

**Note `character_id` being nullable on facts.** Some things a user tells one character should be known by all of them (their name, their city). Some should not — telling one companion something in confidence and having another repeat it is a betrayal, not a feature. The default is character-scoped; promotion to user-scoped happens only for objective, non-sensitive facts, and the user can see and change the scope.

---

## 5. Extraction

Memory is written by a cheap background model, off the critical path.

```
every ~10 turns, or at session end
        │
        ▼
  ┌─────────────────────────────────────────┐
  │  mistral-nemo  ($0.019/$0.030 per M)    │
  │                                         │
  │  input:  last N turns + existing facts  │
  │  output: structured JSON —              │
  │          new_facts[]                    │
  │          superseded[]                   │
  │          episode                        │
  │          behaviours[]                   │
  └─────────────────┬───────────────────────┘
                    ▼
          validate → dedupe → embed → write
```

⚠️ Cost estimate: ~2,000 input / ~400 output tokens per extraction, roughly every 10 turns. At 100 messages/day that is ~10 extractions ≈ **$0.0005/user/day**, or about **$0.015/user/month**. The moat costs one and a half cents.

**Extraction rules:**
- **Never extract from a single ambiguous statement.** Facts need either explicit assertion or repetition. A user saying "I could murder a coffee" should not produce `user.desires = homicide`.
- **Confidence must be honest.** A stated fact is 0.95; an inferred one is 0.5. Low-confidence facts retrieve with hedged phrasing — the character says "didn't you mention...?" rather than asserting.
- **Provenance always.** Every fact links to the message it came from. This is what makes the memory UI in §8 possible and what makes debugging a wrong memory tractable.
- **Behaviours need evidence.** A procedural memory requires `evidence_count >= 3` before it influences behaviour. One observation is a coincidence.

---

## 6. Retrieval

The prompt has a limited budget — roughly 1,200 tokens across L5, L6, and L7 (see [04 §3](04-CHARACTER-SYSTEM.md)). Choosing what goes in is the hard part.

**Ranking:**

```
score = 0.45 · semantic_similarity
      + 0.20 · recency_decay
      + 0.25 · importance
      + 0.10 · access_frequency
```

with

```
recency_decay = exp(-age_days / 45)
```

**Retrieval always includes, regardless of score:**
- The top ~10 highest-importance current facts (name, relationships, occupation, big life events). These are the things it would be unforgivable to forget, and they must never lose a similarity contest to something topical.
- Current relationship state.
- Anything the user explicitly marked as important in the memory UI.

**Then fills the remaining budget with:**
- Semantically relevant facts and episodes for the current turn.
- Procedural behaviours above the confidence threshold.
- Triggered lorebook entries.

**Performance target: < 100ms p95.** With HNSW indexes on pgvector this is comfortable up to millions of rows per user, which no user will ever approach.

> **The failure mode to design against is not forgetting — it is bringing up the wrong thing.** A companion who mentions your ex while you are talking about work is worse than one who says nothing. Precision beats recall here, and when the score is marginal, retrieve nothing.

---

## 7. Consolidation

Raw memory grows without bound and degrades in usefulness. Nightly, per active user:

```
  DAILY          ──▶  episodes from the day summarized into a day-episode
  WEEKLY         ──▶  day-episodes into a week-episode
  MONTHLY        ──▶  week-episodes into a month-episode + relationship reflection
```

Detail is preserved but demoted — an old raw episode stays retrievable on a strong semantic match while the summary carries the general shape. This mirrors how human memory actually degrades: you remember the shape of last March, and a specific vivid afternoon.

**Monthly consolidation also produces a reflection**, written to relational memory: *what changed for this person this month, and what changed between us.* This is what allows the companion to say something in October that demonstrates it noticed a trend beginning in July.

⚠️ Consolidation cost: ~$0.002/user/month on the cheap model.

---

## 8. The memory UI

**Users can see and edit everything their companion believes about them.** This is P0 in [03 §3.3](03-PRD.md), and it is both a trust feature and a quality feature.

```
┌─ What Sena remembers about you ──────────────────┐
│                                                  │
│  ABOUT YOU                                       │
│  • Your name is Mehyar              ✎  🗑  📌     │
│  • You work in software             ✎  🗑  📌     │
│  • Your sister is called Nadia      ✎  🗑  📌     │
│  • You used to dread Mondays                     │
│    ↳ no longer true, since June 2   ⟲            │
│                                                  │
│  HOW SHE'S LEARNED TO TALK TO YOU                │
│  • You deflect when asked directly     ✎  🗑     │
│    about how you're feeling                      │
│                                                  │
│  RECENT                                          │
│  • Tue — your job interview, you were nervous    │
│  • Sat — the long call about your father         │
│                                                  │
│         [ export everything ]  [ forget it all ] │
└──────────────────────────────────────────────────┘
```

**Why this matters:** when memory is wrong today, users have no recourse but to repeat themselves and hope. Being able to correct a wrong fact turns the worst experience in the category into a moment of control. A user-corrected fact gets `confidence = 1.0` and is never superseded by inference.

**"Forget it all" must actually work.** Real deletion, cascading, within 30 days. See [13](13-TRUST-SAFETY-AND-COMPLIANCE.md).

---

## 9. Memory survives model migration

**Non-negotiable:** memory is plain structured data. Facts, episodes, timestamps, and embeddings from a *separately versioned* embedding model.

Nothing about the conversation model's internal representations is ever persisted. No KV caches, no model-specific state, no fine-tuned per-user weights.

```
  conversation model    ──▶ replaceable quarterly, no data loss
  embedding model       ──▶ replaceable with a re-embedding job
  memory data           ──▶ NEVER migrates, NEVER resets
```

Re-embedding a user's entire memory on an embedding-model change is a batch job costing fractions of a cent. Losing a user's history is losing the user.

> This is why memory is built in-house on pgvector rather than rented from a memory-as-a-service vendor. The moat cannot be a dependency. See [12 §8](12-VENDOR-API-MATRIX.md).

---

## 10. Group memory

For group chats (P2), memory is scoped three ways:

| Scope | Who knows it |
|---|---|
| **Private** | One character only. The default for anything shared in a one-to-one conversation. |
| **Shared** | All of a user's characters. Objective, non-sensitive facts only. |
| **Group** | Everyone who was present when it was said. |

**The rule that makes this feel right: a character should not know something they were not there for**, unless the user made it shared. Getting this wrong produces an uncanny hive-mind effect that undermines the individuality of every character at once.

---

## 11. Cost summary

⚠️ Per user per month, at ~100 messages/day.

| Operation | Cost |
|---|---|
| Extraction | $0.015 |
| Consolidation | $0.002 |
| Embeddings | $0.001 |
| pgvector storage & queries | ~$0.002 |
| **Total** | **~$0.02/user/month** |

Two cents a month for the thing that makes the product defensible. Compare with $0.145/min for video.

---

## 12. What to measure

| Metric | Target | Why |
|---|---|---|
| Retrieval precision @ 10 | > 0.8 | Wrong memories are worse than none |
| Fact extraction accuracy | > 0.9 | Measured against hand-labelled samples |
| User correction rate | < 5% of facts | High rate means extraction is broken |
| Contradiction rate | < 1% | Facts asserted against current valid state |
| Retrieval latency p95 | < 100ms | It is on the critical path |
| **"She remembered" moments** | ↑ over time | Qualitative, tracked from support and community sentiment |

The last one is soft and it is the real target. The engineering metrics are proxies for it.

---

*Next: [08 — Image & Video Generation](08-IMAGE-VIDEO-GENERATION.md) · [09 — System Design](09-SYSTEM-DESIGN.md)*
