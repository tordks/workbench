---
name: wiki-maintain
description: Maintain a karpathy-style LLM wiki (an Obsidian vault) through ingest / query / lint. Use when adding a source to the wiki, answering from it, or health-checking it against decay.
---

# wiki-maintain

Operate a karpathy-style knowledge wiki without letting it rot. Three operations: **ingest**,
**query**, **lint**. Before doing anything, read the vault's `wiki/_schema.md` — it owns the rules
(page types, naming, frontmatter, controlled tags, autonomy). This skill owns the *procedure*.

## Autonomy (from the schema — restated because it's load-bearing)

- Create new pages and add to existing ones **autonomously**.
- **Ask first** before overwriting content, resolving a contradiction, or deleting anything.
- **Never** edit or delete files under `sources/` — they are immutable raw material.
- Commit small; git diff is the human's review surface.

## ingest — fold a source into the wiki

1. **Capture raw, immutably.** Write the source's raw material (or a faithful excerpt + URL) to
   `sources/<kebab-title>.md` and never edit it again. Add a `source`-type stub with frontmatter and
   a one-paragraph summary.
2. **Decompose** the source into atomic, evergreen ideas/claims.
3. For each idea, **search the vault first** (grep titles, aliases, tags, body):
   - **Exists** → update that page. If the new info *contradicts* what's there, stop and flag for
     approval — do not overwrite.
   - **New** → create one atomic page of the correct `type` in the correct folder, with full
     frontmatter, `status: seed`, and `source: "[[<the-source>]]"`.
4. **Cross-link** each touched page to its neighbours and back to the source.
5. Reuse existing **tags** only; if a genuinely new tag is needed, add it to the vocabulary in
   `_schema.md` first.
6. **Completion criterion:** every atomic idea in the source is either reflected in an existing page
   or has its own page, and each is linked to the source. Touching 5–15 pages is normal.

## query — answer from the wiki

1. Search the wiki; answer from it, citing the pages used.
2. If the answer is durable and not already captured, **file it back** as a new page (same rules as
   ingest step 3).

## lint — the entropy audit

Run the two tiers. Report findings; **suggest** fixes, apply only the safe ones autonomously.

**Syntactic (delegate to CLI — fast, deterministic):**
- `md-dead-link-check` — dead URLs, broken file refs, missing heading anchors
- `mlc --offline <vault>` — internal/relative link integrity, no network
- `markdownlint-cli2` — markdown style / frontmatter shape

These run automatically on commit (repo `.pre-commit-config.yaml`); run them by hand for an
out-of-band audit.

**Semantic (agent reads — no tool does this):**
- **Orphans** — pages no other page links to (and that link to nothing). Propose a home in a map.
- **Near-duplicates** — two pages covering one idea. Propose a merge (ask before merging).
- **Contradictions** — pages that disagree. Flag both; propose a reconciliation for approval.
- **Stale claims** — `status: stale`, or `updated` old on a fast-moving topic. Flag for review.
- **Coverage gaps** — `[[links]]` to pages that don't exist yet. Propose writing them.
- **Taxonomy drift** — `type` outside the closed set, or tags outside the vocabulary. Fix tags to
  the nearest existing vocabulary term; flag type violations.

**Completion criterion:** every page accounted for against each check above; findings reported as a
list, with only unambiguous fixes (e.g. a tag normalized to an existing term) applied.
