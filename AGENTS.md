# AGENTS.md — Repository Operating Contract

These are AI-mate's repository-specific working instructions. Use native Hermes profiles and tools for coordination.

Follow the assigned native Hermes profile for role ownership, concise communication and model fallbacks. Repository requirements and user instructions remain authoritative.

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

Use the active Hermes profile configuration and its native fallback_providers. Do not use a repository router or hard-coded provider entitlement claims. Preserve task context before handoff. If a fallback cannot meet the task capability, collect evidence or pause that decision rather than waive acceptance criteria. Keep credentials and private data out of artifacts.

## Hermes and OpenCode division

Hermes owns intent, gate state, routing, budget, decomposition, and final synthesis. OpenCode creates bounded workers in isolated worktrees and returns commits/results. GitHub and CI enforce the policy. No worker is allowed to reinterpret a product decision or widen its scope.

## Native project coordination

Hot Zero coordinates sustained work through the existing native project and board `ai-mate-a2f6103`. Discuss ideas in native Bot Mode rooms; create or assign tasks when scope is agreed. Use native Kanban tools; no registration script, duplicate board, mandatory G0-G6 template or custom router is required. Each committed task has an owner, scope, acceptance criteria and evidence.

The existing `.factory/PROJECT_STATE.md`, handoffs and gate records are historical project evidence, not an orchestration engine. Preserve and consult relevant decisions; use current profile configuration for routing. New project documentation belongs under docs/.

## Stop and escalate

Stop on an ambiguous requirement, unsupported factual claim, missing source, secret exposure, unexpected schema/auth/tenant change, repeated identical failure, unresolved high-severity security finding, or a requested action outside the packet. Escalate production, payments, credential changes, public messages, legal claims, and destructive migrations to the designated human gate.
