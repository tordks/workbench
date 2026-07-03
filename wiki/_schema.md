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

The **inbox** (`inbox/`) is a staging *lane*, not a layer: raw, mutable captures — ideas, notes,
links — awaiting ingest. `capture` appends to it; `ingest` drains and consumes it. It is not part of
the synthesized wiki and is not linted as wiki pages.

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

## Provenance

`source:` frontmatter ties a page to its raw material; per-claim markers say how load-bearing each
claim is, so `lint` can tell knowledge from speculation. Every synthesized claim is one of:

- **extracted** (default) — stated by a source. No marker needed.
- **inferred** — the agent's synthesis, not stated by any source. Mark inline `^[inferred]`.
- **ambiguous** — sources disagree. Mark inline `^[ambiguous]` and name the disagreement.

A page that has drifted mostly to `inferred` / `ambiguous` is speculation-heavy — `lint` flags it.

## Operations

Four operations, one skill each — `wiki-capture`, `wiki-query`, `wiki-ingest`, `wiki-lint`. The
*procedure* lives in the skill; this file holds the *rules* it obeys. The skills run wherever the
agent runs, so they reach this vault — including this file — through the **Obsidian Local REST API
MCP server**, and each reads `_schema.md` first. The rules each operation must honour:

- **capture** appends one raw idea/note/link per file to `inbox/`; synthesis is `ingest`'s job.
- **ingest** drains the inbox and folds named sources in. Capture external material to `sources/`
  (immutable) + a `source` stub; **search the vault before creating** any page, so you extend an
  existing one instead of duplicating an idea. A contradiction is gated, not overwritten (see
  Autonomy).
- **query** reads the wiki; it never writes. A durable answer that isn't captured goes back through
  `capture`, not a direct page write.
- **lint** is the entropy defense, in two tiers: *automated* (pre-commit — broken links, dead URLs,
  markdown style; see `.pre-commit-config.yaml`) and *on-demand* (the `wiki-lint` skill — structural
  graph checks plus semantic checks the agent must read for).

## Autonomy rules

- **Autonomous:** creating new pages and adding to existing ones; appending captures to `inbox/`.
- **Approval-gated:** overwriting existing content, resolving contradictions, and any deletion of a
  wiki page or source.
- **Inbox is staging:** deleting an inbox item *after* `ingest` has folded it in is autonomous — git
  preserves the trail. This is the one deletion that is not gated; it never touches `sources/` or the
  wiki layer.
- **Never delete or overwrite raw `sources/` — ever.** When new info contradicts a page, do not
  silently overwrite; reconcile and flag for the human. Git diff is the safety net — commit small.
