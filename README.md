# workbench

An opinionated engineering setup and workflow. Two halves that fit together:

- a **karpathy-style LLM wiki** (`wiki/`)
- the **skills** (`skills/`) unique to this workflow


## Quickstart

```
# Install the skills — the general engineering set, then this repo's workflow skills on top
npx skills@latest add mattpocock/skills     # select all the default skills
npx skills@latest add tordks/workbench

# Per repo, once — set up the general conventions, then converge to these on top
/setup-matt-pocock-skills
/setup-skills

# To edit the wiki: open `wiki/` (not the repo root) as an Obsidian vault, then `pre-commit install`
```


## The workflow

The path most work travels, from idea to shipped code. Each named step is a skill. Some defined in
this repo and some from the matt pocock skills. At a glance the steps are:

1. **Sharpen the idea** — interview until the plan/spec holds together; prototype when a question needs a runnable answer.
2. **Split the work** — a multi-session build becomes a PRD, then independently grabbable issues; a single session goes straight to implementation.
3. **Pick what's next** — `/backlog` presents the open issues in dependency order.
4. **Build** — `/orchestrate` delegates each unit to a subagent sequentially, or you implement a single unit directly with `/implement`.
5. **Review** — `/code-review` for code against standards and spec, `/review-docs` for docstrings/comments/prose. Run automatically after each unit by `/orchestrate`
6. **Bank the learnings** — `/wiki-capture` parks durable findings to the wiki inbox; `/wiki-ingest`
   folds them into the wiki.

For the full sett of skills and how to use them see [`workflow`](wiki/practices/workflow.md).


## The wiki

A [karpathy-style LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): a
knowledge base **written and read mainly by agents**, so durable learnings from one project carry
into the next. It has three layers — immutable **raw sources** (`sources/`), an agent-owned
**synthesized wiki**, and a **schema doc** (`wiki/_schema.md`) that teaches an agent how to maintain
it — plus an `inbox/` staging lane for raw captures. The agent works it through four operations, one
skill each: **capture** (`inbox/`), **query**, **ingest**, **lint**. Step 6 of the workflow captures
and ingests into it; later work queries it.

**The tooling is still in progress on both sides.** The `wiki-*` skills the agent uses to read and
edit the wiki reach the vault through the **Obsidian CLI** (so they run wherever the agent runs, and
depend on Obsidian being available); they are unreviewed and unfinished, and the human-facing side is
thin: for now you can open the `wiki/` folder as an Obsidian vault to read and hand-edit it; a minimal
`.obsidian/` config is committed.

Two lint tiers guard against decay:
- **Syntactic (automated):** `pre-commit install`, then every commit runs dead-link, broken-anchor,
  and markdown-style checks.
- **Structural + semantic (on demand):** the `wiki-lint` skill — the Obsidian CLI finds orphans,
  dangling links, and dead-ends; the agent reads for contradictions, near-duplicates, stale claims,
  provenance drift, and tag drift (no tool does the reading).
