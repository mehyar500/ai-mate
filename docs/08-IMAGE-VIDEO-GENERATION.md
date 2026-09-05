# Image & Video Generation

**The requirement:** the character looks like herself. In image one and image ten thousand, in a selfie and in a video call, three years apart.

Nobody in this category reliably achieves that, and it is the most immediately visible quality difference a user can perceive.

---

## 1. The problem

Diffusion models are stochastic. The same prompt with a different seed produces a different person. Most companion apps handle this by generating from a fixed seed and hoping, which works until the pose, lighting, or outfit changes — at which point the face drifts and the user is looking at a stranger wearing their companion's clothes.

```
   naive approach                    what the user sees
   ───────────────                   ──────────────────
   prompt + seed 4471   ──▶   image 1: a woman
   prompt + seed 4471   ──▶   image 2: a similar woman
   prompt + seed 4471   ──▶   image 3: someone else entirely
   (different pose)
```

A companion whose face changes between images is not a person. It is a slideshow. And once a user notices it, they cannot un-notice it.

---

## 2. Identity lock — the three-stage solution

Introduced in [04 §7](04-CHARACTER-SYSTEM.md); here is the implementation.

```
  ┌──────────────────────────────────────────────────────────┐
  │  STAGE 1 — GENESIS         (once, at character creation) │
  │                                                          │
  │  appearance params + style register + fixed seed         │
  │            │                                             │
  │            ▼                                             │
  │  generate 8-12 candidate portraits                       │
  │            │                                             │
  │            ▼                                             │
  │  user picks one  ──▶  THE CANONICAL FACE                 │
  │            │                                             │
  │            ▼                                             │
  │  generate reference set from the canonical face:         │
  │  front · three-quarter · profile · smiling · neutral     │
  └──────────────────────────┬───────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────┐
  │  STAGE 2 — ENCODING                     (minutes)        │
  │                                                          │
  │  reference set ──▶ identity embedding                    │
  │                    (PuLID / InstantID / IP-Adapter-FaceID)│
  │                    stored as id_embed.npy                │
  │                                                          │
  │  [Infinite tier] ──▶ train per-character LoRA            │
  │                      rank 16-32, ~15 min on an A40       │
  │                      stored as identity.safetensors      │
  └──────────────────────────┬───────────────────────────────┘
                             ▼
  ┌──────────────────────────────────────────────────────────┐
  │  STAGE 3 — GENERATION            (every image, forever)  │
  │                                                          │
  │  scene prompt                                            │
  │    + fixed seed                                          │
  │    + identity embedding  (weight ~0.8)                   │
  │    + LoRA if present     (weight ~0.7)                   │
  │            │                                             │
  │            ▼                                             │
  │       generate                                           │
  │            │                                             │
  │            ▼                                             │
  │  ┌─────────────────────────────────────┐                 │
  │  │  FACE SIMILARITY GATE               │                 │
  │  │  cosine(result, canonical) >= 0.72  │                 │
  │  └────────┬───────────────────┬────────┘                 │
  │           │ pass              │ fail                     │
  │           ▼                   ▼                          │
  │       deliver          retry (max 3), then fail          │
  │                        gracefully — never deliver        │
  │                        a wrong face                      │
  └──────────────────────────────────────────────────────────┘
```

**The gate is the part that matters.** Everything above it is standard technique that several competitors use. Verifying the output and *refusing to deliver a failure* is what nobody does, and it is the difference between "usually looks like her" and "is her."

⚠️ Threshold 0.72 cosine on an ArcFace-style embedding is a starting point; tune against a hand-labelled set. Too high and legitimate variation (a different angle, strong side lighting) gets rejected; too low and drift leaks through. Expect a ~5–12% retry rate at 0.72.

**Cost of the gate:** one extra face-embedding pass, ~30ms, plus the retry rate. At a 10% retry rate the effective image cost rises 10%. On a $0.01 image that is a tenth of a cent to never ship a wrong face.

---

## 3. Model selection

All open-weight, so all of them run on any permissive host or on your own GPUs.

