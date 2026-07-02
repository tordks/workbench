"""Extract documentation from Python sources for a review-docs Scan.

Emits every docstring with its `file:line` and the signature it attaches to, plus
every comment — the compact bundle a review subagent reads instead of the source
tree. The signature travels with each docstring so the reviewer can judge whether
the docstring stays in its own unit and still matches the code (Rules 3-4). Prose
files (`*.md`, ADRs) are already documentation and are read directly, not harvested.

Usage:
    python harvest_docs.py <path> [<path> ...]

Each path is a file or directory; directories are walked for `*.py`. Output is
grouped by file, docstrings and comments in source order.
"""

from __future__ import annotations

import ast
import sys
import tokenize
from pathlib import Path


def _signature(lines: list[str], node: ast.AST, doc_lineno: int) -> str:
    """The header of `node` — its `def`/`class` line(s) up to the docstring.

    Spans multi-line signatures: everything from the node's own line to the line
    before the docstring begins.
    """
    start = node.lineno - 1
    header = lines[start : doc_lineno - 1] or lines[start : start + 1]
    return "\n".join(line.rstrip() for line in header).strip()


def _harvest_file(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    out: list[tuple[int, str]] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"  [skipped: {exc.msg} at line {exc.lineno}]"]

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is None:
            continue
        doc_node = node.body[0]
        lineno = getattr(doc_node, "lineno", 1)
        if isinstance(node, ast.Module):
            header = "<module>"
        else:
            header = _signature(lines, node, lineno)
        block = f"  [docstring] L{lineno} {header}\n" + "\n".join(
            f"      {line}" for line in doc.splitlines()
        )
        out.append((lineno, block))

    with path.open("rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type == tokenize.COMMENT:
                out.append((tok.start[0], f"  [comment] L{tok.start[0]} {tok.string}"))

    return [block for _, block in sorted(out, key=lambda pair: pair[0])]


def _iter_py(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
        elif p.suffix == ".py":
            files.append(p)
    return files


def main(argv: list[str]) -> int:
    paths = argv or ["."]
    for path in _iter_py(paths):
        blocks = _harvest_file(path)
        if blocks:
            print(f"=== {path} ===")
            print("\n".join(blocks))
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
