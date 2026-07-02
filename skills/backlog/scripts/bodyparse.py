#!/usr/bin/env python3
"""Grammar for the in-body `## Blocked by` section.

The `## Blocked by` body section — a heading followed by `#NN` references — is a convention this
workflow establishes per-repo (recorded in the repo's issue-creation convention by `setup-skills`),
not an upstream default. Two consumers read the grammar: `promote-body-to-native.py` (bridges it
into GitHub's native graph) and `order-from-body.py` (the backstop reader for trackers with no
native graph). Defining the grammar here keeps those two in lockstep.
"""

from __future__ import annotations

import re

# `#NN` references inside the "## Blocked by" section, up to the next markdown heading.
_SECTION = re.compile(r"^##\s+Blocked by\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
_REF = re.compile(r"#(\d+)")


def blockers_from_body(body: str, self_num: int) -> set[int]:
    """The `#NN` referenced under the issue's `## Blocked by` heading, minus self-references."""
    m = _SECTION.search(body or "")
    if not m:
        return set()
    return {int(n) for n in _REF.findall(m.group(1))} - {self_num}
