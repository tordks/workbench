# Issue dependency conventions

How issue-to-issue blocking is recorded, so `backlog` can order the work — and why there is exactly
one source of truth for it. `setup-skills` applies this convention to a repo; this file is the
canonical statement of it.

## The rule: use the tracker's built-in dependency graph

Whatever issue tracker a repo uses, record blockers in **that tracker's native dependency system** —
GitHub's issue dependencies, GitLab's linked/blocking issues, Jira's "is blocked by" links. That
native graph is the single source of truth; `backlog`'s engine reads it from there and topologically
sorts the open issues. One place, no second copy to drift, no sync loop.

A repo may instead record blockers in a `## Blocked by` section in the issue *body*. That is a
convention `setup-skills` configures per-repo (the upstream skills do **not** write it by default);
it is turned on in the repo's issue-creation convention. Where it is in force but the native graph
is the source of truth, treat the body as **draft input, not truth**: promote it into the tracker's
native graph and read from the graph thereafter. The body text is authority-free.

## Backstop: trackers with no dependency system

Some trackers have no native dependency graph — a local-markdown tracker under `.scratch/`, a
freeform tracker described in prose. There, and only there, the **`## Blocked by` section in the
issue itself is the source of truth**: the reader parses `#NN` (or file references) straight from the
body. It's the fallback precisely because the tracker gives us nowhere better to put it.

So the rule is one sentence with a fork: *use the tracker's dependency graph; if it hasn't got one,
the issue body is the graph.* Which case a given repo is in is recorded in that repo's
`docs/agents/issue-tracker.md` (see "Applying this to a repo").

## GitHub

GitHub **has** a native dependency graph, so it takes the primary path, not the backstop:

- **Source of truth** — native `blocked_by` dependencies (`gh api …/dependencies/blocked_by`).
- **Reader** — `order-from-github-deps.py` (bundled with the `backlog` skill): reads the native
  links, topo-sorts the open issues, marks the ready ones, and detects dependency **cycles**. The
  body backstop reader is `order-from-body.py`; both share the `order_core.py` engine.
- **Bridge** — `promote-body-to-native.py` (also bundled with `backlog`): only when the repo uses the
  `## Blocked by` body convention. After a creation batch it parses each `## Blocked by` body section,
  resolves `#NN` → numeric id, and POSTs the missing native links. `--check` reports drift/dangling
  refs without writing; `--mirror` also deletes native links absent from the bodies (full reconcile).
  Run once per creation batch — that one bridge keeps the native graph the only thing anyone reads
  afterward.

## Who reads, who writes

| Actor | Role |
|---|---|
| issue creation (upstream `to-issues`, per repo convention) | writes the *draft* `## Blocked by` body section — only where `setup-skills` turned that convention on |
| `promote-body-to-native.py` | GitHub: bridges those bodies into the native graph, at creation |
| `order-from-github-deps.py` | reads GitHub's native graph → dependency order + ready set |
| `order-from-body.py` | backstop: reads the `## Blocked by` bodies → same order + ready set |
| `backlog` skill | runs the matching reader; presents order + reasons about next; **never writes** |
| `triage` (upstream) | changes an issue's *state* (labels, briefs) — not its dependencies |

## Applying this to a repo

Target doc: `docs/agents/issue-tracker.md`. Converge it to state:

- **Source of truth** — the tracker's native graph (name it: GitHub `blocked_by`, GitLab blocking
  links, …) or, for a tracker without one, the `## Blocked by` body backstop.
- **`## Blocked by` section (only if needed)** — make issue creation emit a `## Blocked by` section
  listing blocker refs, in two cases: a body-backstop tracker (the body *is* the truth), or a
  GitHub-native-with-drafts repo (blockers drafted in the body, then promoted). A GitHub repo that
  authors native links directly needs neither.

Follow-up (GitHub-native-with-drafts only): run `backlog`'s `promote-body-to-native.py` once after
each creation batch to bridge the new bodies into the native graph.

`setup-skills` makes these edits in place — see it for why the vendored doc, not `CLAUDE.md`, is what
gets edited. The reader/bridge tooling ships with the `backlog` skill (installed via `npx skills`),
not the repo.
