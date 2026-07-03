## 01. Compute — Compose Your Own (Metadata + Graph + Content Engines)

This cluster decides which off-the-shelf engines can serve the wiki's three headless query axes —
frontmatter/metadata, link-graph, and ranked/semantic content — when the vault is hosted as a
**shared, team-wide, always-on MCP service** rather than launched from one WSL box with Obsidian
open. The hard constraint holds throughout: the plain-markdown files stay canonical and
git-diffable; every engine here is a **disposable index layer** rebuilt from those files, never the
source of truth. The central finding from the prior single-user report survives but sharpens: **no
single engine covers all three axes**, so a cloud deployment composes at least two — a graph/metadata
tool and a content tool — and each half now additionally needs a persistence/daemon/concurrency
layer that was optional on a laptop.

**Takeaways:**

- **No all-in-one engine exists in this cluster.** You compose a graph/metadata tool + a content
  tool. `obsidiantools` + `qmd` remains the shape, now both wrapped as daemons.
- **The new dominant filter is "daemon-readiness".** Tools that are libraries (obsidiantools,
  Tantivy, Orama, SQLite FTS5) cost you a service wrapper; tools that ship a daemon (qmd,
  Meilisearch, Typesense, markdown-oxide) do not.
- **Graph/lint half:** `obsidiantools` is still the only surveyed tool with native dangling-link
  detection — adopt it, but you must author the watcher + cache + MCP endpoint around it.
- **Content half:** `qmd` strengthens under cloud constraints (`qmd mcp --http --daemon` is already a
  shared server); `Meilisearch` is the credible alternative because it has an official MCP server +
  managed multi-tenant Cloud tier, at the cost of an ingest pipeline.
- **Lean fallback:** `SQLite FTS5` is the most literal embodiment of "index is disposable, files are
  truth" — zero infra, but you write all the glue.
- **Lock-in flag:** `Turbopuffer` is SaaS-only with no self-hosted option — the strongest lock-in
  risk here even though it structurally respects files-as-truth.

### Capability matrix

| Tool | Metadata (frontmatter) | Graph (backlinks/orphans/dead-ends/dangling) | Content (ranked/semantic) | Ships a daemon? | Native file-watch | MCP / transport | License | Cost |
|---|---|---|---|---|---|---|---|---|
| **obsidiantools** | Yes (`front_matter_index`) | **Yes — incl. native dangling** | No | No (library) | No | No (wrap it) | BSD-3 | Free |
| **MarkdownDB / mddb** | Yes (SQL columns) | Partial — **roadmap only** | No | No (build step) | **Yes (`--watch`)** | No (query DB directly) | MIT | Free |
| **markdown-oxide** | Partial (tags, no props) | Yes (interactive, no batch report) | No | **Yes (LSP)** | **Yes (LSP dynamic reg)** | LSP only (no HTTP/MCP) | Apache-2.0 | Free |
| **Meilisearch** | Yes (after ingest) | No | **Yes (hybrid FT+vector)** | **Yes** | No (ingest step) | **Official MCP** | MIT / Cloud | Free self-host / $20+/mo Cloud |
| **Typesense** | Yes (after ingest) | No | Yes (FT+vector) | **Yes** | No (ingest step) | No official MCP | GPL-3.0 / Cloud | Free self-host / Cloud (unconfirmed) |
| **qmd** | **No (metadata-blind)** | **No (graph-blind)** | **Yes — strongest** | **Yes (`--http --daemon`)** | No (manual `update`) | **Native MCP+HTTP** | MIT | Free (~2GB RAM/daemon) |
| **Turbopuffer** | Filtering (unconfirmed) | No | Yes (vector+BM25) | SaaS-only | N/A | No official MCP | Proprietary SaaS | $16–$4,096+/mo |
| **SQLite FTS5** | Yes (you build) | No (you build edges) | Yes (BM25) | No (embedded) | No | No (embed it) | Public domain | Free |
| **Tantivy** | Yes (facets) | No | Yes (Lucene-grade) | No (library) | Yes (incremental) | No | MIT | Free |
| **Orama** | Yes (facets, nested) | No | Yes (hybrid FT+vector) | No (embeddable) | No | No | Apache-2.0 | Free |

---

### Graph + metadata tools

#### obsidiantools — https://github.com/mfarragher/obsidiantools