| Style register | Model family | Notes |
|---|---|---|
| `photoreal` | Modern rectified-flow photoreal checkpoint | Best skin and lighting; the default |
| `cinematic` | Same, with LUT-style prompt conditioning | Shallow depth of field, film grain |
| `illustrated` | Illustration-tuned checkpoint | Semi-realistic, painterly edges |
| `anime` | Illustrious / NoobAI lineage | Category standard; enormous LoRA ecosystem |
| `painterly` | Artistic checkpoint | Brushwork, non-photographic |
| `stylized_3d` | 3D-render tuned checkpoint | Pixar-adjacent |

**The style register is fixed at character creation and cannot be changed**, because it is part of the identity. An anime character rendered photoreal is a different person, and the identity embedding does not transfer across registers anyway.

**Providers** ([12 §6](12-VENDOR-API-MATRIX.md)): **Runware** primary at $0.0006–0.24/image ✅, with LoRA loading support — which the architecture requires. **Novita** as failover. Never single-source; a policy change at one vendor should not take the feature down.

---

## 4. In-scenario selfies

The single best interaction model for companion imagery, and Nomi is right to lead with it.

**Wrong:** a form with dropdowns for pose, outfit, and background.
**Right:** the character sends a photo because the conversation called for one.

```
user:   "how was the beach?"
char:   "so good, the water was actually warm for once"
        [ image: her at the beach, wet hair, holding a coffee ]
        "borrowed someone's jumper after, it got cold fast"
```

**The pipeline:**

```
conversation context (last ~10 turns)
        │
        ▼
  cheap model (mistral-nemo) constructs a scene description
        │  — location, time of day, outfit, pose, expression
        │  — consistent with what was just said
        ▼
  merge with the character's fixed appearance params
        │
        ▼
  generate → identity gate → deliver in-conversation
```

⚠️ Prompt construction costs ~$0.00005. The image dominates.

**Triggering:** either the user asks, or the character offers when context strongly suggests it — after describing a place, an outfit, a moment. Rate-limit character-initiated images hard. An unprompted photo is delightful once a day and cloying five times an hour.

---

## 5. What the user can control

| Fixed forever | Adjustable per image |
|---|---|
| Face structure | Expression |
| Style register | Pose |
| Base body type | Outfit |
| Identity seed | Location / background |
| Signature features | Lighting, time of day |
| | Framing (portrait, full body, selfie) |
| | Hair styling (not colour on locked characters) |

**Why the split:** identity is the things that would make you say "that's not her." Everything else is what a person changes about themselves day to day. Hair *colour* sits on the fixed side because it is a strong identity cue in generated imagery, though a deliberate, versioned "she dyed her hair" event is supported — it creates a new character version with a re-derived identity embedding, exactly as [03](03-PRD.md) C-07 requires.

---

## 6. NSFW image generation

Governed by the same tier system as text ([05 §3](05-AI-ARCHITECTURE.md)). The image pipeline is not a separate policy surface.

| Tier | Imagery |
|---|---|
| T0 | Portraits, everyday scenes |
| T1 | Suggestive, swimwear, lingerie, intimate framing — no nudity |
| T2 | Nudity and explicit content, verified adults, opt-in per character |
| T3 | T2 plus opted-in preference tags from the bounded taxonomy |

**Rules:**

1. **Tier resolves server-side and selects the pipeline.** A T1 request does not reach a model configured for T2 output. Same principle as text: routing, not prompting.
2. **The hard blocklist runs pre-generation on every tier**, including T0. No minors or minor-coded characters, no non-consent framing, no real identifiable people, no bestiality, no incest. No user consent unlocks these.
3. **A dedicated visual classifier runs post-generation** as well — image models can produce things the prompt did not ask for. Fail closed.
4. **Age-appearance verification on every generated character.** A character whose generated appearance reads as under 18 to the classifier cannot be created, regardless of the stated age field. This check runs at Stage 1 of identity lock, so a non-compliant character never exists in the first place.
5. **No uploads of real people's faces, ever**, for identity lock or anything else. This closes both the deepfake vector and the TAKE IT DOWN Act exposure in one rule, and it is worth the feature it costs.
6. **Generated media is private by default**, encrypted at rest, deletable for real.

