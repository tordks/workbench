---
type: concept
title: Blast radius
aliases: [blast-radius, minimize blast radius]
tags: [architecture, workflow]
created: 2026-07-02
updated: 2026-07-02
status: evergreen
related: ["[[_schema]]"]
---

# Blast radius

The blast radius of an edit is the number of places that must change in lockstep when one fact
changes. Prefer the form that costs the least to change later — keep blast radius small.

- **Single source of truth.** State each fact in exactly one canonical place and point to it; never
  restate it inline where it can drift.
- **Refer by stable name, not by position.** Prefer durable identifiers (a glossary term) over
  positional or numeric ones that rot when things are reordered or renumbered. A decision referenced
  in 80 places can't be renumbered without an 80-edit sweep.

This is why this vault encodes `type` in frontmatter (not filenames) and navigates by
[[_schema|maps and links]] rather than deep folders: a page can be re-typed or re-homed without a
rename that ripples through every reference.
