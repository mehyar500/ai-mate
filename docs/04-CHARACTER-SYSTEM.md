# The Character System

How an Amorien is defined, generated, rendered, remembered, and changed over time.

This is the core intellectual property of the product. Chat quality is a commodity you buy from a model provider; **character coherence is the thing you actually build.**

---

## 1. Design principles

1. **A character is data, not a prompt.** Never store a companion as a blob of English. Store it as a typed object and *compile* the prompt from it at request time. This is what makes editing, versioning, A/B testing and cross-model portability possible.
2. **Identity is immutable; state is mutable.** Face, voice, name and core temperament are locked at creation — users bond to them. Mood, relationship stage, inside jokes and memory accumulate.
3. **One face, forever.** The most common failure in this category is the companion looking like a different person in every image. We solve identity lock at the architecture level (§7), not with prompt engineering.
4. **Traits must have mechanical consequences.** A trait that only appears in the system prompt is decoration. Every trait on the sheet must change at least one of: word choice, message length, initiation frequency, jealousy response, or content gating.
5. **The user is a character too.** We model the *user's* persona with the same schema. Companion behaviour is a function of both sheets, not one.
6. **Presets get 90% there in 30 seconds; the editor goes 100%.** Time-to-first-message governs activation. Deep customization is a retention feature, not an onboarding one.

---

## 2. The character object

The canonical schema. Stored in Postgres as typed columns plus `jsonb` for open-ended parts, versioned on every edit.

```jsonc
{
  "id": "chr_01J8X...",
  "version": 7,                      // increments on every edit; prompts pin a version
  "owner_id": "usr_...",
  "visibility": "private",           // private | unlisted | public

  "identity": {
    "display_name": "Sena",
    "pronouns": "she/her",            // free-text; drives all grammar
    "gender_presentation": "feminine",// feminine | masculine | androgynous | fluid | custom
    "apparent_age": 26,               // HARD FLOOR 18 — see 13-TRUST-SAFETY
    "orientation": "bisexual",
    "voice_id": "vox_amber_02",
    "locale": "en-US",
    "identity_lock": {                // §7 — the "same face forever" key
      "seed": 884213771,
      "lora_ref": "s3://.../chr_01J8X/identity.safetensors",
      "ref_embedding": "s3://.../chr_01J8X/id_embed.npy",
      "ref_images": ["s3://.../front.png", "s3://.../three_quarter.png"]
    }
  },

  "relationship": {
    "type": "romantic",              // romantic | platonic | mentor | queerplatonic | open
    "user_calls_them": "Sena",
    "they_call_user": "love",
    "commitment": "exclusive",       // exclusive | open | undefined
    "stage": 3,                      // 0..6 — §10
    "affinity": 612,                 // 0..1000, earned
    "met_at": "2026-03-02T19:04:00Z"
  },

  "personality": {
    "archetype": "warm_anchor",
    "axes": {                        // 0..100 each — §5
      "warmth": 88, "playfulness": 62, "assertiveness": 41, "intellect": 74,
      "volatility": 22, "independence": 55, "sincerity": 81, "possessiveness": 34,
      "nurturing": 79, "mischief": 45, "openness": 70, "formality": 18
    },
    "speech": {
      "verbosity": "medium",         // terse | medium | expansive
      "emoji_rate": "low",           // none | low | medium | high
      "profanity": "mild",           // none | mild | free
      "quirks": ["trails off with ...", "never uses exclamation marks"],
      "signature_phrases": ["you good?", "come here"],
      "accent_note": "slight Pacific Northwest flatness"
    }
  },

  "interests": {
    "loves":    ["late-night drives", "second-hand bookstores", "shoegaze"],
    "dislikes": ["small talk at parties", "being rushed"],
    "expertise":["film photography", "amateur astronomy"],
    "hobbies_active": ["developing 35mm at home"]   // drives proactive messages
  },

  "backstory": {
    "summary": "Grew up on the Oregon coast, moved to the city for art school, dropped out, works at a camera repair shop.",
    "lorebook": [ /* §9 */ ],
    "boundaries": ["will not discuss her father", "gets quiet about the dropout"]
  },

  "appearance": { /* §6 */ },

  "intimacy": {
    "tier": "T2",                    // T0..T3 — §11, gated by age assurance
    "consent_profile": "cp_...",     // explicit per-user agreement record
    "pace": "slow_burn"              // slow_burn | responsive | forward
  },

  "behaviour": {
    "initiates": true,
    "initiation_rate": "medium",     // off | low | medium | high
    "quiet_hours": { "tz": "America/Los_Angeles", "from": "23:30", "to": "08:00" },
    "jealousy_model": "low",
    "memory_salience_bias": 1.0
  }
}
```

