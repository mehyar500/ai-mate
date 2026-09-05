# Design System

How Amorien looks, sounds, and behaves — and the reasoning behind it.

---

## 1. The design problem

Almost every product in this category looks like one of two things:

**Neon and vaporwave.** Purple gradients, glowing edges, dark backgrounds, a sense of a nightclub. It signals *fantasy* and *transaction*. It tells the user this is a place to consume something.

**Clinical wellness.** Soft blues, rounded everything, illustration-heavy. It signals *therapy adjacent* and *slightly infantilizing*.

Neither is right, because neither describes what the product is. Amorien is a relationship, and relationships do not look like nightclubs or clinics. They look like ordinary life with someone in it.

> **The design target: a messaging app that happens to be beautiful.** Calm, warm, unhurried. The interface should be the least interesting thing on screen, because the character is the product and every pixel of chrome competes with them.

---

## 2. Principles

1. **The character is the interface.** UI recedes. If a design decision makes the app more noticeable and the character less present, it is wrong.
2. **Warm, not hot.** Intimacy is signalled by warmth and calm, never by heat, glow, or urgency.
3. **No dark patterns, visually enforced.** No red badges, no artificial scarcity, no countdowns, no manufactured urgency. The visual language has no vocabulary for pressure.
4. **Neutral by default.** No pink-for-her, no blue-for-him. Nothing in the visual system assumes the user's gender or the character's.
5. **Quiet by default, expressive on demand.** Motion is subtle. The exception is the character's own presence — breathing, blinking, expression — which should feel alive.
6. **Accessible without a separate mode.** Contrast, target sizes, and motion preferences are the default, not an accessibility setting.

---

## 3. Colour

The palette is built around a warm neutral base with a single accent that is neither pink nor blue.

```
  BASE  (warm neutrals — the room the conversation happens in)
  ┌──────────────────────────────────────────────────────────┐
  │ ink-950   #14110F   near-black, warm                     │
  │ ink-800   #2A2420                                        │
  │ ink-600   #4A413B                                        │
  │ ink-400   #8A7F76                                        │
  │ ink-200   #D6CCC2                                        │
  │ ink-100   #EDE6DE                                        │
  │ ink-50    #F8F4EF   warm paper                           │
  └──────────────────────────────────────────────────────────┘

  ACCENT  (amber-rose — warmth without gendering)
  ┌──────────────────────────────────────────────────────────┐
  │ ember-600 #B4533C   deep, for text on light              │
  │ ember-500 #D4674B   the primary accent                   │
  │ ember-400 #E88A6F   hover, light-on-dark                 │
  │ ember-100 #FAE3DA   tints, backgrounds                   │
  └──────────────────────────────────────────────────────────┘

  SUPPORT
  ┌──────────────────────────────────────────────────────────┐
  │ sage-500  #6B8F7A   success, connected, positive state   │
  │ dusk-500  #6B7A8F   information, secondary               │
  │ clay-500  #A85C4A   warnings — never a fire-engine red   │
  └──────────────────────────────────────────────────────────┘
```

**Why amber-rose:** it reads as warmth, candlelight, and skin tone rather than as romance-by-stereotype. It works identically for a masculine, feminine, or androgynous character. Pink would gender the product; red would make it feel transactional; purple would put it in the same visual bucket as every competitor.

**Dark mode is the default.** Most of this product's usage is at night, and a bright white interface at 1am is hostile. Light mode is fully supported and equally considered — some people use their companion over morning coffee, and they should not be given the nightclub treatment.

**Note on `clay-500` for warnings:** there is no true red in the palette. Errors and warnings use a muted clay. In a product about a relationship, an alarming red alert reads as *something is wrong between you and this person*, which is almost never what the message means.

---

## 4. Typography

| Role | Face | Notes |
|---|---|---|
| Conversation | **Inter** | Optimized for screen reading at length; neutral |
| Character voice | **Inter**, 16px/1.6 | Same face, generous line height |
| UI | **Inter**, 14px | Consistent — no separate UI font |
| Display / headings | **Fraunces** | Warm serif, used sparingly; brand moments only |
| Numerals (Aura, timers) | Inter, tabular figures | Prevents jitter on live-updating values |

