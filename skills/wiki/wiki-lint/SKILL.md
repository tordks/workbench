---
name: wiki-lint
description: "Audit the karpathy-style wiki for decay — orphans, dead links, contradictions, staleness. Use for an on-demand health check of the vault."
---

The entropy defence. Surface what's rotting and propose fixes; apply only the safe ones yourself,
flag the rest.

**Load the rules first:** `obsidian read _schema.md` — the closed page-type set, the controlled tag
vocabulary, provenance. The skill runs wherever your agent runs, so every vault touch goes through
the **Obsidian CLI**, which reaches the live vault.

## Deterministic tier — the Obsidian CLI

Fast, exact graph checks no prose linter can do:

- `obsidian orphans` — pages nothing links to.
- `obsidian unresolved` — dangling `[[links]]` (the schema's *coverage gaps* — pages worth writing).
- `obsidian deadends` — pages that link out to nothing.

(Dead URLs, broken file refs, and markdown style are handled separately at commit time by the repo's
pre-commit hooks — no Obsidian needed for those.)

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