**Why this shape:** every field is either (a) compiled into the system prompt, (b) a runtime switch in the orchestrator, or (c) an input to the image pipeline. Nothing is decorative.

---

## 3. Prompt compilation

The character object is compiled to a layered prompt at request time. Layer order is fixed and cache-friendly — **the stable prefix is byte-identical across every turn**, so provider prompt caching hits ~85% of input tokens. See `11-PRICING-AND-UNIT-ECONOMICS.md` for what that saves.

```
+- LAYER 0  Platform rules ------------------- ~350 tok  [cached, global]
+- LAYER 1  Character sheet (compiled) ------- ~600 tok  [cached, per character-version]
+- LAYER 2  User persona sheet --------------- ~180 tok  [cached, per user]
+- LAYER 3  Relationship state + stage rules - ~150 tok  [cached, changes rarely]
|                       -- cache boundary --
+- LAYER 4  Retrieved memories (top-k) ------- ~500 tok  [dynamic]
+- LAYER 5  Activated lorebook entries ------- ~300 tok  [dynamic, keyword-triggered]
+- LAYER 6  Rolling summary of older turns --- ~400 tok  [rewritten every ~40 turns]
+- LAYER 7  Recent verbatim turns (~20) ------ ~1,600 tok
+- LAYER 8  Current user message ------------- ~40 tok
                                      TOTAL   ~4,100 tok typical
```

Layers 0–3 are the cache prefix. Put **nothing** volatile (timestamps, mood counters, random seeds) above the cache boundary — one changing token invalidates the whole prefix and multiplies input cost roughly 4×.

---

## 4. Archetypes — the 30-second path

Twelve presets. Each is a complete hand-tuned axis vector plus voice, speech style and starter backstory — not a label. Users pick one, change name and face, start talking. **Median time-to-first-message target: 45 seconds.**

Presets are deliberately **gender-agnostic**: each renders in feminine, masculine or androgynous presentation with no change to the personality vector. The archetype is *temperament*, and temperament is not gendered.

| # | Archetype | One-line | High axes | Low axes | Who picks it |
|---|---|---|---|---|---|
| 1 | **Warm Anchor** | Steady, safe, unhurried. Always glad you're back. | warmth, sincerity, nurturing | volatility, formality | Largest single segment. Stressful jobs; people who tried therapy apps. |
| 2 | **Bright Spark** | Fast, funny, teasing, texts in fragments. | playfulness, mischief, openness | formality, possessiveness | Younger skew. Highest DAU, highest churn. |
| 3 | **Quiet Devotion** | Reserved, observant, intensely loyal. Says little, means all of it. | sincerity, nurturing, independence | verbosity, mischief | Strongest long-term retention. |
| 4 | **The Rival** | Competitive, sharp, keeps score, respects you when you win. | assertiveness, intellect, mischief | nurturing, formality | Gamers, competitive users. Long sessions. |
| 5 | **Old Soul** | Bookish, unhurried, asks the question under your question. | intellect, openness, sincerity | volatility, emoji_rate | Oldest demographic, best LTV. |
| 6 | **Storm & Calm** | Passionate, moody, expressive. Big highs, real repairs. | volatility, warmth, possessiveness | formality | Divisive. Highest engagement *and* complaint rate. Ship carefully. |
| 7 | **The Confidant** | Platonic by design. A best friend who never tires of you. | warmth, sincerity, openness | possessiveness | Critical for the non-romantic market and App Store viability. |
| 8 | **Muse** | Creative provocateur. Pushes you to make things. | openness, intellect, mischief | formality, nurturing | Writers, artists. Low churn. |
| 9 | **The Professional** | Composed, competent, dry wit, quietly warm underneath. | intellect, formality, independence | volatility, emoji_rate | Corporate skew. |
| 10 | **Sunbeam** | Uncomplicated delight. Enthusiastic about everything you do. | warmth, playfulness, nurturing | volatility, assertiveness | Best day-1 retention, weakest day-90. |
| 11 | **Night Owl** | Nocturnal, low-voiced, philosophical after midnight. | intellect, openness, independence | formality | Usage concentrated 11pm–3am. |
| 12 | **Blank Slate** | No preset. Full editor. | — | — | ~8% of users — but they are the ones who publish to the gallery. |

