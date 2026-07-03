---
name: backlog
description: "Present the open issues in dependency order and reason about what to implement next — which are ready, which are blocked, which are underspecified. Use when the user or an orchestrator asks what to work on next, what's blocked, or wants the dependency-ordered backlog before picking work."
---

Present the open issues in **dependency order** and reason with the user about what to pick next. Read-only in the strictest sense: you surface the picture and discuss it — you never change an issue's state, and you never invoke another skill. Present; don't dispatch.

## Read the picture

Run the reader bundled with this skill — it owns the ordering and readiness computation, so never re-derive it by hand. Pick the reader that matches where this repo records dependencies (stated in the repo's `docs/agents/issue-tracker.md`, converged there by `setup-skills`):

```
scripts/order-from-github-deps.py   # PRIMARY: GitHub's native dependency graph (blocked_by)
scripts/order-from-body.py          # BACKSTOP: derive edges from each issue's `## Blocked by` body
```

Both take the same flags and emit the same shape (they share `order_core.py`, the one engine):

```
scripts/order-from-github-deps.py           # topo-ordered; ▶ marks ready, reason on the rest
scripts/order-from-github-deps.py --json    # {order, ready} for reasoning
```

`order` is every open issue topologically sorted by its dependencies; `ready` is the subset with no *open* blocker that carries the readiness label. The canonical definition of "ready" lives in `order_core.py`.

**Foreign / freeform trackers.** Both scripts read issues via `gh`. If a repo's tracker is neither GitHub nor a body with a parseable `## Blocked by` grammar (a local-markdown tracker, freeform prose), there is no script — build the nodes graph in-agent (`{number, title, labels, blocked_by}` per issue, `blocked_by` filtered to open blockers) and reason over it the same way. The buckets below are identical regardless of how the graph was sourced.

## Present and reason

Bucket the output:

- **Ready** (`▶`) — pick-up-able now.
- **Blocked** — held by an open upstream; name the blocker(s) so a near-done one is visible.
- **Underspecified** — no open blocker but missing the readiness label.

Then reason with the user: recommend an order among the ready set, flag anything blocked only by an almost-finished issue, and call out underspecified issues worth specifying next. Done when the user holds a picture they can decide from.

Acting on that picture — implementing a unit, or moving an issue's state — is another skill's job. You only present.
