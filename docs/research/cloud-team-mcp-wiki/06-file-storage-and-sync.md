## 06. File Storage and Sync — Where the Canonical Markdown Actually Lives

This cluster decides the **substrate**: where the plain-markdown source of truth physically sits for a
cloud-hosted, team-shared MCP wiki, and how edits (from MCP tools, lint/ingest jobs, and any human
editor) get onto and off of the box the server runs on. The hard constraint dominates every choice
here — the canonical store must stay git-diffable, agent-editable plain markdown, so any option that
owns its own opaque format is disqualified *as the store* (it may still serve as a disposable layer).
The recurring lesson across everything surveyed: nothing gives true multi-writer coordination for
free, and git's merge/conflict-marker model is the most mature answer to "two writers touched the same
page at once" precisely because it was built for that problem.

**Takeaway:**
- **Adopt a git repo (GitHub/GitLab) as the source of truth**, reached by the MCP server through a
  persistent local clone (pull → edit → commit → push), writes serialized to dodge `.git/index.lock`
  races. Git history *is* the durability/audit/backup story — no bolt-on backup product needed.
- **Prefer plain git plumbing over the Contents REST API** for a busy multi-agent workload — the API's
  documented no-parallel-writes rule and sha-based optimistic concurrency make it fragile past
  occasional single-file edits.