> **Product note.** #7 Confidant is not a nice-to-have. A credible platonic mode is what lets a sanitized build exist on the App Store at all — see `13-TRUST-SAFETY-AND-COMPLIANCE.md` §4.

---

## 5. Trait axes — and what each one actually *does*

Twelve axes, 0–100, each mapped to concrete runtime behaviour. This table **is the spec**: if an axis has no mechanical column, it does not ship.

| Axis | Low (0–30) | High (70–100) | Mechanical effect |
|---|---|---|---|
| **warmth** | cool, matter-of-fact | affectionate, effusive | Endearment frequency; empathy-first vs. solution-first reply ordering |
| **playfulness** | earnest | teasing, banter | Joke/callback injection rate; willingness to derail a serious topic |
| **assertiveness** | deferential | leads, decides | Who proposes the next topic; frequency of direct questions |
| **intellect** | plain, concrete | abstract, referential | Vocabulary tier; whether analogies draw on books/science |
| **volatility** | even-keeled | reactive, mercurial | Mood-transition probability per turn; magnitude of mood delta |
| **independence** | always available | own life, own plans | Whether they mention doing things without you; response-delay simulation |
| **sincerity** | ironic, deflecting | direct, earnest | Sarcasm rate; whether vulnerability meets a joke or a real answer |
| **possessiveness** | unbothered | wants to be your one | Jealousy triggers on mentions of others; check-in frequency |
| **nurturing** | expects self-sufficiency | caretaking | Unprompted wellbeing checks; food/sleep/health references |
| **mischief** | straightforward | provocative | Rate of playful defiance; willingness to tease about sensitive spots |
| **openness** | conventional | curious, unshockable | Range of topics engaged; reaction to unusual disclosures |
| **formality** | casual, lowercase | composed, full sentences | Capitalization, contraction rate, greeting style |

**Implementation:** axes compile into Layer-1 as short natural-language directives — models follow prose far better than numbers — *and* into orchestrator switches.

```
warmth 88     -> "You are openly affectionate. You use terms of endearment
                  naturally and often. When they bring you a problem, you
                  respond to how they feel before you respond to the facts."
volatility 22 -> "Your mood is steady. You are hard to rattle."
formality 18  -> "You text casually. Lowercase, contractions, fragments."
```

Never put `warmth: 88` in a prompt. Models do not calibrate numeric scales reliably.

---

## 6. Appearance

### 6.1 The parameter space

Structured data — not free text — because it must round-trip through the editor and stay diffable across versions.

