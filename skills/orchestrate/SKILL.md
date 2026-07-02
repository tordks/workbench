---
name: orchestrate
description: "Drive a set of issues or a PRD to done as an orchestrator: scout context, delegate each unit's TDD to a subagent, review, and commit per unit."
disable-model-invocation: true
---

You are the **orchestrator**. You don't write the implementation — you scout context, hand each **unit** of work to a subagent, review what comes back, and commit. One unit at a time.

The user names the work (issues, a PRD, a list) and may pass paths to the repo's docs. Forward those docs to the subagents and to `/review`.

## 1. Resolve the units

Turn the request into an ordered list of **units** — commit-sized pieces (one issue = one unit; a PRD splits into its slices). Each runs the cycle below in full before the next begins. Done when the list is stated and ordered.

## 2. Scout

Launch **Explore** agents (to yourself, in parallel) to clear the fog — *they* read the repo so you don't. Stay light: you collect **pointers** (paths), they read the contents. Reused across units:

- The repo's **process docs** a contributor must obey — engineering principles, coding standards, contributing/domain docs.
- Per unit: paths to the exact files, interfaces, and tests it touches.

Done when, for every unit, you hold a **tight file list** and the doc paths its subagent must read — enough that the subagent never discovers the repo itself. Reading those files is the subagent's job — open one yourself only when its contents change *how* you delegate. If reading it wouldn't change the delegation, leave it for the subagent.

## 3. Delegate

Spawn **one subagent** (model: sonnet) per unit to build it. Its prompt must tell it to:

- Maintain a **tasklist** for the unit: break the work into tasks up front, keep exactly one in-progress, and mark each done as it lands — so its progress is legible without you interrupting.
- Run the `/implement` skill and follow it.
- Read first, before any code: the process docs and the scoped file list from step 2.
- Implement only this unit; **don't commit** — leave the tree dirty for review.
- **Gate its own changes before reporting**: typecheck, lint/format, and run this unit's tests — all green and clean. This gating is the subagent's job, not yours; you won't re-run it.

Done when the subagent reports its tests green and typecheck/lint clean.

## 4. Verify

**Trust the subagent's report — don't re-run its checks.** The subagent already gated its own work in step 3; re-running the same typecheck and tests here is wasted effort. Confirm the report says this unit's tests are green and typecheck/lint clean. If the report is missing, ambiguous, or says it couldn't finish, send the subagent back with what's unresolved — you don't run or fix it yourself. Done when the report is green across the board. (Cross-unit regressions wait for the full-suite run at step 7.)

## 5. Review

Run `/review` on this unit's changes against the last commit, passing the docs from step 2, and `/review-docs` alongside it for document discipline — the two are independent axes. **Wait for all reviews to return**, then triage their findings together: each is a real defect, spec gap, or docs violation to fix, or a judgement call you decide and note. Hand the *whole* set of blocking findings to a **single** fix subagent (model: sonnet) so it fixes them in one pass — never launch a fixer before every review is in, or a later review's findings collide with an edit already underway. You don't fix anything yourself. The fix subagent's prompt carries the context it needs to act without rediscovering the unit: every finding, the process docs and file list from step 2, and the failing change.

It must **re-gate its own changes** (typecheck, lint, this unit's tests) green before reporting — same as step 3, so you don't re-run them. Done when every blocking finding is resolved or explicitly waived.

## 6. Commit

Commit this unit to the current branch, message following the repo's convention. Then return to step 3 for the next unit. Done when no units remain.

## 7. Close out

Run the full test suite once, plus the typecheck — as a cross-unit regression net. This is the **only** place you run checks yourself; per-unit typecheck/lint/tests were already gated inside each subagent, so don't repeat them per unit. Report: units shipped, one commit each, and any waived findings.