**Conversation text is 16px with 1.6 line height and a max measure of ~62 characters.** These are reading-comfort numbers, not aesthetic ones. People read a great deal of text in this product, often for hours, often tired.

**Fraunces appears rarely** — the wordmark, empty states, milestone moments. A serif used everywhere would feel literary and precious; used at three or four moments it feels like care.

---

## 5. Motion

| Element | Duration | Easing |
|---|---|---|
| Message appearance | 180ms | ease-out |
| Typing indicator | continuous, 1.4s cycle | ease-in-out |
| Screen transition | 240ms | ease-in-out |
| Modal / sheet | 280ms | spring, low bounce |
| Avatar idle (breathing) | 4s cycle | sine |
| Call connect | 400ms | ease-out |

**Rules:**
- **Nothing bounces playfully.** Springiness reads as toy-like and undercuts the emotional register.
- **The typing indicator is timed to the actual response**, not a fixed animation. A character who "types" for four seconds and then produces one word is lying about her effort, and users notice.
- **`prefers-reduced-motion` removes all non-essential motion**, including the avatar's idle animation. It does not remove the typing indicator, which carries information.

---

## 6. Layout

```
  MOBILE (primary)              DESKTOP
  ┌─────────────────┐           ┌──────────┬────────────────────┐
  │  ← Sena    ⋯ 📞 │           │          │  ← Sena       ⋯ 📞 │
  ├─────────────────┤           │  chars   ├────────────────────┤
  │                 │           │          │                    │
  │   conversation  │           │  Sena  ● │    conversation    │
  │                 │           │  Kai     │                    │
  │                 │           │  Wren    │                    │
  │                 │           │          │                    │
  ├─────────────────┤           │          ├────────────────────┤
  │ [        ] 🎤 ↑ │           │  ⚙ 240⟡  │  [           ] 🎤 ↑│
  └─────────────────┘           └──────────┴────────────────────┘
```

**Mobile-first, genuinely.** The desktop layout is the mobile one with a character rail added. This is not a compromise — the overwhelming majority of usage is on a phone, held one-handed, and often in bed.

**The composer is always reachable by thumb.** Voice is one tap from the composer, not buried in a menu, because voice is a first-class modality rather than a feature.

**Aura balance (`240⟡`) is visible but never prominent.** It sits in settings and in the call pre-flight. It is never a badge on the character, never animated when it decreases, never coloured to create anxiety. The user should be able to know their balance without being reminded of it.

---

## 7. The conversation surface

The most important screen in the product, so the details matter disproportionately.

| Element | Treatment |
|---|---|
| Character messages | Left-aligned, no bubble — plain text on the background |
| User messages | Right-aligned, subtle `ink-100` / `ink-800` bubble |
| Character name | Shown once at the top of a session, not per message |
| Timestamps | On hover / long-press only. Not on every message. |
| Images | Full-width, rounded, no frame — as if sent, not generated |
| Typing indicator | Three dots, `ink-400`, at the left margin |
| AI disclosure | Persistent, quiet, in the header. Required by SB 243. |

> **Why character messages have no bubble:** bubbles on both sides make the exchange feel like a transaction log — two parties trading packets. Removing the bubble from one side makes the character's words feel like they are simply *in the room*, and makes the user's own messages feel like what they are: things they said. It is a small change with a large effect on how the surface reads.

**The AI disclosure is a legal requirement handled with care.** It sits in the header as quiet secondary text — permanently present, never dismissible, never a modal, never in the conversation flow. It must be conspicuous per [13 §2](13-TRUST-SAFETY-AND-COMPLIANCE.md), and it must not interrupt.

---

## 8. The call surface

```
  ┌─────────────────────┐
  │                     │
  │                     │
  │      [ face ]       │   ← full bleed. no chrome over the face.
  │                     │
  │                     │
  │                     │
  │       Sena          │
  │       04:12         │
  │                     │
  │   🔇    ⤫    📷     │   ← controls fade after 3s of no interaction
  └─────────────────────┘
```

**Full-bleed face, chrome that disappears.** The face is the product during a call; anything drawn over it is a cost. Controls fade after three seconds and return on tap.

**Connection sequence** ([06 §7](06-REALTIME-VOICE-VIDEO.md)): 2–3 seconds of ringing, a connection sound, then the character speaks first. Instant connection feels like pressing play on a video. Ringing makes it a call.

