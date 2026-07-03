---
name: wiki-query
description: "Answer a question from the karpathy-style wiki — read-only. Use when you need what the wiki already knows; prefer it over re-deriving."
---

Read the wiki and answer from it. This skill is the read interface: it knows the vault's layout and
conventions so you don't have to.

**Load the rules first:** `vault_read "_schema.md"` — page types, tags, aliases. Every vault touch
goes through the **`obsidian` MCP server** (its `vault_*` / `search_*` tools), which reaches the live
vault by paths relative to its root — never a filesystem path. The README covers connecting it.

## Find and read

- `search_simple` — full-text. `search_query` runs JsonLogic over each note's metadata to narrow by
  tag or field, e.g. `{"in": ["<tag>", {"var": "tags"}]}`.
- Traverse the neighbourhood — the graph often holds the answer the search terms missed. `vault_read`
  a page and follow its `[[wikilinks]]`; find its inbound links with
  `search_query {"in": ["<path>", {"var": "links"}]}`.
- `vault_read` — read the pages you land on.

## Answer

Answer **from the wiki**, citing the pages you used by title / `[[wikilink]]`. If the wiki doesn't
hold it, say so plainly rather than inventing.

## Route gaps back — never write inline

`query` is read-only; it never edits the wiki layer. If the answer is durable and *not* yet
captured, hand it to `wiki-capture` (park a note to `inbox/`) so it flows through `ingest` on the
normal path. Done when the answer is given with citations and any gap is parked.
