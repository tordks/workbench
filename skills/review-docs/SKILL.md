---
name: review-docs
description: Review documentation for document discipline — docstrings, comments, and prose (markdown, ADRs, README). Runs the review in a subagent and flags meta-commentary, restated facts that widen blast radius, docstrings that stray outside their own unit, and staleness. Use when the user wants to review the docs of a change (a diff), or to audit the docs of named files or the whole repo out of band. Separate from code review, so it runs on its own.
---

Review **documentation** — docstrings, inline comments, and prose (`*.md`, ADRs, `README`) — for document discipline. Deliberately separate from a correctness or spec review: launch it on its own after a docs-only edit, alongside a code review, or as a standalone audit.

**The review runs entirely in a `general-purpose` subagent.** The parent's only job is to pick the target (below) and spawn the subagent with it; everything from *Harvest* down is the subagent's brief, so neither the harvest bundle nor the source tree ever reaches the parent's context. The parent aggregates only the findings that come back.

## Target — parent picks

Choose by what the user asks for:

- **Diff** *(default)* — the documentation touched by a change: the working diff (`git diff HEAD`), or a range the user names. Scoped to what changed.
- **Scan** — the documentation in files or paths the user names, or a whole subtree, with no diff. An out-of-implementation audit that catches discipline the diff never surfaced.

Spawn one subagent with the target — the diff command, or the set of **paths** to Scan — plus the brief below. For a Scan spanning many files, split the paths across subagents in parallel and aggregate only their findings. Review only docs either way.

---

The sections below are the **subagent's brief**. It runs them; the parent does not.

## Harvest — Scan only

A whole-repo Scan must not read entire source files into review context; most of each file is code the review ignores. Extract just the documentation first:

- **Python** — run `python harvest_docs.py <path> ...` (in this skill's folder). It emits every docstring with its `file:line` and the signature it attaches to — what Rules 3–4 judge against — plus every comment, in source order.
- **Prose** (`*.md`, ADRs) — already documentation; read it directly.

Review that compact bundle and open full source only for a unit whose docstring you suspect — to confirm staleness or collaborator-narration — never wholesale. (Diff mode skips this: the diff is already scoped and small.)

## Rules

Flag every place the docs break one of these, and anything that departs from the documentation conventions already in force in the repo:

1. **No meta-commentary.** Docs say what something does, and why a non-obvious decision holds — never issue or task IDs, PR or session narrative, or "why this change was made." That context belongs in the tracker, not in files that outlive the work.

2. **Single source of truth — minimize blast radius.** Each fact has one home; everywhere else refers to it by stable name, not by number or position. Flag a fact restated where it can drift from its source, and an unstable identifier (an ADR number, a line or position) cited away from the place that owns it.

3. **Docstrings stay in their own unit.** A docstring describes only its unit's contract — purpose, parameters, return, invariants, and the non-obvious *why*. It does not narrate a collaborator, caller, or downstream module. Favour *why* over *what*; the code and types already state the *what*.

4. **No staleness.** A docstring or comment must still match the code it describes.

## Report

List findings, each naming the rule it breaks with the offending line quoted. Separate hard violations from judgement calls. End with a one-line count and the worst issue.
