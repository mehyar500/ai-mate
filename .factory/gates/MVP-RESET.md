# Reset verification

Scope: documentation and offline tooling only. No live inference, deployment, payments or age verification was run.

Verified 2026-09-07 local date:

- `python -m unittest discover -s tests -v`: 12 passed, including repeated-context billing, media units, idle-GPU losses, failed clips, reserve/cash separation, free-account verification, changed assumptions, Chaturbate buyer/payout separation and prevention of JSON overwriting the pricing document.
- `python -m compileall -q scripts tests`: passed.
- `python scripts/economics.py --write`: generated document matches configuration exactly.
- `python scripts/snapshot_cloudflare.py`: 86 unique classified entries, 18 deprecated; no video-generation output task. Public requests only.
- Local Markdown-link audit: all 16 reviewed Markdown files have valid local file targets. All selected Cloudflare environment model IDs exist in the snapshot. Template has 48 setting names and no credentials.
- `git diff --check`: passed; Git's LF/CRLF notices are informational.
- Product documentation reduced from 36 files / 49,554 words to 7 files / 4,684 words (90.5% fewer words), excluding reference JSON and agent operating records.

Independent reviewer `reset_review` reproduced the arithmetic and verified official Chaturbate rate qualifications. Its three initial findings—stale duplicate-worker README, hardcoded generated prose, and unbudgeted adult-text availability—were fixed and re-reviewed without remaining blockers. Its final CLI flag safeguard was also implemented and regression-tested. Research reviewers corrected RunPod eligibility, model licenses, processor fees and US verification assumptions.

Baseline local call scenario: $0.05177875/minute, $1.55/30 minutes, $3.11/60 minutes. These are unbenchmarked assumptions, not actual performance or a provider quote. Original model/hosting/pricing claims are retired, not silently treated as proven.

The founder explicitly requested direct publication to main. Source checkout and remote were verified at the task source commit before applying the reviewed reset. This record is included in the resulting main commit; the final commit hash is reported in the completion message.

Remaining gates: applicable GPU and email agreements, CCBill underwriting/fees, reviewed US state allowlist and verification configuration, exact model artifact/license manifest, measured call/clip results, and independent cross-provider R2 implementation review. Founder/engineer/reviewer own these respectively; adult and paid features remain disabled until resolved.
