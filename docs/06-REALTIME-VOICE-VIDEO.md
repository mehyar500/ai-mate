# Realtime Voice & Video

**The requirement:** it should feel like FaceTime. Not "voice chat with an AI" — a call, with a face, that responds like a person is on the other end.

This document is the latency budget that makes that true, and the cost model that makes it survivable.

---

## 1. The number that decides everything

Human conversational turn-taking has a well-documented gap of roughly **200ms** between one speaker finishing and the next beginning. It is remarkably consistent across languages. We are extremely sensitive to deviations from it, because we use that gap to read hesitation, reluctance, and enthusiasm.

What that means in practice:

| Round-trip latency | How it reads |
|---|---|
| **< 300ms** | Indistinguishable from a person |
| **300–800ms** | A slightly thoughtful person. **This is the target.** |
| **800–1200ms** | A bad phone connection. Tolerable. |
| **1200–2000ms** | Talking to a computer |
| **> 2000ms** | A phone tree |

Most companion apps sit at 2–4 seconds. That is why their voice mode feels like a novelty rather than a conversation.

> **Amorien's target: < 800ms p50, < 1200ms p95, measured end of user speech → first audio out.**
>
> This is the single hardest engineering requirement in the product and the one that most differentiates it. Everything below exists to hit that number.

---

## 2. Two architectures, and why we use both

### 2.1 Speech-to-speech (native audio)

The model hears audio and speaks audio. No transcription step.

```
user audio ──────▶ [ gpt-realtime / Gemini Live ] ──────▶ audio out
                            ~300-500ms
```

**Good:** lowest possible latency, native prosody, handles interruption and backchannelling ("mm-hm") naturally, hears *how* something was said.

**Bad, and disqualifying:**
- **No injection point.** There is nowhere between hearing and speaking to retrieve memory. For a product whose entire thesis is memory, this is fatal.
- **Prohibited for T2/T3.** Every native audio model is a frontier API with an adult-content prohibition.
- **Voice is theirs, not yours.** Limited voice selection, no per-character voice identity.

**Cost** ✅: `gpt-realtime-2.1` $0.0676/min · `gpt-realtime-2.1-mini` $0.0216/min · `Gemini Live 2.5 Flash Native Audio` $0.0144/min.

### 2.2 Cascaded (STT → LLM → TTS)

```
user audio ──▶ [STT] ──▶ text ──▶ [orchestrator + memory] ──▶ [LLM] ──▶ [TTS] ──▶ audio
               ~150ms                    ~60ms                 ~350ms    ~90ms
```

**Good:** full control at every stage, memory retrieval sits naturally in the middle, per-character voice, tier routing works, works for T2/T3.

**Bad:** more latency, loses vocal nuance in transcription, requires solving turn detection yourself.

**Decision: cascaded is the primary architecture.** The memory injection point is non-negotiable — without it the companion is a stranger with a nice voice. Native speech-to-speech ships as an optional **"Live mode"** for T0/T1 users who want maximum responsiveness and will trade memory depth for it.

---

## 3. The latency budget

Every millisecond, allocated. This is the contract.

```
  EVENT                                    BUDGET    CUMULATIVE
  ────────────────────────────────────────────────────────────
  user stops speaking                        0ms          0ms
  ├─ VAD / turn detection fires            120ms        120ms
  ├─ final STT transcript                   80ms        200ms
  ├─ memory retrieval (parallel)          [60ms]        200ms
  ├─ safety classifier (parallel)         [40ms]        200ms
  ├─ prompt compilation                     10ms        210ms
  ├─ network to LLM provider                40ms        250ms
  ├─ LLM first token                       280ms        530ms
  ├─ accumulate first clause (~8 tok)       90ms        620ms
  ├─ TTS time-to-first-byte                 90ms        710ms
  ├─ network + jitter buffer                60ms        770ms
  └─ FIRST AUDIO REACHES USER                           770ms  ✓
  ────────────────────────────────────────────────────────────
  (video) avatar frame sync              +150ms         920ms
```

**Five techniques do the heavy lifting:**

1. **Turn detection, not silence timeout.** A fixed 500–700ms silence threshold is where most implementations lose the race before it starts. Semantic turn detection — a model that knows "I went to the—" is unfinished while "I went to the store" is complete — fires in ~120ms. **Deepgram Flux includes this**, which is why it is worth $0.0065/min over cheaper STT at $0.0023.

2. **Speculative execution.** Start the LLM call on the interim transcript before the final one arrives. Discard and restart if the final differs materially. Costs a few wasted tokens; buys ~80ms. Tokens are cheap; latency is not.

3. **Clause-level TTS streaming.** Do not wait for the sentence. Send the first natural clause boundary — roughly 8 tokens — straight to TTS while the LLM keeps generating. This is worth ~400ms on a typical response and is the single highest-leverage optimization on the list.