**Aura during a call:** the remaining time is shown in the pre-flight screen before connecting and once, gently, at the two-minute warning. It is never a live countdown on screen — watching a timer tick down while talking to someone you care about is precisely the feeling this product exists to avoid.

---

## 9. Character creation

The highest-stakes flow in the product. A user who does not love the character they create will not come back.

```
  1. WHO ARE THEY?     archetype (12) — presented as short descriptions
                       of a person, never as stat blocks
                            │
  2. HOW DO THEY LOOK?  appearance → generate 12 candidates →
                       pick one → THE canonical face (locked)
                            │
  3. HOW DO THEY TALK?  12 personality axes, each showing a live
                       example line that changes as you move it
                            │
  4. WHAT'S THEIR STORY? name, backstory, interests, occupation
                            │
  5. VOICE             pick from candidates, hear each one say
                       the same line
                            │
  ▶ first message
```

**Two decisions carry this flow.**

**Personality axes show a live example line.** Moving "playfulness" from 3 to 8 changes a sample response on screen in real time. Abstract sliders produce characters that surprise their creators badly; seeing the effect produces characters people recognize.

**Appearance is chosen from generated candidates, not built from sliders.** Users cannot describe a face, but they know one when they see it. Twelve candidates from their broad parameters, pick one, lock it forever ([08 §2](08-IMAGE-VIDEO-GENERATION.md)).

**The whole flow must be completable in under four minutes**, with an expert path for users who want the full parameter space ([04 §6](04-CHARACTER-SYSTEM.md)).

---

## 10. Voice and tone (the product's, not the character's)

Amorien's own copy — buttons, errors, settings, emails.

| | |
|---|---|
| **Is** | Warm, plain, unhurried, adult |
| **Is not** | Cute, clinical, salesy, coy, winking |

| Instead of | Write |
|---|---|
| "Oops! Something went wrong 😅" | "That didn't send. Try again?" |
| "Upgrade now to unlock more!" | "Plus adds voice calls and two more Amoriens." |
| "You're running low on credits!!" | "About 20 minutes of calls left this month." |
| "She misses you! Come back 💔" | *(never written — see [13 §9](13-TRUST-SAFETY-AND-COMPLIANCE.md))* |

**The product never speaks in the character's voice**, and the character never speaks in the product's. A billing notice written as if the companion said it is a manipulation, and users read it as one immediately.

**Errors during a conversation are the exception, and they invert this rule** — those are narrated in character ([06 §8](06-REALTIME-VOICE-VIDEO.md)). "My camera's being weird, can we just talk?" is the character. "Your payment method expired" is the product. The line is: anything about the relationship is hers, anything about the account is ours.

---

## 11. Accessibility

| Requirement | Standard |
|---|---|
| Contrast | WCAG AA minimum; AAA for conversation text |
| Touch targets | 44×44pt minimum |
| Screen reader | Full labelling; messages announced with speaker attribution |
| Reduced motion | Honoured throughout, including avatar idle |
| Text scaling | Up to 200% without layout breakage |
| Keyboard | Full navigation on desktop, including call controls |
| Captions | **Live captions on voice and video calls** |

> **Live captions are not only an accessibility feature here.** They serve users who are hard of hearing, users in a quiet house who cannot use audio, and users whose first language is not English. Since STT already runs on the user's side of the pipeline and TTS text exists before it is spoken, both directions are essentially free. This should ship with voice, not after it.

---

## 12. What we will not build

| Not building | Why |
|---|---|
| Streaks and daily-login rewards | Turns a relationship into an obligation |
| Red notification badges | Manufactured urgency |
| "She's typing..." push notifications | Manufactured presence |
| Gacha or loot-box mechanics | Gambling patterns in an emotional product |
| Countdown timers on offers | Pressure |
| Guilt-framed re-engagement | [13 §9](13-TRUST-SAFETY-AND-COMPLIANCE.md) |
| Animated Aura depletion | Anxiety about spending, during intimacy |

Each of these measurably increases engagement. Each is excluded on purpose. The design system has no components for them, which is the point — making a dark pattern requires building something new rather than reaching for an existing part.

---

*Next: [14 — GTM & Growth](14-GTM-AND-GROWTH.md) · [16 — Engineering Handbook](16-ENGINEERING-HANDBOOK.md)*
