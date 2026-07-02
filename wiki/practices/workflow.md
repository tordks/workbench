---
type: practice
title: The Workflow
aliases: [workflow]
tags: [workflow]
created: 2026-07-02
updated: 2026-07-02
status: draft
related: ["[[python-project]]", "[[react-vite-project]]"]
---

# The Workflow

> **status: draft** — this is a first pass to correct, not gospel. Edit it until it matches reality.

The path most work travels, from idea to shipped code. The named steps are skills. Some are local to
this vault; the rest are mattpocock skills, installed via `npx skills@latest add mattpocock/skills`.
The mattpocock skills span categories — most steps are `engineering/`, but `grill-me` and `handoff`
are `productivity/`.

## Setup (once per repo)
`setup-matt-pocock-skills` scaffolds the generic per-repo config; `setup-skills` then converges the
convention docs to this workflow's. Run both once after the skills are installed, before the flow
below.

## Idea → ship

1. **Sharpen the idea** — `grill-with-docs` (also writes ADRs + glossary via `domain-modeling`) or
   `grill-me` (the plain interview, no docs). Both run a relentless `grilling` session: interview
   until the plan holds together, settling every question you can in conversation. When the reading
   legwork is heavy, `research` runs it in a background agent while you keep going.
2. **Detour to prototype** — `prototype` when a question needs a runnable answer (state, business
   logic, a UI you have to see): a throwaway build that settles the question, then is discarded.
3. **Split the work:**
   - Multi-session build → `to-prd` (synthesize the conversation into a PRD) → `to-issues`
     (slice the PRD into independently grabbable issues).
   - Single session → go straight to implementation.
4. **Pick what's next** — `backlog` presents the open issues in dependency order (ready / blocked /
   underspecified) so you choose the next unit. It reads, never writes.
5. **Build** — `orchestrate` for multi-unit work (delegate each unit to a subagent running
   `implement`, review, commit per unit); or `implement` directly for a single unit. `implement`
   builds test-first via `tdd` (red-green-refactor), against `codebase-design` — deep modules,
   clean seams.
6. **Review** — `code-review` (standards + spec) + `review-docs` (docstrings/comments/prose).

## Bridging context
- `handoff` — compact the current conversation into a document a fresh agent picks up. It cross-cuts
  the whole flow: carry context into a prototype detour and the finding back, pass a grilling session
  to the next, or park a concept to investigate later.

## Other entry points
Ways in when you're not starting from a fresh idea:
- A hard bug or performance problem → `diagnosing-bugs` (build a tight, red-capable repro loop
  before theorising, then hypothesise → fix → regression-test).
- An incoming request or issue → `triage` (categorise, verify, grill if needed, and write an
  agent-ready brief that `implement` can pick up).

## Maintenance
- Architectural drift or identify codebase improvements → `improve-codebase-architecture` (scan the codebase, surface fixes).
- Merge/rebase conflicts → `resolving-merge-conflicts` (trace each side to its primary source, then reconcile intent).
- Durable learnings → `wiki-capture` parks them to the wiki `inbox/` mid-task; `wiki-ingest` later
  folds the inbox (and named sources) into atomic pages, so the next project starts further ahead.
  `wiki-query` reads the wiki; `wiki-lint` audits it. All four reach the vault via the Obsidian CLI.
