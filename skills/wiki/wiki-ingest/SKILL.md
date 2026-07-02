---
name: wiki-ingest
description: "Fold new material — inbox captures and named raw sources — into the karpathy-style wiki as atomic, cross-linked pages. Use when draining the inbox or adding a source."
---

Turn raw material into atomic, interlinked wiki pages without duplicating what's already there. This
is the heavy operation; it owns all writes to the wiki layer.

**Load the rules first:** `obsidian read _schema.md` — layers, page types, frontmatter, controlled
tags, provenance, and autonomy. The skill runs wherever your agent runs, so every vault touch goes
through the **Obsidian CLI**, which reaches the live vault.

## Gather

- Inbox: `obsidian files inbox/`, then `obsidian read <item>` for each.
- Plus any source the user names directly.

## Capture raw, immutably

For external material, write it (or a faithful excerpt + URL) to `sources/<slug>` and never edit it
again; add a `source`-type stub. A personal idea from the inbox needs no source file — record its
origin in provenance instead.

## Decompose → search-before-write → merge

Break the material into atomic, evergreen ideas. For **each** idea:

- `obsidian search` + `obsidian backlinks` to find an existing page first.
- **Exists** → update it. If the new info *contradicts* the page, **stop and flag** — do not
  overwrite (approval-gated per the schema).
- **New** → create one atomic page of the correct `type`, full frontmatter, `status: seed`, linked
  to its source.
- **Provenance-tag** each claim per `_schema.md` (`extracted` default, `^[inferred]`, `^[ambiguous]`).
- **Cross-link** the touched page to its neighbours and back to the source.

## Consume the inbox

Once an inbox item is fully folded in, delete it (`obsidian delete inbox/<item>`) — git is the
trail. This is the one autonomous deletion; it never touches `sources/` or wiki pages.

**Done when** every idea in the material is reflected in a page and linked to its source, and every
processed inbox item is removed.
