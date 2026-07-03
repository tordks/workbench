## 02. All-in-One Compute Servers (single-process "BUY" candidates)

This cluster asks a narrow question: **is there a single existing server product we can point at the wiki's folder of `.md` files, run headless on a cloud box, and get metadata + link-graph + content query out of one process — for a whole team?** The answer is a qualified *almost*. Two of the eight tools surveyed keep markdown as the source of truth (Basic Memory, SilverBullet); the other six own their storage in a SQLite/Postgres/CRDT/RocksDB schema and treat markdown as an import/export bridge — which disqualifies them as the **canonical store** under the hard constraint, though several are worth studying as presentation or MCP-design references. No single tool here delivers native first-party MCP **and** real self-hosted team auth **and** markdown-as-truth simultaneously; that gap is the main finding of this cluster.

**Takeaways:**
- **Only Basic Memory and SilverBullet pass the markdown-as-truth test.** Everything else stores canonical content in its own DB/CRDT and is disqualified as the store (still possibly useful as a disposable layer or UI).
- **Basic Memory** is the closest single-process fit (MCP-native, files canonical, SQLite/Postgres index as a rebuildable layer, all three query types in one server) — but its **team auth is a paid hosted SaaS tier** (WorkOS-gated); self-hosted OSS is effectively single-user and AGPL-3.0.
- **SilverBullet** is a genuine headless HTTP server over a folder of `.md` files with a native SLIQ query language and bidirectional links — but its **MCP is a third-party sidecar**, and team auth is coarse (space-level).
- **Logseq** splits: its mature file-graph mode is markdown-native (no MCP); its actively-developed DB version drops files for SQLite + adds team RTC — the wrong direction, and self-flagged data-loss-risky in beta.
- **Disqualified as store** (own their format): TriliumNext (SQLite), Anytype (CRDT object DB), Outline (Postgres — but best native MCP + SSO to study), AppFlowy (RocksDB, documented data-loss bug), AFFiNE (CRDT + Postgres, no MCP found).
- The persistent gap (native MCP + team auth + markdown-truth in one process) is the strongest argument that the **compose route** (obsidiantools + qmd from the prior single-user report) may still need re-examination for team/cloud, rather than assuming Basic Memory alone closes it.

---

### At-a-glance comparison

| Tool | Markdown = canonical? | Native MCP | Link-graph | Content search | Frontmatter query | Team auth (self-host) | License | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Basic Memory** | ✅ Yes (files; SQLite/PG = index layer) | ✅ First-party (stdio + HTTP) | ✅ Typed `[[wikilink]]` backlinks | ✅ Hybrid FTS + vector (FastEmbed) | ✅ Yes | ⚠️ Paid hosted tier only (WorkOS) | AGPL-3.0 | **Adopt (leading BUY)** |
| **SilverBullet** | ✅ Yes ("Space" = folder of `.md`) | ⚠️ Third-party sidecar | ✅ Bidirectional backlinks | ⚠️ Page/attribute search, not semantic | ✅ SLIQ (SQL-like) | ⚠️ Coarse (space-level) | MIT | **Evaluate / steal-the-idea** |
| **Logseq (file mode)** | ✅ Yes (`.md`/`.org` graph) | ❌ None first-party | ✅ Backlinks/queries native | ⚠️ App-side, not headless API | ✅ Live queries | ❌ None in file mode | AGPL-3.0 | **Evaluate (UI layer only)** |
| **Logseq (DB version)** | ❌ No (SQLite) | ❌ | ✅ | ⚠️ | ✅ | ⚠️ RTC alpha | AGPL-3.0 | **Avoid (wrong direction)** |
| **TriliumNext** | ❌ No (SQLite doc DB) | ⚠️ Community only (ETAPI) | ✅ Relation/note maps | ✅ Built-in FTS | — | ⚠️ OpenID+TOTP (single-tenant) | AGPL-3.0 | **Avoid as store** |
| **Anytype** | ❌ No (CRDT object DB) | ❌ (gRPC/Agents API) | — | — | ⚠️ Run whole any-sync network | ASYAL 1.0 (source-available) | **Avoid** |
| **Outline** | ❌ No (Postgres) | ✅ **First-party** (OAuth) | — (collections) | ✅ Built-in | ✅ **SSO: Google/Slack/Cognito/OIDC** | BSL 1.1 | **Avoid as store; study MCP+SSO** |
| **AppFlowy** | ❌ No (RocksDB + SQLite) | ❌ None found | ❔ Unconfirmed | ❔ Unconfirmed | ⚠️ Separate AppFlowy Cloud stack | AGPLv3 | **Avoid** |
| **AFFiNE** | ❌ No (CRDT + Postgres) | ❌ None found | ❔ Unconfirmed | ❔ Unconfirmed | ❔ Implied, unconfirmed | AGPLv3 (unconfirmed this pass) | **Avoid** |