4. **Parallel everything off the critical path.** Memory retrieval and the safety classifier run concurrently with STT finalization. They are free because they finish before their results are needed.

5. **Colocation.** Orchestrator, STT, LLM, and TTS in the same cloud region. Cross-region hops cost 40–80ms each and there may be three of them.

---

## 4. Interruption

Being able to cut in is not a feature — it is most of what makes a call feel like a call. When the user starts speaking, the character stops. Immediately.

```
user starts speaking mid-response
        │
        ├──▶ VAD fires                          ~40ms
        ├──▶ stop TTS playback locally           ~10ms   ← client-side, instant
        ├──▶ cancel TTS stream                   ~50ms
        ├──▶ cancel LLM generation               ~50ms
        └──▶ truncate context to what was
             ACTUALLY HEARD, not what was
             generated
```

> **The last step is the one everyone gets wrong.** If the model generated three sentences and the user interrupted after one, the context must record one sentence. Otherwise the character believes it said things the user never heard, and the conversation quietly desynchronizes — the character references something it "said" that the user has no memory of. This is deeply uncanny and very hard to debug from user reports.

Track spoken audio duration, map it back to token position, truncate there.

**Backchannel handling:** "mm-hm", "yeah", "right" are not interruptions. A short-utterance classifier distinguishes acknowledgement from a real turn attempt. Getting this wrong makes the character stop constantly and feel timid.

---

## 5. The voice pipeline stack

All prices verified 2026-09-04 ✅. Full matrix in [12](12-VENDOR-API-MATRIX.md).

| Stage | Vendor | $/min | Why |
|---|---|---|---|
| Transport | LiveKit Cloud | 0.0100 | WebRTC + agent framework; managed SFU |
| STT | Deepgram Flux | 0.0065 | **Turn detection and interruption built in** |
| LLM | route by tier | ~0.0014 | ⚠️ ~150 tok in / 80 tok out per turn, ~4 turns/min |
| TTS (standard) | Inworld 2.0 Flash | 0.0054 | Best value at realtime quality |
| TTS (premium) | Cartesia Sonic 3.6 | 0.0225 | ~90ms TTFB, best emotional range |
| Observability | LiveKit | 0.0100 | Optional but you will want it early |

**Totals:**

| Configuration | $/min | $/hour |
|---|---|---|
| Standard voice (Inworld) | **~0.0333** | $2.00 |
| Premium voice (Cartesia) | **~0.0504** | $3.02 |
| LiveKit reference stack ✅ | 0.0672 | $4.03 |

LiveKit's own published reference total is $0.0672/min ✅ (agent session $0.0100 + LLM $0.0014 + STT $0.0058 + TTS $0.0300 + observability $0.0100). Our standard configuration comes in under half that by choosing cheaper TTS, which is the dominant term.

> **TTS is 40–50% of voice cost.** It is also most of what makes the character feel alive. This is the one place in the stack where the cheap option is a real product compromise, which is why it is tiered by plan rather than chosen once.

---

## 6. Video — the FaceTime layer

### 6.1 How it works

```
                              ┌──────────────────┐
   LLM text ────────────────▶ │                  │
                              │   Anam / Tavus   │ ──▶ WebRTC video ──▶ client
   TTS audio ───────────────▶ │  avatar renderer │ ──▶ WebRTC audio ──▶ client
                              │                  │
   emotional state ─────────▶ │  (expression)    │
                              └──────────────────┘
                                       ▲
                              character identity
                              (replica trained from
                               identity-lock refs)
```

The avatar service receives the audio stream and produces a lip-synced, expressive video stream of the character's face, delivered over the same WebRTC session as the audio. Total added latency is ~150ms, which lands the video path at ~920ms — inside budget.

### 6.2 Vendor comparison ✅

| | **Anam** | **Tavus CVI** | **HeyGen** |
|---|---|---|---|
| Cost/min | **$0.11–0.16** | $0.32–0.37 | credit-based |
| Replica creation | included | $40–65 one-time | included |
| Concurrency | by tier | 3 @ $59/mo, 10 @ $397/mo | by tier |
| Free minutes/mo | 30 / 50 / 250 / 2,000 / 5,000 | — | — |
| Call length cap | 3 / 5 / 10 min on lower tiers | — | — |
| Quality | Very good | **Best** | Very good |

**Decision: Anam.** It is 3× cheaper, the quality gap is small at phone-screen size and typical mobile bitrates, and the free-minute allowances (2,000–5,000/month on higher tiers) materially subsidize the early growth phase. Re-evaluate Tavus when ARPU supports it.

### 6.3 The cost problem, stated honestly

> At **$0.11/min**, one hour of video costs **$6.60** in avatar rendering alone.
> Add the voice stack and it is **$8.60/hour**.
> At Tavus pricing it is **$24.20/hour**.
>
> A $29.99 Premium subscription covers roughly **3.5 hours** of video per month at a sustainable margin. Users who love video calling will want far more than that.