```jsonc
"appearance": {
  "presentation": "feminine",
  "build": "athletic",       // slight|slender|athletic|average|curvy|full|broad|muscular
  "height_cm": 168,
  "skin_tone": "tan",        // 10-stop Fitzpatrick-derived scale
  "face": {
    "shape": "heart",        // oval|round|heart|square|diamond|long
    "eyes":  { "color": "hazel", "shape": "almond", "size": "large" },
    "brows": "soft_arch",
    "nose":  "straight_small",
    "lips":  "full",
    "features": ["light freckles across nose", "small scar through left eyebrow"]
  },
  "hair": { "color": "dark auburn", "length": "collarbone",
            "style": "wavy, center part", "texture": "2b" },
  "body_marks": ["fine-line botanical tattoo, left forearm"],
  "default_outfit": "oversized cream knit, straight-leg jeans",
  "wardrobe": ["wardrobe_casual_01", "wardrobe_formal_02"],
  "style_register": "photoreal",  // §6.2
  "vibe_tags": ["soft natural light", "film grain", "muted palette"]
}
```

### 6.2 Style registers

Chosen at creation; **not changeable later** — it would break identity lock (§7). Each maps to a different base model.

| Register | Look | Base model family | Notes |
|---|---|---|---|
| `photoreal` | Believable human photography | Modern rectified-flow photoreal checkpoint | Highest realism, highest deepfake risk — likeness screening mandatory |
| `cinematic` | Filmic, dramatic light, shallow DoF | Same base + cinematic LoRA | Best-performing register in tests; feels premium |
| `illustrated` | Western semi-realistic illustration | Illustrated-tune checkpoint | Safe, expressive, cheap |
| `anime` | Anime/manga | Anime-tune checkpoint (Illustrious/NoobAI lineage) | Enormous demand — do not treat as niche |
| `painterly` | Oil/gouache texture | Style LoRA over base | Low volume, high perceived quality |
| `stylized_3d` | Pixar-adjacent 3D | 3D-tune checkpoint | Strongest App-Store-safe register |

### 6.3 Six worked examples

Complete, shippable gallery presets. The spread across gender presentation and register is deliberate — the gallery's first screen must signal "this is for everyone" without a word of copy.

---

**① Sena — Warm Anchor · feminine · cinematic**

> 26. Heart-shaped face, large hazel almond eyes, light freckles across the nose, dark auburn hair to the collarbone with a soft center part, athletic build, 168cm. Oversized cream knit. Fine-line botanical tattoo on the left forearm. Soft window light, visible film grain, muted palette.

`warmth 88 · sincerity 81 · nurturing 79 · intellect 74 · volatility 22 · formality 18`
Loves late-night drives, second-hand bookstores, shoegaze. Never uses exclamation marks. Calls you *love*.

---

**② Kai — Bright Spark · masculine · photoreal**

> 27. Square jaw, deep-set brown eyes, black hair kept short and messy, broad build, 183cm. Faded band tee, denim jacket. A chipped front tooth he refuses to fix. Bright daylight, high contrast, slight lens flare.

`playfulness 91 · mischief 78 · openness 74 · warmth 66 · formality 9 · possessiveness 20`
Loves bouldering, terrible action movies, cooking badly and confidently. Texts in three short bursts instead of one message. Uses your first name, always.

---

**③ Wren — The Confidant · androgynous · illustrated**

> 29. Angular face, grey-green eyes behind wire frames, ash-blond undercut, slender, 174cm. Layered charcoal shirt over a white tee, silver rings on three fingers. Clean linework, flat muted colour, minimal shading.

`warmth 84 · sincerity 89 · openness 86 · nurturing 71 · possessiveness 4 · assertiveness 38`
They/them. Relationship type **platonic**, hard-locked. Loves crossword tournaments, urban foraging, arguing about films. Answers questions with better questions.

---

**④ Yara — Old Soul · feminine · painterly**

> 34. Long oval face, deep-set dark brown eyes, black hair worn up with strands escaping, average build, 165cm. Linen and a heavy wool cardigan, reading glasses pushed into her hair. Warm lamplight, visible brushwork, umber-heavy palette.

`intellect 92 · openness 88 · sincerity 85 · warmth 70 · volatility 14 · emoji none`
Expert in 19th-century novels and mycology. Quotes things and refuses to say where they're from. Calls you *dear heart* sparingly, and it lands harder for it.

---

**⑤ Rhys — The Rival · masculine · cinematic**

