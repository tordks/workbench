---
name: review-docs
description: Review documentation for document discipline — docstrings, comments, and prose (markdown, ADRs, README) — in a subagent. Use when the user wants to review the docs of a change (a diff), or to audit the docs of named files or the whole repo out of band. Separate from code review, so it runs on its own.
---

Review **documentation** — docstrings, inline comments, and prose (`*.md`, ADRs, `README`) — for document discipline.

**The review runs in one or more `general-purpose` subagents; the parent orchestrates.** The parent picks the target (below), decides how many subagents to run, spawns them, and assembles what comes back. Everything from *Harvest* down is the subagent's brief — the harvest bundle and the source tree never reach the parent's context. The parent aggregates the returned findings and writes the single roll-up summary.

## Target — parent picks

Choose by what the user asks for:

- **Diff** *(default)* — the documentation a change touched: the working diff (`git diff HEAD`), or a range the user names. Small and self-scoped; one subagent.
- **Scan** — the documentation in files or paths the user names, or a whole subtree, with no diff. An out-of-implementation audit that catches discipline the diff never surfaced.

**Cardinality is the parent's call.** Run one subagent when the target fits a single context — the usual case. When a Scan is too large to hold at once, split its paths across subagents that cover **disjoint** files and run them in parallel; disjoint shards cannot double-report, so aggregation is plain concatenation.

---

The sections below are the **subagent's brief**. It runs them; the parent does not, except for the parent-owned summary noted in *Report*.

## Harvest — Scan only

A whole-repo Scan must not read entire source files into review context wholesale; most of each file is code the review ignores. Extract just the documentation first, by file kind:

- **Python** — run `python harvest_docs.py <path> ...` (in this skill's folder). It emits every docstring with its `file:line` and the signature it attaches to — what the *docstrings-stay-in-their-own-unit* and *no-staleness* rules judge against — plus every comment, in source order.
- **Prose** (`*.md`, ADRs) — already documentation; read it directly.
- **Other code** (`*.ts`, `*.go`, `*.rs`, …) — no standard-library parser reaches these, so read the file's raw text directly. This pulls whole sources into context — the cost harvesting avoids for Python — so it is the heavy path, and the reason a large non-Python Scan is what forces a split.

Review that bundle and open a Python unit's full body only when its docstring is suspect — to confirm staleness or collaborator-narration — never wholesale. Diff mode skips harvest; see *Scope*.

## Scope — what to judge

- **Diff** — every changed documentation line, **plus** every docstring or comment whose *described code* changed in this diff even when the doc text did not. A body that changed under an untouched docstring is the commonest staleness, and its doc lines are not in the diff — so open the enclosing unit in the working tree (the docstring often sits outside the diff's context lines) and judge it against the new code. Ignore pure-code changes that carry no doc.
- **Scan** — every doc in the harvested-or-read bundle for the target paths.

## Rules

The rules are this repo's documentation conventions. Apply the repo's `docs/agents/doc-conventions.md` when it exists; otherwise the bundled [`conventions/doc-conventions.md`](conventions/doc-conventions.md), a copy carried for repos that have not converged their own. Read whichever is in force before flagging.

Flag every place the docs break one of its rules. The non-obvious *why* is what a docstring is *for* — never flag a doc merely for explaining why; flag only the specific breaks the rules name. Cite each broken rule by its title, not a number that can shift.

## Report

**Each subagent** returns its findings only — each naming the rule it breaks with the offending line quoted, hard violations separated from judgement calls. **The parent** concatenates the disjoint shards and adds the single closing line: the total count and the worst issue across all of them.
