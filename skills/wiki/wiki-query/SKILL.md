---
name: wiki-query
description: "Answer a question from the karpathy-style wiki — read-only. Use when the question is about a concept, convention, tool reference, or past decision the project would have curated; prefer it over re-deriving. Not for general knowledge, live code state, or facts read straight from the repo."
---

The read interface to the vault: it knows the layout and search primitives so the caller doesn't.
Read-only — it never writes the wiki layer.

**Load the rules first:** `vault_read "_schema.md"` — page types, controlled tags, aliases, what's
immutable. Every vault touch goes through the **`obsidian` MCP server** (its `vault_*` / `search_*`
tools), which reaches the live vault by paths relative to its root — never a filesystem path. The
README covers connecting it.

## The cascade

One bounded pass, cheapest rung first; **stop the moment a rung answers** — this is an escalation,
not a checklist to complete.

1. **Text fast-path** — `search_simple` (fuzzy, ranked). The first move for any pointed question.
2. **Structural narrow** — when text is scattered or you need a specific slice, `search_query`
   (JsonLogic over each note's metadata) by tag or frontmatter field; run `tag_list` first to see
   the real vocabulary rather than guess a tag.
3. **One-hop graph** — from a page you landed on, follow a `[[link]]` or read its `backlinks`,
   **only if that neighbour looks relevant** to the question. One hop, not a walk. A `map` among the
   backlinks is a curated hub for the theme — a good hop; do not fan out across its outlinks.
4. **Verdict** — below.

A broad, thematic question ("what does the wiki know about X") may enter at a `maps/` MOC instead of
rung 1 — but at this vault's size `home` is usually the only map, so text still leads.

## Search primitives

Exact call shapes, verified against the plugin's `NoteJson`. `search_query`'s top-level `var`s are
`tags`, `frontmatter`, `content`, `path`, `links`, `backlinks`, `stat`:

| search by | tool + shape |
|---|---|
| text (ranked) | `search_simple "<terms>"` — the only fuzzy/ranked path |
| tag | `search_query {"in": ["<tag>", {"var": "tags"}]}` |
| frontmatter field | `search_query {"==": [{"var": "frontmatter.<field>"}, "<value>"]}` |
| alias / title | `frontmatter.aliases` / `frontmatter.title` — no top-level var; else `path` |
| outbound links | `{"var": "links"}` — resolved targets only |
| inbound links | read the page's `{"var": "backlinks"}` directly |
| filename / path | `search_query` on `{"var": "path"}`, or `vault_list` |

`vault_read` the pages you land on. (Dangling `[[links]]` leave no trace in `links`/`backlinks` —
that gap is `wiki-lint`'s job, not query's.)

## Verdict

- **Found** → answer **from the wiki**, citing the pages by `[[wikilink]]`.
- **Dry pass** → say the wiki doesn't hold it, plainly. **Never** fall back to invented knowledge.
  If the answer is durable and the vault *should* have it, hand the gap to `wiki-capture` (parks a
  note to `inbox/` for `ingest`) — `query` never writes the wiki layer itself.

Done when the answer is given with citations, or the absence is stated and any gap parked.