Legend: ✅ present / native · ⚠️ present but caveated · ❌ absent · ❔ not confirmed in this pass · — not applicable/not documented.

---

### Tier 1 — Passes markdown-as-truth

#### Basic Memory — `github.com/basicmachines-co/basic-memory`

**What it is.** A local-first knowledge-management **MCP server** where plain Markdown files on disk are the canonical store, and a SQLite (default) or Postgres index is built alongside purely as a disposable search/metadata cache. This is the **only surveyed all-in-one server that passes the markdown-as-truth test outright** — frontmatter, backlink graph, and hybrid search all come from one MCP process reading the same folder of `.md` files the wiki already uses, with **no format conversion**.

**Why it fits the mandate.**
- Canonical store is plain Markdown — the project's own framing is *"plain text on your disk. Forever."* The SQLite/Postgres index is **rebuildable, not authoritative** — exactly the "disposable layer over files" shape the hard constraint demands.
- A **single MCP server process exposes all three capabilities at once**:
  - **Frontmatter query** — YAML title / permalink / tags.
  - **Link-graph query** — a typed `[[wikilink]]` knowledge graph with backlinks.
  - **Content query** — hybrid full-text + **vector semantic search** via **FastEmbed** embeddings.
- **Native MCP transport (stdio + HTTP)**, compatible with Claude Desktop, Claude Code, Cursor, VS Code, and any MCP client — **no proxy layer needed**, unlike the Obsidian local-rest-api plugin approach already ruled out (which needs the desktop app running).
- Tools exposed include `write_note`, `search_notes`, `build_context` — it can **read and write** notes.

**Concrete details.**
- Repo: `github.com/basicmachines-co/basic-memory` · License **AGPL-3.0** · **v0.22.1** · 86 releases · 1,487 commits · ~12.5k Discord community.
- Self-host: **Dockerfile + docker-compose included**; requires **Python 3.12+ via `uv`**; **Testcontainers** support for Postgres-backed testing.
- Storage config: **SQLite by default**, optional **Postgres backend** for the index/metadata layer.
- Auto-update channels via `uv` / Homebrew.

**Gotchas / constraints.**
- **Team auth is not free and not self-hosted.** *"Basic Memory Teams"* is a **hosted multi-user cloud tier** with cross-device sync and **WorkOS AuthKit** auth. The **self-hosted OSS build is effectively single-user / single-vault** and needs **Git or Syncthing** for multi-machine sync. To get team access on self-hosted, you would bolt on a reverse proxy + SSO (Authelia / oauth2-proxy) yourself — see open question (1).
- **AGPL-3.0** is copyleft; **network use may trigger source-disclosure obligations** depending on deployment shape. Needs legal review if bundled into anything distributed.
- **Write capability is a double-edged sword.** Because it can write (`write_note`), if adopted as a layer its writes could nudge files toward *its own* conventions — a risk already flagged in the prior single-user research. Concurrent multi-agent writes to the same files also raise corruption/merge-conflict questions (open question (1)).

