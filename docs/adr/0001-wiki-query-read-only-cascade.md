# ADR-0001: wiki-query is read-only with a bounded single-pass cascade

Status: Accepted
Date: 2026-07-03

## Context

`wiki-query` answers questions from the vault. Surveyed karpathy-style wiki
implementations diverge on two axes: whether the query operation may write, and how
hard it searches before giving up.

- On a miss, `green-dalii/obsidian-llm-wiki` falls back to answering from the model's
  general knowledge; `ekadetov/llm-wiki` always files the answer and git-commits;
  `atomicstrata/llm-wiki-compiler` is read-only by default and writes only on `--save`.
- Retrieval in all of them is a **bounded single pass** — search, optionally expand
  seeds, follow at most one hop of links — not an iterative loop. Graph traversal is
  always bounded (ekadetov: one level of `[[links]]`; atomicstrata: depth 1–2, capped
  at 20 neighbours).

The `obsidian` MCP server offers `search_simple` (the only fuzzy/ranked path),
`search_query` (JsonLogic over `NoteJson`: `tags`, `frontmatter`, `content`, `path`,
`links`, `backlinks`, `stat`), and `tag_list`. No semantic ranking beyond
`search_simple`.

## Decision

`wiki-query` is **strictly read-only** — it never writes the wiki layer. A durable
answer the vault lacks routes through `wiki-capture` → `inbox/` → `wiki-ingest`, the
one reviewed write path.

Retrieval is a **bounded single-pass cascade**, cheapest rung first, stopping the
moment a rung answers: text fast-path (`search_simple`) → structural narrow
(`search_query` by tag/frontmatter) → one-hop, relevance-gated graph
(`links`/`backlinks`) → verdict. On a dry pass the skill states the absence plainly
and never invents; there is no general-knowledge fallback.

## Consequences

- Read (query) and write (capture/ingest) stay cleanly separated — the vault only
  grows through the reviewed ingest path.
- Honest absence over plausible fabrication; this rejects green-dalii's
  general-knowledge fallback.
- A second retrieval pass — re-query with terms learned from near-miss pages before
  declaring absence — is deliberately deferred until a real need appears.
- No semantic ranking beyond `search_simple`'s fuzziness; acceptable at the current
  vault scale, revisit if the corpus grows large enough for scattered hits to hurt.
