# AGENTS.md — Repository Operating Contract

This file is copied into each SaaS repository and then completed with repository-specific facts. The project-specific file outranks a role's general preferences.

Every role also follows [.agents/contracts/agent-operating-system.md](.agents/contracts/agent-operating-system.md). It supplies the shared heavy-reasoning loop, model capability floor, typed handoffs, spawn policy, coding discipline, skill factory, and project/Kanban invariant. A role file adds specialist authority; it cannot weaken this contract.

## Instruction order

Human instructions and approval policy come first, followed by accepted specifications and ADRs, this repository contract, the assigned role contract, and the task packet. Lower layers cannot override a higher layer.

## Repository facts

- Current stack: Markdown, JSON and Python 3.11+ standard library; no package manager required.
- Install: none for offline tools.
- Format/lint: `git diff --check`; no configured formatter.
- Build: none for docs; `python -m compileall -q scripts tests` checks Python syntax.
- Unit checks: `python -m unittest discover -s tests -v`.
- Local services: none. Live inference/integration/E2E checks are not implemented.
- Staging: not provisioned. Documentation rollback uses a reviewed revert commit.
- Owner/escalation: founder in this project conversation and GitHub issue #1.

Do not invent commands. If a command is unknown, stop and ask the integration lead to confirm it.

## Worktree and Git rules

Every task has one issue, branch, and isolated worktree pinned to a source commit. Record allowed paths in the task packet. Do not share a mutable directory between workers. Never write directly to protected `main`, force push, merge your own PR, or edit outside the assigned scope.

A PR must name requirement IDs, risk class, source commit, migration/rollback implications, observability changes, screenshots or API examples where relevant, checks run, known risks, and the independent reviewer.

## Risk classes

- **R0:** documentation or trivial copy.
- **R1:** normal code without sensitive boundaries.
- **R2:** authentication, billing, PII, tenancy, migrations, external communication, AI tool execution, or security controls.
- **R3:** production access, secrets, regulated data, legal commitments, destructive or irreversible actions.

Agents cannot lower a risk class. R2 requires independent security and correctness review plus staging evidence. R3 requires a human decision immediately before the irreversible step.

## Definition of done

A task is complete only when:

- Acceptance criteria are linked to code, tests, or a documented reason.
- The result packet lists the exact files/commit and commands with outcomes.
- Negative, empty, error, permission, cancellation, and recovery behavior is covered where relevant.
- Security, accessibility, performance, migration, and data handling implications are recorded.
- Documentation and telemetry are updated when behavior changes.
- Required CI and independent review are green.
- Remaining risks and uncertainties have owners, due dates, or an explicit decision to stop.

“Done” in chat has no authority without this evidence.

## Model and data routing

Use logical routes from `.factory/routing.yaml`, not provider names in permanent role prompts. Before a route is used, record actual provider/model, quota/health result, reasoning level, context bundle version, and source commit.

The default route is direct Codex OAuth, `gpt-5.6-terra`, Hermes reasoning medium. The first fallback is a healthy, verified Claude reasoning route through OmniRoute. Hephaestus Frontier Builder uses this frontier pool for difficult code and high-risk vertical slices; Forgehand Builder and Minimax Steward are reserved for bounded work after the contract is accepted. An author and reviewer should use different provider families for consequential changes.

Use [.factory/routing.yaml](.factory/routing.yaml) for current route candidates; no external pool is claimed verified. Every discovered model may be selected explicitly after its probes pass; unclassified catalog rows are probationary and never a silent fallback. The UI/UX studio uses Ariadne UX, Vitruvius Experience, Mies Interface, Lumen Design, Vesalius Accessibility, and Raphael Motion with visual Gemini/Claude routes and independent accessibility review.

Send the minimum context required. Redact secrets, tokens, direct identifiers, customer records, and production data. Check provider data-handling terms before sending sensitive material. The inventory marks Cursor Fable as NO ZDR; keep data-sensitive work on approved routes unless a human explicitly accepts the policy.

## Hermes and OpenCode division

Hermes owns intent, gate state, routing, budget, decomposition, and final synthesis. OpenCode creates bounded workers in isolated worktrees and returns commits/results. GitHub and CI enforce the policy. No worker is allowed to reinterpret a product decision or widen its scope.

## Project intake invariant

The Conductor first reads the persistent founder profile and obtains the minimum
project facts. Casual support and the one-time founder interview remain outside
Kanban. Before assigning any worker in a sustained venture, new folder, or
cloned repository, run `scripts/register-project-kanban.ps1` from the default
Hermes Foundry home. The script calls native `hermes project` and
`hermes kanban`; it creates or reuses the project and bound board and adds G0–G6
starter cards with named role owners. If registration fails, record
`.factory/INTAKE_BLOCKED.md` and stop assignment until the same command
succeeds. This rule applies to Hermes, OpenCode, and any future agent adapter.

## Required project structure

```text
SOUL.md
AGENTS.md
.agents/roles/
.agents/contracts/
.agents/gates/
.factory/PROJECT_STATE.md
.factory/routing.yaml
.factory/gates/
.factory/handoffs/
docs/research/
docs/product/
docs/design/
docs/architecture/
docs/trust/
docs/operations/
```

## Stop and escalate

Stop on an ambiguous requirement, unsupported factual claim, missing source, secret exposure, unexpected schema/auth/tenant change, repeated identical failure, unresolved high-severity security finding, or a requested action outside the packet. Escalate production, payments, credential changes, public messages, legal claims, and destructive migrations to the designated human gate.
