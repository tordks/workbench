## 10. Contribution, Discovery & Notification UX

This cluster decides how a **team** contributes to and stays aware of a cloud-hosted, markdown-as-truth
wiki without stepping on each other: the *find-before-write* dedup gate that stops two people (or two
agents) from creating near-identical pages, the *discovery* surface that lets a contributor see existing
near-matches before typing a duplicate into existence, and the *notification/subscription* channel that
tells teammates a page changed. The headline finding is that **none of these three is available off the
shelf as a wiki-native, team-scale, server-side feature** — every concrete mechanism surveyed is either
single-user/desktop-coupled, or a generic pattern with no wiki-specific implementation, or a git-host
feature with a hard granularity gap. This wiki will *compose* these capabilities on top of the compute
split already settled in the prior reports (obsidiantools for graph/frontmatter + a BM25/vector content
tool), not adopt a turnkey product for them.

**Takeaways:**

- **Find-before-write dedup is a DIY composition, not a product.** The right shape is: embed a draft
  page's title+summary, ANN-search the existing vector index, surface top matches, and block/warn above a
  cosine threshold. green-dalii/obsidian-llm-wiki is the closest working exemplar (two-tier
  alias+similarity gate) but is Obsidian-desktop-only. Build the gate *inside the `wiki-ingest` skill*,
  reusing whatever vector index the content-query tool already maintains.
- **Discovery-at-creation-time works best as "search box IS the new-page action"** (Dendron's Lookup
  pattern): never expose a create path that bypasses seeing near-matches.
- **Notifications ride the git host, not the wiki.** GitHub→Slack `/github subscribe` is the concrete
  baseline, but has **no per-file/per-page granularity** — "notify me when `concepts/llm-agents.md`
  changes" is unbuilt and needs a custom CI step diffing changed paths against a subscriber list.
- **Every genuinely headless markdown-wiki server surveyed is single-tenant** (markdown-vault-mcp,
  SilverBullet) — a team endpoint needs a reverse-proxy/OIDC auth gateway *regardless* of the query tool
  chosen underneath.
- **markdown-vault-mcp is the one adopt-and-evaluate candidate** here: a real HTTP-mode MCP server over a
  plain-markdown folder with hybrid search, frontmatter indexing, and OIDC-committer git integration —
  pair it with a separate graph-lint pass for the backlink/orphan/dangling capabilities it lacks.
- **Onyx and Foam are rule-outs** for this wiki (heavy enterprise-search platform; desktop-extension-only
  respectively), each instructive for one transferable idea.

### 10.1 Capability comparison