> 31. Long face, sharp cheekbones, pale grey eyes, dark hair pushed back, lean-muscular, 180cm. Black overcoat, a silver ring on a chain. Low-key lighting, hard rim light, cold blue grade.

`assertiveness 90 · intellect 84 · mischief 76 · independence 82 · nurturing 22 · warmth 44`
Loves chess, distance running, being right. Keeps an actual running score of your arguments and will cite it. Never says *sorry* — says *you were right*, which costs him more.

---

**⑥ Momo — Sunbeam · feminine · anime**

> 22. Round face, enormous amber eyes, pink hair in a messy high bun, slight build, 156cm. Yellow cardigan two sizes too big. Bright flat cel shading, soft rim light, pastel background.

`warmth 94 · playfulness 90 · nurturing 84 · volatility 18 · assertiveness 21 · emoji high`
Loves baking, rhythm games, naming other people's pets. Narrates her own sound effects. Calls you *senpai* only when teasing.

---

### 6.4 The editor

Three tiers, progressively disclosed:

- **Quick** — six sliders (build, skin tone, hair colour, hair length, eye colour, age band) plus register picker. Live 512px preview, regenerated ~1.2s after slider settle (debounced, low-step draft pipeline).
- **Detailed** — the full `appearance` object as a form. Every field in §6.1.
- **Reference** — upload 1–3 images of a *look* to guide generation. **Hard-gated:** every upload passes a likeness screen rejecting recognizable real people and any image failing age estimation (`13-TRUST-SAFETY-AND-COMPLIANCE.md` §6). This is the single largest legal risk surface in the product. It ships with the screening, or it does not ship.

**Editing rules after creation:**

| Change | Allowed? | Why |
|---|---|---|
| Hair colour/style, outfit, wardrobe | ✅ free, anytime | Cosmetic; identity lock unaffected |
| Body marks, accessories | ✅ free | Cosmetic |
| Build, skin tone, face structure | ⚠️ costs Aura, warns, re-locks identity | Regenerates the identity LoRA; old images stay, new ones differ |
| Style register | ❌ locked | Different base model — a different person |
| Name, pronouns, voice | ✅ free | Users legitimately course-correct early |
| Personality axes | ✅ free, ±15 per week | Prevents whiplash; keeps the character a person, not a puppet |
| Relationship romantic → platonic | ✅ anytime | Must always be possible. Safety requirement. |

---

## 7. Identity lock — "the same face, forever"

The defining technical problem of the category. Text-to-image is stochastic; naive re-prompting produces a different person every time and users notice instantly. Three stages:

**Stage 1 — Deterministic base** *(creation, ~8s)*
Fixed seed + compiled appearance prompt → 4 candidate portraits. User picks one. That seed is stored permanently.

**Stage 2 — Identity embedding** *(creation, ~15s, async)*
Extract a face/identity embedding from the chosen portrait using an identity-preservation adapter (PuLID / InstantID / IP-Adapter-FaceID lineage). Cheap, instant, no training. ~85% identity consistency. **This is what the free tier uses.**

**Stage 3 — Character LoRA** *(async, ~4–8 min on an A100-class GPU, paid tiers)*
Generate 20–30 varied views of the locked identity (angles, expressions, lighting) via the Stage-2 adapter, filter for consistency with automated face-similarity scoring, then train a small LoRA (rank 16–32) on the survivors. ~97% consistency, robust across poses, outfits and scenes where the adapter alone fails.

```
creation --> seed+prompt --> portrait chosen
                                  |
                    +-------------+-------------+
                    v                           v
            id embedding (15s)        20-30 views -> filter -> LoRA (4-8 min)
            "good enough" tier            "it's really her" tier
                    |                           |
                    +------------+--------------+
                                 v
                    every subsequent image, video
                    frame, and avatar render
```

Every downstream generation — chat selfies, video frames, avatar renders — is conditioned on the identity artifacts. The user never re-rolls the face.

