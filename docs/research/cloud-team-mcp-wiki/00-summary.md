# Hosting the Wiki as a Shared Team Cloud MCP Server

The karpathy-style LLM wiki today is an Obsidian vault reached through the Obsidian Local REST API's
built-in MCP server — which only works while the desktop app is running on one WSL box, so the wiki
cannot be a team-wide, always-on service. This report decides how to move that MCP server onto a
cloud platform where multiple teams share one persistent endpoint, while the canonical store stays
plain, git-diffable markdown and every index/graph/search engine remains a disposable layer rebuilt
from those files. It re-opens the compute-layer question that the prior single-user research
(`docs/research/headless-wiki-hosting.md`) closed, because "team + cloud + always-on" changes which
tool properties dominate — and settles the hosting, auth, write-safety, storage, editing-surface, and
MCP-tool-design choices around it.

## Recommendations at a glance

- **Compute layer verdict — the single-user `obsidiantools + qmd` shape survives, but sharpens into
  "two daemons, not two libraries."** No surveyed engine covers metadata + link-graph + content in one
  process, so a cloud deployment still composes a graph/metadata tool with a content tool. The
  difference from the single-user recommendation is operational, not architectural: `obsidiantools`
  (BSD-3, the only tool with native dangling-link detection) now needs a hand-written watcher + cache +
  MCP wrapper, and `qmd` (MIT) *strengthens* because its `qmd mcp --http --daemon` mode and ~2GB model
  footprint amortize across many shared clients. `Basic Memory` (AGPL-3.0, MCP-native, all-three-in-one)
  is the one credible all-in-one, but its team auth is a paid SaaS gate and its concurrent-write story
  is undocumented — so it stays a strong lead to imitate, not the settled answer.
- **Host it on Fly.io (or a plain VPS+Docker) so the vault is a literal git checkout on a persistent
  disk** — the cleanest read of markdown-as-truth, and it runs the Python `obsidiantools`/`qmd` stack
  that JS-only serverless platforms (Cloudflare Workers, Vercel) cannot host without a rewrite. Take the
  Cloudflare Workers+Durable Objects / Cloud Run serverless path only if the team deliberately accepts a
  git→object-store (R2/GCS) sync layer for true scale-to-zero.
- **Auth is a fixed contract plus a placement decision.** The server must be an OAuth 2.1 resource
  server implementing RFC 9728 PRM + RFC 8707 Resource Indicators + PKCE S256 — non-negotiable, every
  client assumes it. No vendor ships per-team scoping turnkey, so the server's own tool layer checks a
  `team`/`org_id` claim. Pilot **Gram** or **Obot** (the only surveyed gateways with turnkey per-team
  sub-catalogs/RBAC); use **WorkOS AuthKit + Cloudflare Access** as the lighter path for one server.
- **Write-safety is a composite pattern, not a product:** optimistic concurrency via a
  **precondition-hash** (GitHub-Contents-`sha` / ETag-If-Match semantics) as the core primitive, applied
  by a **single serialized writer/compactor**, wrapped in **git branch-per-write + PR/merge-queue** as
  the outer loop — the `obsidian-memory-for-ai` propose→apply→receipt design maps almost one-to-one onto
  the existing `inbox/` + ingest-skill + git structure. CRDTs and advisory file locks are ruled out.
- **Storage substrate: a GitHub/GitLab git repo reached via a persistent local clone.** Git history is
  the backup/audit/DR story for free. SQLite+Litestream backs up only the *disposable* index; object
  storage (R2) is a backup target, never the live edit surface; managed NFS is oversized and avoided.
- **Human editing surface: git-PR flow + Perlite (read-only) + the agent-only-writes discipline** — zero
  net-new always-on services. Add **Sveltia CMS** (MIT, PAT-mode, no backend) only if a guided
  form/preview editor is wanted. HedgeDoc is disqualified (owns its own DB).
- **MCP tool surface: build a custom, direct-filesystem server** copying cyanheads/obsidian-mcp-server's
  shape (Apache-2.0, safe to vendor) with Basic Memory's naming (AGPL, imitate only). Pin spec
  `2025-11-25`; expose capture/query/ingest/lint as **tools**, pages as a `wiki:///{path}` **resource
  template**; annotate every tool; split ingest `propose`/`apply` with a precondition-hash; gate
  destructive lint + alias-merge behind elicitation.