> Rule 5 deserves emphasis because users will ask for it and it looks like a reasonable feature. "Make my companion look like this person" is the single highest-liability request this product can receive. The answer is no, in all cases, including for the user's own face.

---

## 7. Non-realtime video

Distinct from the realtime avatar in [06](06-REALTIME-VOICE-VIDEO.md). Short generated clips — a few seconds, sent in conversation like a video message.

⚠️ Current open-weight image-to-video models produce 3–5 second clips at meaningful cost (roughly $0.05–0.40/clip depending on model and length). Identity consistency across frames is decent from a strong first frame but degrades with motion.

**Recommendation: P2, not launch.** The realtime avatar delivers a better experience for the same money, and generated clips at current quality sit in an uncanny middle ground. Revisit when quality improves or cost drops by an order of magnitude.

---

## 8. Realtime avatar identity

The video face must match the image face. If it does not, the illusion is worse than having no video at all — the user now has two different people.

**Approach:** the identity-lock reference set (Stage 1) is the input to the avatar provider's replica creation. Anam and Tavus both build a replica from reference imagery; feeding them the same canonical face used for image generation keeps both surfaces aligned.

**Verification:** run the same face-similarity gate against sample frames from the avatar before enabling video for a character.

```
avatar sample frames ──▶ cosine vs canonical ──┬── >= 0.70 ──▶ video enabled
                                               └──  < 0.70 ──▶ video DISABLED
                                                               for this character
```

**Disabling video for a character whose replica does not match is the correct outcome**, and it must be a supported product state rather than an error. Per [03](03-PRD.md) VD-02: a mismatched video face damages the product more than a missing feature does.

⚠️ Replica creation cost: included on Anam; $40–65 one-time on Tavus. On Tavus this materially changes the economics of letting every user create custom characters, which is a second reason to launch on Anam.

---

## 9. Costs

⚠️ Estimates except where marked.

| Operation | Cost |
|---|---|
| Single image, standard | ~$0.008 |
| Single image, high quality | ~$0.02–0.05 |
| Identity gate (embed + expected retries) | ~$0.001 |
| Scene prompt construction | ~$0.00005 |
| **Effective per delivered image** | **~$0.01** |
| Character genesis (12 candidates + references) | ~$0.15 |
| LoRA training (A40 @ $0.44/hr ✅, ~15 min) | ~$0.11 |
| Video clip, 4s (P2) | ~$0.05–0.40 |

At **2 Aura per image** (≈ $0.02 of plan value against ~$0.01 cost), images carry a healthy margin and act as the natural Aura sink that keeps the credit economy meaningful. See [11](11-PRICING-AND-UNIT-ECONOMICS.md).

**LoRA training at $0.11 is cheap enough to offer more widely than the Infinite tier**, and probably should be once the pipeline is proven. It is gated at launch for operational reasons — training queues, failure handling, storage — not cost.

---

## 10. Storage

| Asset | Where | Retention |
|---|---|---|
| Canonical face + reference set | Object storage, encrypted | Life of character |
| Identity embedding (`.npy`) | Object storage | Life of character |
| Per-character LoRA (`.safetensors`) | Object storage | Life of character |
| Generated images | Object storage, encrypted, per-user prefix | Until deleted |
| Avatar replica | Provider-side | Life of character |

⚠️ Storage is negligible — a few MB per character for identity assets, plus generated media. Budget ~$0.02/user/month at typical volumes. Serve through signed, short-lived URLs; generated media must never sit behind a guessable path.

**On deletion:** deleting a character deletes the identity assets, the LoRA, the generated media, and requests replica deletion from the provider. Verify the provider actually supports deletion before signing with them — several media APIs retain training inputs by default, which is incompatible with a real deletion promise.

---

*Next: [09 — System Design](09-SYSTEM-DESIGN.md) · [10 — Design System](10-DESIGN-SYSTEM.md)*
