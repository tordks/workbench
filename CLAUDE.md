# CLAUDE.md

This repo holds two independent products: a **karpathy-style LLM wiki** (`wiki/`) and the **skills
unique to this workflow** (`skills/`). `README.md` is the human overview; this file is the working
discipline for an agent editing either. Read the relevant section before you touch that half.

## The dividing line

Knowledge lives in `wiki/`; skills are tooling. A convention or tool a skill needs to *apply in
another repo* ships **with the skill** — the wiki isn't present where a skill installs, so anything
that must travel has to live in the skill folder. The wiki keeps the durable knowledge and, at most,
names the skill; it never holds a second copy of what the skill already owns.

## Prime directive — minimize blast radius

State each fact in exactly one canonical place and point to it; never restate it where it can drift.
Refer to things by stable name, not by position or number. This is the `[[blast-radius]]` concept the
wiki itself is built around — the repo should practise it.

## No meta-commentary

In any file — wiki page, skill, script, doc — state what something *does* and why a non-obvious
decision was made. Never reference tickets, task IDs, or the narrative of *how a change came to be*;
that context belongs in the tracker, not in files that outlive the work.

## Editing the wiki

**Read `wiki/_schema.md` first.** It is the canonical maintenance discipline and every wiki edit
obeys it — the closed set of page types, the three layers, and the ingest / query / lint operations.
Key invariants: `sources/` is **immutable** (read, never rewrite); every page declares exactly one
`type`; cross-link liberally with `[[wikilinks]]`.

Prefer the `wiki-maintain` skill (ingest / query / lint) over ad-hoc edits. Open the `wiki/` folder
(not the repo root) as the Obsidian vault, so `skills/` stays out of the graph.

## Editing skills

- **Never fork or edit the upstream `mattpocock/skills`.** Those install separately (`npx skills`);
  layer on top or override a consuming repo's own docs, never patch the vendored files in place.
- **Tooling ships inside the skill folder** (e.g. `skills/backlog/scripts/`) so it travels on install;
  nothing is copied into target repos.
- **SKILL.md is the generic process; specifics go in bundled reference files** reached by a pointer
  (e.g. `setup-skills/conventions/`), so each fact has one home and adding a case is dropping a file.
- Skill scripts are **Python, standard library + `gh` only** — no third-party deps. Shared logic
  lives in one module imported by the rest (define each meaning once).
- For skill-authoring principles (leading words, information hierarchy, pruning), the
  `writing-great-skills` skill is the reference.

## Dev setup

- **Lint:** `pre-commit run --files <changed-file> …` (dead-link + markdown-style checks; see
  `wiki/_schema.md` → lint). Run `pre-commit autoupdate` once to pin hook revs. Semantic lint —
  contradictions, near-duplicates, orphans — is the `wiki-maintain` lint operation, not a hook.
- **Skill scripts:** sanity-check with `python3 -m py_compile skills/backlog/scripts/*.py`.

## Folder tree

```
README.md                    # human overview + install instructions
pyproject.toml               # config for the md-dead-link-check pre-commit hook
.pre-commit-config.yaml      # syntactic wiki lint tier
skills/                      # installable skills unique to this workflow (via `npx skills`)
  backlog/                   #   present open issues in dependency order (read-only)
    scripts/                 #     order_core / bodyparse / ghlib + the two readers + the bridge
  setup-skills/              #   converge a repo's convention docs to these (docs only)
    conventions/             #     the convention docs it applies (ship with the skill)
  orchestrate/               #   drive issues/PRD to done via per-unit subagents
  review-docs/               #   documentation-discipline review
  wiki-maintain/             #   ingest / query / lint the wiki
wiki/                        # the Obsidian vault (open THIS as the vault, not the repo root)
  _schema.md                 #   the maintenance discipline — read first before editing the wiki
  concepts/ practices/ references/ sources/ maps/
```
