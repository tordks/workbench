# workflow-vault

My engineering setup and how I work — a **karpathy-style LLM wiki** plus the **skills** unique to my
workflow. The wiki is knowledge an LLM agent maintains and grows over time; the skills are tooling,
installable into any agent.

```
workflow-vault/
  skills/          # my own agent skills (installable via the `skills` CLI)
    wiki-maintain/ #   ingest / query / lint the wiki
    orchestrate/   #   delegated multi-unit implementation
    review-docs/   #   documentation-discipline review
    router/        #   which-skill-fits index (+ pointers to upstream skills)
  wiki/            # the Obsidian vault (the karpathy wiki)
    _schema.md     #   the rules an agent follows to maintain the vault — read this first
    concepts/  practices/  references/  sources/  maps/
```

## The wiki

A [karpathy LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): three
layers — immutable **raw sources** (`sources/`), an LLM-owned **synthesized wiki**, and a **schema
doc** (`wiki/_schema.md`) that teaches an agent how to maintain it. The agent maintains it through
three operations — **ingest**, **query**, **lint** — all defined in `_schema.md` and driven by the
`wiki-maintain` skill.

### Open it in Obsidian
Open the `wiki/` folder as an Obsidian vault (not the repo root — that keeps `skills/` out of the
graph). Minimal `.obsidian/` config is committed; per-machine churn is gitignored.

**Recommended plugins** (for human editing sessions — the agent maintains the vault via CLI and
doesn't need them):
- Core: Backlinks, Outgoing links, Graph, Properties, **Bases**, Canvas
- **Obsidian Git** — for diff/history. Keep **auto commit-and-sync OFF** (the agent/CLI is the sole
  committer; auto-sync races external writes and fights `.git/index.lock`).
- **Templater + QuickAdd** — convention-enforcing note creation
- **Smart Connections** — local-embedding "related notes" while you browse (the one thing an
  external agent can't do live)
- Quality-of-life: Advanced Tables, Commander, Homepage, and Dataview + Dataview Serializer if you
  need queries Bases can't express

### Keep it from rotting (lint)
- **Syntactic (automated):** `pre-commit install`, then every commit runs dead-link, broken-anchor,
  and markdown-style checks. Run `pre-commit autoupdate` once to pin current hook versions.
- **Semantic (on demand):** run the `wiki-maintain` skill's *lint* — the agent reads for
  contradictions, near-duplicates, orphans, stale claims, and tag drift (no tool does this).

## The skills

Install into any agent (Claude Code, Cursor, Codex, …) with the [`skills`
CLI](https://github.com/vercel-labs/skills):

```
npx skills@latest add tordks/workflow-vault
```

You'll be prompted to pick which skills and which agent. Only the skills **unique to my workflow**
live here; the general engineering skills come from upstream — install those separately and keep
them current instead of forking:

```
npx skills@latest add mattpocock/skills
```

Not sure which skill fits? Invoke `router`.