**Verdict.** **Adopt as the leading BUY candidate for compute.** It is the only tool here where markdown genuinely stays canonical and one process gives all three query types. But for a *self-hosted team* deployment it still needs bolt-on auth (reverse proxy + SSO), and the AGPL-3.0 license needs review if bundled into a distributed product.

---

#### SilverBullet — `github.com/silverbulletmd/silverbullet`

**What it is.** A web-based, self-hosted "note-taking wiki" server where a **"Space" = a folder of Markdown pages**, built as a **TypeScript/Deno** server with a browser client. Queries and bidirectional links are first-class. It **already solves the "no Obsidian app needed" half of the mandate** — it runs as a persistent headless HTTP server by design.

**Why it fits (and where it doesn't).**
- **Passes markdown-as-truth:** the Space is literally a directory of `.md` files served over HTTP, **no DB in the write path** for canonical content.
- **Native metadata query — SLIQ.** Built-in **"Objects and Queries" (SLIQ)** gives SQL-like querying over frontmatter/page attributes and other extracted "objects" (tasks, tags, links). This is a **native** frontmatter/metadata query mechanism, not bolted on — and is a strong pattern worth mimicking even if the wiki keeps its own skills.
- **Link-graph:** bidirectional links are tracked automatically (backlinks panel) in the same process serving the pages.
- **Genuinely headless:** `docker run -p 3000:3000 -v <PATH>:/space silverbullet` — no desktop app dependency at all.
- **MCP is *not* native/first-party.** The GitHub UI shows only a generic "MCP Registry" nav item (a GitHub feature, not a SilverBullet one). MCP comes via a **third-party bridge**: `github.com/Ahmad-A0/silverbullet-mcp`, a standalone sidecar that talks to SB's own HTTP API and handles its own token auth — it works even against managed hosts like Pikapod.
- **Content search is page/attribute-level, not semantic.** No vector/rerank retrieval documented — so it does **not** match the "ranked / semantic retrieval" requirement on its own; you'd still pair it with something like qmd for that.

**Concrete details.**
- Repo: `github.com/silverbulletmd/silverbullet` · License **MIT** (no lock-in) · latest **v2.9.0 (2026-06-11)** · stack TypeScript 73% / Rust 16% / Lua 7.5%.
- Self-host: `docker run -p 3000:3000 -v <PATH>:/space silverbullet`; server has **built-in authentication for the space** (coarse, space-level — no documented per-user ACLs in the fetched material).
- MCP bridge `github.com/Ahmad-A0/silverbullet-mcp`: standalone **Docker Compose sidecar**; env vars **`SB_AUTH_TOKEN`** (SB→bridge) and **`MCP_TOKEN`** (client→bridge); **SB default `:3000`, MCP server default `:4000`**; works with `mcp-remote` config in `claude_desktop_config.json` / `~/.cursor/mcp.json` / windsurf config.

**Gotchas / constraints.**
- **Team auth is coarse** (space-level, not documented per-user ACLs) — needs more investigation before a team deployment.
- **MCP path is third-party and of unverified maturity** — the bridge is a small community project. Treat as evaluate-only until maturity is checked (open question (2)).

**Verdict.** **Steal-the-idea / evaluate as a compute layer**, not necessarily the wiki editor itself. Its native SLIQ query engine over frontmatter + objects is a strong headless-metadata-query answer worth mimicking even if the wiki keeps using its own capture/ingest skills. Because MCP is a third-party sidecar and content search isn't semantic, treat it as evaluate-only.

---

### Tier 2 — Split / transitional

#### Logseq — `github.com/logseq/logseq`

**What it is.** A local-first, block-based outliner/PKM tool. **Historically** stores everything as plain **Markdown (or Org-mode) files on disk** — but is **mid-transition** to a new SQLite-backed "DB version" with real-time collaboration.

**The split.**
- **Traditional (file-graph) mode — passes markdown-as-truth.** Canonical storage is plain Markdown/Org files in a local folder ("graph"), local-first, no DB required. Matches the wiki's existing file layout closely, including its own `[[wikilink]]` convention and block-refs. Backlink graphs and block/page queries are core, native features.
- **New "DB version" (beta) — fails the mandate.** Switches canonical storage to **SQLite** and adds **RTC (Real-Time Collaboration, currently alpha)** for team/multi-device sync. This is the **opposite direction** from the mandate, and the project's own docs warn *"data loss is possible"* and recommend automated backups during beta.
- **No first-party MCP** found in either mode. The repo shows `.agents/skills` directories (agent-integration scaffolding) but **no documented first-party MCP tool surface** — a custom or community bridge would be needed.
- **Self-hosting serves the app UI, not a headless query API.** Docker is possible (Dockerfile + a "Docker Web App Guide"), but it serves the app, so you'd still compose obsidiantools/qmd on top for headless metadata/graph/search — **same situation as the Obsidian case in the prior report.**

**Concrete details.**
- Repo: `github.com/logseq/logseq` · License **AGPL-3.0** · 43.7k stars · 24,863 commits · 152 releases · active on both `master` (file graphs) and `test/db` (SQLite DB version).
- DB version status: **beta**; **RTC is alpha**; official recommendation to keep automated backups due to possible data loss.
- Docs: plugin API `plugins-doc.logseq.com`; "Docker Web App Guide" for self-hosting the UI.

**Verdict.** **Evaluate only in classic file-graph mode** as a possible UI/graph-query layer over the exact same markdown folder — but it has **no MCP**, so it does not solve headless team query by itself. **Avoid the new DB version entirely** for this mandate: it moves away from markdown as canonical (the opposite of the constraint) and is beta/alpha with data-loss risk. Note the tension: the file mode that respects the mandate has **no team sync**, and the version that adds team sync (RTC) is the one that **drops markdown as canonical**.

---

### Tier 3 — Disqualified as the canonical store (own their format)

All five below fail the markdown-as-truth test **structurally, not as a maturity gap** — each treats markdown as an import/export convenience at the edges, never the live representation. They are listed for completeness and for the design ideas worth scavenging.

#### Outline — `github.com/outline/outline` — *the best MCP+SSO to study*

**What it is.** A polished team wiki/knowledge-base web app (*"the fastest wiki and knowledge base for growing teams"*) on a **Postgres + Redis** backend, markdown-compatible editing and import/export.

- **Disqualified as store:** documents live in **PostgreSQL** (attachments in S3/MinIO/local disk). Markdown is only the editing/import-export surface — no folder of `.md` files to git-diff or edit directly. Round-tripping through Outline would lose the git-diffable file as truth.
- **Genuine first-party MCP** — the strongest in this whole cluster. Outline's own docs include an MCP guide (`docs.getoutline.com/s/guide/doc/mcp-6j9jtENNKL`) letting AI assistants search, read, create, and edit documents via the open MCP standard, defaulting to **OAuth** (API-key auth also available). This is a **real native MCP server**, not just a wrapper (though third-party servers `nbhansen/outline-mcp-server` and `Vortiago/mcp-outline` also exist).
- **Strongest team/SSO story of the disqualified group:** SSO via **Google, Slack, AWS Cognito/OIDC**, collections-based hierarchy, comments.
- Self-hosting mature via Docker/Compose (community guides: AWS Cognito+RDS, Zerops, Dokploy templates, OIDC + local object storage).

**Concrete details.**
- License **BSL 1.1** (Business Source License — converts to open-source after a time-delay per BSL terms; **not permissive at time of use**) · latest **v1.8.1 (2026-06-06)**.
- Backend: **PostgreSQL** (documents/metadata), **Redis** (cache/realtime), **S3-compatible storage or local disk** (attachments) — e.g. `postgres://outline:outline_password@postgres:5432/outline`.

**Verdict.** **Avoid as the canonical store** (Postgres-backed, fails markdown-as-truth) — but note as the **strongest evidence in this cluster that a product-grade MCP server + team SSO + Docker self-host combination is achievable.** Worth studying its MCP design. Also flagged for a possible **presentation-layer** role (read-only, fed by one-way markdown→Outline sync, mirroring Perlite) — see open question (4).

#### TriliumNext Notes — `github.com/TriliumNext/Trilium`

- A hierarchical PKB (community fork of original Trilium) storing everything in an **internal SQLite document database** (notes / branches / attributes / relations), with Markdown as **import/export only**. **Disqualified:** editing the wiki's `.md` files would mean round-tripping through Trilium's converter, breaking git-diffability and agent-editability.
- **No first-party MCP.** Its automation surface is the **ETAPI REST API**. MCP exists only via community servers: `tan-yong-sheng/triliumnext-mcp`, `perfectra1n/triliumnext-mcp`, `RadonX/mcp-trilium`, `ovden13/trilium-mcp` (Go binary, ETAPI + token).
- Link/graph exists as **relation maps** and **note/link maps** (visualization); full-text search built in — but over Trilium's own note graph, not an external markdown folder.
- Auth: **OpenID + TOTP** for the instance — single-tenant personal-KB auth, **not team RBAC**.
- License **AGPL-3.0** · latest **v0.103.0 (2026-05-13)** · **351+ releases**, nightly builds, official DockerHub images, scales to 100,000+ notes.
- **Verdict: avoid as the store.** Could theoretically be scavenged for its relation-map UI concept, but not worth adopting given the format mismatch.

#### Anytype — `github.com/anyproto/anytype-ts`

- Local-first, offline-first knowledge/object DB on a **proprietary CRDT sync protocol (any-sync)** with zero-knowledge encryption. **Not a markdown-file app at all** — content is typed "objects" in Anytype's own format. **Disqualified: there is no folder of `.md` files to point tooling at.**
- **No first-party MCP** — extensibility is via **gRPC API** and an "Agents" surface (separate `AGENTS.md`), a lower-level path than MCP.
- **"Self-hosting" is heavy:** it means running your own **any-sync network** — `any-sync-coordinator`, `any-sync-node` ×3, `any-sync-filenode`, `any-sync-consensusnode` — backed by **MongoDB, Redis, and S3-compatible storage (MinIO)**. That is standing up a whole P2P sync backend, not a wiki server. A community bundle `grishy/any-sync-bundle` packs the official services into a single Go binary for simpler homelab self-hosting.
- License **"Any Source Available License 1.0" (ASYAL 1.0)** — **source-available, not a standard OSI open-source license** (verify terms before any commercial/team use).
- Repo: `anytype-ts` · latest **v0.55.21-alpha (2026-06-29)** · 286 releases · 32,438 commits on develop (still alpha-versioned).
- Self-host repos: `anyproto/any-sync-dockercompose` (official, personal-scale), `grishy/any-sync-bundle` (community), docs at `tech.anytype.io/how-to/self-hosting`.
- **Verdict: avoid.** Fails markdown-as-truth and self-hosting means operating a multi-service P2P backend — disproportionate operational cost, heaviest footprint surveyed.

#### AppFlowy — `github.com/AppFlowy-IO/AppFlowy`

- Open-source **Flutter/Rust** "AI collaborative workspace" (Notion-style) storing live data in **RocksDB** (via `RocksdbDiskPlugin`, local cache/plugin store) plus **SQLite** (Diesel ORM, `flowy-sqlite` crate). Markdown/Notion import + markdown export are **conversion features only**. **Disqualified.**
- **Documented data-loss risk tied to that design:** GitHub issue **#8112**, *"Full data loss in case of migration problems due to data storage in RocksDB"* — direct evidence markdown is not the live format and the proprietary store is migration-fragile. Users have filed requests for markdown-as-primary-storage precisely because the RocksDB approach is opaque.
- **No first-party MCP** found (repo surfaces only GitHub's generic "MCP Registry" nav link).
- **Backlink graph and content search were not documented** in the fetched material — could not confirm either is native.
- Team support via a **separate AppFlowy Cloud self-hosting stack** (a "Zero-to-Production" guide), distinct from the local Flutter app.
- License **AGPLv3** · latest **v0.12.5 (2026-06-23)** · 139 releases · 7,210 commits · Flutter/Dart 73.8% / Rust 24.1%.
- **Verdict: avoid.** Fails markdown-as-truth, documented data-loss history, no evidence of native MCP/backlink/search to offset it.

#### AFFiNE — `github.com/toeverything/AFFiNE`

- Notion/Miro-style "next-gen knowledge base" (docs + whiteboard) on a **CRDT local-first engine (BlockSuite)**, with an official Docker/Compose server backed by **Postgres + Redis**. Content lives in the CRDT engine's own format, persisted in Postgres — **not markdown files. Disqualified.**
- Two official self-host paths:
  1. **Docker Compose (recommended)** — AFFiNE server + Postgres + Redis + migration jobs: `wget -O docker-compose.yml https://github.com/toeverything/affine/releases/latest/download/docker-compose.yml`.
  2. **Single container** — `docker run -it --name affine -d -v YOUR_PATH:/app/data -p 3000:3000 ghcr.io/toeverything/affine-self-hosted:latest`.
- **No MCP surface found at all** in this pass — no first-party or notable community MCP integration turned up (unlike Outline/Trilium/SilverBullet/Basic Memory, which all have at least a community bridge).
- **Backlink graph and content search unconfirmed** — AFFiNE markets docs+whiteboard collaboration rather than a wiki-graph feature set; treat as unverified/likely-absent.
- Companion self-host repo: `github.com/toeverything/docker`. Docs: `docs.affine.pro/self-host-affine/install/docker-compose-recommend`. Default port `http://localhost:3000` (compose) or `:3010` depending on guide. Backend deps: PostgreSQL, Redis, migration jobs, persistent volume.
- **License not independently confirmed this pass** — the direct repo fetch **404'd**; AFFiNE is known in the ecosystem to use **AGPLv3** for its core, but re-check. Needs a follow-up primary-source fetch (open question (3)).
- **Verdict: avoid.** Fails markdown-as-truth and, in this pass, no MCP surface was found — strictly weaker than Outline/Basic Memory/SilverBullet/Trilium even before the storage disqualification.

---

### Cross-cutting notes

The BUY side splits cleanly into three tiers against the markdown-as-truth test:

- **Pass (files stay canonical):** **Basic Memory** (MCP-native, files + SQLite-index-as-layer, but AGPL-3.0 and team auth is a paid hosted tier) and **SilverBullet** in normal mode (MIT, headless Docker server over a folder of `.md`, native SLIQ query for frontmatter/metadata, but MCP is a third-party sidecar and team auth is coarse).
- **Split/transitional:** **Logseq** — its mature, stable file-graph mode is markdown-native with no first-party MCP, while the actively-developed DB version that adds team RTC sync explicitly drops files for SQLite (opposite direction) and is self-flagged data-loss-risky in beta.
- **Disqualified (own their store):** TriliumNext (SQLite), Anytype (CRDT + P2P any-sync), Outline (Postgres — but the most mature *native* MCP + team SSO of anything surveyed, worth studying), AppFlowy (RocksDB/SQLite, with an open data-loss bug), AFFiNE (CRDT + Postgres, no MCP evidence found).

**The key structural pattern:** every disqualified tool treats markdown as an import/export convenience at the edges, never the live representation. This is **structural, not a maturity gap**, and matches the "own its own store = disqualified as canonical" rule verbatim. The two passing tools (Basic Memory, SilverBullet) both compensate by building their query layer (index / SLIQ) as a **rebuildable cache over the files** rather than replacing them — the exact shape the mandate calls for.

**The gap:** none of the 8 tools gives a genuinely native, first-party **MCP + real team auth + markdown-as-truth in one process simultaneously.** Basic Memory is closest, but its team auth is a paid SaaS gate; SilverBullet's MCP is third-party. This is the strongest argument that the **compose side** (obsidiantools + qmd, from the prior single-user report) may still need re-examination for a team/cloud deployment rather than assuming Basic Memory alone closes it — e.g., checking whether Basic Memory's self-hosted (non-Teams) build can be fronted with a standard reverse-proxy + SSO (Authelia / oauth2-proxy) to get team auth without the paid tier.

### Open questions carried forward

1. **Basic Memory team auth + write safety:** can the AGPL-3.0 self-hosted build be given team auth via a standard reverse-proxy SSO (oauth2-proxy / Authelia) instead of the paid WorkOS-gated Teams tier — and does concurrent multi-agent **write** access to the same markdown files risk corruption / merge conflicts?
2. **SilverBullet bridge maturity + SLIQ coverage:** how mature/maintained is `Ahmad-A0/silverbullet-mcp`, and does SLIQ expose enough of frontmatter + **dangling-link detection** to match `wiki-lint`'s needs, or would it still need obsidiantools-equivalent tooling alongside?
3. **AFFiNE follow-up fetch:** the direct GitHub repo fetch 404'd (reconstructed from search only) — confirm license and re-check for any MCP/backlink/search feature this pass may have missed.
4. **Outline as presentation layer:** given BSL 1.1 + Postgres disqualify it as canonical, is it worth adopting purely as a **read-only team-UI layer** fed by one-way markdown→Outline sync (mirroring the Perlite role from the prior single-user report)? → belongs in a follow-up presentation-layer cluster.

---

### Recommendation for this cluster

For a **cloud-hosted, team-shared, markdown-as-truth MCP wiki**, rank the all-in-one options:

1. **Basic Memory — the leading BUY candidate, adopt-and-augment.** It is the *only* tool here that simultaneously keeps markdown canonical, treats its index as a disposable layer, and exposes native first-party MCP delivering all three query types (frontmatter, backlink graph, hybrid FTS+vector search) from one process. The blocker is team auth: solve it by fronting the self-hosted OSS build with a reverse proxy + SSO (resolve open question (1) first — both the auth pattern and concurrent-write safety) rather than paying for the WorkOS-gated Teams SaaS. Budget an AGPL-3.0 license review if it will be bundled into anything distributed.
2. **SilverBullet — evaluate as a complementary layer / idea source, not the store's brain.** Its headless Docker-over-`.md` architecture and native SLIQ query language are exactly the right shape and worth mimicking, but the third-party MCP sidecar and non-semantic search mean it can't fully replace Basic Memory or a qmd-style content layer on its own. Best case: a read/edit web UI + SLIQ metadata surface *alongside* the primary MCP server.
3. **Logseq (file mode) — distant optional UI/graph layer only.** No MCP, no headless query API, no team sync in the mode that respects the mandate; only interesting as a human graph-view over the same folder. Avoid the DB version.
4. **Outline — reject as the store, but keep for two things:** (a) study its native MCP + SSO design as the reference for what a team-grade MCP server looks like, and (b) consider it for a *separate presentation-layer cluster* as a read-only UI fed by one-way sync. BSL 1.1 caveats apply.
5. **TriliumNext, Anytype, AppFlowy, AFFiNE — avoid.** All fail markdown-as-truth structurally; AppFlowy additionally has a documented data-loss bug and AFFiNE showed no MCP surface at all. None is worth adopting for this mandate.

**Bottom line:** this cluster does not hand us a turnkey answer, but it does hand us a strong lead — **Basic Memory + bolt-on SSO** — plus a clear signal that the composed approach from the prior report stays on the table until Basic Memory's self-hosted team story and write-concurrency behavior are proven out.
