# Amorien repository review — 7 September 2026

Amorien has a clear product idea and a substantial design dossier, but the repository is not yet a validated implementation plan. Its strongest material describes persistent, editable memory, versioned characters, consistent identity, and honest monetization. Its weakest material turns speculative infrastructure, assumed competitor weaknesses, and inconsistent arithmetic into confident guarantees.

The highest-value next step is to reconcile the decisions and build one measured end-to-end experience. Adding more broad strategy documents would currently increase ambiguity.

**Review scope and evidence**

I read all 44 working-tree files present before this report: 36 documents, six root files, and two scripts. They total 5,959 lines and 352,577 bytes. Hidden project files were included. I inspected tracked/untracked status and recent commit subjects. I did not treat Git's internal object database as application source or audit historical versions of every file. No AGENTS.md was found in the repository or the checked ancestor locations.

There are no application source directories, dependency installation directories, model weights, media assets, database migrations, containers, deployment manifests, CI workflows, or executable evaluation suites in this checkout. The only Python file is 67 lines; its apparent model interaction is simulated.

External checks were targeted, not an exhaustive refresh of every price, model, law, or competitor assertion. Findings below distinguish observed repository facts, calculations using the documents' own assumptions, and claims checked against official external sources. A missing evidence file means the claim is not reproducible here; it does not prove that research never happened elsewhere.

I added only this review. Existing files and the 13 pre-existing untracked files were left untouched.

**What I understand the product to be**

Amorien is an adult-only AI companion service, inclusive of different genders, orientations, and platonic relationships. Users adopt or create a character with a recognizable appearance, voice, personality, and backstory. Text, voice, and eventually live avatar video share the same relationship history. Verified adults may opt into additional content capabilities, subject to provider, payment, and jurisdiction constraints.

The original thesis has four parts:

- Long-term memory makes the relationship feel continuous.
- Low response latency makes spoken conversation feel natural.
- Consistent appearance and personality make the character recognizable.
- Subscription revenue plus metered media pays for the experience without placing emotional moments behind purchase prompts.

The latest committed distribution decision is PWA-first, with native iOS deferred. Document 30 explicitly withdraws earlier implications of already-validated margins, provider approval, and unrestricted native distribution. It proposes approved web checkout and a verified entitlement ledger; it does not establish that the infrastructure exists.

The intended original request flow is authentication → content eligibility → input checks and memory retrieval → prompt compilation → model selection → streamed response → persistence and background memory updates. Voice adds transcription, turn handling, synthesis, and interruption tracking. Video adds avatar rendering and synchronization. Images add identity conditioning and output verification. Billing and usage authorization cross all paid paths.

That is a coherent product concept. The repository currently contains several incompatible implementations of it.

**The competing plans**

| Area | Original numbered specification | Later proposals | Unresolved decision |
|---|---|---|---|
| Backend | TypeScript/Fastify modular monolith | Cloudflare Workers and Durable Objects | Runtime ownership and actual module interfaces |
| Memory | Postgres/pgvector, temporal facts | Pinecone/Supabase; D1/Vectorize; graph memory | Authoritative store, retrieval method, migration and consistency rules |
| Voice | Cascaded STT → LLM → TTS | Native audio is declared mandatory in consensus files | Benchmark comparable pipelines instead of declaring either universally superior |
| Visuals | Hosted Anam avatar | RunPod/LivePortrait; local Gaussian splats | One chosen renderer, supported inputs, license, measured device/session performance |
| Content | Server-side tiers and mandatory classifiers | “Zero moderation” and “No filter logic” | One consistent content policy and enforcement contract |
| Pricing | $12.99/$29.99/$79.99 with Aura | $14.99/$24.99, $49.99, $59.99, $99, then $29.99 | Single calculator and allowance model |
| Distribution | PWA plus native launch requirements | Native call-first UX; later PWA-only launch | Apply document 30 throughout the roadmap and README |
| Business scale | Small team; low infrastructure break-even | $250k monthly overhead and $700k acquisition spend | Founder budget and realistic staffed operating model |

The existence of alternatives is normal. Labeling multiple alternatives “approved,” “master,” “consensus,” “validated,” and “executive lock” without supersession records is the problem. Document 30 is a useful correction, but it does not reconcile every architecture or pricing choice.

**Critical finding: the economics are not reliable enough to price the product**

The following corrections use the repository's own rates. They are internal arithmetic checks, not current vendor quotes.

