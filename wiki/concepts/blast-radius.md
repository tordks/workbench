---
type: concept
title: Blast radius
aliases: [blast-radius, minimize blast radius]
tags: [architecture, workflow]
created: 2026-07-02
updated: 2026-07-03
status: evergreen
---

# Blast radius

The blast radius of an edit is the number of places that must change in lockstep when one fact
changes. Prefer the form that costs the least to change later — keep blast radius small.

- **Single source of truth.** State each fact in exactly one canonical place and point to it; never
  restate it inline where it can drift.
- **Refer by stable name, not by position.** Prefer durable identifiers (a glossary term) over
  positional or numeric ones that rot when things are reordered or renumbered. A decision referenced
  in 80 places can't be renumbered without an 80-edit sweep.

The cheapest-to-change form usually stores a fact as *data* keyed by a stable name, not baked into a
position that other things count on. Classifying a document by a `type` field rather than by its
folder lets it be reclassified without a move that every link to it has to follow; addressing a
config value by key rather than by line number keeps callers valid when the file is reordered. The
test is the same each time: when this one fact changes, how many other places have to change with
it — and can you drive that number toward one.