Python library (BSD-3-Clause) that parses an unmodified Obsidian-style vault folder into an in-memory
NetworkX graph plus pandas-indexed frontmatter. It is the **only surveyed tool with native
dangling-link detection out of the box**, and stays the strongest single-tool fit for the lint/graph
half — unchanged in capability from the single-user recommendation. The delta for cloud is purely
operational: you must build the daemon loop.

- **API surface:**
  - Build: `obsidiantools.api.Vault(vault_path).connect().gather()`
  - Metadata: `vault.front_matter_index`, `vault.get_front_matter(note)`
  - Backlinks: `vault.backlinks_index`, `vault.get_backlinks(note)`
  - Orphans: `vault.isolated_notes`
  - Dead-ends: NetworkX `DiGraph` out-degree == 0
  - Dangling: `vault.nonexistent_notes`, `vault.nonexistent_media_files`,
    `vault.nonexistent_canvas_files`
- **Content query:** **None** — plain-text extraction only, no ranked/semantic search.
- **Version/license:** v0.11.0 (2025-07-08), BSD-3-Clause, 8 releases, single-maintainer project, no
  1.0/stable-API commitment.
- **Gotchas for a cloud service:**
  - **Library, not a server** — no built-in daemon, HTTP API, or MCP transport. Wrap it (e.g. FastAPI
    process calling `gather()` and serving JSON).
  - **No file watcher / no incremental reindex** — `gather()` re-walks and re-parses the whole vault
    every call. Add your own `watchdog`/`inotify` watcher (or APScheduler timer) and re-run `gather()`
    on change, holding the last-built `Vault` object in a module-level cache.
  - **No documented concurrency model** — synchronous object construction. Concurrent reads at scale
    means either many stateless handlers each recomputing `gather()`, or the cached-Vault-behind-a-lock
    pattern you design.
  - **No built-in auth** — any wrapper must add its own access control for multi-tenant team use.
  - **Restart-safe by construction** — never writes to the vault, purely reads files into memory.
    Fully rebuildable/disposable, so it respects files-as-truth perfectly.
- **Files-as-truth:** Fully compliant — read-only over the folder.
- **Verdict:** **Adopt** as the metadata+graph half, but only after writing a thin service wrapper
  (watcher + cache + HTTP/MCP endpoint). This wrapper is the **single biggest net-new engineering
  cost** versus the single-user recommendation.

#### MarkdownDB / mddb — https://github.com/datopian/markdowndb

JavaScript/TypeScript CLI + library (npm package `mddb`, MIT) that indexes a folder of markdown into a
queryable SQL database (SQLite default, or MySQL/Postgres via Knex.js), turning frontmatter fields
into SQL columns. Architecturally the closest of the graph/metadata tools to "cloud service" out of
the box — but its graph features are not shipped.

- **CLI:** `npx mddb ./content-folder [--watch]`
- **Backends (Knex.js):** SQLite (default, zero setup), MySQL (needs `mysql2`), PostgreSQL (needs
  `pg`) — a real relational DB, useful if the cloud service already runs Postgres and wants
  frontmatter/links as ordinary rows.
- **Metadata:** Yes — frontmatter fields become SQL columns, queryable with any SQL client.
- **Graph:** **Partial / roadmap only.** Forward + backlinks and a "deadlinks" (dangling) feature are
  described as roadmap ("Links extraction ... so we can compute backlinks or deadlinks"), **not
  confirmed shipped** in v0.9.5. Wikilink/alias resolution against Obsidian's `[[link]]` /
  `[[link|alias]]` syntax is **unverified**.
- **Content:** **None** — metadata+link indexer, not a search engine. Prose only via SQL `LIKE`; no
  FTS integration documented.
- **Standout capability:** **`--watch` flag** (`npx mddb ./blog --watch`) monitors files and updates
  the SQLite DB incrementally — the only graph/metadata tool in this cluster with a built-in watcher.
  Primarily framed as a build step (recommended in a `package.json` `prebuild` script), but `--watch`
  gives it long-running-service behavior.
- **Concurrency:** SQLite backend on disk means many concurrent readers can query directly with any
  SQL client while a single `--watch` process is the sole writer — composes cleanly with SQLite's WAL
  model.
- **Version/license:** v0.9.5 (2024-03-07), MIT, 492 stars / 23 forks, 14 releases — **stalled, not
  actively developed** (last release March 2024).
