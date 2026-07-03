---
name: wiki-lint
description: "Audit the karpathy-style wiki for decay — orphans, dead links, contradictions, staleness. Use for an on-demand health check of the vault."
---

The entropy defence. Surface what's rotting and propose fixes; apply only the safe ones yourself,
flag the rest.

**Load the rules first:** `vault_read "_schema.md"` — the closed page-type set, the controlled tag
vocabulary, provenance. Every vault touch goes through the **`obsidian` MCP server** (its `vault_*` /
`search_*` tools), which reaches the live vault by paths relative to its root — never a filesystem
path. The README covers connecting it.

## Deterministic tier — `search_query` over the graph

Fast, exact graph checks no prose linter can do. `search_query` runs JsonLogic over each note's
NoteJson — `links` is its resolved outlinks, `backlinks` its resolved inlinks, and an empty array is
falsy in JsonLogic:

- **Orphans** — pages nothing links to: `{"!": {"var": "backlinks"}}`.
- **Dead-ends** — pages that link out to nothing: `{"!": {"var": "links"}}`.
- **Dangling links** — `[[targets]]` resolving to no page (the schema's *coverage gaps* — pages worth
  writing). `links` lists resolved targets only, so no single query finds these: `vault_read` each
  page, pull its `[[…]]` refs, and flag any with no matching resolved `links` entry.

(Dead URLs, broken file refs, and markdown style are handled separately at commit time by the repo's
pre-commit hooks — no MCP call needed for those.)

## Semantic tier — read; no tool does this

- **Contradictions** — pages that disagree. Flag both; propose a reconciliation (approval-gated).
- **Near-duplicates** — two pages covering one idea. Propose a merge; ask before merging.
- **Stale claims** — `status: stale`, or `updated` old on a fast-moving topic. Flag for review.
- **Provenance drift** — a page that has drifted mostly to `^[inferred]` / `^[ambiguous]` is
  speculation-heavy. Flag it.
- **Taxonomy / tag drift** — `type` outside the closed set, or tags outside the vocabulary. Fix tags
  to the nearest existing term; flag type violations.

## Report

Every page accounted for against each check above, findings as a list. Apply only unambiguous fixes
autonomously (e.g. a tag normalised to an existing term); everything destructive stays gated.
