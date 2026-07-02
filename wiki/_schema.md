---
type: map
title: Wiki Schema
aliases: [schema, _schema]
tags: [meta]
created: 2026-07-02
updated: 2026-07-02
status: evergreen
---

# Wiki Schema

The rules that make this vault a *karpathy wiki* — a knowledge base an LLM agent can maintain
without letting it decay. Any agent editing this vault reads this file first. This is the single
highest-leverage file in the system: it, not automation, keeps the agent a disciplined maintainer
rather than a generic chatbot.

## The three layers

1. **Raw sources** (`sources/`) — captured external material, **immutable**. The agent reads them
   but never edits them. Provenance lives here.
2. **The wiki** (`concepts/`, `practices/`, `references/`, `maps/`) — synthesized, cross-linked
   pages. The agent owns this layer entirely.
3. **The schema** (this file) — how the wiki is structured and maintained.

## Page types

Every page declares exactly one `type` in frontmatter. The set is closed — do not invent new types.

| type | what it is | folder |
|---|---|---|
| `concept` | one atomic, evergreen idea | `concepts/` |
| `practice` | a how-to / convention / recipe you act on | `practices/` |
| `reference` | factual notes on a specific tool/library/API | `references/` |
| `source` | a **stub** pointing at immutable raw material in `sources/` | `sources/` |
| `map` | a navigation hub (MOC) | `maps/` |

`source` pages are lightweight: frontmatter + a short summary + a link to the raw file. The raw file
itself is never rewritten.

## Naming

- Filenames are `kebab-case.md`, matching the note title.
- **Type is never encoded in the filename** — it lives in frontmatter + folder — so a page can be
  re-typed without a rename (keeps blast radius small).
- One idea per page (atomicity). If a claim only makes sense as a *qualifier* of an existing idea,
  it is an edit to that page, not a new page.

## Frontmatter (required on every page)

```yaml
---
type: concept | practice | reference | source | map
title: Human Readable Title
aliases: []          # alternate names for [[link]] resolution
tags: []             # controlled vocabulary only — see below
created: 2026-07-02
updated: 2026-07-02
status: seed | draft | evergreen | stale
source: "[[some-source]]"   # provenance; required on synthesized pages
related: []
---
```

`status` + `updated` are the staleness signal `lint` checks. `source` ties every synthesized claim
back to the raw material it came from.

## Controlled tag vocabulary

Uncontrolled tags are a top entropy source. **Reuse an existing tag; do not coin a near-synonym.**
Adding a tag means adding it here first. Seed vocabulary:

- `meta` — about the vault itself
- `python`, `frontend`, `testing`, `tooling`, `architecture`, `workflow`, `ai`

## Links

- Cross-link liberally with `[[wikilinks]]`. A `[[link]]` to a page that doesn't exist yet is fine —
  it marks a page worth writing.
- Navigation is by **Maps of Content**, not deep folders. A page can belong to many maps at once.

## Operations

The agent maintains the wiki through exactly three operations. The procedure lives in the
`wiki-maintain` skill; the *rules* live here.

### ingest
Fold a new source into the wiki. Capture the raw material in `sources/` (immutable) + a `source`
stub, then decompose it into atomic ideas. For each idea: **search the vault first** — if a page
exists, update it; if not, create one atomic page of the right type. Link every synthesized page
back to its `source`. Touching 5–15 related pages per source is normal.

### query
Answer a question from the wiki. If the answer is durable and not yet captured, file it back as a
new page.

### lint
The entropy defense. Two tiers:
- **Syntactic (automated, pre-commit):** broken links, dead URLs, missing anchors, markdown style.
  Run by CLI tools — see repo `.pre-commit-config.yaml`.
- **Semantic (on-demand, agent):** contradictions, near-duplicate pages, orphans, coverage gaps,
  taxonomy/tag drift, stale claims. No tool does this — the agent must read.

## Autonomy rules

- **Autonomous:** creating new pages and adding to existing ones.
- **Approval-gated:** overwriting existing content, resolving contradictions, and any deletion.
- **Never delete or overwrite raw `sources/` — ever.** When new info contradicts a page, do not
  silently overwrite; reconcile and flag for the human. Git diff is the safety net — commit small.