- **Object storage (S3/R2/GCS)** = great backup/replica target (R2's free egress especially), **not**
  the live edit surface — every official FUSE client disclaims safe concurrent multi-writer access.
- **Managed NFS (EFS/Filestore)** = avoid; priced/provisioned 100–1000× oversized for a wiki and gives
  no version history on its own.
- **SQLite + Litestream/LiteFS** = right tool, right layer — for the *disposable derived index*, never
  the markdown.
- **obsidian-headless** = a sync transport tied to Obsidian's paid Sync backend; only relevant if a
  human insists on editing through the desktop app, and then only in one-way mirror mode.

---

### Option A — Git repo as backing store (the recommended substrate)

**What it is.** The GitHub/GitLab repository itself is the canonical persistence layer for the markdown
files. Two integration modes:

1. **Normal git plumbing against a working-copy clone** — the server keeps a persistent clone on its
   disk/volume and does ordinary `git pull` / `git add` / `git commit` / `git push`. Supports atomic
   multi-file commits, branches, PRs, and full conflict tooling.
2. **Contents REST API, no local clone** — fully stateless; one HTTP call per file, with GitHub/GitLab
   as the only durable store and zero server-side disk.

This is the pattern git-based CMSs use to read/write markdown with no working copy at all: **Decap
CMS** (github.com/decaporg/decap-cms, MIT — the actively-maintained fork of the archived Netlify CMS)
and **TinaCMS** (github.com/tinacms/tinacms, Apache-2.0) both drive markdown/YAML/JSON straight from a
git repo via the GitHub/GitLab/Bitbucket/Azure DevOps/Gitea APIs. Decap caches one API request per
content entry.

**Contents API write semantics** (docs.github.com/en/rest/repos/contents):

```
PUT /repos/{owner}/{repo}/contents/{path}
{
  "message": "commit message",
  "content": "<base64-encoded file body>",
  "sha":     "<current blob sha — REQUIRED on update, omit on create>"
}
```

- The `sha` requirement on update **is** optimistic-concurrency control: a stale sha is rejected, and
  the caller must re-fetch the current blob sha and retry.
- GitHub explicitly documents that the create/update and delete endpoints **must not be called in
  parallel** against the same repo: *"the concurrent requests will conflict and you will receive
  errors. You must use these endpoints serially instead."*

**Concurrency in git-clone mode.** Concurrent writers hitting one working directory race on
`.git/index.lock`. The standard fix (used by multi-agent coding setups) is **one git worktree/branch
per writer**, merged at commit time via normal git conflict resolution — conflicts surface as visible
merge markers in the markdown, never silent overwrites. Alternatively, serialize all writes through a
single queue/lock.

**Rate limits.** GitHub REST: **5,000 req/hr** standard, **15,000 req/hr** Enterprise. A
per-file-per-call ingest or lint pass over a large wiki can burn meaningfully into that budget. The
git-clone mode sidesteps it entirely — one `git pull` / `git push` regardless of file count.

| Property | Git-clone mode | Contents REST API mode |
|---|---|---|
| Server-side disk needed | Yes (persistent clone) | No (fully stateless) |
| Atomic multi-file commit | Yes | No (one file per PUT) |
| Concurrency model | `.git/index.lock` race → worktree-per-writer / queue | Serial-only (documented), sha optimistic-locking |
| Rate-limit exposure | One pull/push per sync | 5k–15k req/hr, one call per file |
| Conflict visibility | Git merge markers in markdown | HTTP error → re-fetch sha → retry |
| Best for | Busy multi-agent ingest/lint | Occasional single-file edits |

**Constraints / limits.** Free on GitHub/GitLab for reasonable repo sizes. GitHub soft-warns above
~1 GB repos; hard-blocks individual files over 100 MB (git push) or 1 MB (Contents API single PUT) —
all irrelevant for a markdown wiki. No vendor lock-in: it's a normal git repo, mirrorable anywhere.

**Maturity.** GitHub/GitLab Contents APIs are long-stable, versioned platform APIs. Decap CMS and
TinaCMS are mature, widely-deployed OSS.

**Verdict — ADOPT as the source-of-truth substrate.** It is the only option in this cluster where
git's own commit history *is* the durability/backup story, it satisfies "git-diffable" by definition,
and it composes cleanly with existing GitHub/GitLab team permissions for a team-shared wiki. Use plain
git (clone + pull/commit/push, serialized or per-request worktrees) rather than the Contents API for
anything beyond occasional single-file edits.

---

### Option B — Object storage (S3 / Cloudflare R2 / GCS) + working copy or FUSE mount

**What it is.** Store the markdown files as bucket objects and give the server a filesystem view either
by (1) **sync** — periodic `rclone sync` / `aws s3 sync` to local disk, edit locally, sync back (no
live FS semantics, but simple and safe), or (2) **FUSE mount** — bucket appears as a live directory.

**FUSE client landscape:**

- **AWS Mountpoint-S3** (github.com/awslabs/mountpoint-s3, official AWS, Rust, GA since 2023, semantics
  at `doc/SEMANTICS.md`). Strong read-after-write consistency by default for writes, listings, and
  new-object creation. If another client modifies an *existing* open object, Mountpoint returns either
  the fully-old or fully-new version — never a torn read; re-open to force a fresh read.
  **Explicitly does NOT support: directory rename (any bucket type), chmod/chown/chgrp, extended
  attributes, POSIX file locks (`lockf`), or hard/symlinks.** Several of those matter for a git-style
  working tree and for atomic-write-via-temp-file-then-rename.
- **gcsfuse** (github.com/GoogleCloudPlatform/gcsfuse, official Google). Surfaces conflicting
  concurrent writes as a hard **`ESTALE`** error to the losing writer/reader — detects the conflict but
  does not resolve it. Its file/list/stat/type caches trade consistency for speed and are explicitly
  flagged as reducing correctness under concurrent access.
- **rclone mount vs s3fs vs goofys** (independent bench, github.com/eran132/rclone-vs-s3fs-bench,
  `REPORT-COMPARISON.md`): rclone mount won essentially every workload against both S3 and MinIO/Ceph,
  by **1.07× up to 38×** depending on backend/operation. goofys trades POSIX completeness (no random
  writes) for raw throughput; s3fs is the most POSIX-complete of the three but least consistent under
  multi-client access. rclone is the portable, cross-cloud, open-source option.

**Universal caveat**, repeated across every FUSE-over-object-storage tool: *"there is no coordination
among multiple clients mounting the same bucket."* Don't share a live mount as a multi-writer
filesystem; the safe pattern is single-writer-at-a-time, or object storage as archival/replica.

**Cloudflare R2 pricing** (developers.cloudflare.com/r2/pricing) — notable for **free egress**:

| Item | Standard | Infrequent Access |
|---|---|---|
| Storage | $0.015 / GB-month | $0.010 / GB-month |
| Class A ops (writes/lists) | $4.50 / million | $9.00 / million |
| Class B ops (reads) | $0.36 / million | $0.90 / million |
| Egress | **Free** | **Free** |
| Free tier | 10 GB-month storage + 1M Class A + 10M Class B ops / month | — |

S3/GCS are comparable order-of-magnitude; R2 is cheaper for egress-heavy read patterns. All the FUSE
tools are free/OSS — the cost is the underlying storage bill.

| Client | Cloud | Rename dir | POSIX locks | Concurrent-write behavior | License |
|---|---|---|---|---|---|
| Mountpoint-S3 | S3 only | ✗ | ✗ | whole-old-or-whole-new, no torn read | OSS (AWS) |
| gcsfuse | GCS only | (limited) | (limited) | `ESTALE` to loser | OSS (Google) |
| rclone mount | cross-cloud | ✓ | partial | no cross-client coordination | MIT-style OSS |
| s3fs | S3-compatible | ✓ | partial | least consistent multi-client | OSS |
| goofys | S3-compatible | ✓ | ✗ (no random writes) | throughput over POSIX | OSS |

**Verdict — STEAL-THE-IDEA for backup/archival, NOT the live editing surface.** Cheap, durable, and
R2's zero-egress makes it attractive as a secondary replica or nightly snapshot target of the git repo
(or of a rendered index). But every official FUSE client disclaims safe multi-writer concurrent
editing, and Mountpoint-S3 lacks directory rename and POSIX locks that a markdown workflow relies on.
Do not make this the sole canonical store for a live-edited wiki. *(As a raw object store holding the
markdown, it does not itself violate the hard constraint — the files stay plain — but its concurrency
semantics make it unsafe as the live edit surface.)*

---

### Option C — Persistent cloud volume / managed NFS (AWS EFS, Google Filestore, Azure Files)

**What it is.** A managed network filesystem attached to the compute running the MCP server, giving the
markdown a **real POSIX filesystem** (rename, locks, permissions — which object-storage FUSE mounts
lack) that can be shared read/write across multiple server instances for scaling or failover.

- **AWS EFS** — elastic, pay-per-stored-GB NFS, mountable simultaneously from many EC2/Fargate/Lambda
  instances with genuine multi-writer NFS locking.
- **Google Filestore** — NFSv3, tiers from Basic HDD up through high-performance; integrates with
  GCE/GKE. **Basic HDD requires a ≥1 TB minimum provisioned capacity.**

**The problems for a wiki:**

- Both are strictly more expensive per GB than object storage, with provisioning minimums wildly
  oversized for a markdown wiki (tens of MB to low GB). You pay for capacity never used.
- **Neither gives git history or content-addressed versioning.** They are live disk — "durability"
  means replication/snapshots (EFS integrates with AWS Backup), not an audit trail of every edit. You'd
  still need git (or manual snapshotting) on top for the diff/revert story the wiki depends on.
- EFS cross-AZ access incurs an explicit **$0.01/GB** data-transfer charge on top of storage.

**Pricing** (aws.amazon.com/efs/pricing):

| Service / tier | Price | Note |
|---|---|---|
| EFS Standard (Regional, multi-AZ) | $0.30 / GB-month | US East N. Virginia |
| EFS One Zone Standard | $0.16 / GB-month | ~47% cheaper, single-AZ |
| EFS cross-AZ transfer | +$0.01 / GB | on top of storage |
| EFS free tier | 5 GB free / 12 months | new accounts |
| Filestore Basic HDD | ~$0.16–0.20 / GB-month | **1 TB minimum → ~$160–200/mo floor** regardless of data size |

EFS full tier list: Standard, Standard-IA, One Zone, One Zone-IA, with lifecycle auto-tiering.

**Maturity.** Mature, long-standing managed services (EFS since 2015, Filestore since 2018).

**Verdict — AVOID for this use case.** Both are priced and provisioned for large multi-instance
workloads (Filestore's 1 TB minimum alone makes it 100–1000× oversized for a few-hundred-page wiki),
neither supplies the version-history/diff story the wiki depends on, and a git working copy on ordinary
block storage (or an ephemeral compute disk re-cloned on boot) delivers the same "shared POSIX view"
outcome for a fraction of the cost when the true source of truth is the git remote.

---

### Option D — SQLite + Litestream / LiteFS (for the derived index only, never canonical)

**What it is.** Replication/durability for a SQLite database:

- **Litestream** (litestream.io, github.com/benbjohnson/litestream) — a sidecar process that streams
  SQLite's WAL pages continuously to S3-compatible object storage for backup, point-in-time restore,
  and read replicas. It reads the WAL directly (not a proxy/driver), so it **cannot corrupt the DB**.
- **LiteFS** (github.com/superfly/litefs, Apache-2.0, ~4.8k stars, Go, **beta/pre-1.0**) — a FUSE
  filesystem that intercepts SQLite transaction boundaries and ships changes as compact "LTX"
  transaction files to a cluster, so every node holds a live, queryable local copy (not just a backup).

**These are candidates ONLY for a disposable derived index** — a materialized backlink / frontmatter /
FTS table built *from* the markdown — never for the markdown itself. This is exactly the "disposable
layer on top of the files" the hard constraint permits, and it pairs naturally with the
`obsidiantools` (graph + frontmatter + native dangling-link detection) and `qmd` (BM25 + vector +
rerank content retrieval) tools recommended in `docs/research/headless-wiki-hosting.md`: whichever of
those persists its output to SQLite is the thing you wrap.

**Litestream commands / config:**

```
# replicate a DB to S3-compatible storage
litestream replicate fruits.db s3://mybkt.localhost:9000/fruits.db

# restore
litestream restore -o fruits2.db s3://mybkt.localhost:9000/fruits.db
```

```yaml
# litestream.yml
dbs:
  - path: /var/lib/db
    replica:
      url: s3://mybkt.litestream.io/db
      region: us-east-1
      access-key-id: ...
      secret-access-key: ...
```

Litestream also added **VFS-based live read replicas** — a query process attaches a read-only,
live-updating copy without a full restore-to-disk first, useful for scaling read-only query traffic
off a single writer. It supports 7 replica types generally (S3 being the headline).

**Critical caveat.** Neither tool changes SQLite's fundamental **single-writer-at-a-time** model. They
solve *replication and durability* of a SQLite file, not concurrent multi-writer access — a single
process (or the LiteFS-elected primary) still owns all writes.

| | Litestream | LiteFS |
|---|---|---|
| Mechanism | Sidecar streams WAL to object storage | FUSE, LTX transaction files across cluster |
| Gives you | Backup + PITR + optional live read replica | Live queryable copy on every node |
| License | OSS, free, self-hosted | Apache-2.0, free; LiteFS Cloud = paid Fly.io add-on |
| Maturity | Mature/stable (v0.5.x) | Beta / pre-1.0 (maintainer-labeled) |
| Fly.io lock-in | None | None ("in no way locked into Fly.io") |
| Multi-writer | No (single writer) | No (single primary) |

**Verdict — ADOPT, strictly as the disposable index layer.** Use **Litestream** (simplest, S3-backed
backup + optional live read replica) if there's one MCP server instance; use **LiteFS** if multiple
MCP replicas each need a live local copy of the index (accepting its beta status — worst case, rebuild
from markdown). **Never point either at anything claiming to be the markdown source of truth.**
Self-hosted Litestream-to-S3 is the $0-infrastructure-cost default; LiteFS Cloud pricing was not
itemized in the fetched sources.

---

### Option E — Official `obsidian-headless` sync client (`ob`)

**What it is.** Obsidian's own official CLI (github.com/obsidianmd/obsidian-headless) that speaks the
Obsidian Sync/Publish protocol from the command line, so a server can pull/push vault changes **without
running the Obsidian desktop Electron app**. It is a sync *transport*, not a query surface (confirmed by
`docs/research/headless-wiki-hosting.md`) — it belongs in this cluster (getting files on/off the box),
not the query-layer clusters.

**Install & commands** (Node.js **22+** required):

```
npm install -g obsidian-headless

ob login                              # auth
ob logout
ob sync-list-remote                   # list remote vaults on the account
ob sync-setup --vault "Name"          # bind a local folder to a remote vault
ob sync                               # one-shot sync
ob sync --continuous                  # watch + sync on the fly (long-lived sidecar)
ob sync-config --mode {bidirectional|pull-only|mirror-remote}
ob sync-config --conflict-strategy {merge|conflict}
```

**Sync modes** via `ob sync-config`:

- `bidirectional` (default) — two-way.
- `pull-only` — download only; local edits ignored.
- `mirror-remote` — download only, and **actively reverts** local changes.

For a server whose canonical edits come from git/the MCP tools, `pull-only` or `mirror-remote` are the
safer choices — they keep this channel a **one-way mirror** so it can't become a second independent
write path fighting the git-based agent path.

**Gotchas / open gaps:**

- Requires an **active paid Obsidian Sync subscription** — this is a client for Obsidian's own paid
  service, not a free/self-hosted protocol. It's an Obsidian-account/product dependency layered on top
  of whatever actually holds the canonical files.
- The `--conflict-strategy` flag offers `merge` / `conflict`, but the fetched README **does not
  document the underlying merge algorithm** or its behavior under simultaneous multi-machine writes —
  a real open gap, not a confirmed guarantee.
- **No license statement** was found in the fetched README/repo — must be checked before depending on
  it in a redistributable pipeline.
- Young project: **184 GitHub stars**, recently released (2026-era launch per HN discussion) — not a
  long-track-record tool.

**Verdict — STEAL-THE-IDEA / EVALUATE, don't anchor on it.** It's the only option that keeps a human
editing in the actual Obsidian desktop app in the loop with a cloud store. But it ties the system to
Obsidian's paid Sync as a hidden **second backend** (alongside the canonical git/markdown), duplicates
the git-repo option's job with less transparency (Obsidian Sync's wire format/history is **not** git
history — no plain diffs), and leaves concurrent-writer conflict mechanics undocumented in the primary
source. If the real edit path is "agents + occasional human via a normal git PR," prefer the git
substrate and skip this. If a human insists on editing through the desktop app against the same cloud
copy, run it in `pull-only`/`mirror-remote` mode as a safe one-way mirror.

---

### Recommendation for this cluster

**Rank for this markdown-as-truth, cloud, team-shared MCP wiki:**

1. **Git repository (GitHub or GitLab) as the source of truth — ADOPT.** Accessed by the cloud MCP
   server via a **persistent local clone** (git pull before reads; commit + push after writes;
   serialized through a queue or one-worktree-per-writer to sidestep `.git/index.lock` races) rather
   than per-file Contents-API calls. This directly satisfies the hard constraint — the canonical store
   *is* plain files — and git's commit history supplies durability/audit/backup for free, with
   GitHub/GitLab's own infrastructure as the off-box durable copy. It also composes cleanly with
   existing team permissions. Git's merge/conflict-marker model is the most mature multi-writer answer
   in this entire cluster.
2. **SQLite + Litestream (or LiteFS for multi-replica) — ADOPT, but only as the disposable index
   layer.** Wrap the `obsidiantools`/`qmd` output so the derived graph/FTS index survives restarts and
   scales reads. Never the markdown.
3. **Object storage (S3 / Cloudflare R2 / GCS) — use as backup/replica only.** R2's free egress makes
   it an attractive nightly-snapshot target of the git repo or the rendered index. Not the live edit
   surface — every official FUSE client disclaims safe concurrent multi-writer access.
4. **`obsidian-headless` — conditional / evaluate.** Only if a human must keep editing through the
   Obsidian desktop app against the same cloud copy, and then only in `pull-only`/`mirror-remote` mode.
   Adds a paid-Sync second backend with opaque history; skip it if the human edit path is a normal git
   PR.
5. **Managed NFS (EFS / Filestore / Azure Files) — avoid.** Priced/provisioned 100–1000× oversized for
   a wiki, and no version history on its own; a git working copy on ordinary block storage gets the
   same shared-POSIX outcome far cheaper.

The through-line: **git is the substrate, everything else is a layer.** Files stay canonical and
diffable; indexes (SQLite), replicas (R2), and optional human-sync bridges (obsidian-headless) all sit
on top and are rebuildable or discardable without touching the source of truth.