- **Transport:** No REST/MCP API shipped; query the resulting SQLite/MySQL/Postgres DB directly or via
  the small in-process Node API.
- **Docs:** https://markdowndb.com , tutorial at https://markdowndb.com/blog/basic-tutorial
- **Files-as-truth:** Compliant — DB is a rebuilt index over the folder.
- **Verdict:** **Evaluate, not adopt outright.** The `--watch` + real-SQL-backend combination is
  architecturally the best fit of the surveyed metadata/graph tools for a persistent multi-reader
  cloud service. But backlinks/dangling detection is roadmap-stage — it cannot yet replace
  obsidiantools for the graph/lint half without a custom link-parsing pass or an upstream
  contribution. Re-check the CHANGELOG before counting on it; the stalled cadence is itself a signal.

#### markdown-oxide — https://github.com/Feel-ix-343/markdown-oxide

Rust LSP daemon (Apache-2.0) that brings Obsidian-like backlinks/completions/daily-notes into any
LSP-capable editor (Neovim, VSCode, Zed, Helix, Kakoune). A long-running process is its native mode —
a good structural fit for "persistent service" — but the wire protocol is **LSP (JSON-RPC over
stdio/socket), not HTTP/REST/MCP**.

- **Metadata:** Partial — handles inline tags/tag references, but **no documented frontmatter
  *property* query API** (no equivalent of `front_matter_index`).
