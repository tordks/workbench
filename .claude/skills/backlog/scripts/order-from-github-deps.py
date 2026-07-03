#!/usr/bin/env python3
"""Backlog reader — GitHub native dependency graph.

Reads GitHub's native issue dependencies (`gh api repos/OWNER/REPO/issues/N/dependencies/blocked_by`),
builds the nodes graph, and hands it to `order_core` for topo-sort + ready computation. This is the
primary reader for a GitHub repo; the backstop for trackers without a native graph is
`order-from-body.py`.

Usage:
  scripts/order-from-github-deps.py           # topo-ordered list; ready issues marked "▶"
  scripts/order-from-github-deps.py --next    # print just the next ready issue number(s)
  scripts/order-from-github-deps.py --json    # machine-readable {order, ready}

Requires: `gh` authenticated in a clone of the repo. No third-party deps.
"""

from __future__ import annotations

import json
import sys

from ghlib import gh, repo
from order_core import run


def load() -> dict[int, dict]:
    slug = repo()
    issues = json.loads(
        gh("issue", "list", "--state", "open", "--limit", "500", "--json", "number,title,labels")
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
    for n, node in nodes.items():
        raw = gh(
            "api", f"repos/{slug}/issues/{n}/dependencies/blocked_by", "--jq", ".[].number"
        ).split()
        # keep only blockers that are still open; closed ones are satisfied
        node["blocked_by"] = [int(x) for x in raw if int(x) in open_nums]
    return nodes


if __name__ == "__main__":
    run(load(), sys.argv[1] if len(sys.argv) > 1 else "")
