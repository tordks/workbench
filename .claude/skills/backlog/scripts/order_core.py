#!/usr/bin/env python3
"""The ordering engine shared by every backlog reader.

A *reader* (one per issue tracker / source shape) produces a `nodes` graph; this module turns it
into a dependency order + ready set and presents it. Defining topo-sort and the "ready" rule here
once keeps every reader's output identical — this file is the canonical definition of "ready".

An issue is **ready** when it is open, no *open* issue blocks it, and it carries the
`ready-for-agent` label (fully specified). Closed blockers are treated as satisfied.

Node shape a reader must produce, keyed by issue number:
    {"number": int, "title": str, "labels": set[str], "blocked_by": list[int]}
`blocked_by` must already be filtered to *open* blockers.
"""

from __future__ import annotations

import json
import sys

READY_LABEL = "ready-for-agent"


def topo(nodes: dict[int, dict]) -> list[int]:
    """Kahn's algorithm, breaking ties by issue number for stable output."""
    order: list[int] = []
    placed: set[int] = set()
    remaining = set(nodes)
    while remaining:
        ready = sorted(n for n in remaining if all(b in placed for b in nodes[n]["blocked_by"]))
        if not ready:  # a cycle — surface it rather than hang
            cycle = sorted(remaining)
            sys.exit(f"error: dependency cycle among {['#%d' % c for c in cycle]}")
        for n in ready:
            order.append(n)
            placed.add(n)
            remaining.discard(n)
    return order


def is_ready(node: dict) -> bool:
    return not node["blocked_by"] and READY_LABEL in node["labels"]


def run(nodes: dict[int, dict], arg: str = "") -> None:
    """Topo-sort, compute the ready set, and present per `arg` (default | --next | --json)."""
    order = topo(nodes)
    ready = [n for n in order if is_ready(nodes[n])]

    if arg == "--next":
        print("\n".join(str(n) for n in ready))
        return
    if arg == "--json":
        print(json.dumps({"order": order, "ready": ready}, indent=2))
        return

    for n in order:
        node = nodes[n]
        if is_ready(node):
            mark, why = "▶", "ready"
        elif node["blocked_by"]:
            mark, why = " ", "blocked by " + ", ".join(f"#{b}" for b in node["blocked_by"])
        else:
            mark, why = " ", f"needs {READY_LABEL}"
        print(f"{mark} #{n:<3} {node['title']}  ({why})")
