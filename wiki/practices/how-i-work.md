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

The path most work travels, from idea to shipped code. The named steps are skills (see the
`router` skill; upstream ones install via `npx skills@latest add mattpocock/skills`).

## Idea → ship

1. **Sharpen the idea** — `grill-with-docs` (with a codebase) or `grill-me` (without). Interview
   until the plan holds together; settle every question you can in conversation.
2. **Detour to prototype** when a question needs a runnable answer (state, business logic, a UI you
   have to see). Bridge with `handoff` out and back.
3. **Split the work:**
   - Multi-session build → `to-prd` → `to-issues` (independently grabbable issues).
   - Single session → go straight to implementation.
4. **Pick what's next** — `backlog` presents the open issues in dependency order (ready / blocked /
   underspecified) so you choose the next unit. It reads, never writes.
5. **Build** — `orchestrate` for multi-unit work (delegate each unit's TDD to a subagent, review,
   commit per unit); or `implement` for a single unit.
6. **Review** — `review` (code) + `review-docs` (docstrings/comments/prose).

## On-ramps
- Bugs / incoming requests → `triage` → produces agent-ready issues that `implement` picks up.

## Knowledge
- Durable learnings from any of the above get folded into this vault via `wiki-maintain` (ingest),
  so the next project starts further ahead.
