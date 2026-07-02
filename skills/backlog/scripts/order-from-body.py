#!/usr/bin/env python3
"""Backlog reader — in-body `## Blocked by` backstop.

For repos whose tracker has no native dependency graph: derive the dependency edges from each
issue's `## Blocked by` body section instead of a native graph, then hand the nodes graph to
`order_core`. The primary reader is `order-from-github-deps.py` (GitHub native graph); use this
only where the body is the source of truth (see the issue-dependency conventions).

The `## Blocked by` body section is a convention this workflow establishes per-repo (recorded in
the repo's issue-creation convention by `setup-skills`); it is not something the mattpocock issue
skills emit by default. This reader only works where that convention is in force.

Scope: this reads issues via `gh`, so it fits a GitHub repo that keeps blockers in the body rather
than the native graph. A genuinely foreign tracker (local markdown, freeform prose) has no
`## Blocked by` grammar to parse — the backlog skill builds the nodes graph in-agent there and
feeds `order_core` directly.

Usage:
  scripts/order-from-body.py           # topo-ordered list; ready issues marked "▶"
  scripts/order-from-body.py --next    # print just the next ready issue number(s)
  scripts/order-from-body.py --json    # machine-readable {order, ready}

Requires: `gh` authenticated in a clone of the repo. No third-party deps.
"""

from __future__ import annotations

import json
import sys

from bodyparse import blockers_from_body
from ghlib import gh
from order_core import run


def load() -> dict[int, dict]:
    issues = json.loads(
        gh(
            "issue", "list", "--state", "open", "--limit", "500",
            "--json", "number,title,labels,body",
        )
    )
    nodes: dict[int, dict] = {
        it["number"]: {
            "number": it["number"],
            "title": it["title"],
            "labels": {lbl["name"] for lbl in it["labels"]},
            "blocked_by": [],
        }
        for it in issues
    }
    open_nums = set(nodes)
    for it in issues:
        n = it["number"]
        want = blockers_from_body(it["body"] or "", n)
        # keep only blockers that are still open; closed ones are satisfied
        nodes[n]["blocked_by"] = sorted(b for b in want if b in open_nums)
    return nodes


if __name__ == "__main__":
    run(load(), sys.argv[1] if len(sys.argv) > 1 else "")
