---
name: setup-skills
description: Converge a repo's convention docs to this workflow's — the counterpart to `setup-matt-pocock-skills`. Docs only; run once per repo after the skills are installed.
disable-model-invocation: true
---

# setup-skills

Converge the repo's agent docs to this workflow's conventions — the counterpart to
`setup-matt-pocock-skills`, but for *these* conventions. It writes docs only. It never installs or checks
skills: installation already happened through `npx skills`, and `setup-matt-pocock-skills` has already
scaffolded the generic per-repo config it converges.

**Converge** means target the docs' desired end state, not a diff: re-running lands the same text
rather than stacking edits, so it survives upgrades to the mattpocock skills and is always safe to re-run.

Each **convention** is a self-contained file in [`conventions/`](conventions/). They come in two
kinds. Most are **content conventions** — the actual rules, stated plainly with no mention of any
skill or of this setup: coding standards, documentation, testing, commits. One is a **routing
convention** — issue dependencies — which records *where* a fact lives rather than a rule, so it reads
as an explainer. Adding a convention later is dropping a new file in `conventions/`; the process below
picks it up unchanged.

The wiring — each convention's target doc and the skills that read it — lives **here**, never in the
convention files (that keeps them portable, pure rule-text). A content convention converges a new
vendored `docs/agents/*.md` that `setup-matt-pocock-skills` doesn't scaffold; the routing convention
edits a doc it does scaffold, in place.

| Convention file | Vendored target | Read by |
|---|---|---|
| `coding-standards.md` | `docs/agents/coding-standards.md` | code-review, implement, tdd |
| `doc-conventions.md` | `docs/agents/doc-conventions.md` | review-docs, code-review |
| `testing-conventions.md` | `docs/agents/testing-conventions.md` | tdd, implement |
| `commit-conventions.md` | `docs/agents/commit-conventions.md` | orchestrate |
| `issue-dependencies.md` | `docs/agents/issue-tracker.md` (in place) | backlog |

## Edit the vendored docs in place

Converge by writing the `docs/agents/*.md` **directly** — never by layering a `CLAUDE.md` override on
top of it. The consuming skills point at these vendored docs as *the* convention; a `CLAUDE.md` note
saying something different doesn't replace them, it just adds a second, contradicting source the agent
must reconcile. Keep one coherent source: the doc the skills read. Every convention applies through
this same principle.

## Input modes — how each convention is answered

For every convention, the user picks one mode. The convention file supplies the default rule-text;
this list is the shared machinery:

- **Skip** — no doc. Skills fall back to their built-ins plus the repo's config. The convention gets
  no row in the `## Conventions` table.
- **Accept the shipped default** — stamp the convention file's rule-text into the vendored doc. The
  convention file is the single source of truth; because this skill *converges*, re-running re-stamps
  from that same file, so the copy in the repo can't silently drift from it.
- **Point at a doc** — the vendored doc points to an existing repo doc (e.g. `docs/principles.md`).
- **Free text** — the repo-specific rules, written inline.

Once a repo diverges (point-at-doc or free text), that becomes the repo's own source and later runs
leave it untouched — convergence only re-stamps a doc still on the shipped default. Mechanical rules
already encoded in the repo's linter/formatter config are never stamped; the convention files defer to
that config rather than restating it.

## The `## Conventions` table in `CLAUDE.md`

Progressive disclosure: the vendored docs are the detail layer, read on demand; a compact
`## Conventions` table in `CLAUDE.md` is the always-present index that routes to them. Fill one row
per *configured* convention, taking its `Doc` and `Read by` from the wiring table above; a skipped
convention has no row, so the table doubles as the "what's in force" manifest. Own **only** the four
new conventions here; leave the `## Agent skills` block that `setup-matt-pocock-skills` wrote
(issue-tracker / triage-labels / domain) as its own index so there aren't two competing maps.

The orchestrator reads this table and injects the in-force docs into each subagent; a skill used
directly finds them through the same table. The shape:

```markdown
## Conventions

Where this repo's conventions live. Skills read the relevant doc on demand; the orchestrator injects
them into each subagent. No row = not configured (skills use built-ins + config).

| Convention | Doc | Read by |
|---|---|---|
| … one row per configured content convention, from the wiring table above … |
```

## Process

### 1. Explore
Read the current state before changing anything: the `docs/agents/*.md` that `setup-matt-pocock-skills`
wrote, the `## Agent skills` section of `CLAUDE.md`, and each file in [`conventions/`](conventions/).
If those docs are absent, stop and ask the user to run `setup-matt-pocock-skills` first — this skill
converges those docs; it does not create them from scratch.

### 2. Present and ask, one convention at a time
For each convention in `conventions/`, summarise what it covers — for a content convention, the gist
of its rule-text; for the routing convention, the choice its explainer governs — then offer the four
input modes (skip / accept the default / point at a doc / free text). Present one convention, get the
answer, then move to the next; don't dump them all at once. Assume the user doesn't know the terms.

### 3. Confirm the edits
Show a draft of each vendored-doc change before writing it. Let the user edit first.

### 4. Converge
Edit each target vendored doc to the end state its convention file and the chosen mode specify.
Update in place; leave surrounding sections the user may have edited untouched. Then converge the
`## Conventions` table. Done when every convention in `conventions/` is reflected in the repo's
`docs/agents/*.md` and the table matches what's configured.

### 5. Report
Per convention, summarise what converged and what already matched, plus any follow-up its file calls
for.
