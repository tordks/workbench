## 05. Concurrent-Write Safety

This cluster decides how a cloud-hosted, team-shared MCP wiki keeps two writers — agents, humans, and sync clients — from silently clobbering each other's edits, while the canonical store stays plain git-diffable markdown. The moment the wiki leaves a single WSL box and becomes a persistent service several people and agents ingest into, "just save the file" is no longer safe: two `wiki-ingest` runs can race the same page and one write vanishes. The question is which coordination mechanism prevents lost updates without making any tool's own store/format the source of truth. The answer is not a single product but a **pattern** — optimistic concurrency via a precondition token, applied by exactly one serializer, with an immutable audit trail — which shows up in four different guises (a file convention, an HTTP header, a database's internals, and git's object model).

**Takeaways:**
- **Adopt optimistic concurrency (precondition hash / ETag-If-Match) as the core per-file safety primitive** — cheapest guarantee of no lost updates that keeps markdown literal.
- **Serialize the apply step through one writer** (a single ingest process / "compactor" / write queue) so applies never race each other; do not build bespoke locking.
- **Use `obsidian-memory-for-ai`'s propose→apply→receipt as the template** for the write path — it maps almost one-to-one onto the repo's existing `inbox/` + ingest-skill + git structure.
- **Use git branch-per-write + PR/merge-queue as the outer coordination layer** for multi-file ingest batches; the PR *is* propose, the merge *is* apply, the commit *is* the receipt.
- **Advisory file locking (flock/lock-files) is the weakest fit** — documented-unreliable on exactly the NFS/cloud-sync/multi-machine setup this wiki targets; use only as a same-host best-effort layer, never the sole guarantee.
- **CRDTs (Yjs/Automerge) are categorically disqualified as the canonical store** — their real storage is a binary/structured CRDT doc, not plain markdown; git-diffability is an explicit non-goal.
- **All-in-one KB servers (Basic Memory) punt** on documented concurrent-write conflict resolution; borrow the "files canonical, index rebuildable" architecture, not the write path.

### The mechanisms at a glance

| Mechanism | Prevents lost updates? | Keeps markdown canonical? | Extra infra | Multi-file atomic? | Fit for cloud/team/multi-machine | License |
|---|---|---|---|---|---|---|
| Advisory locking (flock/fcntl/lock-file) | Only if every writer honors it | Yes | None | No | **Poor** — unreliable on NFS/cloud-sync | OS syscall / convention |
| Precondition hash (ETag/If-Match, GitHub `sha`) | Yes (detects, rejects stale) | **Yes — cleanest fit** | Thin write API or git SHA check | Per-file only | **Strong** | Protocol pattern (none) |
| propose→apply→receipt (obsidian-memory-for-ai) | Yes (precondition_hash) | Yes (envelopes/receipts are md/YAML) | None (files + shell script) | Ordered, not ACID | **Strong** | Unstated — verify |
| Git branch-per-write + PR/merge-queue | Yes (structural, merge refuses stale) | **Yes — native git** | Git host (already present) | **Yes** (a commit) | **Strong** | Free / merge-queue plan-gated |
| Serialized write queue (single-writer/actor) | **Yes — by construction** | Yes (if writer only applies diffs) | One always-on process | Depends on impl | **Strong** | Architectural pattern |
| CRDTs (Yjs/Automerge) | **Yes — automatic merge** | **NO — binary/structured CRDT store** | Live sync server + runtime | Yes (doc model) | Disqualified as store | MIT (Yjs), MIT/Apache (Automerge) |
| All-in-one KB (Basic Memory) | Undocumented | Yes (files + rebuildable index) | SQLite/Postgres index | Undocumented | **Caution — unverified** | AGPL-3.0 |

---

### 1. Advisory file locking (flock/fcntl, lock-file convention)