- **Cost is a rounding error and git is the DR plan.** All-in ≈ under ~$40/month for a single team
  (Hetzner €5–20 + Claude tokens $1–20 + sub-$1 storage), a step function in volume not a per-seat
  multiplier. "Backup ≠ DR" — losing the index is a rebuild, never data loss.

## Recommended end-to-end stack

| Concern | Chosen tool | Why | License |
|---|---|---|---|
| Graph + metadata + lint | **obsidiantools** (wrapped as a daemon) | Only surveyed tool with native dangling-link detection (`nonexistent_notes`) + frontmatter + backlink graph | BSD-3 |
| Content / semantic query | **qmd** (`qmd mcp --http --daemon`) | Speaks MCP natively, reads markdown directly (no ingest step), BM25+vector+rerank; footprint amortizes across shared clients | MIT |
| — content alternative | Meilisearch (official MCP + Cloud) or SQLite FTS5 (lean fallback) | Managed SLA/SSO path, or the most literal "index is disposable" embodiment | MIT / public domain |
| — all-in-one lead to watch | Basic Memory | Only MCP-native single process doing all three; blocked on paid team auth + unproven concurrent writes | AGPL-3.0 |
| Cloud hosting | **Fly.io** (Machines+Volumes) | Literal git checkout on a real persistent disk; runs the Python stack; autostop ≈ $5–15/mo | (PaaS) |
| — hosting alternatives | Plain VPS+Docker (zero lock-in) / Cloudflare Workers+DO (scale-to-zero, needs git→R2 sync) | Lowest-delta off Obsidian / true serverless economics | — |
| Auth contract | **MCP Authorization spec** (OAuth 2.1 + RFC 9728 + RFC 8707 + PKCE S256) | The fixed wire contract every MCP client assumes | spec |
| Per-team gating | **Gram** or **Obot** (pilot) / **WorkOS AuthKit + Cloudflare Access** (light) | Only surveyed tools with turnkey per-team sub-catalogs/RBAC / lightest spec-compliant path | AGPL-3.0 / OSS+paid / proprietary |
| Write-safety | **precondition-hash + serialized compactor + git PR/merge-queue** (propose→apply→receipt) | Cheapest no-lost-update guarantee that keeps markdown literal; maps onto existing `inbox/`+git | pattern / free |
| Storage substrate | **Git repo (GitHub/GitLab) via persistent local clone** | Git history = durability/audit/backup for free; satisfies git-diffable by definition | free |
| Index backup | **Litestream → Backblaze B2** | Fast index-recovery only (index is disposable); sub-$1/mo | OSS / commercial |
| Human write surface | **git-PR flow** (+ optional **Sveltia CMS**, PAT mode) | Zero new services, perfectly git-diffable, reuses repo auth | host / MIT |
| Human read surface | **Perlite** (read-only) | Obsidian-like browse over the folder, writes nothing | MIT |
| Editing discipline | **agent-only-writes** (Karpathy pattern) | Shrinks the human write requirement to near-zero | policy |
| MCP server | **custom direct-FS server**, cyanheads shape + Basic Memory naming | Backend-agnostic surface honoring markdown-canonical; neither precedent adoptable as runtime | Apache-2.0 (vendor) |
| Security | MCP spec transport MUSTs in-server + **mcp-context-forge** gateway + tool-per-scope RBAC + gitleaks/Presidio + mcp-scan | Gateway = RBAC+rate-limit+audit in one; two-tier PII scan flag-and-report only | Apache-2.0 / MIT |
| Seeding extractors | **docling** (PDF/office), slackdump (Slack), confluence-to-llm-wiki (template) | Disposable step-1 front-ends feeding this repo's own `wiki-ingest`; all taxonomy-blind | MIT / AGPLv3 / MIT |
| Governance | **CODEOWNERS** + `owner:`/`review_by:` frontmatter + SSoT sentence + Vale | File-native ownership, staleness trigger, controlled-vocab enforcement | free / MIT |
| Ops / hosting cost | **Hetzner** (€5–20/mo) + git-as-DR + Uptime Kuma + healthchecks.io | Two monitoring signals (reachable-now vs. cron-ran); git is the primary DR | commercial / MIT / BSD |

## Cross-cluster capability matrix

For the compute/server candidates — the tools that could *be* (or back) the wiki's query engine:

| Candidate | Headless | Metadata query | Backlink graph | Dangling-link detect | Content search | API / MCP | Keeps files canonical | Multi-user |
|---|---|---|---|---|---|---|---|---|
| **obsidiantools** | Yes (library) | Yes (`front_matter_index`) | Yes | **Yes (native, unique)** | No | No — wrap it | Yes (read-only) | No (you build it) |
| **qmd** | Yes (daemon) | No | No | No | **Yes (BM25+vector+rerank)** | **Native MCP+HTTP** | Yes (no ingest step) | Reachability yes; isolation unverified |
| **Meilisearch** | Yes (daemon) | Yes (after ingest) | No | No | Yes (hybrid FT+vector) | Official MCP | Yes (index only) | Yes (Cloud multi-tenant) |
| **SQLite FTS5** | Embedded | Yes (you build) | No (you build edges) | No | Yes (BM25) | No — embed it | **Yes (cleanest)** | WAL: many readers / 1 writer |
| **markdown-vault-mcp** | **Yes (HTTP/SSE)** | Yes (frontmatter index) | **No** | **No** | Yes (FTS5+vector RRF) | **Yes (32+6 tools)** | Yes (index disposable) | Auth at proxy only |
| **Basic Memory** | Yes (MCP server) | Yes | Yes (typed wikilinks) | (not documented) | Yes (FTS+vector) | **First-party MCP** | Yes (SQLite = layer) | Paid hosted tier only |
| **SilverBullet** | Yes (Docker) | Yes (SLIQ) | Yes (bidirectional) | (via SLIQ, unverified) | Page/attribute only | Third-party sidecar | Yes ("Space" = folder) | Coarse (space-level) |
| **markdown-oxide** | Yes (LSP daemon) | Partial (tags) | Yes (interactive) | No batch report | No | LSP only (no MCP) | Yes | 1 client/process |
| **cyanheads/obsidian-mcp-server** | Yes (stdio+HTTP) | Yes (frontmatter tools) | No | No | BM25 via plugin | **Yes (14 tools)** | Needs FS swap (app-dep today) | Folder-scoped ACL |
| **Our custom server (proposed)** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes (native)** | **Yes** | **Yes (team-scoped)** |

The bottom row is the target: no single existing tool fills every column, which is exactly why the
recommendation is a *composed* custom MCP server over `obsidiantools`+`qmd`, not adoption of one product.

## Phased migration plan

**Phase 0 — today.** Single-user WSL, Obsidian desktop open, `wiki-*` skills reaching the vault through
the Obsidian Local REST API MCP. Canonical markdown already in git. This is the baseline to de-risk away
from without ever putting the files at risk.

**Phase 1 — Stand up the headless server beside Obsidian (dual-run, read-mostly).** Deploy the custom
direct-filesystem MCP server (cyanheads shape) wrapping `obsidiantools`+`qmd` on Fly.io (or a VPS),
pointed at a persistent git clone of the same vault. Run it **read-only** and in parallel with the
existing Obsidian-MCP path. *De-risks:* proves headless query (metadata + backlinks + dangling-link +
content) works off-app before anything writes; the Obsidian setup stays the fallback. Add Perlite as the
read UI so humans can browse without the desktop app.

**Phase 2 — Add the safe write path.** Turn on `wiki_capture`/`wiki_ingest` behind the precondition-hash
+ serialized-compactor + git-PR/merge-queue pattern, with `wiki-lint` as a required status check.
*De-risks:* concurrent ingest can no longer silently clobber a page; every write becomes an auditable git
commit; the propose→apply→receipt split gives a human review gate before anything lands on `main`.

**Phase 3 — Make it team-shared: auth + RBAC.** Put the MCP Authorization contract in the server itself,
front it with a gateway (Gram/Obot pilot, or WorkOS AuthKit + Cloudflare Access), and enforce
tool-per-scope RBAC (`wiki-capture`→write `inbox/`; `wiki-ingest`→write canonical layers; query/lint
read-only) with the disposable index inheriting the same tenant predicate. Add governance files
(CODEOWNERS, `owner:`/`review_by:` frontmatter). *De-risks:* multi-team access without cross-team leakage;
named ownership and staleness triggers before a second human contributor arrives.

**Phase 4 — Cut over and keep a local editor.** Retire the Obsidian-desktop MCP dependency as the
*primary* path; the cloud server becomes canonical-access. **Deliberately keep a local editing escape
hatch** — the git-PR flow (github.dev) for hand-fixes and, if wanted, Sveltia CMS in PAT mode, plus the
option of `obsidian-headless` in `pull-only`/`mirror-remote` mode for anyone who insists on the desktop
app as a one-way mirror. *De-risks:* no single point of failure on the cloud server; humans never lose
the ability to touch files directly; the agent-only-writes discipline keeps that path rarely needed.

