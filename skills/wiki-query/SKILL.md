---
name: wiki-query
description: "Answer a question from the karpathy-style wiki — read-only. Use when you need what the wiki already knows; prefer it over re-deriving."
---

Read the wiki and answer from it. This skill is the read interface: it knows the vault's layout and
conventions so you don't have to.

**Load the rules first:** `obsidian read _schema.md` — page types, tags, aliases. The skill runs
wherever your agent runs, so every vault touch goes through the **Obsidian CLI**, which reaches the
live vault.

## Find and read

- `obsidian search "<terms>"` — full-text; `obsidian tags` / `obsidian tag <t>` to narrow by tag.
- `obsidian backlinks <page>` and `obsidian links <page>` — traverse the neighborhood; the graph
  often holds the answer the search terms missed.
- `obsidian read <page>` — read the pages you land on.

## Answer

Answer **from the wiki**, citing the pages you used by title / `[[wikilink]]`. If the wiki doesn't
hold it, say so plainly rather than inventing.

## Route gaps back — never write inline

`query` is read-only; it never edits the wiki layer. If the answer is durable and *not* yet
captured, hand it to `wiki-capture` (park a note to `inbox/`) so it flows through `ingest` on the
normal path. Done when the answer is given with citations and any gap is parked.