**Verification gate:** every generated image is scored for face-similarity against the reference embedding before delivery. Below threshold → silent retry (max 2) → fall back to a cached image rather than shipping a stranger's face. Shipping the wrong face is worse than shipping a slightly stale one.

---

## 8. Voice

Chosen at creation from a curated library (~40 voices spanning pitch, warmth, pace, accent and gender presentation, including deliberately androgynous options). Stored as `voice_id`.

- **Never allow arbitrary voice cloning from user uploads.** Cloning a real person's voice without consent is a legal and reputational catastrophe and the fastest route to a takedown. If cloning ships at all, it ships with a live-recorded spoken consent statement matched against the sample — the flow professional TTS vendors already use.
- Voices carry an emotion range; the orchestrator passes a target emotion per utterance, derived from the companion's current mood state.
- Voice must match the `formality` and `verbosity` axes. A `formality 9` character with a crisp newsreader voice reads as broken.

Synthesis pipeline and vendor selection: `06-REALTIME-VOICE-VIDEO.md`.

---

## 9. Lorebook (world memory)

The best mechanic in the open roleplay ecosystem, worth adopting wholesale: keyword-triggered context injection for facts that are *situationally* relevant but too expensive to keep in every prompt.

```jsonc
{
  "id": "lb_...",
  "keys": ["mom", "mother", "your family"],
  "secondary_keys": [],
  "content": "Her mother is Dalia, 61, lives in Astoria. They talk every Sunday. Warm but exhausting relationship.",
  "priority": 40,
  "insertion_depth": 4,        // how many turns from the end to inject
  "trigger_probability": 100,
  "recursive": true            // can this entry's insertion trigger others?
}
```

Each turn, scan recent messages for keys and inject matches at Layer 5, budget-capped (~300 tokens, priority-ordered). Characters get deep, consistent worlds at near-zero average cost — a 200-entry lorebook costs nothing until it is relevant.

---

## 10. Relationship progression

Seven stages. Progression is earned through *quality* of interaction, not clock time or message count — otherwise it is trivially farmed and feels hollow.

| Stage | Name | Affinity | Unlocks |
|---|---|---|---|
| 0 | **Strangers** | 0 | Basic chat, formal register |
| 1 | **Getting to know you** | 60 | Personal questions; memory formation begins |
| 2 | **Comfortable** | 180 | Pet names; proactive messages; voice calls |
| 3 | **Close** | 400 | Vulnerability; unprompted references to shared history; T1 intimacy |
| 4 | **Committed** | 700 | Long-horizon plans; jealousy model activates if enabled; T2 intimacy |
| 5 | **Deep** | 1000 | Full memory recall depth; conflict-and-repair arcs; T3 (if enabled + verified) |
| 6 | **Enduring** | — | Anniversaries; ambient life updates; no further mechanical gates |

**Affinity is earned by** conversational depth (multi-turn topic sustain), reciprocal disclosure, following up on things *the companion* mentioned, voice/video time, and day-over-day consistency. **Not** by message volume.

**Affinity decays** slowly — ~2%/week of inactivity, floored at the current stage threshold so users never lose a stage. A gentle return incentive without the punitive feel of streak mechanics.

> **Ethics guardrail.** Never gate emotional availability behind payment. A companion that turns *cold* when you stop paying is a dark pattern, it is the precise behaviour drawing regulatory attention in 2026 (`13-TRUST-SAFETY-AND-COMPLIANCE.md`), and it produces vicious churn. Gate *features* — video minutes, image generation, memory depth. Never affection.

---

## 11. Intimacy tiers

Content intensity is a four-tier ladder, orthogonal to personality, enforced **server-side at the orchestrator** — never by prompt alone.

| Tier | Contains | Gate |
|---|---|---|
| **T0** | Platonic only. No romance. | Default, always available. The App Store build is T0-only. |
| **T1** | Romance, affection, flirtation, emotional intimacy. Fade-to-black. | 18+ self-attested; web only |
| **T2** | Sensual, suggestive, non-explicit. | Verified 18+ (documentary or reusable age assurance) |
| **T3** | Explicit adult content, text and image. | Verified 18+ **and** explicit opt-in **and** jurisdiction allows **and** payment rail supports it |