Source: [man7.org/linux/man-pages/man2/flock.2.html](https://man7.org/linux/man-pages/man2/flock.2.html)

**What it is.** OS-level or convention-level locks — `flock(2)` / `fcntl()` byte-range locks, or a plain "lock-file exists" convention — that a writer acquires before touching a file and releases after. It gates byte-level access to one file so two writers don't interleave a torn, mid-write state.

**How it would apply here.** In principle it could gate writes to individual wiki markdown pages so two writers don't interleave — but only if *every* writer (each agent, Obsidian's own autosave, a human's editor, a sync client) shares and honors the same lock protocol. That "everyone participates" precondition is exactly what a heterogeneous team+agent+sync environment cannot guarantee.

**Key points / gotchas:**
- **Advisory, not mandatory.** Nothing in the OS enforces the lock. A non-participating writer — a stray script, Obsidian's autosave, an agent that skips the check — writes anyway. The lock only works among cooperating processes.
- **Reliability collapses on network/shared filesystems.** `flock()` historically did **not** lock over NFS at all. Since Linux 2.6.12 the NFS client emulates it via `fcntl()` byte-range locks, but there is **no portable way to detect whether locking actually works** on a given NFS-style mount, and many implementations still get it wrong. Cloud-sync mounts (rclone, Dropbox, OneDrive, WSL/NTFS bridges) are in this danger zone.
- **A lock is not guaranteed released on SIGKILL.** Per ["On the Brokenness of File Locking"](http://0pointer.de/blog/projects/locking.html), a crashed writer that receives `SIGKILL` can wedge the resource indefinitely. The locker also needs write access to the *containing directory*, and there is no cross-platform correctness guarantee.
- **The NFS-safe fallback isn't flock at all.** The portable lock-file primitive over NFS is **atomic hard-link creation** (`link()`), because `link` is atomic across NFS-shared mounts while `flock`/`fcntl` are not (see the [NFS locking chapter](https://docstore.mik.ua/orelly/networking_2ndEd/nfs/ch11_02.htm)). If you *must* lock on a shared mount, you use the hard-link trick, not `flock`.
- **Locks prevent torn writes, not semantic conflicts.** Serializing byte-level access to one file handle says nothing about detecting that two edits touched the same paragraph or the same frontmatter field. It stops corruption, not lost meaning.

**Constraints.** No license (kernel syscall / OS convention). Platform-dependent: local ext4/xfs reliable, NFS/cloud-sync unreliable. Zero extra infra.

**Maturity.** `flock(2)` is a decades-old, universally available POSIX/Linux syscall; the lock-file-via-hardlink pattern is an old, well-understood workaround, not a maintained project.

**Verdict.** *Avoid as the primary mechanism.* Fine as a cheap best-effort guard on a single trusted host, unsafe as the sole safety net for a shared cloud filesystem with heterogeneous writers. This is the **weakest fit** for this wiki precisely because the target environment (multi-machine, cloud, WSL/Windows plus other team members' machines) is the exact scenario where advisory locks are documented to be unreliable.

---

### 2. Optimistic concurrency via precondition hash / ETag-If-Match

Source: [docs.github.com/en/rest/repos/contents](https://docs.github.com/en/rest/repos/contents)

**What it is.** A reader captures a content hash (or ETag) when it fetches a file. The writer submits that hash with its write request. The server rejects the write (HTTP 409 / 412) if the current hash no longer matches — meaning someone else wrote in between. This is classic **optimistic concurrency control (OCC)**: it *detects* collisions rather than *preventing* them.

**How it would apply here.** Directly usable. Any write path — a small HTTP/MCP write service in front of the markdown folder — can require callers to send the SHA/hash of the page they last read. An ingest agent then can *never* silently clobber a page another agent just changed: the write races, but a stale precondition causes a hard rejection instead of an overwrite. Because `vault_read` already returns page content, hashing it before proposing a change is trivial to bolt on.

**Key points / gotchas:**
- **Detects, does not prevent, collisions.** The write is allowed to race; a stale precondition triggers a hard rejection instead of a silent overwrite. Not locking — OCC.
- **Two agents on the same page.** Whichever write lands first succeeds and advances the hash. The second agent's stale hash is caught at commit time; it must re-read, re-apply (possibly re-diff), and retry. No lost update, but **the loser must implement the retry/merge itself** — it is not automatic.
- **Preserves plain markdown perfectly.** The hash is *metadata about* the file, not a new storage format. This is the **cleanest fit** with the hard "files stay canonical markdown" constraint of any mechanism surveyed.
- **Awkward for multi-file atomic changes.** An ingest that touches `inbox/` + a concept page + a map page together has no built-in multi-file transaction; each file's precondition is checked independently. (This is where the git-PR outer layer, mechanism 4, complements it.)
- **A client-side retry-with-backoff loop is mandatory, not optional.** Real-world GitHub API users report intermittent 409s even with a supposedly fresh sha, due to propagation delay between read and write. Budget for retries.

**Concrete details:**
- **GitHub REST Contents API** — `PUT /repos/{owner}/{repo}/contents/{path}` requires the current blob `sha`. If the file changed since you fetched it, the API returns **409** with a message like `"...is at <currentSha> but expected <providedSha>"`, forcing a re-fetch-and-retry loop. This is the concrete, production-grade reference implementation of the exact pattern, at scale, for markdown or any files in git.
- **HTTP semantics generally** — `If-Match` with an ETag on `PUT`/`PATCH` returns **412 Precondition Failed** on mismatch ([RFC 7232](https://www.rfc-editor.org/rfc/rfc7232)) — the general-purpose version of GitHub's specific 409 behavior.

**Constraints.** No license issue — it's a protocol pattern, implementable in any language with a hash function and a thin write API. Complexity low-to-moderate (needs a small service or a git-native SHA check), but requires callers to implement retry logic.

**Maturity.** GitHub Contents API is stable, heavily used, production-grade since GitHub's early API days; general HTTP conditional-request semantics (RFC 7232) is a long-standing IETF standard.

**Verdict.** *Adopt as the core per-file safety mechanism for the write path.* Cheapest way to guarantee no lost updates while keeping markdown as literal source of truth; pair with a retry/merge policy for the loser.

---

### 3. obsidian-memory-for-ai propose→apply→receipt protocol (v3.1)

Source: [github.com/jrcruciani/obsidian-memory-for-ai](https://github.com/jrcruciani/obsidian-memory-for-ai)

**What it is.** A three-stage cooperative-concurrency workflow for agent-authored markdown memory:
1. **Propose** — agents write proposed changes as *operation-envelope* files into an inbox, **never touching canonical files directly**.
2. **Apply** — a trusted *compactor* validates preconditions and applies non-conflicting operations.
3. **Receipt** — applied/rejected outcomes are recorded as **immutable receipts**.

**How it would apply here.** A near-exact template for `wiki-ingest`. Agents never write `wiki/` pages directly; they drop proposed changes (with a precondition hash) into an inbox-like staging area; a compaction step (human or scripted) validates, applies, and writes an audit receipt. This is directly compatible with the repo's existing `inbox/` + ingest-skill design — the mapping is nearly one-to-one.

**Key points / gotchas:**
- **Lost updates prevented via `precondition_hash`.** The compactor recomputes the current file's hash at apply time and compares it to the hash recorded when the operation was proposed. A mismatch means someone else wrote first; the operation is marked `conflict` rather than applied. Same OCC idea as ETag/If-Match, but **file-based and git-auditable** instead of HTTP-based.
- **Two agents on the same page.** If they edit *different* files/predicates (e.g. `facts/elena-voss/employer.md` vs `.../role.md`), both apply cleanly, no collision. If they target the *exact same file*, whichever applies first wins and the second's precondition hash mismatches, surfacing in `_views/conflicts.md` / `_views/contradictions.md` for a human to resolve (merge, pick one, or create a new versioned predicate with `superseded_by`).
- **Advisory claims are explicitly *not* the safety mechanism.** `memory/_claims/{target-id}.yaml` (exclusive file creation with an `expires_at`) is an optional pre-write collision-avoidance signal layered *on top of* the hash check. The spec explicitly states these are "intentionally weaker than locks" and "diagnostic only" on cloud-synced filesystems — i.e. the design **does not trust locking**, only the hash check. (This corroborates mechanism 1's verdict from a second source.)
- **Fully preserves plain git-diffable markdown.** Envelopes, claims, and receipts are themselves markdown/YAML files under `memory/_inbox/`, `memory/_claims/`, `memory/_ops/applied/`. Nothing binary, nothing outside git; the full history is auditable via `git log` on those directories.
- **Scoped as "cooperative concurrency, not transactional ACID"** for small agent teams with human oversight — not a correctness claim under adversarial or high-throughput load. The trusted compactor is a **serialization point** (see mechanism 5) that this design leans on to avoid needing distributed locking at all.

**Concrete details:**
- **Envelope path:** `memory/_inbox/{agent-id}/ops/{operation-id}.md`. Frontmatter fields include `operation_id`, `op`, `agent_id`, `target_id`, `target_path`, `precondition_hash`, `status` (state machine: `proposed → validated → applied → rejected → conflict → superseded`), and a `payload` block with the actual content to write.
- **Claim path:** `memory/_claims/{target-id}.yaml`, created via exclusive file creation (fails if it already exists); fields `agent_id`, `operation_id`, `claimed_at`, `expires_at`, `reason`. Stale (expired) claims do not block new writes.
- **Apply step:** `tools/compact.sh` validates schema (`operation.schema.yaml`), checks the precondition hash against the current file (or `null` if the file doesn't exist yet), applies if it matches, writes the applied receipt to `memory/_ops/applied/{operation-id}.md`, and rebuilds `_views/` (including `_views/conflicts.md` and `_views/contradictions.md`) from canonical `facts/` + `events/` + `_archive/`.
- **Deterministic processing order:** compaction walks the inbox in **lexicographic order by `operation_id`** (which embeds a timestamp), giving a reproducible, auditable apply sequence.

**Constraints.** **No stated license found on the fetched spec page — verify before vendoring/adapting text verbatim into a skill** (open question). Zero extra infrastructure: pure convention over files plus a shell script — no server, no database, no daemon.

**Maturity.** Stated as "current stable version v3.1." Single-maintainer GitHub project (`jrcruciani/obsidian-memory-for-ai`), not a widely-adopted standard, but the mechanics are simple enough to audit and adopt directly.

**Verdict.** *Adopt as the closest existing template for wiki-ingest's write path.* Purpose-built for exactly this scenario (agent-authored markdown memory, human-in-the-loop apply, git as the audit trail); needs only light adaptation to the wiki's existing `inbox/` + type taxonomy.

---

### 4. Git-branch-per-write + merge/PR (or a staging/integration branch)

Source: [docs.github.com/.../managing-a-merge-queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

**What it is.** Each writer (agent or human) makes its ingest/edit on its own branch or worktree, then merges back to `main` via a PR — optionally through a **merge queue** that serializes merges and re-tests each before landing. For many concurrent branches, an intermediate **integration/staging branch** absorbs merges before a final promotion to `main`.

**How it would apply here.** A natural fit given the repo is already git-based. An ingest agent works on `ingest/<page>-<timestamp>`, opens a PR, and either a human or an automated merge-queue check (e.g. `wiki-lint`) gates the merge. Git's own three-way merge and standard PR review become the conflict-resolution mechanism.

**Key points / gotchas:**
- **Prevents lost updates structurally.** Git's merge (or GitHub's merge queue) refuses to fast-forward/merge if the branch is stale relative to `main` in a conflicting way, forcing a rebase/re-merge. The write is never silently applied over someone else's change.
- **Two agents editing the same page.** Non-overlapping lines → git's line-based three-way merge auto-resolves. Same lines (both add a bullet to the same list, both edit the same paragraph) → a textual merge conflict requiring resolution. **Git does not understand markdown/wikilink semantics**, so semantically-different-but-textually-overlapping edits (e.g. two agents each renaming the same heading differently) surface as ordinary line conflicts, not smart merges — and, worse, non-overlapping-but-semantically-conflicting edits can auto-merge into a *textually clean but semantically broken* result (see the residual-risk note below).
- **Fully preserves git-diffable plain markdown by construction.** This is literally native git — the most "markdown stays canonical" of all mechanisms; no side format, no derived state to keep in sync.
- **Merge queue serializes merges one-at-a-time.** GitHub's merge queue groups multiple approved PRs, merges each temporary branch with the *latest* `main`, runs required status checks, and merges to `main` only if checks pass — exactly a queueing solution to the concurrent-write problem, layered on top of git.
- **Moderate complexity.** Needs branch/PR tooling (present in any git host), a policy for how many agents work in parallel before contention on the same pages becomes frequent, and ideally a lint/consistency check (`wiki-lint`) as a *required status check* so index rebuilds and dangling-link checks gate the merge rather than running after the fact.

**Concrete details:**
- **GitHub merge queue** — enabled per-branch via a branch-protection rule. PRs are added to the queue after passing required reviews; GitHub creates a temporary merge commit combining the PR with the latest target-branch state, runs CI against it, and merges only if checks pass — otherwise removes it from the queue.
- **Parallel-agent staging pattern** — create a shared integration branch, merge each agent's ingest branch into it first, run tests/lint there, then fast-forward or PR that integration branch into `main` once green. Keeps `main` always stable under many concurrent contributors.
- **Git worktrees** — `git worktree add` gives each agent an isolated working directory sharing one `.git` object store, so parallel agents never collide on the working tree itself, only at merge time where standard git tooling (and conflict markers) surface any overlap.

**Constraints.** No license issue; free on GitHub for public/most private repo tiers. **Merge queue requires GitHub Team/Enterprise-tier branch protection in some plans — verify the team's current plan gating** (open question), or approximate it on any git host with a simple serialize-and-test script.

**Maturity.** Git merging is decades-mature; GitHub's merge queue is a current, actively documented and maintained product feature (docs page live as of this research).

**Verdict.** *Adopt for the ingest workflow's outer loop.* Pairs naturally with the propose→apply→receipt inner mechanism — **the PR *is* the propose step, the merge *is* the apply step, the merged commit *is* the receipt** — and requires no new infrastructure beyond the git host already in use.

---

### 5. Serialized write queue (single-writer / actor pattern)

Source: [dev.to/daichikudo/...sqlite-wal-mode](https://dev.to/daichikudo/fixing-claude-codes-concurrent-session-problem-implementing-memory-mcp-with-sqlite-wal-mode-o7k)

**What it is.** All writes funnel through one process/lock — a queue, a single-writer actor, or a database's own single-writer discipline — that applies them one at a time, eliminating races **by construction** rather than detecting them after the fact.

**How it would apply here.** Implement it as the trusted "compactor" in the propose→apply→receipt model, or as a small write-service in front of the markdown folder that agents call instead of touching files directly, guaranteeing writes never interleave. Even something as simple as one Python process reading the `inbox/` directory in a loop satisfies this.

**Key points / gotchas:**
- **Prevents lost updates by construction.** Only one writer executes at a time, so there is no window in which two writes race — a **stronger guarantee than optimistic hash-checking**, at the cost of a serialization bottleneck and a single point of failure/backpressure.
- **Two agents on the same page.** Both requests are processed in arrival order by the sole writer; the second operates on the already-updated state, so no data is lost. But if the second agent's proposed diff was computed against stale content, it may still need to re-derive its edit — **this pattern prevents corruption, not semantic staleness**, so it still benefits from being paired with precondition hashes so the second writer *notices* it's stale and re-plans.
- **Preserves git-diffable markdown perfectly** if the single writer's only job is applying validated diffs to plain files (no new storage format required).
- **Concretely demonstrated via SQLite WAL mode.** WAL mode ("single writer, many readers") plus a `busy_timeout` lets concurrent sessions read/write one DB file without corruption, because SQLite serializes writers internally and blocks/waits rather than racing.
- **Low complexity if a queue/actor is already natural** (e.g. a single always-on ingest service). It becomes the availability bottleneck under load and needs its own **crash-recovery story (queue durability)** if the process dies mid-batch — which the `inbox/` directory itself can provide (persist pending writes as files).

**Concrete details:**
- **dev.to writeup (Daichi Kudo):** *"the `busy_timeout` is critical — if two sessions try to write simultaneously, the second one waits up to 5 seconds instead of failing immediately... allowing 10+ concurrent Claude Code sessions to read and write the same `memory.db` without corruption or blocking."* SQLite WAL mode as the concrete single-writer-with-queueing implementation.
- **`RMANOV/sqlite-memory-mcp`** and **`Daichi-Kudo/mcp-memory-sqlite`** (GitHub) — existing drop-in MCP memory servers built specifically around WAL-mode SQLite for the concurrent-agent-write scenario. Evidence the pattern is a known, reusable building block, not novel. (Caveat: in *those* designs SQLite *is* canonical — not applicable here unchanged; the **technique** transfers, not the tool.)
- **General shape:** a queue/actor sits in front of the canonical files; write requests are appended; a single consumer loop pops requests, validates (ideally against a precondition hash), applies to the markdown file, and acks/rejects — the same shape as the compactor step of propose→apply→receipt, framed as infrastructure rather than a file convention.

**Constraints.** No license issue (architectural pattern). Complexity low if there's already a natural single service. Needs its own durability plan (persist the queue, e.g. via the `inbox/` directory) so a crash doesn't lose pending writes.

**Maturity.** The WAL-mode SQLite variant is production-proven with multiple maintained open-source MCP servers; the generic single-writer-actor pattern is a decades-old, well-understood distributed-systems building block.

**Verdict.** *Adopt as the implementation strategy for whichever process ends up being the "trusted compactor/apply step."* Don't build bespoke locking; use a single-writer queue (even one Python process reading `inbox/` in a loop) fronting the markdown files, combined with precondition hashes so late-queued writers detect staleness rather than blindly overwrite. **No primary source was found describing a purpose-built "serialized write queue as a service" for markdown wikis specifically** (open question) — this would be built bespoke, consistent with the repo's stdlib-only skill-scripting constraint.

---

### 6. CRDTs for collaborative editing (Yjs, Automerge)

Source: [github.com/yjs/yjs](https://github.com/yjs/yjs)

**What it is.** Conflict-free replicated data types let multiple peers concurrently mutate a shared document with automatic, mathematically-guaranteed merge — no conflicts, no central lock — originally built for real-time rich-text/collaborative editors (the Yjs/Automerge/Loro family).

**How it would apply here.** The **worst fit of the seven**. Usable in principle for a real-time co-editing UI, but **disqualified by the hard constraint** that canonical storage must stay plain git-diffable markdown — CRDTs do not store their document as plain text.

**Key points / gotchas:**
- **Prevents lost updates and merges two concurrent edits automatically** — this is CRDTs' whole purpose, and it merges without conflict markers or a human resolution step. On the "never lose an update, never block a writer" axis it is strictly stronger than every other mechanism here.
- **Does NOT preserve git-diffable markdown — confirmed from primary sources.** [electric.ax on AI agents as CRDT peers](https://electric.ax/blog/2026/04/08/ai-agents-as-crdt-peers-with-yjs): *"The system uses structured rich text CRDT, not plain text... The underlying format is Yjs's binary CRDT representation, not human-readable markdown or text files"* and *"git-diffability is not addressed."* Markdown is used only as an **intermediate streaming format** parsed into native CRDT nodes, not as the storage of record.
- **Automerge is no better on this axis.** Automerge trades performance for a richer *Git-like change-history* model; Yjs is "the default choice... smallest bundle, good enough performance." But per the [pkgpulse CRDT comparison (2026)](https://www.pkgpulse.com/guides/yjs-vs-automerge-vs-loro-crdt-libraries-2026), even Automerge — the most git-history-friendly of the three — offers its **own internal history model, not literal git history over markdown files**. A separate exporter would have to flatten the CRDT doc back to markdown, reintroducing exactly the "CRDT as source of truth" problem the constraint disqualifies.
- **High infrastructure cost.** Needs a live sync transport (WebSocket / Durable-Streams-style server), a server-side peer/runtime if agents participate as CRDT peers (not just text-diff bots), and persistence for the CRDT doc itself — categorically heavier than a file-based propose/apply/receipt convention or a git PR.
- **"Steal the idea, not the tool."** The concurrent-merge guarantee is attractive, but adopting Yjs/Automerge as the write layer would make the CRDT engine (or its binary doc) the de facto source of truth for in-flight edits — precisely the disqualified pattern.

**Concrete details:**
- **[github.com/yjs/yjs](https://github.com/yjs/yjs)** — "Shared data types for building collaborative software"; exposes `Map`/`Array`/`Text` shared types whose changes are automatically distributed and merged among peers.
- **[electric.ax primary source](https://electric.ax/blog/2026/04/08/ai-agents-as-crdt-peers-with-yjs)** — agents act as server-side Yjs peers, translate tool calls into native CRDT ops, use a streaming markdown-to-CRDT-node parser, and require a transport layer (Durable Streams, self-hosted or cloud) plus a server-side agent runtime. Explicitly not a plain-text storage model; does not discuss git-diffability.

**Constraints.** Yjs: **MIT**, mature/widely used, small bundle. Automerge: typically **MIT/Apache-dual**, WASM-based, richer history at a performance cost. Both require a live sync server/persistence layer as additional infrastructure.

**Maturity.** Yjs: long-established, most mature CRDT ecosystem ("the incumbent"). Automerge: active, "the research-backed alternative." Both actively maintained as of 2026.

**Verdict.** *Avoid as the wiki's write-safety mechanism.* Violates the hard "plain markdown is canonical, no tool owns its own store/format" constraint outright. Reconsider only narrowly if a future real-time multi-cursor editing UI is wanted — as an *ephemeral* layer that exports back to markdown on save, never as the store of record. Not needed for an agent-driven ingest workflow, which is not humans typing concurrently in one buffer.

---

### 7. All-in-one KB/MCP servers' concurrent-write handling (Basic Memory, SQLite-backed memory MCPs)

Source: [github.com/basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)

**What it is.** A survey of how the all-in-one candidate from the prior single-user research (Basic Memory) and adjacent SQLite-backed memory MCP servers actually handle concurrent writers, now that the constraint has shifted to team/cloud use.

**How it would apply here.** Directly answers whether the previously-recommended all-in-one alternative is safe for team concurrent ingest as-is. It **is not clearly documented to be**. Its architecture (files as source of truth + a rebuildable SQLite index) is the useful part to borrow even if the tool itself isn't adopted for writes.

**Key points / gotchas:**
- **Files stay source of truth; the index is disposable.** Basic Memory keeps markdown files as source of truth with a derived SQLite/Postgres index kept in sync by `bm sync`, which "mitigates write conflicts by making files the source of truth." Even the index owner treats the index as rebuildable — consistent with this project's hard constraint. **But its README does not document a specific concurrent-write conflict-resolution algorithm** for simultaneous edits from multiple agents/clients.
- **Cloud/sync variant is under-documented.** Described only as "rclone-powered with conflict resolution" for bidirectional device sync — no further mechanism detail surfaced. **Treat as unverified rather than assume safe** before relying on it for concurrent team writes (open question).
- **It ships a drift *detector*, not a merge resolver.** `basic-memory doctor` does a "file ↔ DB consistency check" to detect when the SQLite index and markdown files have diverged — useful evidence that index/file divergence is an acknowledged real failure mode in this class of tool, reinforcing why the index must stay rebuildable/disposable rather than authoritative. **No documented automatic repair/merge algorithm for genuine concurrent-edit conflicts was found.**
- **Partial write-side guards.** `write_note` "guards against accidental overwrites"; `edit_note` supports append/prepend rather than full-file replace where possible. Partial mitigations, **not** a documented precondition-hash or locking scheme comparable to mechanisms 2–5.
- **Contrast with dedicated SQLite memory MCPs.** `RMANOV/sqlite-memory-mcp` and `Daichi-Kudo/mcp-memory-sqlite` solve *their* concurrency by making the database itself the concurrent-write-safe layer (WAL + `busy_timeout`) — which works because in those designs SQLite *is* canonical. **Not applicable here unchanged**, since this project's canonical store must stay markdown files. The transferable part is the *technique* (single-writer-with-wait, mechanism 5), not the tool.

**Concrete details:**
- **[github.com/basicmachines-co/basic-memory](https://github.com/basicmachines-co/basic-memory)** — **AGPL-3.0**; latest version **v0.22.1** (release notes dated **2026-06-13**); local-first MCP-native markdown personal knowledge graph with a SQLite/Postgres derived index.
- **`basic-memory doctor`** — documented as a file↔DB consistency checker; no documented automatic repair/merge for concurrent-edit conflicts in the fetched README.

**Constraints.** **AGPL-3.0** — copyleft, relevant if self-hosted-as-a-service for a team; verify obligations. Its own SQLite/Postgres index adds a moving part even though it's rebuildable. Its own writing-schema was already flagged as invasive in the prior single-user research.

**Maturity.** Active project, v0.22.1 as of 2026-06-13, but **concurrent multi-writer conflict handling specifically is not documented in depth** on its primary README.

**Verdict.** *Evaluate-with-caution / steal-the-idea.* The "files canonical, index disposable + rebuildable + diagnosable" architecture is exactly right and worth keeping, but **do not assume Basic Memory (or any all-in-one KB server) has solved team concurrent writes out of the box** — its concurrency story is thin/undocumented, and its AGPL-3.0 license plus own writing-schema were already flagged as invasive. If ever adopted as a passive-read layer that also accepts writes, its actual conflict algorithm needs a **source-code-level check, not just the README** (open question).

---

### Residual risk that no mechanism here fully solves

Every option except CRDTs shares one blind spot: **git's own three-way merge (and file-based precondition hashes) do not understand wikilink/frontmatter semantics.** Two agents renaming the same page differently, or both adding a new `related:` frontmatter entry via order-dependent list edits, can auto-merge into a *textually clean* but *semantically broken* result — a duplicated/rotated `related:` list, a dangling `[[wikilink]]` to the old page name — that **no write-safety mechanism in this cluster catches**. Only a post-merge/post-apply **`wiki-lint` pass** (its own cluster/skill) detects that class of error. **The write-safety layer and the lint layer are complementary, not substitutes for each other** — precondition hashes and serialization stop lost *updates*; lint stops lost *meaning*.

---

### Recommendation for this cluster

Adopt a **composite pattern, not a single product** — the same idea in four guises:

1. **`obsidian-memory-for-ai`'s propose→apply→receipt** as the inner per-write contract. Agents drop operation envelopes into `inbox/` (propose); a serialized applier validates and applies (apply); git commits are the immutable receipt. This maps almost one-to-one onto the repo's existing `inbox/` + ingest-skill + git structure, so it is nearly zero net-new machinery.
2. **Precondition hashes (ETag/If-Match / GitHub-Contents-API `sha` semantics)** as the actual conflict-detection primitive inside that contract — hash the page on read (`vault_read` already returns content), record it in the envelope, recompute at apply time, reject on mismatch. This is the cheapest guarantee of no lost updates that keeps markdown literal, and the **cleanest fit** with the hard constraint.
3. **A single-writer serialized queue/compactor** (even one Python process reading `inbox/` in lexicographic order) as the applier, so applies never race each other and precondition checks are evaluated against a stable current state. Persist pending writes as `inbox/` files for crash durability.
4. **Git branch-per-write + PR / merge-queue** as the outer coordination layer for larger, multi-file ingest batches — the PR is propose, the merge is apply, the commit is the receipt — with **`wiki-lint` as a required status check** so semantic breakage (the residual risk above) is caught before landing on `main`.

**Ranking for this wiki:**
- **Precondition hash — adopt (core primitive).** Cleanest fit, cheapest, keeps markdown literal.
- **propose→apply→receipt — adopt (template).** Closest existing purpose-built design; verify its license before copying schema verbatim.
- **Serialized write queue — adopt (implementation of the applier).** Don't build bespoke locking.
- **Git branch + PR/merge-queue — adopt (outer loop).** Native git, free, verify merge-queue plan gating.
- **Advisory locking — avoid as primary.** Documented-unreliable on this exact cloud/multi-machine setup; same-host best-effort only.
- **All-in-one KB servers (Basic Memory) — evaluate with caution.** Borrow the architecture, not the undocumented write path; AGPL-3.0 caveat.
- **CRDTs — avoid / disqualified as store.** Violates the plain-markdown constraint outright; reconsider only as an ephemeral real-time-editing UI that exports to markdown on save.

The net message: this cluster requires **very little new infrastructure**. The wiki already has the `inbox/` staging lane, an ingest skill, and git. Layering precondition hashes on read, a single serialized applier, and git commits/PRs as the audit trail turns those existing pieces into a team-safe, cloud-hostable write path — with `wiki-lint` as the complementary semantic backstop.
