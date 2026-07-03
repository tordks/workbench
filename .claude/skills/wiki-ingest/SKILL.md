---
name: wiki-ingest
description: "Fold new material — inbox captures and named raw sources — into the karpathy-style wiki as atomic, cross-linked pages. Use when draining the inbox or adding a source."
---

Turn raw material into atomic, interlinked wiki pages without duplicating what's already there. This
is the heavy operation; it owns all writes to the wiki layer.

**Load the rules first:** `vault_read "_schema.md"` — layers, page types, frontmatter, controlled
tags, provenance, and autonomy. Every vault touch goes through the **`obsidian` MCP server** (its
`vault_*` / `search_*` tools), which reaches the live vault by paths relative to its root — never a
filesystem path. The README covers connecting it.

## Gather

- Inbox: `vault_list "inbox/"`, then `vault_read` each item.
- Plus any source the user names directly.

## Capture raw, immutably

For external material, `vault_write "sources/<slug>.md"` with the content (or a faithful excerpt +
URL) and never edit it again; add a `source`-type stub. A personal idea from the inbox needs no source
file — record its origin in provenance instead.

## Decompose → search-before-write → merge

Break the material into atomic, evergreen ideas. For **each** idea:

- `search_simple` (and `search_query` for tag/field, or inbound links via
  `{"in": ["<path>", {"var": "links"}]}`) to find an existing page first.
- **Exists** → update it with `vault_patch` (surgical — target one heading, block, or frontmatter
  field) or `vault_append`, not a whole-file rewrite. If the new info *contradicts* the page, **stop
  and flag** — do not overwrite (approval-gated per the schema).
- **New** → `vault_write "<type-dir>/<slug>.md"` — one atomic page of the correct `type`, full
  frontmatter, `status: seed`, linked to its source.
- **Provenance-tag** each claim per `_schema.md` (`extracted` default, `^[inferred]`, `^[ambiguous]`).
- **Cross-link** the touched page to its neighbours and back to the source.

## Tend the maps

New pages accrete into themes. When a cluster has grown enough that `home` no longer routes to it
well, extend the theme's `map` — add the new page to the relevant MOC, or split a crowded cluster
into its own (the mint trigger lives in `_schema.md`). Minting a map is bottom-up and autonomous —
it's a new page; don't design a hierarchy ahead of the pages.

## Consume the inbox

Once an inbox item is fully folded in, `vault_delete "inbox/<item>"` — git is the trail. This is the
one autonomous deletion; it never touches `sources/` or wiki pages.

**Done when** every idea in the material is reflected in a page and linked to its source, and every
processed inbox item is removed.
