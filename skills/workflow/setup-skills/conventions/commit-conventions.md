# Commit conventions

1. **Match the prevailing shape.** The repo's existing `git log` is the reference; a new commit reads
   like the ones before it. Absent a clear pattern, use `type: subject` (Conventional Commits) —
   `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

2. **Subject states the change, not the narrative.** Imperative mood, one line, no issue or task IDs,
   no session or PR story. The body (when needed) says *why* a non-obvious change holds.

3. **One coherent change per commit.** A commit is the smallest self-contained unit that leaves the
   tree green — not a checkpoint of unrelated edits.

4. **Trailers carry attribution.** Co-authorship and sign-off go in trailers at the end of the
   message, not woven into the subject or body.