| Tool / pattern | Category | Headless server? | Markdown = truth? | MCP surface | Multi-user / team | License | Verdict |
|---|---|---|---|---|---|---|---|
| [green-dalii/obsidian-llm-wiki](https://github.com/green-dalii/obsidian-llm-wiki) | Dedup gate (alias + 2-tier semantic merge) | No (in-Obsidian) | Yes | No | None | Apache-2.0 | steal-the-idea |
| [Dendron](https://wiki.dendron.so/notes/qFX0OoWP5U7yD6NWPeEin/) | Discovery UX (`duplicateNoteBehavior` + fuzzy Lookup) | No (VSCode ext) | Yes | No | Multi-*vault*, not multi-user | MIT | steal-the-idea (UX shape) |
| [GitHub→Slack](https://docs.github.com/en/integrations/how-tos/slack/customize-notifications) | Notifications/subscriptions | N/A (SaaS) | N/A (git-hosted) | No | Yes (channel-scoped) | Free/built-in | steal-the-idea, gap flagged |
| [markdown-vault-mcp](https://github.com/pvliesdonk/markdown-vault-mcp) | Shared content+metadata MCP server | **Yes (HTTP/SSE)** | **Yes** | **Yes (32+6 tools)** | Auth at proxy only | MIT | **adopt-and-evaluate** |
| [SilverBullet](https://github.com/silverbulletmd/silverbullet) | Headless markdown wiki server | Yes (Rust binary/Docker) | Yes | No | Single-tenant | MIT | architecture reference only |
| [Onyx](https://github.com/onyx-dot-app/onyx) (ex-Danswer) | Enterprise search / RAG platform | Yes (Docker/K8s) | **No — copies into own index (unconfirmed)** | Yes (surface unconfirmed) | Yes (RBAC in EE) | MIT CE + proprietary EE | avoid |
| [Foam](https://github.com/foambubble/foam) | PKB + graph/backlinks | No (VSCode ext) | Yes | No | Via git host only | MIT | avoid (query layer) |
| [Embedding + cosine-threshold](https://zilliz.com/ai-faq/how-do-i-use-embeddings-for-duplicate-detection) | Near-dup detection pattern | N/A | N/A | N/A | N/A | N/A (pattern) | steal-the-idea, build it |

---

### 10.2 Find-before-write dedup

#### green-dalii/obsidian-llm-wiki — mandatory alias + tiered semantic merge

<https://github.com/green-dalii/obsidian-llm-wiki>

An Obsidian **plugin** (not a server) that runs an LLM-driven wiki-compilation pipeline entirely inside the
desktop app. Its dedup mechanism is the single most complete wiki-native exemplar found, and the piece to
steal — the *mechanism*, not the plugin, which has zero server or team story.

- **Mandatory aliases.** Every generated page must carry at least one alias (translation, abbreviation, or
  variant). Aliases are load-bearing for dedup: pages created before **v1.7.11** lack them and are
  effectively invisible to the dedup pass. A **"Complete Aliases"** batch command backfills
  translations/acronyms/alternate names onto old pages.
- **Two-tier duplicate check before any new page is created:**
  - **Tier 1 (always LLM-verified):** direct / near-direct title matches — catches cross-language
    translations, abbreviations, and high-similarity titles.
  - **Tier 2 (token-budget-bounded):** moderate-similarity candidates surfaced via *shared links* and
    medium textual similarity, verified only as token budget allows.
- **On confirmed duplicate:** performs "smart LLM fusion", merging content while **preserving all aliases
  from both pages**.
- **Curator lock:** pages marked `reviewed: true` are protected — merges route to an **append-only** path
  instead of overwriting.
- **Query loop feeds back too:** conversational answers get concept/entity-extracted and semantic-deduped
  against the vault *before* being saved as new pages.

**Concrete details:** License **Apache-2.0**. **206 stars, 23 forks, 62 releases**, latest **v1.23.1
(2026-07-02)** — actively maintained. **v1.23.0** was the maintainer's "biggest architectural change since
1.0": migrated to Vercel AI-SDK and added a graph-based retrieval engine. **No multi-user/team features of
any kind** — one Obsidian instance, no backend.

**Verdict — steal-the-idea.** Adopt the two-tier alias+similarity gate as a **required step inside
`wiki-ingest`**: query existing aliases/titles/links before writing any new page. This mirrors green-dalii's
mechanism but implemented as a *query-then-decide loop* (surface matches, let agent/human adjudicate) rather
than an automatic LLM merge — which fits this wiki's propose→apply→receipt discipline better. Do **not** adopt
the plugin: it is single-user, in-Obsidian only, no server mode.

#### Embedding + cosine-threshold near-duplicate detection (generic ML pattern)

<https://zilliz.com/ai-faq/how-do-i-use-embeddings-for-duplicate-detection>

The industry-standard recipe underlying *every* "semantic dedup" feature in this survey (green-dalii's Tier 2,
generic RAG-ingest gates). Captured explicitly because **no purpose-built OSS tool implementing it for a
markdown/Obsidian-style wiki's page-creation step exists** — it is assembled, not adopted.

- **Standard pipeline:** normalize text → embed with a sentence-level model → index with an ANN structure →
  top-N nearest-neighbor lookup → cosine-similarity threshold decision.
- **Model choices cited:** OpenAI embeddings API, or local `sentence-transformers` models.
- **ANN index choices cited:** FAISS, hnswlib.
- **Evaluation pattern:** retrieve top-5 or top-10 nearest neighbors per new document, then a human or LLM
  adjudicates *true-duplicate* vs. *related-but-distinct*. Threshold choice is a precision/recall tradeoff;
  research (Sentence-BERT Gherkin-step dedup, the "Multi-reference Cosine" paper) explores hybrid exact-hash
  + fuzzy-string + embedding pipelines along a precision/compute frontier rather than a single threshold.
- **Directly composable with markdown-vault-mcp** (§10.4): that server already computes embeddings for its
  hybrid search index, so a "search this draft title/summary before writing" MCP call against the *same
  index* is the natural bolt-on — no separate dedup service needed.

**Confirmed absence:** search surfaced only generic ML how-tos, research papers, or narrow domain apps
(Gherkin test steps, SEO content cannibalization). No maintained wiki/KB "duplicate-page gate" product.

**Verdict — steal-the-idea, build it yourself.** The `wiki-ingest` mandatory dedup step = embed candidate
page's title+summary → query the existing vector index (markdown-vault-mcp / qmd / obsidiantools-adjacent) for
nearest neighbors → surface top matches to agent/human before write. Cost/latency depends entirely on
embedding backend + ANN index choice; no license implications (it is a pattern).

#### Dendron — `duplicateNoteBehavior` + fuzzy Lookup

<https://wiki.dendron.so/notes/qFX0OoWP5U7yD6NWPeEin/>

A VSCode-based hierarchical markdown note system. Two relevant mechanisms, only one of which transfers.

- **Lookup (the transferable idea):** the fuzzy-matching command (**Ctrl+L / Cmd+L**, backed by **fusejs**)
  is *simultaneously* the navigation search **and** the note-creation command — there is **no separate "new
  page" action that bypasses seeing existing near-matches first**. Tab-complete walks the hierarchy one level
  at a time using the highest-scoring match, reinforcing hierarchical naming over ad hoc duplicate titles.
  Tie-break: most-recently-updated note wins the top rank.
- **`duplicateNoteBehavior` (does *not* transfer):** a workspace-config setting that deterministically
  resolves *same-named* notes across multiple vaults. Only one strategy today — **`useVault`**: give an
  ordered list of vault names; on a same-ID collision, resolve to the first vault in the list containing it.
  Applied automatically on the **"Vault Add"** command, not on every note creation. This is a **naming-collision
  resolver, not a semantic-merge tool** — it solves multi-vault ID collision, not team-scale near-duplicates
  with different titles.

**Concrete details:** MIT-licensed VSCode extension. Config key `duplicateNoteBehavior`, single supported
action value `useVault` with a `vault` array payload. Established, actively documented wiki
(wiki.dendron.so); release cadence not checked.

**Verdict — steal-the-idea (UX shape only).** Route every new-page decision through a **fuzzy-search-first
step** (analogous to Lookup) rather than a bolt-on lint pass after the fact. The `duplicateNoteBehavior`
mechanism itself does not transfer. Same **desktop-app coupling** disqualifier as Obsidian — not a server/API
surface.

---

### 10.3 Notifications & subscriptions

#### GitHub Slack integration — `/github subscribe` / `unsubscribe`

<https://docs.github.com/en/integrations/how-tos/slack/customize-notifications>

The **most concrete, confirmed** "notifications/subscriptions to changes" mechanism for a git-backed markdown
store. Because the wiki is plain files in git, this is the transport a team actually uses to know pages
changed — with one important gap.

- **Subscribe:** `/github subscribe owner/repo [event]`; **unsubscribe:** `/github unsubscribe owner/repo
  [event]`.
- **Independently controllable event categories:** issues, pulls, commits, releases, deployments, reviews,
  workflows, branches, comments, discussions.
- **Commit notifications are branch-filterable:** default-branch-only, a specific branch (`commits:main`), a
  glob (`commits:feature/*`), or all branches (`commits:*`).
- **Issue/PR notifications support label-gating** via `+label:"your label"` syntax, including emoji labels.
- **CONFIRMED GAP — no per-file/per-page granularity.** No file-path or file-glob filter exists anywhere in
  the documented syntax. A subscription is **repo / branch / label-scoped only**, never "notify me when
  `concepts/llm-agents.md` changes". A teammate watching one concept page has **no native tool support**.
- **Formatting gotcha:** Slack messages use GitHub's own **mrkdwn** variant, not CommonMark — bold `*text*`,
  italics `_text_`, links `<url|text>`. Account for this if auto-generating notification text from wiki
  frontmatter.
- **Setup:** GitHub Slack app installed to the workspace + repo connected via `/github subscribe`.

**Concrete details:** Free, built into GitHub; requires a GitHub-hosted repo and a Slack workspace admin to
install the app. Official GitHub product feature, stable.

**Verdict — steal-the-idea, gap flagged.** Use repo-level GitHub→Slack subscriptions as the baseline
"someone changed the wiki" signal, then build a **thin custom CI layer** to recover the missing per-page
granularity: a CI step that diffs changed paths against a per-teammate/per-topic subscriber list (e.g. stored
as frontmatter `watchers:` on each page, or a separate config file) and posts via a repo-owned webhook. **No
existing tool provides per-page subscription** — this is unbuilt and must be composed.

---

### 10.4 Headless markdown-wiki servers (the query/hosting substrate)

#### markdown-vault-mcp (pvliesdonk) — the one adopt-and-evaluate candidate

<https://github.com/pvliesdonk/markdown-vault-mcp>

The **closest surveyed off-the-shelf candidate** for "shared, team-wide MCP server over the plain-markdown
wiki". A generic, headless MCP server over a folder of markdown files, already running as a persistent
service over HTTP/SSE (not stdio-only) — the transport shape a cloud-hosted, multi-teammate MCP endpoint
needs. **Keeps markdown files canonical** (the index is a disposable layer) — satisfies the hard constraint.

- **Three transport modes:** `stdio` (default, single local client), `SSE`, and **`HTTP`**. HTTP mode is
  explicitly designed to sit **behind a reverse proxy with authentication** — built for centralized/shared
  hosting, not one loopback client.
- **Frontmatter-aware indexing:** required-field enforcement + configurable indexed/promoted frontmatter keys
  feed a tag index — covers this wiki's metadata-query requirement (`type`/`tags`/`status`) natively.
- **Hybrid content search:** FTS5 (BM25 + porter stemming) **+ embedding vectors** fused by **Reciprocal
  Rank Fusion (RRF)**. Pluggable embedding backend: **FastEmbed (local), Ollama, or OpenAI**. Results are
  diversity-capped (**max two chunks per document**) and snippet-bounded (**~200 words**).
- **Git integration, three modes:** **managed** (server owns clone+setup), **unmanaged** (commits into an
  existing local repo), **disabled**. Configurable **push delay** batches rapid successive writes into one
  push. **OIDC-claim override of committer identity per request** — the concrete mechanism for "many users,
  one shared git history, correct attribution".
- **Tool surface:** exposes **32 LLM-facing MCP tools** (search / read / write / edit / delete / rename /
  move_folder / git-history / sync / transfer-links / admin) plus **6 app-only tools** for MCP Apps UI
  clients.
- **CONFIRMED GAP — no graph computation.** No backlink / orphan / dead-end / dangling-link analysis at all.
  Pure metadata + content — exactly the split the prior headless-hosting report noted between graph tools and
  search tools.
- **CONFIRMED GAP — no native multi-user permission model.** Access control is **entirely bearer-token/OIDC
  at the HTTP layer**. A team endpoint needs a reverse-proxy/OIDC gateway component regardless.

**Concrete details:** License **MIT**. Bring-your-own reverse-proxy/OIDC and bring-your-own embedding backend
(FastEmbed local / Ollama / OpenAI). Active project (exact star count/age not surfaced); the 32-tool surface
suggests non-trivial development investment.

**Verdict — adopt-and-evaluate.** Run markdown-vault-mcp in **HTTP mode behind an auth proxy** as the shared
**content + metadata** MCP server. Pair it with **obsidiantools** (from the prior report) for the graph half:
run a separate graph-lint pass for backlinks/orphans/dangling-links, since this tool does none of them. Its
existing vector index is also the natural place to bolt on the §10.2 dedup gate.

> **Open question (spike before commit):** whether the OIDC-committer override is sufficient for real
> multi-user git attribution at team scale — i.e. that concurrent writers land as their *own* commits, not
> all as one service-account commit. Not stress-tested against concurrent writers.

#### SilverBullet — architecture reference for "headless Obsidian"

<https://github.com/silverbulletmd/silverbullet>

A self-hosted, browser-based (PWA) markdown wiki server — **Rust backend + CodeMirror 6 frontend** — with
wiki-style `[[links]]`, automatic bidirectional backlinks, a built-in query language (Space Lua / SLIQ), and
Lua scripting over the note space. The clearest example of a markdown-native wiki that is **already a headless
server** (not a desktop-app plugin) with backlinks built in.

- **Storage matches the constraint exactly:** a "Space" is literally a folder of markdown pages — no
  proprietary DB for content.
- **Automatic bidirectional backlinks:** "Linked Mentions" appear at the bottom of every page it is
  referenced from, and links survive page renames.
- **Ships a real server today:** standalone Rust binary or Docker container (Dockerfile in repo) — this is
  what "headless Obsidian" looks like built from scratch.
- **Query/scripting:** Space Lua expressions embed inline (`${lua expression}`), turning pages into small
  dashboards/calculators — heavier than this wiki needs, but demonstrates "live computed views over
  frontmatter" done server-side.
- **CONFIRMED — single-tenant.** Explicitly positioned as a "Personal Knowledge Database". **No multi-user
  auth, concurrent-editor conflict resolution, or team permission model** documented anywhere.
- **No MCP surface** — exposes its own web UI/API, not an agent-facing protocol. Would need a custom MCP
  bridge to serve as this wiki's agent-facing layer.

**Concrete details:** License **MIT**. Distribution: Rust server binary or Docker. Active (covered by an
LWN.net editorial piece); star count not fetched.

**Verdict — evaluate as an architecture reference only, not adopt.** It proves headless markdown-native wiki
servers with real-time backlinks are buildable and shippable, but has **no MCP surface and no team story** —
both would have to be built before it fits the cloud/team requirement.

---

### 10.5 Rule-outs (with one transferable idea each)

#### Onyx (formerly Danswer) — enterprise search platform

<https://github.com/onyx-dot-app/onyx>

An open-source enterprise search / RAG chat platform with 50+ connectors (Slack, GitHub, Confluence, Google
Drive, etc.), hybrid keyword+vector search, and an MCP integration surface; deployable via Docker / Kubernetes
/ Helm. Relevant as the "what would a team already run for cross-source semantic search" baseline — and as a
cautionary example of deployment cost.

- **Licensing:** **MIT Community Edition** (connectors / RAG / search / chat / MCP core); a **proprietary
  Enterprise Edition** layers on RBAC for agents/actions and sharing.
- **Two deployment tiers:** **"Lite"** runs under **1GB memory**; **"Standard"** requires separate
  vector/keyword indexing, background-job containers, ML inference servers, **Redis**, and **MinIO** blob
  storage — materially heavier than any single-purpose tool in this survey.
- **Hybrid search** explicitly combines semantic (vector) + keyword retrieval.
- **GitHub connector exists** (one of 50+), so a git-hosted markdown wiki *could* be ingested — **but** the
  fetch could **not confirm** whether ingestion is **read-through** (files stay canonical) or **copy-and-own**
  (content copied into Onyx's own index as the query surface). If the latter, it **violates the hard
  constraint** by becoming a second "owns its own index" layer.
- **No duplicate-detection / pre-creation-check feature** found — Onyx is a read/query surface over ingested
  sources, not a contribution-authoring tool.

**Concrete details:** MIT (CE) + proprietary EE. One-command install script for quick self-hosted setup; full
Standard-mode production stack needs Kubernetes/Helm/Terraform. 50+ connectors (GitHub, Confluence, Slack,
Google Drive, Asana, Zendesk, MS Teams). MCP listed among "Agents, Web Search, RAG, MCP, Deep Research"
features; exact MCP tool/endpoint names not surfaced. Active, well-known (TechCrunch coverage), formerly
Danswer.

**Verdict — avoid for this wiki.** A heavy, general enterprise-search platform built to unify many disparate
sources, not a lean MCP server over one markdown folder. Only reconsider if the wiki becomes *one of several*
knowledge sources a whole org wants unified search over — and even then it risks becoming a disqualified
"owns its own index" layer.

> **Open question:** confirm Onyx's GitHub connector semantics (read-through vs. copy-and-own) against its
> connector docs before ruling it in as a passive-read discovery layer.

#### Foam — VSCode PKB, ruled out (same disqualifier as Obsidian)

<https://github.com/foambubble/foam>

A VSCode extension turning a folder of markdown + `[[wikilinks]]` into a personal knowledge base with graph
visualization and a backlinks panel, designed to publish to GitHub Pages / Netlify / Vercel / GitLab Pages.
Cited here to **rule it out** and note its one transferable idea.

- **Storage** is plain markdown with wikilinks + atomic-note conventions — matches the canonical-store
  constraint — **but the query layer (graph view, backlinks panel) is entirely inside the VSCode extension
  process**, the same disqualifying pattern this whole research track is escaping.
- **No standalone server or headless mode** documented anywhere — confirmed absence. **No MCP.**
- **Collaboration model** = push the markdown folder to a GitHub repo and let GitHub / static-site publish be
  the sharing mechanism. It **outsources team-sharing to git hosting** rather than solving it itself — the one
  transferable idea.
- Self-describes as **alpha / "Work in Progress"** despite scale, with an explicit no-lock-in promise.

**Concrete details:** License **MIT**. **17.3k stars, 1,576 commits, 769 forks, 115 watchers** — one of the
most popular tools in this whole research track by stars, despite the desktop-app limitation. Publish targets:
GitHub Pages, Netlify, Vercel, GitLab Pages, custom SSGs.

**Verdict — avoid as a hosting/query component** (same desktop-dependency disqualifier as Obsidian's own MCP
transport). But note its scale (17.3k stars) as evidence that **"plain markdown + wikilinks + push to git for
team sharing" is a well-trodden, popular pattern** — reinforcing that **git itself, not a bespoke sync
protocol, is the right multi-user distribution layer** for this wiki's files.

---

### Recommendation for this cluster

For a cloud, team-shared, markdown-as-truth MCP wiki, rank the options as follows:

1. **markdown-vault-mcp (adopt-and-evaluate) — the only turnkey server piece.** Run it in **HTTP mode behind
   an OIDC/reverse-proxy auth gateway** as the shared content+metadata MCP endpoint. It satisfies the hard
   constraint (markdown stays canonical, index is disposable), covers metadata + hybrid content query
   natively, and its OIDC-committer git integration is the concrete multi-user-attribution mechanism. Two
   caveats: it does **no graph analysis** (pair with **obsidiantools** for backlinks/orphans/dangling-links,
   per the prior report) and has **no built-in permission model** (the auth gateway is mandatory, not
   optional). Spike the OIDC-committer override under concurrent writers before committing.

2. **Find-before-write dedup — build it inside `wiki-ingest` (steal-the-idea, no product exists).** Combine
   **green-dalii's two-tier alias+similarity gate** (the mechanism) with the **generic embed→ANN→cosine-
   threshold pattern** (the implementation), reusing markdown-vault-mcp's existing vector index. Implement as
   a **query-then-decide loop** (surface top matches, adjudicate) rather than green-dalii's automatic LLM
   merge — it fits this wiki's propose→apply→receipt discipline. The `wiki-ingest` skill, which already reads
   `_schema.md` first, is the natural forcing function: make a dedup-search a **mandatory step before any new
   page is created**. (Agents get this for free via prompt discipline; humans get it only via a CI gate or PR
   review — so also mirror it as a CI check on new-file PRs.)

3. **Discovery UX — adopt Dendron's Lookup shape (steal-the-idea).** Ensure no create path bypasses seeing
   near-matches: the search step *is* the new-page action.

4. **Notifications — GitHub→Slack baseline + custom per-page CI layer (steal-the-idea, gap flagged).** Use
   `/github subscribe owner/repo` for the coarse "wiki changed" signal; build a thin CI step that diffs
   changed paths against a `watchers:` subscriber list to recover the **missing per-page granularity** — no
   tool provides it.

5. **SilverBullet — architecture reference only.** Consult if a bespoke headless server ever becomes
   necessary; it proves the pattern but ships neither MCP nor a team model.

6. **Onyx, Foam — avoid.** Onyx is too heavy and may violate the canonical-store constraint (connector
   semantics unconfirmed); Foam is desktop-extension-only. Foam's popularity does confirm the load-bearing
   architectural decision underneath everything else here: **git is the multi-user distribution layer for the
   files; the MCP server is a disposable query layer on top.**

**Net:** the cluster does not yield a single product that does contribution + discovery + notification for a
team. It yields one server to adopt (markdown-vault-mcp + obsidiantools + auth gateway) and three mechanisms
to **build into the `wiki-ingest`/`wiki-capture` skills and CI** (dedup gate, search-first discovery, per-page
notification). Everything keeps the markdown files canonical.
