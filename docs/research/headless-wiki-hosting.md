# Hosting the Wiki on a Server: Headless Metadata / Backlink / Content Search

**Question.** The wiki is a folder of atomic markdown pages (YAML frontmatter, `[[wikilinks]]`, a
closed page-type taxonomy, an `inbox/` lane), currently reached through the Obsidian desktop app
(Obsidian CLI + the local-rest-api plugin's MCP). The goal is to **drop the desktop dependency and
host the wiki on a Linux server** (Windows 11 + WSL2), while still being able to search frontmatter
tags/properties, walk the backlink/link graph, and search content — headless.

---

## Recommendations at a glance

- **There is no single headless drop-in for Obsidian. You compose a two-part stack**: one tool that
  computes the **link graph** (backlinks, orphans, dead-ends, dangling `[[links]]`, frontmatter) and
  one that does **ranked/semantic content search**. Obsidian bundled these; a server split does not.
- **wiki-lint's graph checks → [obsidiantools](https://github.com/mfarragher/obsidiantools)** (Python
  library, BSD-3). It is the only surveyed tool that gives backlinks, orphans, dead-ends, **and
  native dangling-link detection** (`nonexistent_notes`) in one in-process call over an unmodified
  vault folder — no server, no daemon, no Obsidian. This is the strongest single fit for the lint half.
- **wiki-query's content + ranked retrieval → [qmd](https://github.com/tobi/qmd)** (MIT). Point it at
  the folder, get BM25 + vector + LLM-rerank over an MCP server (`qmd mcp --http --daemon`), no ingest
  step. It is metadata-blind and graph-blind, so it covers only the content half — which is exactly
  what wiki-query needs.
- **All-in-one alternative → [Basic Memory](https://github.com/basicmachines-co/basic-memory)** (MCP
  server, AGPL-3.0): frontmatter + a real `[[link]]` knowledge graph + hybrid BM25/vector search in one
  headless process. The tradeoff is it owns its own SQLite index and its writes nudge notes toward its
  own schema — good as a passive-read layer, less so if it also writes.
- **Rule these out for the server goal** (they need the Obsidian app *running*): the local-rest-api
  plugin and every MCP server that proxies it (`MarkusPfundstein/mcp-obsidian`,
  `cyanheads/obsidian-mcp-server`). Convenient today, structurally disqualified for headless.

---

## 1. The core tension: Obsidian bundled three capabilities; a server splits them

The desktop app answers three different kinds of question over the same vault:

1. **Metadata query** — "which pages have `type: practice` / tag `#x`?" (frontmatter + tags)
2. **Graph query** — backlinks, orphans (no inlinks), dead-ends (no outlinks), unresolved `[[links]]`
3. **Content query** — ranked / semantic retrieval over prose

**No surveyed headless tool does all three.** The tools cluster by which capability they were built
for, and the clusters barely overlap:

- **Search engines** (SQLite FTS5, Meilisearch, Typesense, qmd, …) do content — and metadata *only if
  you pre-parse frontmatter into fields yourself*. **None compute a link graph.**
- **Graph/parsing tools** (obsidiantools, markdown-oxide, MarkdownDB) do backlinks + frontmatter — but
  have **no ranked/semantic content search**.
- **Static publishers** (Quartz, Perlite, MkDocs) render a read-only *site*, not a queryable service.

So "host it on a server" concretely means: **run a graph/lint tool and a search tool side by side over
the same markdown folder.** The rest of this report makes that composition specific.

---

## 2. Capability matrix — headless candidates only

Only tools that genuinely run without the Obsidian app are listed. Marks are honest about gaps.

