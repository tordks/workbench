#!/usr/bin/env python3
"""Thin `gh` CLI helpers shared by the GitHub-backed readers and the bridge."""

from __future__ import annotations

import subprocess


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def repo() -> str:
    return gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
