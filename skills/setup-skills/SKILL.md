---
name: setup-skills
description: Converge a repo's convention docs to mine — the counterpart to the upstream engineering-skills setup, for my conventions. Docs only; run once per repo after the skills are installed.
disable-model-invocation: true
---

# setup-skills

Converge the repo's agent docs to my conventions — the counterpart to `setup-matt-pocock-skills`, but
for *my* conventions. It writes docs only. It never installs or checks
skills: installation already happened through `npx skills`, and `setup-matt-pocock-skills` has already
scaffolded the generic per-repo config it converges.

**Converge** means target the docs' desired end state, not a diff: re-running lands the same text
rather than stacking edits, so it survives upstream version bumps and is always safe to re-run.

One repo doc converges per **convention** — each is a self-contained file in
[`conventions/`](conventions/) that carries its own explainer, target doc, and desired end state.
Adding a convention later is dropping a new file there; the process below picks it up unchanged.
Today there is one: issue dependencies.

## Edit the vendored docs in place

Converge by editing the `docs/agents/*.md` the upstream setup wrote **directly** — never by layering a
`CLAUDE.md` override on top. The consuming skills (`to-issues`, `triage`, …) already point at these
vendored docs as *the* convention; a `CLAUDE.md` note saying something different doesn't replace them,
it just adds a second, contradicting source the agent must reconcile. Keep one coherent source: fix the
doc the skills already read. Every convention below applies through this same principle.

## Process

### 1. Explore
Read the current state before changing anything: the `docs/agents/*.md` the upstream setup wrote, the
`## Agent skills` section of `CLAUDE.md`, and each file in [`conventions/`](conventions/). If the
upstream docs are absent, stop and ask the user to run `setup-matt-pocock-skills` first — this skill
converges those docs; it does not create them from scratch.

### 2. Present and ask, one convention at a time
For each convention in `conventions/`, use its explainer to walk the user through the choice it
governs — present one, get the answer, then move to the next; don't dump them all at once. Assume the
user doesn't know the terms; lead with the short why from the convention file.

### 3. Confirm the edits
Show a draft of each vendored-doc change before writing it. Let the user edit first.

### 4. Converge
Edit each target vendored doc to the end state its convention file specifies. Update in place; leave
surrounding sections the user may have edited untouched. Done when every convention in `conventions/`
is reflected in the repo's `docs/agents/*.md` and the `## Agent Skills` section in `CLAUDE.md`.

### 5. Report
Per convention, summarise what converged and what already matched, plus any follow-up its file calls
for.