**Phase 5 — Operationalize.** Litestream/restic → B2 for fast index recovery, Uptime Kuma +
healthchecks.io for the two monitoring signals, a quarterly git-clone→rebuild→health-check DR drill with
a named owner. *De-risks:* the silently-stale-index failure mode, and turns DR from tribal knowledge into
a timed runbook.

## Reading guide

- **01 — Compute, compose your own.** The graph/metadata + content engine survey (obsidiantools, qmd,
  Meilisearch, Typesense, SQLite FTS5, Tantivy, Orama, mddb, markdown-oxide, Turbopuffer); why "no single
  engine covers all three axes" survives into the cloud and "daemon-readiness" becomes the new filter.
- **02 — All-in-one compute servers.** The "buy one process" candidates (Basic Memory, SilverBullet,
  Logseq, Outline, TriliumNext, Anytype, AppFlowy, AFFiNE) against the markdown-as-truth test; only Basic
  Memory and SilverBullet pass, and neither closes the native-MCP + team-auth + files-canonical gap.
- **03 — Cloud hosting for the MCP server.** Where the process runs (Fly.io, VPS, Cloudflare Workers+DO,
  Cloud Run, Railway, ECS/Fargate, Lambda, App Runner, Render, Vercel); the "literal git checkout vs.
  object-store sync" fork; why Smithery/Gram/mcp.run are not compute layers.
- **04 — MCP auth & multi-tenancy.** The fixed OAuth 2.1 + RFC 9728/8707 + PKCE contract, and where the
  authorization server and per-team scoping live (WorkOS, Stytch, Descope, Auth0, Clerk, Ory, Cloudflare
  Access, Gram, Obot, Docker MCP Gateway).
- **05 — Concurrent-write safety.** The composite no-lost-update pattern — precondition hash + serialized
  compactor + git PR/merge-queue + propose→apply→receipt — and why advisory locks and CRDTs are ruled out.
- **06 — File storage and sync.** Where canonical markdown physically lives: git repo (adopt) vs. object
  storage (backup only) vs. managed NFS (avoid) vs. SQLite+Litestream (index only) vs. obsidian-headless.
- **07 — Team conventions & governance.** Ownership (CODEOWNERS), staleness triggers (`owner:`/`review_by:`
  frontmatter, Confluence/Notion patterns), an explicit SSoT sentence, and Vale for prose linting.
- **08 — Seeding & growing the wiki.** Bulk-ingest front-ends (docling, slackdump, confluence-to-llm-wiki),
  ingest-safety (secure-llm-wiki trust tiers), and calibration numbers (stub thresholds, atoms-per-page).
- **09 — MCP discovery & supply-chain vetting.** How to find, trust, package, and sandbox MCP servers
  (official Registry, Anthropic Connectors, Glama, PulseMCP, Smithery, Docker MCP Toolkit, mcp-scan, OWASP).
- **10 — Contribution, discovery & notification UX.** Find-before-write dedup (build it in `wiki-ingest`),
  search-first page creation (Dendron Lookup), per-page notifications (GitHub→Slack gap), and the one
  adopt-and-evaluate server, markdown-vault-mcp.
- **11 — Wiki information architecture.** Keeping the closed 5-type taxonomy; the multi-team namespacing
  answer — one vault + an `owner:` frontmatter field (Backstage pattern) + per-team `map` pages, never
  folder-per-team or numeric IDs.
- **12 — Security & tenant isolation.** The six-threat architecture: MCP transport MUSTs in-server, one
  gateway for RBAC+rate-limit+audit, tool-per-scope dual enforcement, two-tier PII scan, the lethal-trifecta
  constraint on ingest.
- **13 — Human editing surface.** Reading/writing without Obsidian: git-PR flow + Perlite + agent-only-writes
  as the baseline; Sveltia CMS as the thin editor; HedgeDoc disqualified; TinaCMS flagged.
- **14 — Our MCP server tool & resource design.** The wire contract and tool surface — tools vs. resources
  vs. prompts, annotations, pagination, progress, elicitation, and the precedent taxonomies (cyanheads,
  Basic Memory) to imitate.
- **15 — Ops, DR & TCO.** Git-as-DR, Litestream/restic/B2 backups for the disposable index, the two
  monitoring signals, the qmd-local-vs-hosted-embedding cost decision, and the sub-$40/month single-team model.
