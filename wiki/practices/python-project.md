---
type: practice
title: Python project setup
aliases: [python-project, python-setup]
tags: [python, tooling, testing]
created: 2026-07-02
updated: 2026-07-02
status: draft
related: ["[[react-vite-project]]"]
---

# Python project setup

A setup recipe, not a scaffold — an agent (or you) executes these steps to stand up a new Python
project with the conventions below. `uv` does the scaffolding; this page is *what to run and why*.

## Bootstrap
```
uv init <name>            # creates pyproject.toml + src layout
cd <name>
uv add --dev pytest mypy ruff vulture pre-commit
```

## Conventions
- **Package manager:** `uv` (lockfile `uv.lock`, committed). Run everything via `uv run …`.
- **Layout:** `src/<package>/` for code, `tests/` for tests.
- **Types:** `mypy` in **strict** mode over `src`. Type everything.
- **Lint + format:** `ruff check` and `ruff format`.
- **Dead code:** `vulture`.
- **Tests:** `pytest`. Prefer **integration tests** over heavy mocking; for external deps
  (databases, services) use `testcontainers` (ephemeral, real) rather than fakes where practical.
- **CLI:** `Typer` for command-line entrypoints.

## Gate everything with one command
`pre-commit` runs ruff (lint + format) + mypy + vulture together. Prefer it over invoking each tool
by hand; scope it to changed files:
```
pre-commit run --files <changed-file> ...
pre-commit run --all-files
```

## Commands cheat-sheet
```
uv run pytest
uv run mypy src
uv run ruff check src tests
uv run ruff format src tests
```