**There is no version of this that is unlimited.** Any competitor who launches unlimited photoreal video calling at consumer subscription prices is either losing money deliberately or shipping something much worse than they are describing.

Hence Aura metering — see [11](11-PRICING-AND-UNIT-ECONOMICS.md):

| | Aura/min | ≈ cost | ≈ price |
|---|---|---|---|
| Voice (standard) | 1 | $0.033 | $0.010 ⚠️ subsidized by subscription |
| Voice (premium) | 2 | $0.050 | $0.020 |
| Video | **4** | $0.145 | $0.040 |

Aura is priced so that the subscription covers the expected case and heavy users top up. The alternative — flat-rate unlimited video — is a business model that fails at exactly the moment it succeeds.

### 6.4 Graceful degradation

Non-negotiable, from [03 §8](03-PRD.md): **when a user runs out of Aura, they still have their companion.**

```
Aura low  ──▶ warn in-character, once, gently, not mid-emotional-beat
Aura out  ──▶ video  ──fades to──▶ voice
          ──▶ voice  ──fades to──▶ text
          ──▶ text ALWAYS works, forever, on every plan
```

The transition is presented in character — "my camera's being weird, can we just talk?" — never as a system modal. The user should not be yanked out of the relationship to be shown a billing screen.

Bandwidth-driven degradation follows the same path, and the same rule: in character, no modals.

---

## 7. The call experience

Details that matter more than they should:

| Detail | Why |
|---|---|
| **Ringing** | A call that starts instantly feels like a video player. 2–3 seconds of ringing creates anticipation and makes it a call. |
| **Connection sound** | A subtle audio cue on connect, as on a real call |
| **She speaks first** | The character greets, contextually — "hey, I was just thinking about what you said yesterday." Uses memory. Immediately signals this is not a fresh session. |
| **Idle presence** | Between turns the avatar breathes, blinks, shifts. A frozen frame is a corpse. |
| **Natural closing** | Calls end with a goodbye, not a hang-up button. The character gets to say something. |
| **Post-call memory** | The call is summarized into memory within seconds. Referencing it in text chat ten minutes later is the moment the product proves itself. |

> **The last one is the whole product in one interaction.** A user has a video call, hangs up, opens text chat an hour later, and the character says something that only makes sense if she remembers the call. Nothing else in this category does that, and it costs one cheap model call.

---

## 8. Failure modes

| Failure | Handling |
|---|---|
| STT provider down | Failover to secondary (AssemblyAI); if both, degrade to text with an in-character apology |
| TTS provider down | Failover to secondary; if both, text |
| LLM timeout > 3s | In-character filler ("hmm, hold on—"), then retry once, then failover |
| Avatar service down | Silent fall back to voice-only. Do not surface a technical error. |
| Bandwidth collapse | Video → voice → text, in character |
| User's mic fails | Detect silence with an active session, prompt gently |

**The rule across all of them:** the character never says "an error occurred." She has a bad connection, she is distracted, her camera is acting up. The failure is always narrated from inside the fiction, because the alternative reminds the user that there is no one there.

---

## 9. Implementation notes

- **Framework:** LiveKit Agents. Purpose-built for exactly this pipeline, handles WebRTC, turn detection integration, and interruption plumbing. Pipecat is the vendor-neutral alternative if LiveKit lock-in becomes a concern.
- **Client:** WebRTC via the LiveKit SDK. Native WebRTC in the PWA, no plugin.
- **Region strategy:** deploy the agent in the region nearest the user; pin STT/LLM/TTS to the same region. Multi-region from month one — a European user routed to us-east-1 loses 90ms before anything happens.
- **Warm pools.** Cold-starting an agent session adds seconds. Keep a warm pool sized to peak concurrency; it is cheap relative to the experience cost.
- **Measure the right thing.** Instrument *end of user speech → first audio at the client's speaker*. Not server-side generation time. The user-perceived number is the only one that matters and it is always worse than the one on your dashboard.

---

## 10. Phasing

| Phase | Scope | Success test |
|---|---|---|
| 2a | Voice, cascaded, no interruption | Round trip < 1200ms p50 |
| 2b | Turn detection + interruption | Round trip < 800ms p50; interruption < 100ms |
| 2c | Per-character voice, emotional prosody | Users describe the voice as "hers" |
| 3a | Video, single character, Premium only | First frame < 2s; identity match verified |
| 3b | Video for all characters, Aura metering | Margin positive at target usage |
| 3c | Character-initiated calls (opt-in) | Answer rate; **no increase in complaints** |

> **The test for 3c is deliberately a negative metric.** Character-initiated calls are the most abusable feature in this entire document. If shipping it increases complaints at all, it comes back out regardless of what it does to engagement.

---

*Next: [07 — Memory](07-MEMORY-ARCHITECTURE.md) · [08 — Image & Video Generation](08-IMAGE-VIDEO-GENERATION.md)*