| Claim | Recalculation | Consequence |
|---|---|---|
| Doc 12: $3.29/hour GPU, 8–15 million tokens/day, yielding $0.008–$0.015/million tokens | $3.29 × 24 = $78.96/day; divide by 8–15 million = **$5.264–$9.87 per million** | The claimed 20–40× savings do not follow from these inputs. Input/output workloads and actual throughput also need separate measurement. |
| Doc 11: Premium spends 1,080 Aura at a 70/30 voice/video mix for $9.72 | Interpreting the mix as spent credits: 756/2 premium voice minutes × $0.0518 + 324/4 video minutes × $0.145 = **$31.33** | Including the document's text, storage and 12% processing assumptions gives approximately **−$7.44 contribution** on $29.99 revenue. Using its higher premium video rate worsens this. |
| Doc 11: Infinite spends 3,600 Aura for $32.40 | Same mix and rates yield **$104.42 in media alone** | More than the $79.99 subscription before text, payment fees, or other costs. |
| Doc 11: 60% Plus / 32% Premium / 8% Infinite gives $22.44 ARPU | 0.60×12.99 + 0.32×29.99 + 0.08×79.99 = **$23.79** | The blended table does not reconcile to its stated plan mix. |
| Doc 28: 38 hours at $0.013/minute fits $29.99 at 50% margin | 38 × 60 × $0.013 = **$29.64** | About 1.2% remains before every other expense. |
| Doc 27: 45 minutes/day at the final $0.013/minute supports about 65% margin | 45 × 30 × $0.013 = **$17.55/month** | Compute-only margin is about **41.5%**, before processing, storage, support, etc. The earlier $0.005 assumption is a different scenario. |
| Docs 17/19/23: subscriber contribution divided into a profit target gives “pure/net profit” | Operating profit must also subtract fixed costs, compensation and acquisition expenses | These are contribution targets, not demonstrated take-home profit forecasts. |

Document 11 explicitly acknowledges selling voice/video below marginal cost, but claims top-ups brake heavy usage. Its top-ups still sell standard voice credits for approximately $0.013–$0.020 against a $0.033 cost per minute. Each fully consumed incremental top-up adds a loss. Unused subscription allowances cannot make an unlimited sequence of loss-making top-ups sustainable.

The claimed 107-user break-even covers only a listed infrastructure/vendor budget, using an unreconciled contribution number. It cannot fund the roadmap's 4–6-person team. The annual discounts also need their own utilization and revenue-recognition scenarios.

Improve this with one executable cost model using explicit units: session minutes, user audio minutes, synthesized audio minutes, GPU seconds, billed tokens, output frames, GB transferred, delivered images, retries, and idle capacity. Model low/typical/heavy utilization, 100% allowance consumption, annual subscriptions, refunds, payment fees, chargebacks, free users, and fixed payroll. Keep reserves in a separate cash-flow view. Price incremental usage above its incremental cost plus the desired contribution.

**Critical finding: commercial and technical prerequisites are missing**