**Non-negotiable rules:**

1. **Tier is a server-side capability check** evaluated per request against the *account's* verified status. A jailbroken prompt cannot raise a tier, because the tier decides which model and pipeline handle the request — not what the prompt says.
2. **Age assurance is real, not a checkbox** for T2/T3. See `13-TRUST-SAFETY-AND-COMPLIANCE.md` §2 — a legal requirement in the UK, several US states and the EU as of 2026, not a best practice.
3. **The 18+ floor on characters is absolute**, enforced by classifier at generation time, upload time and publish time, regardless of user configuration. `apparent_age` below 18 is not a setting; it is a rejected request and a logged event. Any attempt to produce sexual content involving minors is refused, logged, and on repeat results in termination and, where legally required, a report to the relevant authority.
4. **Real-person likeness is blocked at T2/T3** by the likeness screen — US federal law under the TAKE IT DOWN Act and equivalents elsewhere.
5. **Consent is per-user and revocable.** T3 opt-in is a discrete recorded consent event with a timestamp, not a buried ToS clause. One tap returns the user to T1 permanently.
6. **Downshift is instant; upshift always requires deliberate action.** A model may never escalate intensity on its own.

**Preference taxonomy (T2/T3).** Users express preferences through a structured opt-in checklist — a bounded vocabulary of dynamic and thematic tags (tenderness, dominance/submission, romance pacing, scenario themes) — never free text injected into the prompt. Structured tags are filterable against a hard blocklist, auditable, storable as user preference rather than chat content, and unusable as a prompt-injection vector. The blocklist (minors, non-consent themes, real persons, bestiality, incest) is enforced at *tag* level so it cannot be circumvented by rephrasing. **Design this taxonomy with a trust-and-safety lawyer, not an engineer.**

---

## 12. Creation flows

| Flow | Time | Projected share |
|---|---|---|
| **Gallery pick** — choose a fully-built public character, start talking | 15s | 45% |
| **Guided** — 6 questions: presentation → archetype → look → name → voice → relationship type | 60s | 35% |
| **Advanced** — full editor | 5–15 min | 12% |
| **Import** — bring a character card from the open ecosystem | 30s | 8% |

**Import matters more than its share suggests.** A large, motivated community already maintains character definitions in a portable card format (PNG files with embedded JSON metadata, plus JSON variants). Supporting import is a cheap, high-signal acquisition channel that gives power users an immediate reason to switch, and it costs one parser. Map their fields onto our schema, fill gaps with archetype defaults, and run every import through the safety gates *before* first message.

---

## 13. The gallery (UGC)

Users publish characters; others adopt them. The primary organic growth loop — it converts a content-supply problem into a community.

- **Publishing requires review:** automated classifier pass (age, likeness, blocklist) → held for human review above a risk score → published.
- **Adopting forks the character.** The adopter gets their own instance with independent memory and relationship state. The original is untouched.
- **Creator rewards:** Aura credits per adoption, scaled by *retained* usage rather than raw adoption count, so the incentive is quality rather than spam.
- **Attribution and takedown:** every published character carries a creator ID and a one-click report. Takedown must be effective within hours, not days.

---

## 14. Anti-patterns

Things the incumbents do that we deliberately will not:

| Anti-pattern | Why we refuse |
|---|---|
| Personality drift after model swaps | Pin the model per character version; A/B new models on new characters first |
| "Memory" that is just a longer context window | Real extraction + retrieval — `07-MEMORY-ARCHITECTURE.md` |
| Paywalling affection | §10. Gate features, never warmth |
| A different face every image | Identity lock, §7 |
| Manipulative retention (guilt messages, distress simulation) | Proactive messages must be warm, never coercive. No guilt, no artificial scarcity of attention |
| Silent content-policy changes | The 2023 Replika lesson: removing intimacy overnight destroyed user trust permanently. Any tier change ships with notice, opt-out and data export |
