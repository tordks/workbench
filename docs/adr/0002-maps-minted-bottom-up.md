# ADR-0002: Maps are curated entry points, minted bottom-up

Status: Accepted
Date: 2026-07-03

## Context

`_schema.md` declared "navigation is by Maps of Content, not deep folders" but never
said what a map is *for* or when to create one. The result was a fuzzy concept: a
single `home` map, no per-entry summaries, and no trigger telling a maintainer when a
second map is warranted — inviting either a premature map hierarchy or none at all.

In the karpathy/LYT tradition a Map of Content (MOC) is a hand-curated index note that
grows bottom-up: at small scale one index suffices, and sub-theme maps are spun off
only once a cluster is large enough to need its own hub.

## Decision

A **map** is a *curated entry point for a theme* — the hand-picked, ordered set of
pages you would start from to explore it. The curation is the content; a map is not an
auto-generated list, not a taxonomy, and does not nest. A page may belong to many maps.

Maps are **minted bottom-up, on crowding**: `home` is enough until a cluster around a
sub-theme has grown large enough that `home` no longer routes to it efficiently; only
then is that cluster split into its own MOC. Map structure is never designed ahead of
the pages. A per-entry one-line gloss is a quality nicety, not a requirement.

This ripples across the wiki skills:

- `wiki-ingest` tends maps as pages accrete — extending `home` or minting a new MOC
  when a cluster outgrows it.
- `wiki-lint` exempts `map` pages from the orphan check — MOCs are navigational roots,
  expected to have few or no inlinks.
- `wiki-query` treats a map reached via `backlinks` as a curated hub (a valid one-hop
  target) and may enter a broad question at a MOC.

## Consequences

- Map structure grows with real need, not ahead of it — consistent with minimizing
  blast radius.
- Maps carry near-zero retrieval value at the current vault scale and gain value as the
  vault grows; the skills already use them, so no rewrite is needed when they multiply.
- The definition lives in `_schema.md` alone; the skills name the action and defer the
  rule there.