- **Graph:** Yes for backlinks/references — "fuzzy match backlinks to files, headings, and blocks",
  code-lens reference counts, and unresolved-reference awareness (completions + a "create missing
  file" code action). **But** these are exposed interactively through LSP requests, **not as a
  batch/report API you can cron.** No whole-vault dangling-link report.
- **Content:** **None** — no ranked or semantic search.
- **File-watch:** Native and built-in — LSP "dynamic registration for watched file changes" means live
  incremental updates are core. **Best-native watch story of the three graph/metadata tools.**
- **Concurrency gotcha:** LSP is typically single-client-per-server-process (one editor ↔ one language
  server over stdio). Running it as a multi-tenant shared network daemon for many simultaneous callers
  is not how LSP servers are normally operated — "concurrent reads at scale" would likely mean one
  process per session/socket, not one shared process. (Inferred from LSP design, not confirmed in
  docs.)
- **Transport cost:** Reaching it from an MCP tool or HTTP query service requires you to build an
  LSP-client/bridge yourself — real integration work, not a thin wrapper.
- **Install:** Cargo, or packaged for Arch/Nix/Alpine/openSUSE/Homebrew; editor extensions for VSCode
  and Zed.
- **Version/license:** Apache-2.0, v0.25.12 (June 2026), 2.2k stars, 815 commits, 33 releases — the
  most actively released of the three graph/metadata tools here. Rust 93.6% / TypeScript 5.7%.
- **Files-as-truth:** Compliant — reads the vault, edits happen through the editor.
- **Verdict:** **Avoid** as the primary cloud-service transport. The protocol mismatch (LSP vs the
  MCP/HTTP surface the workflow standardizes on) costs a custom LSP-to-MCP bridge for capability
  obsidiantools already gives more directly (frontmatter query, batch dangling report). Revisit only
  if the team **also** wants live editor tooling as a separate, additional surface.

---

### Content-search engines (daemon-shipping)

#### qmd — https://github.com/tobi/qmd

MIT-licensed TypeScript tool running BM25 + vector search + LLM rerank + query expansion over a folder
of markdown via local GGUF models, exposed as an MCP/HTTP daemon. **This is the one place the
recommendation genuinely strengthens under cloud constraints** — the daemon/HTTP mode that was a
"nice bonus" on a laptop becomes the load-bearing feature for a shared service.

- **Content:** **Yes, and the strongest surveyed** — BM25 + vector fused by Reciprocal Rank Fusion,
  then LLM rerank with query expansion, all through **local embedded models (no per-query external API
  cost)**.
- **Metadata:** **None** — explicitly metadata-blind, ignores frontmatter entirely.
- **Graph:** **None** — graph-blind, ignores `[[links]]` entirely.
- **Daemon mode (cloud-shaped, first-class):**
  - `qmd mcp --http --daemon` starts a background process (PID at `~/.cache/qmd/mcp.pid`).
  - Endpoints: `POST /mcp` (stateless JSON MCP calls), `GET /health` (liveness — directly usable
    behind a load balancer / orchestrator health check).
  - `--host 0.0.0.0` serves multiple clients from one container/instance — docs describe this as a
    deliberate "shared, long-lived server that avoids repeated model loading" pattern.
- **Memory footprint:** ~2GB resident across three GGUF models (embedding ~300MB, reranking ~640MB,
  query-expansion ~1.1GB) in VRAM/RAM across requests; embedding/reranking contexts torn down after
  **5 minutes idle**. A fixed cost per daemon, but **shared across all clients of that instance** — so
  per-tenant marginal cost drops as more teams share it, unlike a per-laptop deployment.
- **Reindexing:** **No automatic file watcher.** Manual `qmd update` (or SDK call). Docs suggest
  driving via `git pull` on the collection. For cloud: wire a webhook/cron (e.g. a GitHub Actions
  post-merge hook that SSHes in and runs `qmd update`).
- **Version/license:** v2.5.3 (2026-05-29), MIT, 13 releases, 82.5% TypeScript.
- **Multi-tenant caveat:** Docs describe multi-**client reachability** (many clients, one daemon) but
  **do NOT address per-request concurrency handling, user isolation, or access control.** Multi-tenant
  **safety** (mutually distrustful teams) is unconfirmed and needs verification/hardening before real
  team-wide production use.
- **Files-as-truth:** Fully compliant — reads markdown directly, **no ingest step**.
- **Verdict:** **Adopt** for the content-query role — the only surveyed content-search tool that speaks
  MCP natively **and** needs no ingest step, fitting the MCP-first convention better than
  Meilisearch/Typesense's REST+ingest model. Caveats: verify/harden multi-tenant isolation; add a
  git-webhook-triggered `qmd update` since there is no native watcher.

#### Meilisearch — https://www.meilisearch.com/

Open-source (MIT, self-hostable) search-engine daemon with a first-party **Meilisearch Cloud** managed
offering; REST API; hybrid full-text + vector search; facets/filters over structured fields. The
credible alternative to qmd specifically because it is **the only search engine surveyed with both a
managed multi-tenant Cloud tier AND an official MCP server**.

- **Content:** Yes — hybrid keyword (full-text) + vector search out of the box, official ranking
  rules, typo tolerance.
- **Metadata:** Yes, **but only after ingest** — you parse each note's frontmatter into JSON document
  fields and index them; Meilisearch then facets/filters natively. Faceted search is a named core
  feature.
- **Graph:** **None.** No link-graph concept. Backlinks/orphans/dangling must be computed elsewhere
  and at most stored as denormalized fields (e.g. a precomputed `inlink_count`) for filtering — not
  real graph traversal.
- **Official MCP server:** https://github.com/meilisearch/meilisearch-mcp — `pip install
  meilisearch-mcp` or `uvx meilisearch-mcp`, **stdio-based**; lets an MCP client manage
  indices/search/settings through tool calls. Directly reusable as the content-query MCP endpoint.
- **Ingest requirement (the real cost):** No "point it at a folder" mode. Every note edit must be
  re-parsed (frontmatter split from body) and pushed as a JSON document via REST/SDK. Your ingest
  script is the bridge that keeps files-as-truth intact.
- **Pricing:**
  - Self-hosted: **free** (MIT binary); you manage updates/backups/scaling.
  - Cloud: **from $20/month**, 14-day free trial, no credit card for trial.
  - Usage-based example: ~$30/mo for 100K docs + 50K searches/month.
  - Resource-based example: ~$23/mo for an XS instance (0.5 vCPU, 1GB RAM + storage).
  - Enterprise tier: SSO/SAML, SOC2, dedicated support, up to 99.999% uptime SLA.
- **Shape:** Purpose-built for the "daemon serving many concurrent clients" shape — REST API,
  multi-index, Cloud tier markets shared/managed hosting with SLAs.
- **Files-as-truth:** Compliant **as long as** the ingest pipeline treats files as canonical;
  Meilisearch is a rebuilt index only.
- **Verdict:** **Adopt as the credible alternative** to qmd for the content+metadata-facet half. The
  real cost is the ingest pipeline (frontmatter/body split → JSON → PUT on every commit/webhook) —
  not optional, since Meilisearch never reads the vault folder directly.

#### Typesense — https://typesense.org/

Open-source (GPL-3.0, self-hostable) typo-tolerant search engine with a managed Typesense Cloud; REST
API; faceting/filtering and vector search. Comparable to Meilisearch but without an official MCP
server.

- **Content:** Yes — tunable typo-tolerant full-text plus vector search (v29.0 API docs confirm a
  dedicated "Vector Search" API resource, "bucketing on vector distance", ongoing work on "CLIP
  embeddings under high concurrency").
- **Metadata:** Yes after ingest — documents are JSON with typed fields; facet/filter on any field.
  Requires **a JSON schema/collection definition per index** (typed fields, unlike Meilisearch's more
  schema-less default) — slightly more upfront config to map frontmatter fields to Typesense types.
- **Graph:** **None** — same gap as Meilisearch.
- **MCP:** **No first-party/official MCP server found.** Integration with an MCP agent workflow would
  need a community or custom-built MCP bridge over its REST API.
- **Concurrency evidence:** v29.0 changelog explicitly mentions concurrency-hardening ("Improved
  reliability of CLIP embeddings under high concurrency", "Improved group-by performance under high
  cardinality fields") — the project actively tunes for concurrent/scale workloads, though no hard
  numbers are published in the fetched docs.
- **Ingest requirement:** Same as Meilisearch — does not read a markdown folder natively; parse
  frontmatter+body into JSON and push via API on every change.
- **Deployment:** Self-hosted daemon (Docker or binary) is supported/documented; managed Typesense
  Cloud exists but **exact tier pricing was not confirmed** in this research — check
  typesense.org/pricing before committing.
- **Docs:** https://typesense.org/docs/29.0/api/
- **Version/license:** v29.0 confirmed, **GPL-3.0** self-hosted (copyleft — relevant if the wiki
  tooling is ever redistributed) or Typesense Cloud.
- **Files-as-truth:** Compliant with an ingest pipeline; index only.
- **Verdict:** **Evaluate as a Meilisearch alternative** — comparable facets + vector + self-hosted
  daemon, but **lacks Meilisearch's official MCP server**, costing more integration work against the
  MCP-first convention. Prefer Meilisearch unless a specific Typesense feature (typo-tolerance tuning)
  or its GPL terms are specifically wanted.

---

### Content-search: SaaS-only

#### Turbopuffer — https://turbopuffer.com/

Managed (**SaaS-only**) vector + full-text (BM25) search database with **multi-tenancy as a
first-class primitive** ("namespaces"). Purpose-built for exactly the "many teams sharing one search
backend" shape this cluster asks about — but with no exit path off the vendor.

- **Content:** Yes — approximate nearest-neighbor vector search plus BM25 full-text, explicitly
  combinable ("filters and ranking").
- **Metadata:** Filtering is mentioned but **exact frontmatter-facet semantics were not confirmed**
  from the pricing-page fetch — verify property-level filter syntax against the query-API docs before
  relying on it.
- **Graph:** **None** — same category as Meilisearch/Typesense.
- **Multi-tenancy:** Namespaces are the native multi-tenant unit, with "instant copy-on-write
  namespace" branching — a good structural fit if "team-wide" means literally separate per-team
  namespaces. Per-namespace CMEK is Enterprise-only.
- **Pricing (all managed, no self-host):**
  - **Launch — from $16/month** (multi-tenancy included).
  - **Scale — from $256/month** (adds HIPAA-ready BAA, SSO, audit logs, private Slack support).
  - **Enterprise — from $4,096/month** (adds single-tenancy, BYOC, CMEK, private networking, 24/7
    support, 99.95% uptime SLA).
- **MCP:** None mentioned in the fetched pricing page; likely needs a custom bridge.
- **Lock-in flag:** **Not self-hostable.** Even "BYOC" (Enterprise) is Turbopuffer-operated
  infrastructure inside your cloud account, not a binary you run. **The strongest lock-in risk of any
  tool in this cluster** — the team has zero exit path off the vendor's infrastructure model.
- **Files-as-truth:** Structurally compliant — Turbopuffer never becomes the canonical store, it is
  just a paid index over the markdown files (same relationship as Meilisearch). The deeper issue is
  SaaS-only, not the store constraint.
- **Version/license:** Proprietary SaaS, actively marketed with a clear enterprise tier; no
  version/release-cadence data surfaced.
- **Verdict:** **Evaluate only** if the team accepts a pure-SaaS, non-self-hostable content layer in
  exchange for multi-tenancy-native design and copy-on-write namespace branching. Otherwise prefer
  Meilisearch (self-hostable, official MCP, cheaper floor) unless namespace-per-team isolation
  specifically outweighs vendor lock-in concerns.

---

### Content-search: libraries (you build the server)

#### SQLite FTS5 — https://www.sqlite.org/fts5.html

Public-domain full-text-search virtual-table extension built into SQLite itself; embeddable,
zero-service, single-file database. **The most literal embodiment of "index is a disposable layer,
truth lives elsewhere" of anything surveyed** — its external-content-table pattern aligns exactly with
the hard constraint.

- **Content:** Yes — built-in BM25 ranking (`ORDER BY bm25(email)` or plain `ORDER BY rank`), with
  per-column weighting: `bm25(email, 10.0, 5.0)`.
- **Metadata:** Yes, **you build it** — ordinary SQLite columns hold parsed frontmatter alongside (or
  in an external-content table referenced by) the FTS5 index. No native frontmatter parser.
- **Graph:** **None** — build a separate edges table and populate it yourself by parsing `[[links]]`.
- **External-content pattern (the key fit):**
  ```sql
  CREATE VIRTUAL TABLE fts_idx USING fts5(b, c, content='t1', content_rowid='a');
  -- plus AFTER INSERT/UPDATE/DELETE triggers on t1 to keep fts_idx in sync
  ```
  The FTS5 index is a disposable layer over a separate "true" table you control, kept in sync via
  triggers. Docs explicitly warn: "It is the responsibility of the user to ensure that an FTS5
  external content table is kept consistent with the content table itself" — no automatic sync with
  markdown files; you write the ingest/trigger layer.
- **Contentless mode:** `CREATE VIRTUAL TABLE ft USING fts5(a, b, c, content='');` stores only the
  index, not the text — minimal storage when the source lives elsewhere (e.g. the markdown files on
  disk).
- **Merge tuning:** `automerge` / `crisismerge` / `usermerge` settings balance read vs write
  performance under incremental updates.
- **Concurrency:** Plain SQLite. In **WAL mode** (https://sqlite.org/wal.html): unlimited concurrent
  readers + a single writer; writers append to the WAL without blocking readers; each reader sees a
  consistent snapshot as of transaction start. Good enough for "many agents reading, one ingest
  process writing" — but **not** true multi-writer concurrency; checkpointing can stall if a reader is
  always active ("checkpoint starvation").
- **Deployment gotcha:** WAL mode over a **networked** filesystem (NFS) is documented as unreliable. A
  shared FTS5 backend should live on **local/attached disk** of the one process that owns it, with
  reads happening in-process or via a thin API in front — not multiple hosts opening the same `.db`.
- **Transport:** Embedded-only, no network protocol of its own. Wrap it in whatever server framework
  the stack uses (Python stdlib `sqlite3`, Node `better-sqlite3`, etc.). Cost: ~100-200 lines of
  ingest/query glue (frontmatter parsing, link-graph edges, result ranking) that
  Meilisearch/Typesense/qmd give for free.
- **License/maturity:** Public domain, zero cost; part of SQLite core — extremely mature, effectively
  permanent API.
- **Files-as-truth:** The **cleanest** fit — external-content tables make the index explicitly
  rebuildable from the files/rows that are truth.
- **Verdict:** **Adopt as the lean, zero-cost fallback** for content search if qmd's ~2GB footprint or
  Meilisearch's ingest complexity is unwanted. Best fit specifically because its external-content-table
  pattern most literally matches the hard constraint. Cost: you author frontmatter parsing, link-graph
  edges, and the query API yourself; no MCP/HTTP wrapper ships with it.

#### Tantivy — https://github.com/quickwit-oss/tantivy

Rust full-text search **library** (MIT), self-described as "closer to Apache Lucene than to
Elasticsearch" — a building block for a search engine, **not** an off-the-shelf server.

- **Content:** Yes — full inverted-index BM25-style search (Lucene-equivalent core).
- **Metadata:** Yes as facets — "Faceted search" and an "Aggregation Collector" (histogram, range
  buckets, average, stats metrics) are named features; frontmatter fields mapped to facet fields are
  filterable/aggregable.
- **Graph:** **None.**
- **Explicitly a library:** README states it is "not an off-the-shelf search engine server, but rather
  a crate that can be used to build such a search engine" and points to **Quickwit**
  (https://github.com/quickwit-oss/quickwit) for a distributed-search server built on top.
- **Primitives present:** Concurrent readers via the Searcher API; incremental indexing confirmed
  (FAQ: "Does tantivy support incremental indexing? Yes").
- **No built-in network/multi-client access** — you write the server wrapper yourself. (Docs mention a
  now-dated `tantivy-cli` with a REST API, but it is not the primary maintained artifact.)
- **Version/license:** v0.26.1 (2026-05-10), MIT, 100% Rust, actively released.
- **Files-as-truth:** Compliant — index rebuilt from files.
- **Verdict:** **Avoid raw Tantivy** — a library requiring you to build the entire
  server/API/multi-client layer, strictly more work than Meilisearch/Typesense for equivalent
  facet+content capability with none of their turnkey daemon/Cloud/MCP story. Worth a second look only
  via **Quickwit** (its packaged distributed-search server) if the team specifically wants
  Rust/Lucene-grade performance — **Quickwit was named but not independently fetched/verified in this
  research** and needs its own pass before being cited as a recommendation.

#### Orama — https://github.com/oramasearch/orama

Embeddable JavaScript/TypeScript search **library** (Apache-2.0), advertised as "a complete search
engine and RAG pipeline in your browser, server or edge network" under 2kb core, supporting full-text,
vector, and hybrid search.

- **Content:** Yes — hybrid full-text + vector in one engine natively (a genuine differentiator: most
  others need two systems fused). Very small.
- **Metadata:** Yes as facets — schema supports nested object fields (e.g. `meta: { rating: 'number'
  }`) with faceted search and field boosting.
- **Graph:** **None.**
- **Deployment-shape mismatch:** Fundamentally an in-process/embedded library for **browser, edge-
  function, or single-server-process** use — the project's own framing signals per-request/per-instance
  embedding, **not a shared always-on daemon** serving many independent clients.
- **Missing for a shared service:** No built-in authentication, concurrency control, or
  distributed-transaction support. Persistence/durability requires the separate
  `@orama/plugin-data-persistence` plugin; the core in-memory index is not durable by default, and
  reindex-on-restart is not documented as automatic. No file-watching over a markdown folder, no MCP
  integration found.
- **Version/license:** Apache-2.0, v3.1.18 (Dec 2025), 10.5k stars — genuinely popular and modern, but
  aimed at edge/serverless/client-side, not shared multi-tenant server backends.
- **Files-as-truth:** Would be compliant with a custom ingest, but that ingest does not exist here.
- **Verdict:** **Avoid** for this cluster's persistent-cloud goal — the least-server-shaped tool
  surveyed. Adopting it means building **both** the persistent-service wrapper (like obsidiantools
  needs) **AND** the ingest pipeline (like Meilisearch/Typesense need) for a less-proven
  concurrent-multi-tenant story — effectively worst-of-both here, despite being an excellent library
  in its own edge/browser niche.

---

### Cross-cutting notes

The central finding is unchanged in kind from the single-user report but sharper in consequence: **no
single engine in this cluster covers metadata + graph + content**, and moving to a persistent cloud
multi-tenant service does not remove that gap — it changes which axis matters most. Daemon-readiness,
multi-client concurrency, and "who runs the ingest/watch loop" now dominate, where before it was "does
this run on my laptop without a hassle".

What changed from the single-user framing:

- **"Daemon-capable" stopped being a nice-to-have and became the primary filter.** This eliminated or
  downgraded tools viable for a single loopback caller: **Tantivy and Orama** are excellent libraries
  but neither ships a server, so both cost the integrator a full custom service layer — a materially
  different ask than obsidiantools' modest wrapper gap.
- **obsidiantools** can no longer be "import and call `gather()` once" — it must be wrapped in a
  service loop (watcher + cache + HTTP/MCP endpoint). This is the single biggest net-new engineering
  cost.
- **qmd strengthens** rather than merely surviving: its ~2GB footprint amortizes across many teams
  sharing one instance instead of being a "why is this so heavy for my laptop" cost.
- **Turbopuffer** is purpose-built for the exact shape asked about (managed multi-tenancy, namespaces,
  from $16/mo) but is SaaS-only — worth flagging explicitly against any lock-in-averse instinct even
  though it structurally satisfies files-as-truth (it never becomes canonical, just a paid index).

Licensing/cost spread (quick comparison): obsidiantools (BSD-3, free), mddb (MIT, free), markdown-oxide
(Apache-2.0, free), qmd (MIT, free, ~2GB RAM/daemon), Meilisearch (MIT self-hosted free / Cloud from
$20/mo), Typesense (GPL-3.0 self-hosted / Cloud unconfirmed), Turbopuffer (SaaS only, $16/mo+, no
self-host), SQLite FTS5 (public domain, free), Tantivy (MIT, free, library-only), Orama (Apache-2.0,
free, library-only).

### Open questions (verify before building)

1. **qmd multi-tenant isolation** — actual concurrent request-handling and per-tenant isolation is
   undocumented. Load-test or ask upstream before trusting it for multiple teams querying one shared
   daemon.
2. **mddb backlinks/dangling** — roadmap language in the README, not confirmed shipped in v0.9.5.
   Re-check current source/CHANGELOG (or file an issue) before counting on it; the stalled cadence
   (last release 2024-03-07) is itself a signal.
3. **Typesense Cloud pricing** — not confirmed in this pass (only API docs fetched). Fetch
   typesense.org/pricing directly if seriously considered.
4. **Turbopuffer filter syntax** — exact metadata/frontmatter filter semantics inferred from a passing
   pricing-page mention, not confirmed against its query API docs.
5. **Quickwit** — Tantivy's packaged distributed-search server was named but not fetched. If raw
   Tantivy's "build the whole server" cost is too high, Quickwit deserves its own dedicated pass.
6. **All-in-one alternative** — no tool here combines all three query types in one process. **Basic
   Memory** (out of scope for this cluster, owned by another cluster/report) is worth cross-referencing
   since its all-in-one design might extend better to a cloud multi-tenant shape than composing 2-3
   services.

### Recommendation for this cluster

For a cloud, team-shared, markdown-as-truth MCP wiki, **compose two daemons, keep the files
canonical**:

1. **Graph + metadata + lint — adopt `obsidiantools`** (BSD-3, free), wrapped in a small
   watcher + cache + HTTP/MCP service you author. It is the only surveyed tool with native
   dangling-link detection (`nonexistent_notes`), the unmatched capability for the lint half. The
   wrapper is the biggest net-new cost, but it is modest (a FastAPI process + `watchdog` +
   module-level Vault cache). **`MarkdownDB / mddb`** is the one to revisit if its
   backlink/dangling roadmap ships — its `--watch` + Postgres/MySQL backend is architecturally closer
   to a cloud service, but today it cannot replace obsidiantools for the graph role.

2. **Content / semantic query — adopt `qmd`** (MIT, free) in `qmd mcp --http --daemon --host 0.0.0.0`
   mode, updated via a git-webhook-triggered `qmd update`. It is the only content tool that speaks MCP
   natively **and** reads markdown directly (no ingest step), fitting the workflow's MCP-first
   convention best. **Verify/harden its multi-tenant isolation before production.** The credible
   alternative is **`Meilisearch`** (MIT self-hosted / Cloud from $20/mo) — the only search engine
   with both an official MCP server and a managed multi-tenant Cloud tier — at the cost of an ingest
   pipeline (frontmatter/body → JSON → PUT) qmd doesn't need. Prefer Meilisearch specifically if the
   team wants managed SLAs/SSO/SOC2 or wants to avoid qmd's ~2GB footprint and unverified concurrency
   story.

3. **Lean fallback — `SQLite FTS5`** (public domain, free) via the external-content-table pattern, if
   qmd's footprint or Meilisearch's ingest cost is unwanted. It is the most literal embodiment of the
   hard constraint (index disposable, files truth), at the price of writing the frontmatter parsing,
   link-graph edges, and query API yourself.

**Rank for this wiki:** (1) obsidiantools + qmd (the recommended pair), (2) obsidiantools +
Meilisearch (if managed/SLA/MCP-official content is preferred over qmd's zero-ingest simplicity), (3)
obsidiantools + SQLite FTS5 (lean, all-owned fallback). **Downrank:** Typesense (no official MCP),
markdown-oxide (LSP-not-MCP transport), Tantivy/Orama (libraries with no server), and Turbopuffer
(SaaS-only lock-in). This is the same two-tool shape as the single-user report — a graph tool plus a
content tool — but each half now additionally carries a persistence/daemon/concurrency layer that was
previously optional.
