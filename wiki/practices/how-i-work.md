---
type: practice
title: How I Work
aliases: [workflow, how-i-work]
tags: [workflow]
created: 2026-07-02
updated: 2026-07-02
status: draft
related: ["[[python-project]]", "[[react-vite-project]]"]
---

# How I Work

> **status: draft** — this is a first pass to correct, not gospel. Edit it until it matches reality.

The path most work travels, from idea to shipped code. The named steps are skills. Local ones live
in this vault; upstream ones install via `npx skills@latest add mattpocock/skills` (use `ask-matt`
if you're unsure which fits).

## Idea → ship

1. **Sharpen the idea** — `grill-with-docs` (with a codebase) or `grill-me` (without). Interview
   until the plan holds together; settle every question you can in conversation. `domain-modeling`
   fires within, pinning down terms and ADRs as they surface.
2. **Detour to prototype** — `prototype` when a question needs a runnable answer (state, business
   logic, a UI you have to see): a throwaway build that settles the question, then is discarded.
   `handoff` bridges context out to the prototype and the finding back.
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

## On-ramps
- Bugs → `diagnosing-bugs` (hard bug / perf loop) or `triage` (incoming request → agent-ready issue
  that `implement` picks up).

## Maintenance
- Architectural drift → `improve-codebase-architecture` (scan the codebase, surface fixes).
- Durable learnings → `wiki-maintain` (ingest), so the next project starts further ahead.