XTTS-v2 is repeatedly treated as the ready-to-use commercial voice engine in documents 25, 27 and 29 and the environment template. Its published model license permits non-commercial use; an open-weight download is not a commercial grant. A separately documented commercial right or another eligible model is needed before that choice can underpin the paid offering. [XTTS-v2 model license](https://huggingface.co/coqui/XTTS-v2/blob/main/LICENSE.txt).

The pipeline diagrams also treat LivePortrait as if voice audio can be directly attached to produce a complete conversational avatar. The official basic workflow uses a source portrait and driving video or motion template, and produces an MP4. It lists separate community audio-driven projects. My inference is that Amorien still needs to select and implement the audio-to-motion/lip-sync stage plus streaming integration; listing LivePortrait alone does not specify that work. [Official LivePortrait repository](https://github.com/KlingAIResearch/LivePortrait).

Similarly, the RunPod runbook requests custom TTS and avatar containers that are not provided. It does not choose the endpoint behavior or explain session lifecycle, streaming, cancellation, GPU warming, or health probes. RunPod distinguishes queued `/run` and `/runsync` jobs from load-balancing endpoints intended for real-time streaming. The demo's unused `/run-sync` URL also differs from the documented `/runsync` spelling. [RunPod endpoint documentation](https://docs.runpod.io/serverless/endpoints/overview).

Maintain a registry per exact model/checkpoint: publisher, revision, code license, weight license, dependent models, commercial rights, voice rights, allowed use, serving API, supported inputs/outputs, deployment artifact and test evidence. Host permission and model permission are separate checks.

**Critical finding: the competitive differentiation needs rebuilding**

Documents 02, 14, 20 and 28 lean on competitors lacking real-time avatar calling. Kindroid's official documentation already describes live avatar calls with real-time lip-sync and gestures. Its website also presents friendship, roleplay and other use cases. That invalidates the blanket “nobody ships this” claim and weakens the blanket “all competitors only serve straight men” positioning. It does not prove Kindroid meets Amorien's desired quality or memory goals. [Kindroid calls documentation](https://kindroid.ai/v2/docs/voice-calls-and-video-calls/), [Kindroid product page](https://kindroid.ai/).

Claims about competitors' internal context windows, databases, centralization, silent downgrades, inability to interrupt, or corporate pivots frequently have no linked evidence. Public behavior is not enough to infer a private backend architecture. “Perfect” memory and “flawless” continuity are target claims with no implementation behind them.

Replace these with dated hands-on comparisons: identical multi-session memory scenarios, contradiction corrections, interruptions, portrait changes, real call costs, privacy controls, and user interviews. Separate observed behavior from a proposed explanation. Compete on demonstrated reliability and user control instead of presumed absences.

**High-priority finding: routing is necessary but not a proof of safe output**

Documents 05, 09 and 13 repeatedly imply that an allowed-route model cannot generate disallowed content because the other model was never called. Selecting an endpoint establishes authorization; it does not establish every possible output of that endpoint. Output checking is mentioned, but its relationship to streaming is not specified.

The actual specification needs decisions about when chunks are released, what happens to audio already queued, how moderation outages behave on every tier, how an immediate tier-down cancels in-flight generation, and how cached entitlements are invalidated. Imported character cards, lorebooks, retrieved memory, user images and conversation summaries are additional untrusted inputs.

There is also a cross-tier data-routing gap. If an adult conversation is summarized, embedded, used to construct an image prompt, or revisited after a tier-down, that history can reach background or clean-route providers unless data classification follows it. A request tier alone does not capture the sensitivity or provider eligibility of its retained context.

Define a capability table separating age eligibility, content consent, jurisdiction, billing entitlement and client surface. Document 30 begins this separation. Carry content provenance through memory and background jobs, and use a provider allowlist appropriate to the payload, not merely the current chat setting. Test that unauthorized routes are never selected and separately evaluate whether permitted routes produce acceptable output.

**High-priority finding: billing and persistence need concrete transactional behavior**

An append-only ledger is a good start, but document 09's table is insufficient for the promised behavior:

- There is no unique idempotency key for a payment event or usage block.
- Per-15-second standard voice usage consumes 0.25 Aura, but `delta` is an integer and no smaller unit is defined.
- Expiring grants and non-expiring purchased credits require allocation of debits to grants; summing rows with expired grants omitted is not a complete spending model.
- Concurrent sessions can both observe the same cached balance unless usage is reserved atomically.
- Settlement, release of unused reservations, rounding, reconnects and partial refunds are unspecified.

Document 30 correctly adds verified server notifications, replay safety, reconciliation and lifecycle events. Those concepts need a schema and state machine, not just prose. Use integer subunits, atomic reservation/settlement, unique provider-event and usage-event keys, and explicit grant consumption order.

Persisting everything only after streaming begins also risks losing conversation or usage records if a process dies. Record an accepted request durably, then reconcile streamed/generated/delivered content and actual usage. Background memory extraction can remain asynchronous. The requirement to remember only spoken content after an interruption is valuable and deserves a delivery acknowledgment design.

If KV is used, do not make its cached copy authoritative for immediate revocation or spending. Cloudflare documents eventual consistency and states that KV is unsuitable when atomic operations or single-transaction reads/writes are needed. [Cloudflare KV consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/).

**High-priority finding: memory is the best specification, but important edge cases remain**

Document 07 has the strongest technical foundation: temporal validity, provenance, confidence, user correction, character scope and separate model lifecycles. Preserve it.

What needs adding:

- Distinguish the real user from a roleplay persona, hypothetical statements and fictional events. A shared schema alone must not mix those facts.
- Track observation time separately from effective time. “I moved last month” must not use today's extraction time as the date of the move.
- Define transactional supersession and deduplication under repeated extraction jobs.
- Add source/derived-memory lineage so deleting a fact invalidates summaries, embeddings, cached prompts and future re-extraction from retained messages.
- Make cross-character sharing explicitly controllable. “Objective” facts such as location are not automatically non-sensitive.
- Define what is forgotten immediately in retrieval and what is purged later from storage/backups. Starting a purge exactly on day 30 leaves no retry margin for a within-30-days promise.
- Version embedding models and record actual dimensions. The proposed D1/Vectorize stack does not automatically implement the Postgres schema.
- Decide how branches and edited messages affect memory. Otherwise facts from an abandoned conversation branch can leak into the current relationship.
- Calibrate retrieval with stale facts, corrections, negation, ambiguous names, no-answer cases, and cross-user leakage tests, not only positive similarity matches.

“Never forgets” is also incompatible with deliberate deletion and a finite retrieval budget. A stronger promise is that memories are inspectable, correctable and used reliably, with uncertainty acknowledged.

**High-priority finding: measured latency is being confused with optimistic component budgets**

The original voice document gives a useful end-of-speech-to-first-audio metric and identifies interruption truncation. Later consensus files promise global 70–90ms or sub-200ms response times, introduce unspecified edge GPUs/enclaves and custom large audio models, and declare entire pipeline families obsolete. No runnable benchmark supports these claims.

Local animation can make idle motion smooth without shortening server reasoning time. A renderer's frame rate is not a conversational response-time guarantee. WebRTC is a transport, not the missing inference or audio-to-motion implementation. A nearest-edge connection does not remove the remaining path to a remote GPU. A list of component averages does not establish end-to-end p95 behavior.

Document 18 also classifies Cartesia Sonic alongside native speech-to-speech intelligence engines. Cartesia identifies Sonic as text-to-speech: it accepts text and synthesizes audio. [Cartesia model overview](https://docs.cartesia.ai/get-started/overview).

Conversely, the original claim that native audio offers no memory integration point is too absolute. LiveKit documents realtime model context handling, external data/RAG, and supported configurations that combine realtime comprehension with separate synthesis. Whether retrieval fits the chosen response timing needs an experiment. [LiveKit realtime models](https://docs.livekit.io/agents/models/realtime/), [LiveKit external data integration](https://docs.livekit.io/agents/logic/external-data/).

Measure cold/warm call setup, end of speech to first audible output, interruption-to-silence, audio/video skew, first frame, reconnect recovery and cost at realistic concurrency. Save raw results with region, device, network, model revision and configuration. Treat the current 800ms target as a target, not an achieved property.

**Product contradictions that will become implementation bugs**

| Conflict | Locations | Needed correction |
|---|---|---|
| T2 means non-explicit sensual content in one document and explicit sexual content in others | 04 versus 05/08/13 | One shared taxonomy with examples and executable eligibility rules |
| Relationship stages are 0–6 in the character object but 1–7 in the memory table | 04 versus 07 | One enum, migration rule and thresholds; “Enduring” has no defined transition condition |
| Identity/voice is immutable, but later edits can change name, voice, body and face | 04 internally; 08 | Define a versioned identity change, user consent and asset regeneration policy |
| Canonical portraits number 4 versus 8–12; retries max 2 versus 3 | 04 versus 08 | One pipeline configuration and cost calculation |
| Memory cannot be monetized, yet free memory lasts 30 days and “memory depth” is a gated feature | 03 versus 04/11 and consensus | Decide retention/access behavior on downgrade without artificial amnesia |
| Visible in-call remaining balance is P0, but live remaining time is prohibited in the design | 03 versus 10 | Transparent, calm billing UI and user-controlled visibility |
| Billing belongs to the product, but credit exhaustion is disguised as the character's camera failure | 06 versus 10 | Honest service notices separate from character dialogue |
| No unsolicited engagement pressure, yet invented missed calls and a deceptive first call are proposed | 13/14 versus consensus files | Explicit opt-in, truthful AI disclosure and user-controlled contact |
| One stable nine-layer prompt is specified in incompatible layouts | 04 versus 05/11 | One compiler contract and one token budget |
| Claimed ~85% cached input versus 1,700/4,100 stable tokens | 04 versus 11 | About 41.5% in that table; actual cache eligibility/hits require provider measurements |
| T0-only native app versus T0/T1; native approval is required to launch despite later deferral | 04 versus 03/13/15/30 | Propagate the PWA-first decision and client-surface capability rules |

The ethical intent is valuable, but repeated “illusion” language undermines it when applied to billing, AI identity or fabricated contact. Optional fiction can coexist with clear service boundaries. The system should not invent a broken camera to conceal an exhausted allowance.

**Actual code and configuration review**

| File | What it does | Critique and improvement |
|---|---|---|
| [README.md](C:/Users/mehya/ai-mate/README.md) | Presents the product thesis and reading order for docs 00–16 | Correctly says pre-code, but “documentation complete” is misleading. Nineteen docs are not indexed, including the latest distribution decision. Add current status, canonical decisions and evidence links. |
| [ai_companion_test.py](C:/Users/mehya/ai-mate/ai_companion_test.py) | Bootstraps a Python virtual environment, installs requirements, prints a simulated audio/video flow | Not an integration test. No model request, valid image, audio, video, WebRTC or assertion. Rename as a mock example, label output explicitly, and separate environment setup from runtime. |
| [requirements.txt](C:/Users/mehya/ai-mate/requirements.txt) | Lists `requests` | Dependency is unpinned and unused by the demo. Remove unused dependencies or declare reproducible versions once real code uses them. |
| [.env.example](C:/Users/mehya/ai-mate/.env.example) | Cloudflare/RunPod and application placeholders | No actual secrets observed. Branding says AMORI. Variable names do not match the Python script's `API_KEY`; the script also never loads `.env`. Document one configuration schema and startup validation. |
| [.gitignore](C:/Users/mehya/ai-mate/.gitignore) | Excludes JS build output, secrets, model weights, media and scratch files | Good baseline, but misses the demo's `venv/`, Python bytecode/cache directories and root dummy image. The `.vscode/extensions.json` exception cannot work while its parent directory is entirely excluded. |
| [LICENSE](C:/Users/mehya/ai-mate/LICENSE) | MIT license including associated documentation | README describes the code as MIT, while the license text also covers associated docs. Clarify intended scope. This license does not grant rights to external model weights. |
| [scripts/check-domains.sh](C:/Users/mehya/ai-mate/scripts/check-domains.sh) | Sequential RDAP status checks with retries | Filename input works with mocked HTTP; advertised stdin mode fails because `-` is opened as a filename. Handle stdin explicitly, trim CRLF/whitespace, support final lines without newlines, validate names, and report failed requests distinctly. |
| [scripts/name-candidates.txt](C:/Users/mehya/ai-mate/scripts/name-candidates.txt) | 140 naming candidates | Useful historical input, not proof of purchased domains or brand clearance. Keep as research with dated check results. |

Additional Python details:

- `bootstrap_venv()` computes an absolute directory beside the script, but creates the relative directory `venv` under the caller's current directory. Running the script from elsewhere can create one environment and try to execute another.
- Bootstrapping runs at import time. Test discovery or importing the module can create files, install packages and relaunch the process.
- `text_to_companion_video` ignores `source_image_path` and always returns an example.com URL after two sleeps.
- `requests`, `base64`, API credentials and both endpoint constants are unused.
- Main writes `dummy image data` to a `.jpg` filename, which is not a valid image. It can mask the absence of a real fixture.
- Printed timing is the programmed sleep duration, not a latency measurement.

I compiled the Python source and executed only the extracted demo function with mocked time, without bootstrapping or invoking main. It returned “success” for a nonexistent image path, confirming the simulation. I syntax-checked the Bash script and ran a temporary copy with mocked `curl` and `sleep`: the advertised pipe usage failed with `-: No such file or directory`; file input executed. A Windows CRLF fixture also carried a carriage return into the printed domain. No model API calls or domain purchases were made.

**File-by-file documentation map**

These are review recommendations, not changes already made to the original documents.

| Document | What I understand from it | Recommended treatment |
|---|---|---|
| [00-EXECUTIVE-SUMMARY.md](C:/Users/mehya/ai-mate/docs/00-EXECUTIVE-SUMMARY.md) | Founding thesis, product pillars, first stack, plans and nine-month sequence | Keep as a shorter summary after reconciling pricing, competitor evidence and current scope. |
| [01-BRAND-AND-NAMING.md](C:/Users/mehya/ai-mate/docs/01-BRAND-AND-NAMING.md) | Amorien rationale, RDAP results, fallback names and brand vocabulary | Keep naming research; separate domain registration evidence from trademark/linguistic assertions. “Zero collision” is not demonstrated by RDAP. |
| [02-MARKET-RESEARCH.md](C:/Users/mehya/ai-mate/docs/02-MARKET-RESEARCH.md) | Competitor landscape, open character-card ecosystem and memory/video opportunity | Rewrite unsupported comparative absolutes; retain useful questions and dated observations. |
| [03-PRD.md](C:/Users/mehya/ai-mate/docs/03-PRD.md) | Detailed requirements with IDs, launch priorities, performance and product rules | Keep as requirements base, but reduce P0 scope and reconcile with 30. Add acceptance evidence and real owners. |
| [04-CHARACTER-SYSTEM.md](C:/Users/mehya/ai-mate/docs/04-CHARACTER-SYSTEM.md) | Typed character, axes, archetypes, appearance, identity lock, relationship and content tiers | Strong domain starting point. Resolve conflicting edits/tier definitions, unsupported success percentages and stage transitions. |
| [05-AI-ARCHITECTURE.md](C:/Users/mehya/ai-mate/docs/05-AI-ARCHITECTURE.md) | Orchestrator, tier minimum, routing, prompt compilation, safety, mood and migrations | Keep modular concepts. Correct routing guarantees, background data-policy gaps and prompt layout. |
| [06-REALTIME-VOICE-VIDEO.md](C:/Users/mehya/ai-mate/docs/06-REALTIME-VOICE-VIDEO.md) | Cascaded voice, latency allocation, barge-in, avatar integration, cost and failure UX | Keep measurement and truncation design. Recheck vendor assumptions; replace fictional billing errors and unsupported memory limitations. |
| [07-MEMORY-ARCHITECTURE.md](C:/Users/mehya/ai-mate/docs/07-MEMORY-ARCHITECTURE.md) | Temporal semantic/episodic/relational/procedural memory, extraction and user controls | Best foundation. Add lineage, deletion, branch semantics, transactional updates and real evaluation data. |
| [08-IMAGE-VIDEO-GENERATION.md](C:/Users/mehya/ai-mate/docs/08-IMAGE-VIDEO-GENERATION.md) | Identity-conditioned images, similarity gate, selfies, avatars and storage | Keep as an experiment plan. Validate renderer inputs and thresholds across supported styles; pin compatible checkpoints and licenses. |
| [09-SYSTEM-DESIGN.md](C:/Users/mehya/ai-mate/docs/09-SYSTEM-DESIGN.md) | Modular monolith, relational schemas, caches, workers, realtime and scaling | Keep patterns. Add tenancy constraints, durable request handling, billing transactions and actual chosen storage backend. |
| [10-DESIGN-SYSTEM.md](C:/Users/mehya/ai-mate/docs/10-DESIGN-SYSTEM.md) | Warm visual palette, typography, chat/call layouts, tone and accessibility | Useful design brief, not implemented components. Test contrast and interactions; reconcile transparent billing and consent. |
| [11-PRICING-AND-UNIT-ECONOMICS.md](C:/Users/mehya/ai-mate/docs/11-PRICING-AND-UNIT-ECONOMICS.md) | Detailed original cost and Aura model | Rebuild calculations before relying on any margin, allowance, LTV or break-even conclusion. |
| [12-VENDOR-API-MATRIX.md](C:/Users/mehya/ai-mate/docs/12-VENDOR-API-MATRIX.md) | Broad dated vendor catalogue, rates and launch recommendations | Convert to source-backed structured inventory. Correct GPU arithmetic; restore missing reproduction script/evidence references. |
| [13-TRUST-SAFETY-AND-COMPLIANCE.md](C:/Users/mehya/ai-mate/docs/13-TRUST-SAFETY-AND-COMPLIANCE.md) | Safety controls, adult eligibility, privacy, moderation and launch checks | Preserve as a requirements inventory. Separate product choices, vendor terms and jurisdiction-specific obligations; reconcile contradictory later proposals. |
| [14-GTM-AND-GROWTH.md](C:/Users/mehya/ai-mate/docs/14-GTM-AND-GROWTH.md) | SEO/community wedge, referrals, creator programme and growth assumptions | Keep channel hypotheses; validate underserved segments and conversion. Remove unsupported claims about all competitors. |
| [15-ROADMAP-AND-MILESTONES.md](C:/Users/mehya/ai-mate/docs/15-ROADMAP-AND-MILESTONES.md) | Six phases, staffing, exit criteria and kill criteria | Replace calendar confidence with dependency gates. Move necessary privacy/safety before alpha; defer native launch per 30. |
| [16-ENGINEERING-HANDBOOK.md](C:/Users/mehya/ai-mate/docs/16-ENGINEERING-HANDBOOK.md) | Proposed TS monorepo, invariants, tests, PR rules and operations | Clearly mark layout and checks as planned. Align stack and provide runnable commands once scaffolded. |
| [17-CURRENT-PLAN-VALIDATION.md](C:/Users/mehya/ai-mate/docs/17-CURRENT-PLAN-VALIDATION.md) | Interim answer about architecture and a $10k target while research was supposedly active | Archive as discussion context; remove stale “agents running” status and “pure profit” implication. |
| [18-FRONTIER-ARCHITECTURE.md](C:/Users/mehya/ai-mate/docs/18-FRONTIER-ARCHITECTURE.md) | Native-audio/WebRTC/avatar/action-tag proposal with a 600ms budget | Treat as an alternative hypothesis; correct TTS/S2S classification and document actual gesture interfaces. |
| [19-PRICING-VALIDATION.md](C:/Users/mehya/ai-mate/docs/19-PRICING-VALIDATION.md) | Alternative two-plan pricing with higher media credit burn | Better direction for incremental pricing, but not “exact net profit.” Feed assumptions into the shared calculator. |
| [20-COMPETITIVE-TEARDOWN.md](C:/Users/mehya/ai-mate/docs/20-COMPETITIVE-TEARDOWN.md) | Aggressive differentiation around perfect memory and video | Archive/rewrite with evidence. “Perfect” and “flawless” should not be build requirements or public promises. |
| [22-GPT6-BUSINESS-PLAN.md](C:/Users/mehya/ai-mate/docs/22-GPT6-BUSINESS-PLAN.md) | Venture-scale $49.99 plan, large ad spend, new-model assumptions and profitability odds | Separate scenario from bootstrap plan. Unsupported probability and technical claims are not a validated business case. |
| [23-BOOTSTRAP-VIRAL-GTM.md](C:/Users/mehya/ai-mate/docs/23-BOOTSTRAP-VIRAL-GTM.md) | $500 content-compute budget and 470-payer target for $15k | Keep as a channel experiment; account for operations and measure conversion rather than forecast virality as a timeline. |
| [24-LEGAL-AND-HOSTING-COMPLIANCE.md](C:/Users/mehya/ai-mate/docs/24-LEGAL-AND-HOSTING-COMPLIANCE.md) | Broad hosting, age/privacy, biometrics and retention overview | Consolidate with 13/30; it lacks the claim-level citations needed for its broad legal statements. Password-derived memory encryption also needs a coherent inference/key-recovery design. |
| [25-NSFW-PREMIUM-TIER-ECONOMICS.md](C:/Users/mehya/ai-mate/docs/25-NSFW-PREMIUM-TIER-ECONOMICS.md) | Self-hosted text/TTS/avatar model and a $59.99 plan | Revalidate licensing, measured serving costs and processing fees. Remove conflict with mandatory moderation policy. |
| [26-MASTER-VENDOR-API-MATRIX.md](C:/Users/mehya/ai-mate/docs/26-MASTER-VENDOR-API-MATRIX.md) | Another vendor stack plus Pinecone, Supabase, Telegram, Obsidian and execution swarms | Strong sign of unrelated scope contamination. Establish whether tool-executing swarms belong to Amorien; otherwise archive these sections. |
| [27-MVP-CLOUDFLARE-NSFW-PLAN.md](C:/Users/mehya/ai-mate/docs/27-MVP-CLOUDFLARE-NSFW-PLAN.md) | Cloudflare control plane and RunPod inference, ending with an “executive lock” | Convert to a proposed ADR, resolve changed cost assumptions, streaming design and model licensing. |
| [28-COMPETITOR-LOGIC-FAULTS-AND-AMORIEN-FIX.md](C:/Users/mehya/ai-mate/docs/28-COMPETITOR-LOGIC-FAULTS-AND-AMORIEN-FIX.md) | Competitive attacks and migration campaigns grounded in a low-cost edge claim | Retire unsupported backend diagnoses, insulting labels and 38-hour margin claim. Evaluate import feasibility and user rights concretely. |
| [29-INFRASTRUCTURE-SETUP-RUNBOOK.md](C:/Users/mehya/ai-mate/docs/29-INFRASTRUCTURE-SETUP-RUNBOOK.md) | Manual DNS migration, Cloudflare configuration and three RunPod endpoints | Incomplete provisioning outline. Supply code, container images, schemas, binding config, dry-run checks, rollback and spending limits before calling it runnable. |
| [30-PWA-IOS-AND-PAYMENTS.md](C:/Users/mehya/ai-mate/docs/30-PWA-IOS-AND-PAYMENTS.md) | PWA-first decision, conditional merchant acceptance, secure billing and native limits | Most useful current decision document. Link prominently and propagate its corrections through requirements and roadmap. |
| [ai_companion_consensus.md](C:/Users/mehya/ai-mate/docs/ai_companion_consensus.md) | Call-first UX, implicit persona calibration, ambient presence and $15 premium | Research brainstorm. Conflicts with consent/onboarding and metered economics. Preserve only testable UX hypotheses. |
| [AI_Companion_Master_Formula.md](C:/Users/mehya/ai-mate/docs/AI_Companion_Master_Formula.md) | Synthesis of native audio, local splat rendering and edge compute | Research proposal, not established architecture. Identify actual artifacts needed for every claimed component. |
| [audio_pipeline_consensus.md](C:/Users/mehya/ai-mate/docs/audio_pipeline_consensus.md) | Simulated expert debate favoring custom large-model full-duplex audio | Archive as simulation. No benchmark, trained model or endpoint establishes the result. |
| [august_2026_financials_and_models.md](C:/Users/mehya/ai-mate/docs/august_2026_financials_and_models.md) | Brief live-video model shortlist and $99/300-minute proposal | Historical assumptions. Verify exact model/endpoint identities and distinguish compute contribution from net profit. |
| [infrastructure_consensus_2026.md](C:/Users/mehya/ai-mate/docs/infrastructure_consensus_2026.md) | Edge enclaves, local NPUs and global 70–90ms architecture | Speculative R&D. No deployment artifact or measurements justify its global guarantee. |
| [realtime_visuals_consensus.md](C:/Users/mehya/ai-mate/docs/realtime_visuals_consensus.md) | Audio-driven local Gaussian splat animation to reduce video bandwidth | Potential research direction; requires asset-generation, deformation model, device coverage and A/V measurements. Smooth local frames do not prove zero response latency. |

There is no document 21. A numbering gap is harmless by itself, but together with duplicated “master” documents and missing indexes it makes the evolution difficult to follow.

**Documentation integrity and repository structure**

The ordinary local Markdown file links checked in the original files resolved. The more important broken references are paths mentioned in prose: `scripts/fetch-vendor-pricing.sh`, `docs/research/`, `docs/vendors/`, `packages/core`, and `wrangler.toml` do not exist. Planned application directories are acceptable in a pre-code design, but a claim that raw captures are preserved or a deployment command is ready needs its referenced artifact.

At review time [.env.example](C:/Users/mehya/ai-mate/.env.example) and documents 17–20 and 22–29 are untracked. They exist locally and were reviewed, but they are not in the current commit. Someone cloning the committed repository receives a different set of decisions. Do not silently lose or automatically commit them; classify and review them first.

I would use the following small structure, adding implementation directories only as code is created:

```text
README.md                    current status, how to run, canonical reading order
docs/
  current/                   product scope, architecture, memory, safety, economics
  decisions/                 dated ADRs with supersedes/superseded-by
  research/                  source-backed vendor and competitor observations
  experiments/               benchmark protocols and result files
  runbooks/                  tested setup, deployment, backup and incident steps
  archive/                   prior proposals and simulated debates
examples/                    clearly named mock demonstrations
scripts/                     reproducible validation and maintenance utilities
```

Each active decision should carry status, owner, date, evidence and supersession metadata. “Proposed,” “accepted,” “implemented,” and “verified” need different meanings. Simulated expert agreement belongs in research notes; it is not independent external validation.

Use one source for each repeated concept: tier definitions, character schema, prompt layers, price/allowance data and provider routes. Generate tables or validate them from that source rather than copying them into five documents. A small CI check for links, missing referenced artifacts, example configuration drift and cost-model regression would provide more value now than another strategy essay.

**What I would do next, in order**

1. Establish a current decision page. Preserve document 30's PWA-first scope; explicitly choose which earlier content policy and architecture rules remain active. Archive competing proposals with links instead of deleting their history.
2. Rebuild the economics and model-rights inventory. Reject allowances that fail under full consumption, and mark every uncertain vendor/model claim as unverified until supported.
3. Build a narrow text-and-memory slice: one preset character, authentication, persisted conversation, temporal facts with provenance, corrections, deletion and policy checks. This validates the strongest differentiator without waiting for all media features.
4. In a bounded technical experiment, demonstrate one real voice call and one avatar. Record actual inputs, audio, video and measured latency/cost. Test cold starts, interruptions and provider failure. Do not treat a placeholder MP4 URL as evidence.
5. Add transactional metering and verified payment sandbox events before a paid pilot. Include concurrent usage, duplicate webhooks, cancellation, refunds and entitlement revocation tests.
6. Run a small consented pilot with a well-defined target segment. Compare user-perceived memory and call quality against a real baseline; collect short-horizon retention and qualitative feedback before making long-horizon claims.

The best first milestone is simple: a user tells the companion a fact, comes back later, receives a relevant recollection, corrects it, and sees that correction respected across text and a real voice call. The user can delete the memory and verify that it stops influencing responses. Record what that experience costs. That would convert the strongest parts of this dossier into evidence for a product.
