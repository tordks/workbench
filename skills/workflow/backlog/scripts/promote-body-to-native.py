#!/usr/bin/env python3
"""Promote in-body `## Blocked by` sections into GitHub's native issue dependencies.

Where a repo records blockers in a `## Blocked by` body section (a convention this workflow
configures per-repo via `setup-skills`) but wants GitHub's native `blocked_by` links to be the
source of truth (see the issue-dependency conventions), this script is the creation-time bridge:
parse each body section, resolve `#NN` to a numeric id, and POST the missing native links. Run once
per creation batch, after issues are created.

Usage:
  promote-body-to-native.py            # add missing native links from the bodies (additive; default)
  promote-body-to-native.py --mirror   # also DELETE native links absent from the bodies (full reconcile)
  promote-body-to-native.py --check    # report drift/dangling refs; write nothing; exit 1 if any drift

Requires: `gh` authenticated in a clone of the repo. No third-party deps.
"""

from __future__ import annotations

import json
import subprocess
import sys

from bodyparse import blockers_from_body
from ghlib import gh, repo


def open_issues() -> list[dict]:
    return json.loads(
        gh("issue", "list", "--state", "open", "--limit", "500", "--json", "number,body")
    )


def native_links(repo_slug: str, num: int) -> set[int]:
    raw = gh(
        "api", f"repos/{repo_slug}/issues/{num}/dependencies/blocked_by", "--jq", ".[].number"
    ).split()
    return {int(x) for x in raw}


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    check = arg == "--check"
    mirror = arg == "--mirror"

    repo_slug = repo()
    issues = open_issues()
    open_nums = {it["number"] for it in issues}
    id_cache: dict[int, int] = {}

    def numeric_id(num: int) -> int | None:
        if num not in id_cache:
            try:
                id_cache[num] = int(gh("api", f"repos/{repo_slug}/issues/{num}", "--jq", ".id"))
            except subprocess.CalledProcessError:
                return None  # nonexistent number — a typo in a hand-edited body
        return id_cache[num]

    drift = False
    for it in issues:
        num = it["number"]
        want = blockers_from_body(it["body"] or "", num)
        have = native_links(repo_slug, num)

        for dangling in (want - open_nums) - have:
            # Body names a blocker that isn't an open issue: closed (already satisfied) or a typo.
            if numeric_id(dangling) is None:
                print(f"#{num}: body references #{dangling}, which does not exist")
                drift = True

        to_add = {b for b in (want - have) if b in open_nums}
        to_remove = (have - want) if mirror else set()

        for b in sorted(to_add):
            bid = numeric_id(b)
            if bid is None:
                continue
            drift = True
            if check:
                print(f"#{num}: would add blocked_by #{b}")
            else:
                gh(
                    "api", "--method", "POST",
                    f"repos/{repo_slug}/issues/{num}/dependencies/blocked_by",
                    "-F", f"issue_id={bid}",
                )
                print(f"#{num}: added blocked_by #{b}")

        for b in sorted(to_remove):
            bid = numeric_id(b)
            if bid is None:
                continue
            drift = True
            if check:
                print(f"#{num}: would remove blocked_by #{b}")
            else:
                gh(
                    "api", "--method", "DELETE",
                    f"repos/{repo_slug}/issues/{num}/dependencies/blocked_by/{bid}",
                )
                print(f"#{num}: removed blocked_by #{b}")

    if check and drift:
        sys.exit(1)


if __name__ == "__main__":
    main()
