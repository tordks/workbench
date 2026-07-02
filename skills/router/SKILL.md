---
name: router
description: Ask which skill fits your situation. A router over this repo's own skills, with pointers to the upstream engineering skills for everything else.
disable-model-invocation: true
---

# router

You don't remember every skill, so ask. This routes over **your own** skills — the ones unique to
this repo. Everything else comes from the upstream engineering skills (Matt Pocock's set); this file
points there rather than restating them.

## Your own skills

- **`wiki-maintain`** — maintain the knowledge wiki (`wiki/`). Reach for it to **ingest** a source
  into the wiki, **query** the wiki, or **lint** it for decay (orphans, contradictions, stale
  claims, broken links). Rules live in `wiki/_schema.md`.
- **`orchestrate`** — deliver a multi-unit piece of work by delegating each unit's implementation to
  a subagent (scout context → per-unit TDD subagent → review → commit per unit). Reach for it when a
  task splits into several independent units and you want them built in parallel with gating.
- **`review-docs`** — review the *documentation* of a change (docstrings, comments, prose) in a
  subagent, flagging meta-commentary and blast-radius violations. Separate from code review.

## Everything else → upstream skills

For idea → ship (`grill-me` / `grill-with-docs` → `to-prd` → `to-issues` → `implement`),
`prototype`, `tdd`, `triage`, `teach`, `handoff`, `codebase-design`, `domain-modeling`,
`diagnosing-bugs`, `resolving-merge-conflicts`, and the rest — use the upstream engineering skills.
Install/update them with:

```
npx skills@latest add mattpocock/skills
```

Do not fork those here. This repo only owns the three skills above; keeping the rest upstream means
they stay current instead of drifting into stale copies.