| Tool | Headless | Metadata / tag query | Backlink graph | Dangling-link detect | Content search (kind) | API / MCP | Points at vault unchanged |
|---|---|---|---|---|---|---|---|
| [obsidiantools](https://github.com/mfarragher/obsidiantools) (Py) | ✅ lib | ✅ `front_matter_index` | ✅ backlinks + orphans + dead-ends (DiGraph) | ✅ **native** (`nonexistent_notes`) | ❌ (plain-text extract only) | ❌ library only | ✅ |
| [qmd](https://github.com/tobi/qmd) (TS) | ✅ daemon | ❌ | ❌ | ❌ | ✅ **BM25 + vector + rerank** | ✅ MCP + HTTP | ✅ (content only) |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory) (Py) | ✅ server | ✅ frontmatter + schema tools | ✅ own knowledge graph | ~ (traversal, not a lint report) | ✅ hybrid FTS + vector | ✅ MCP | ~ (owns its index/schema) |
| [markdown-oxide](https://github.com/Feel-ix-343/markdown-oxide) (Rust) | ✅ LSP daemon | ~ tag refs, no property query | ✅ backlinks/refs (files+headings+blocks) | ✅ unresolved-ref aware | ❌ | ⚠️ **LSP only** (needs a bridge) | ✅ |
| [MarkdownDB / mddb](https://markdowndb.com) (JS) | ✅ CLI+lib | ✅ frontmatter → SQL columns | ~ forward+back links (v0.1.0) | ❌ not documented | ~ SQL over fields | ✅ CLI + Node API | ~ generic md, wikilinks unverified |
| [Piotr1215/mcp-obsidian](https://github.com/Piotr1215/mcp-obsidian) (Py) | ✅ MCP | ✅ frontmatter + inline tags | ❌ | ❌ | ✅ boolean/regex keyword | ✅ MCP | ✅ |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | ✅ (embed) | ✅ *if you build columns* | ❌ (build edge table yourself) | ❌ (custom) | ✅ BM25 | ❌ (wrap it) | ~ content yes, frontmatter needs ingest |
| [Meilisearch](https://github.com/meilisearch/meilisearch) | ✅ daemon | ✅ facets *after ingest* | ❌ | ❌ | ✅ hybrid FT + vector | ✅ REST + **official MCP** | ❌ needs JSON ingest step |
| [Typesense](https://github.com/typesense/typesense) | ✅ daemon | ✅ facets *after ingest* | ❌ | ❌ | ✅ tunable + vector | ✅ REST (no 1st-party MCP) | ❌ needs JSON ingest step |
| [Perlite](https://github.com/secure-77/Perlite) (PHP) | ✅ live web app | ~ tags in `metadata.json` | ✅ graph + backlinks (server-side) | ❌ | ✅ built-in (human UI) | ~ `metadata.json` artifact only | ✅ **live**, zero conversion |
| [Quartz](https://github.com/jackyzha0/quartz) (TS SSG) | ✅ build CLI | ~ tag listings | ✅ at build → `linkIndex.json` | ~ community `wikilint` on top | ✅ client-side FlexSearch | ~ JSON artifacts, no live API | ✅ (rebuild per edit) |

Legend: ✅ yes · ~ partial/conditional · ⚠️ caveat · ❌ no.

---

## 3. What to rule out (needs the Obsidian app running)

These appear in "Obsidian + server" searches but **require the desktop Electron process live** — they
reintroduce exactly the dependency being removed. Named so they don't mislead:

- **[coddingtonbear/obsidian-local-rest-api](https://github.com/coddingtonbear/obsidian-local-rest-api)**
  — the current transport. It is an Obsidian *plugin*; its REST API and built-in MCP server exist only
  inside the running app. No standalone/headless mode by construction.
- **[MarkusPfundstein/mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian)** and
  **[cyanheads/obsidian-mcp-server](https://github.com/cyanheads/obsidian-mcp-server)** — MCP servers
  that *proxy* the plugin above. Docker only containerizes the proxy, not Obsidian. Both are gated on a
  live desktop app.
- **[obsidian-mkdocs-publisher](https://mkdocs-publisher.github.io/)** — the export step is an Obsidian
  desktop plugin; the app must open at least once per publish.
- **Obsidian Publish** — closed hosted SaaS, not self-hostable at all.
- **Running full Obsidian under Xvfb** — technically headless, but it is still the Electron app + plugin
  API, just without a visible window. The ecosystem now treats this as unnecessary complexity. It buys
  nothing over a real filesystem tool.

**Adjacent but not a query surface:** the official
[obsidian-headless](https://github.com/obsidianmd/obsidian-headless) CLI (~2026) is a **sync/publish
transport only** — it keeps the vault folder up to date on the server but exposes no backlink /
frontmatter / graph API. Useful for *getting the files onto the box*, not for querying them. Treat it
as "how the markdown arrives," orthogonal to the search stack.

---

## 4. Recommended concrete stack for this wiki

Map each wiki operation to a named tool. The stack is deliberately small: one graph tool, one search
tool, optional human UI.

### wiki-lint (graph checks: backlinks, orphans, dead-ends, dangling links, frontmatter)

**→ [obsidiantools](https://github.com/mfarragher/obsidiantools)** (Python, BSD-3-Clause).

`Vault(path).connect().gather()` yields everything wiki-lint needs from a single process over the
unmodified vault folder:

- `backlinks_index` / `get_backlinks(note)` — backlinks
- `isolated_notes` — orphans (no in/out links)
- NetworkX `DiGraph` → out-degree == 0 — dead-ends
- `nonexistent_notes` — **dangling/unresolved `[[links]]` natively** (also
  `nonexistent_media_files`, `nonexistent_canvas_files`)
- `front_matter_index` / `get_front_matter(note)` — frontmatter + tags, queryable in Python

This is the single most complete lint fit found: no server to run, pure-library, and it is the *only*
tool here with out-of-the-box dangling-link detection (see §5). A wiki-lint skill imports it, runs
`gather()`, and reads off every metric — no persistent service to babysit.

Secondary option if the tooling must live in **Node** instead of Python:
[MarkdownDB / mddb](https://markdowndb.com) indexes the folder to queryable SQLite with frontmatter and
forward/back links, but **dangling-link detection is undocumented** and Obsidian `[[wikilink]]`/alias
handling is unverified — check its schema before relying on it.

### wiki-query (content + ranked/semantic retrieval)

**→ [qmd](https://github.com/tobi/qmd)** (MIT).

Closest to "point at the folder and go": no ingest-to-JSON step, walks markdown directly, and runs a
persistent headless daemon (`qmd mcp --http --daemon`, `/mcp` + `/health` endpoints) that an agent
queries over MCP. Retrieval is the strongest surveyed: BM25 + vector fused by Reciprocal Rank Fusion,
then an LLM rerank pass with query expansion — precisely wiki-query's ranked/semantic requirement.

Cost: the local GGUF models total ~2 GB resident in daemon mode — heavier than a plain index. If that
footprint is unwelcome, **[SQLite FTS5](https://www.sqlite.org/fts5.html)** (public domain, zero extra
service, BM25, single `.db` file) is the lean fallback, at the price of ~100–200 lines of ingest/query
glue you own. **[Meilisearch](https://github.com/meilisearch/meilisearch)** (MIT community edition) is
the turnkey-daemon middle ground and ships an **official MCP bridge**, but requires a small indexer that
parses each note's frontmatter+body into a JSON document on change.

Note that qmd is **metadata-blind and graph-blind** — it ignores frontmatter and `[[links]]` entirely.
That is fine here: obsidiantools owns metadata + graph, qmd owns content. The split is clean.

### Human-browsable server UI (optional)

**→ [Perlite](https://github.com/secure-77/Perlite)** (PHP, MIT).

If a person also wants to *read* the vault in a browser without Obsidian, Perlite is the best fit: a
self-hosted PHP app (Docker image) that serves the raw vault folder live — markdown, graph view,
backlinks, tags, search — with **zero conversion and no build step**, reflecting edits immediately. It
is an Obsidian-Publish alternative built for exactly this. It also emits a `metadata.json` (notes,
tags, links) a script could poll, though its query surface is thinner than a real API.

Prefer Perlite over **[Quartz](https://github.com/jackyzha0/quartz)** (MIT) for a *live* view: Quartz is
a rebuild-the-site generator (`quartz build` per edit), though its `contentIndex.json` /
`linkIndex.json` artifacts are the cleanest parseable link-graph JSON in the static-publisher family if
a build-time artifact is acceptable. Both are read-only human UIs, not the agent's query path.

### Stack summary

| Operation | Tool | Role | License |
|---|---|---|---|
| wiki-lint (graph + frontmatter) | **obsidiantools** | in-process backlinks/orphans/dead-ends/dangling/frontmatter | BSD-3 |
| wiki-query (content) | **qmd** | headless MCP daemon, BM25+vector+rerank | MIT |
| wiki-query lean fallback | SQLite FTS5 / Meilisearch | BM25 (+ vector); you own ingest | Public domain / MIT |
| Human browse (optional) | **Perlite** | live server-side Obsidian-style UI | MIT |
| All-in-one alternative | **Basic Memory** | frontmatter + graph + hybrid search, one MCP server | AGPL-3.0 |

**If you prefer one process over two:** Basic Memory is the only surveyed tool covering all three needs
headlessly. Weigh AGPL-3.0 and the fact that it maintains its own SQLite index and its writes follow its
own semantic schema — ideal as a passive-read layer over the vault, more invasive if it also authors
notes.

---

## 5. The dangling-link gap — say it plainly

Dangling-link detection (a `[[link]]` whose target file does not exist) is the capability that most
"headless Obsidian" tools quietly lack, because it requires **parsing every `[[...]]` out of content and
diffing against the set of resolved page names** — a graph operation, not a search operation.

- **Native, no custom code:** **obsidiantools** (`nonexistent_notes`). This alone is a strong reason to
  put it at the center of wiki-lint.
- **Aware but not a batch report:** **markdown-oxide** knows unresolved refs (offers completions / a
  "create the missing file" code action) but exposes them via LSP interactively, not as a scriptable
  one-shot lint you can cron.
- **Needs a small custom script:** **SQLite FTS5, Meilisearch, Typesense, qmd, Piotr1215/mcp-obsidian,
  MarkdownDB** — none detect dangling links. You would parse `[[...]]` (e.g. with a regex or
  `remark-wiki-link`'s `exists` flag against a permalink set) and diff. This is exactly the residual
  "only dangling-link lint needs content-parsing" note already captured in memory: every *other* lint
  metric falls out of a resolved link/backlink index for free, but dangling detection specifically must
  read content.

Practical consequence: choosing obsidiantools for the lint layer **eliminates** the one piece that
otherwise forces custom parsing. If the stack instead standardizes on an MCP search tool (qmd / Basic
Memory) for everything, budget a ~50-line dangling-link script alongside it.

---

## 6. WSL2 / Linux-server and licensing constraints

- **Platform.** Every recommended tool runs natively on Linux/WSL2 with no GUI: obsidiantools
  (`pip install`), qmd (Node daemon), Basic Memory (Python server), Perlite (PHP/Docker), SQLite (in
  every distro). None need X11, Electron, or a display — the whole point of the migration. Keep the
  vault on the **Linux/ext4 side**, not an NTFS mount, to avoid the WSL↔NTFS sync gotchas already
  documented in the wiki (the same discipline as the Unison reference).
- **qmd resource footprint.** ~2 GB of GGUF models resident in daemon mode. Fine on a real server /
  workstation; on a small VPS prefer the SQLite FTS5 or Meilisearch fallback.
- **Licensing to weigh for self-hosting:**
  - Permissive, no obligations: obsidiantools (BSD-3), qmd (MIT), Perlite (MIT), Quartz (MIT),
    Meilisearch community edition (MIT), SQLite (public domain).
  - **Copyleft — check before adopting:** **Basic Memory is AGPL-3.0** (network-use share-alike;
    matters if the server is ever exposed as a service to others). Typesense server is GPL-3.0.
    Meilisearch's *Enterprise* edition is BSL-1.1 (the community edition you'd use is MIT).
  - **Not FOSS / disqualified anyway:** Obsidian Publish (proprietary SaaS); the official
    obsidian-headless is Obsidian-terms tooling, sync-only.

---

## Bottom line

Host the vault as plain markdown on the Linux box (sync it there however you like, e.g. the official
obsidian-headless client or Unison), then run **two headless tools over that folder**:
**obsidiantools** for the link graph + frontmatter + dangling-link lint, and **qmd** for ranked content
search — with **Perlite** if a human also wants to browse it in a browser. If a single process is
strongly preferred over composing two, **Basic Memory** is the only all-in-one that clears the
headless bar, subject to its AGPL license and self-owned index. In every case, retire the local-rest-api
plugin and its proxy MCP servers — they cannot run without the desktop app this migration is designed to
remove.
