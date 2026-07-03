## 14. Our MCP Server Tool & Resource Design

This cluster decides the **wire contract and tool/resource surface** for the wiki MCP server we
would build to run headless, cloud-hosted, and team-shared — independent of *which* graph/search
backend fills it in (that is deferred to the compute-layer and hosting-platform clusters). It fixes
the MCP-protocol primitives each of our four operations (capture / query / ingest / lint) maps onto,
the exact schemas, error channels, pagination, progress, and human-in-the-loop gates, and the
concrete precedent servers whose tool taxonomies we imitate. The hard constraint holds throughout:
**plain markdown files stay canonical**; the MCP server and any index behind it are a disposable,
rebuildable layer — a precedent server is disqualified as our *runtime* the moment it makes its own
store load-bearing, but its *tool-naming pattern* is still fair game to copy.

**Takeaways:**
- **Pin one spec revision** in the `initialize` handshake — recommend **2025-11-25** (cyanheads
  targets it; more recent stable pagination/annotation semantics than 2025-06-18, which is verified
  compatible for everything checked here).
- **Tools** = model-controlled actions → all of capture/query/ingest/lint. **Resources** =
  client-picked context objects → expose pages as `wiki:///{path}`. **Prompts** = user-invoked
  slash-commands → skip for the core surface.
- **Annotate every tool** (`readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint`) — the
  conservative defaults otherwise make plain metadata queries look destructive+open-world and force a
  confirmation click, so this is correctness, not polish.
- **cyanheads/obsidian-mcp-server** (Apache 2.0) is the nearest complete blueprint; **Basic Memory**
  (AGPL-3.0) is the richest taxonomy to imitate but *not* vendor from; the thin REST proxies are
  floor-level references only.
- Split ingest **propose / apply** with a **precondition-hash** argument; gate alias-merge and
  destructive lint fixes behind **elicitation** with a deterministic non-eliciting fallback.

---

### 14.1 The MCP primitives — which one each operation maps onto

The single deciding rule, confirmed across all three primitive spec pages, is **who controls
invocation**:

| Primitive | Controlled by | Spec (2025-06-18) | Our use |
|---|---|---|---|
| **Tools** | Model (agent decides to invoke mid-reasoning) | [/server/tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) | **All of capture / query / ingest / lint** — schema-validated, structured, mutating or ranked-retrieval actions |
| **Resources** | Application / client (human or IDE picks context) | [/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources) | Expose every wiki page as `wiki:///{path}`; aggregate `wiki://tags`, health `wiki://status` |
| **Prompts** | User (slash-command menu) | [/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts) | **Skip for core surface**; reserve only for optional canned human conveniences later |

#### Tools primitive — the wire contract to adopt verbatim

Source: <https://modelcontextprotocol.io/specification/2025-06-18/server/tools>. License CC0/Apache
via the MCP working group (Anthropic + community stewardship); no cost.

- Server declares `capabilities.tools.listChanged` at init; `listChanged:true` lets the server push
  `notifications/tools/list_changed` when the tool set changes (e.g. after a schema migration).
- `tools/list` is **paginated** (cursor-based); `tools/call` invokes by `name` + `arguments`
  validated against `inputSchema`.
- Tool definition fields: `name`, optional `title` (human display), `description`, `inputSchema`
  (JSON Schema), optional `outputSchema`, optional `annotations`.
- **Two distinct error channels** — this is the most load-bearing design decision here:
  - JSON-RPC **protocol errors** (unknown tool, bad args → code `-32602`) for malformed requests.
  - **Tool-execution errors** reported *inside a normal result* with `isError:true` + a text
    explanation — this is what capture/ingest must use for **business-logic failures** (duplicate
    alias, precondition-hash mismatch, path outside allowed section) so the model sees actionable
    text and can react. Example:
    `{"content":[{"type":"text","text":"Failed to fetch weather data: API rate limit exceeded"}],"isError":true}`
- Results can mix unstructured `content` blocks (text/image/audio/`resource_link`/embedded resource)
  with a `structuredContent` JSON object. If `outputSchema` is declared, `structuredContent` MUST
  validate against it, and servers SHOULD *also* emit the same JSON serialized as a `text` block for
  backward compat. Example: return both
  `content:[{type:text,text:'{"temperature":22.5,...}'}]` **and**
  `structuredContent:{"temperature":22.5,"conditions":"Partly cloudy","humidity":65}`.
- **`resource_link`** content lets a search tool return lightweight pointers instead of inlining every
  page body — direct analogue for a wiki hit:
  `{"type":"resource_link","uri":"file:///project/src/main.rs","name":"main.rs","description":"...","mimeType":"text/x-rust","annotations":{"audience":["assistant"],"priority":0.9}}`.
  The client/model then does a separate `resources/read` only for the pages it actually wants.
- Tool-list response shape:
  `{"tools":[{"name":...,"title":...,"description":...,"inputSchema":{...},"outputSchema":{...},"annotations":{...}}],"nextCursor":"..."}`.
- **Security obligations** (directly relevant to write tools): servers MUST validate all inputs,
  implement access control, rate-limit invocations, sanitize outputs; clients SHOULD show tool inputs
  before calling and confirm destructive operations.

> **Verdict — adopt verbatim.** Capture/ingest return `isError:true` + message for *expected*
> business failures (not a protocol error). Query/search return `resource_link` content pointing at
> `wiki://` URIs **plus** a `structuredContent` hit-list validated by an `outputSchema` — one call
> serves both a downstream agent (parses JSON) and a human reading the transcript (reads the text).

#### Resources primitive — pages as URI-addressed context

Source: <https://modelcontextprotocol.io/specification/2025-06-18/server/resources>.

- Resources are **application-driven** (client surfaces them: tree view, search, auto-include) vs.
  tools which are model-controlled — this is *the* criterion for choosing resource vs. tool.
- Capability negotiation separates `subscribe` (per-resource change notifications) from `listChanged`
  (whole-list notifications); support neither, either, or both.
- `resources/list` (paginated) returns `{uri,name,title,description,mimeType}`; `resources/read`
  returns a `contents` array (text or base64 `blob`).
- **`resources/templates/list`** exposes RFC-6570 URI Templates — e.g. `wiki:///{path}` standing in
  for *every* page without enumerating them. Template example:
  `{"uriTemplate":"file:///{path}","name":"Project Files","title":"📁 Project Files","mimeType":"application/octet-stream"}`.
- **Subscriptions:** client sends `resources/subscribe {uri}`; server later pushes
  `notifications/resources/updated {uri}`; client re-issues `resources/read`. Natural fit for "watch
  this page while I'm mid-edit."
- Annotations are **fixed** to `audience` (user|assistant), `priority` (0-1), `lastModified`
  (ISO8601) — you cannot jam `type`/`status` frontmatter into them; surface those via the metadata
  query tool instead.
- Standard URI schemes: `https://` only if the client can fetch it itself; `file://` for
  filesystem-like (even virtual — tag directories `inode/directory`); `git://`; custom schemes must
  be RFC-3986-valid — so `wiki://` is legal.
- **Resource-not-found is its own code `-32002`** (distinct from `-32603` internal), with `data.uri`:
  `{"error":{"code":-32002,"message":"Resource not found","data":{"uri":"file:///nonexistent.txt"}}}`.

> **Verdict — adopt.** Expose pages as `wiki:///<relative-path>.md` via a **resource template** (not
> an exhaustive per-page list — the vault grows unboundedly). Declare `subscribe:true`. Use `-32002`
> for "no such page" rather than inventing an error shape.
> **Gotcha:** many clients don't call `resources/subscribe` even when servers advertise it — don't
> make subscription the only invalidation path; keep queries cheap enough to just re-fetch.

#### Prompts primitive — the one to reject for core logic

Source: <https://modelcontextprotocol.io/specification/2025-06-18/server/prompts>.

- Prompts are **user-controlled** — surfaced as discoverable slash-commands, not model-selected.
- A prompt has `name`, optional `title`/`description`, and an `arguments` array of
  `{name, description, required}` — **plain strings, no JSON-Schema validation, no structured return**.
- `prompts/get` returns a `messages` array (role + content) — it literally returns conversation turns
  to seed, not a parseable payload:
  `{"description":"Code review prompt","messages":[{"role":"user","content":{"type":"text","text":"Please review this Python code:\n..."}}]}`.
- Errors: bad name or missing required arg → `-32602`.

> **Verdict — skip for the core surface.** capture/query/ingest/lint are model-invoked,
> schema-validated, structured operations — exactly what tools are for. Prompts have no argument
> validation and no structured return, so they are the wrong primitive for anything the parent
> orchestrator must parse. Reserve them only for optional human conveniences (a canned "summarize
> this week's inbox" starter). Real-world adoption is low: none of Basic Memory / mcp-obsidian /
> obsidian-mcp-server lean on prompts for their core feature set.

---

### 14.2 Cross-cutting protocol utilities

#### Pagination

Source: <https://modelcontextprotocol.io/specification/2025-06-18/server/utilities/pagination>.

- **Cursor-based, not page-numbered.** The cursor is an **opaque string**; clients MUST NOT parse,
  construct, or persist cursors across sessions.
- Page size is **server-determined**; clients MUST NOT assume a fixed size.
- More data exists **iff** `nextCursor` is present; its absence is terminal.
- Only **4 built-in** operations get this shape automatically: `resources/list`,
  `resources/templates/list`, `prompts/list`, `tools/list`. **Our custom tools must roll their own**
  `cursor`/`nextCursor` fields — pagination is a *pattern to imitate*, not inherited.
- Invalid cursor SHOULD → `-32602`; servers SHOULD handle stale cursors gracefully, not crash.
- Paged shape: `{"result":{"resources":[...],"nextCursor":"eyJwYWdlIjogM30="}}` (that example cursor
  is base64 of `{"page": 3}` — servers commonly base64-encode opaque state, but **clients must never
  rely on that encoding**).

> **Verdict — adopt the identical shape** (`cursor` in / `nextCursor` out, opaque) on every
> unbounded custom tool: `wiki_query_metadata`, `wiki_query_backlinks`, `wiki_query_graph_health`,
> `wiki_query_content`, `wiki_list_pages`. Encode the cursor server-side as an opaque
> checkpoint (e.g. base64 of last-sorted-key + query-hash) so paging stays stable if pages are added
> or removed mid-walk. **Gotcha:** the pattern defines no max page size or backpressure — that is our
> policy (cap e.g. `wiki_query_content` at 50 hits/page).

#### Progress notifications

Source: <https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/progress>.

- The requester **opts in** by attaching `_meta.progressToken` (string or int, unique across active
  requests) to the original request: `{"method":"...","params":{"_meta":{"progressToken":"abc123"}}}`.
  No token → no progress channel → plain blocking request/response.
- The receiver MAY send zero or more `notifications/progress`, each carrying the same token, a
  `progress` value, optional `total`, optional human `message`:
  `{"jsonrpc":"2.0","method":"notifications/progress","params":{"progressToken":"abc123","progress":50,"total":100,"message":"Reticulating splines..."}}`.
- **Hard invariant:** `progress` MUST monotonically increase per token even if `total` is unknown (a
  raw counter still shows forward motion). `total` MAY be omitted entirely. Values MAY be float.
- Both sides SHOULD rate-limit; MUST stop sending once the operation completes; a token for a
  completed/unknown request is invalid.

> **Verdict — adopt for `wiki_ingest_apply`** (batch inbox folding, potential re-embed) and any
> vault-wide relint/reindex — emit a `message` per page ("Ingesting inbox/2026-07-03-idea.md →
> concepts/foo.md") so a long run is legible in the agent transcript instead of one multi-minute
> opaque blocking call that may exceed client timeouts. **Gotcha:** requires a duplex transport that
> carries out-of-band notifications concurrently with a pending request (true for stdio and HTTP+SSE;
> a naive request/response-only HTTP proxy would break it — confirm against the chosen host).

#### Elicitation (client feature)

Source: <https://modelcontextprotocol.io/specification/2025-06-18/client/elicitation>. **New in
2025-06-18, spec text flags "design may evolve."**

- Client MUST declare `capabilities.elicitation:{}` at init — it is optional and not universally
  supported, so any tool using it MUST have a non-interactive fallback.
- Server sends `elicitation/create` with a human `message` and a `requestedSchema` **restricted to
  flat objects with primitive properties only** (no nested objects, no arrays of objects) to keep
  client form-generation simple.
- Field types: string (`minLength`/`maxLength`, format restricted to `email|uri|date|date-time`),
  number/integer (`minimum`/`maximum`), boolean (`default`), and **enum** (`enum` + optional
  `enumNames` display labels).
- **3-way response**, not accept/reject: `accept` (content matches schema), `decline` (explicit no),
  `cancel` (dismissed). Handle all three distinctly. Examples:
  `{"result":{"action":"accept","content":{"name":"octocat"}}}` / `{"result":{"action":"decline"}}`
  / `{"result":{"action":"cancel"}}`.
- **Hard security rule:** servers MUST NOT use elicitation to request secrets/credentials.
- Enum disambiguation schema is directly reusable for ingest merge-target picking:
  `{"type":"string","title":"Merge target","enum":["concepts/blast-radius.md","concepts/minimal-surface.md"],"enumNames":["Blast Radius","Minimal Surface Area"]}`.
- **Shipped precedent:** cyanheads/obsidian-mcp-server already uses `ctx.elicit` in production to
  confirm `obsidian_delete_note` before an irreversible delete — implementable today, not theory.

> **Verdict — adopt narrowly** for exactly the two decision points the karpathy-wiki-implementations
> research names as needing human judgment: (1) **ingest alias-merge disambiguation** (fold into
> existing page vs. create new), (2) **any destructive lint action** (deleting an orphan, rewriting a
> dangling-link target). Always pair with a deterministic fallback (return the candidate list as a
> normal tool result and ask the agent to re-call with an explicit argument) for non-eliciting
> clients. **Do not** make elicitation the sole gate for correctness-critical merges — the spec flags
> it as still evolving.

#### Tool annotations (the "risk vocabulary")

Sources: Tools spec page + MCP blog
<https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/>.

| Annotation | Default | Meaning | Our usage |
|---|---|---|---|
| `readOnlyHint` | `false` | Only reads, never modifies | **`true`** on every query + lint-report tool |
| `destructiveHint` | `true` (only if not read-only) | May overwrite/delete vs. purely additive | `true` on overwrite/delete ingest & lint-fix; `false` on append/create |
| `idempotentHint` | `false` (only if not read-only) | Repeated identical calls have no extra effect | `true` on `wiki_capture` keyed by a content-hash idempotency key |
| `openWorldHint` | `true` (conservative default) | Touches an open world of external entities | **`false`** on all wiki tools — closed markdown corpus |

- A tool **cannot** be both read-only and destructive; if `readOnlyHint:true`, omit the other two.
- **Defaults are conservative:** omitting annotations makes hosts treat a tool as destructive AND
  open-world, forcing a manual confirmation click even on a plain metadata query — so annotating is a
  **correctness/usability requirement, not a nicety.**
- Clients MUST treat annotations as **untrusted** unless the server is trusted — they are a UX hint,
  **never** a substitute for the server's own authorization/rate-limiting.

Recommended annotation set per operation (confirmed already used in production by Basic Memory and
cyanheads):

| Tool | Annotations |
|---|---|
| `wiki_query_*` / `wiki_lint_report` | `{readOnlyHint:true, openWorldHint:false}` |
| `wiki_capture` (append-only inbox write) | `{readOnlyHint:false, destructiveHint:false, idempotentHint:true, openWorldHint:false}` |
| `wiki_ingest_apply` (rewrites/moves pages) | `{readOnlyHint:false, destructiveHint:true, idempotentHint:false, openWorldHint:false}` |
| `wiki_lint_apply_fix` (deletes/rewrites) | `{readOnlyHint:false, destructiveHint:true, idempotentHint:false, openWorldHint:false}` |

---

### 14.3 Precedent servers — tool taxonomies to imitate

| Server | Tools/Resources | License | Version / maturity | Store (canonical?) | Transport | Verdict for us |
|---|---|---|---|---|---|---|
| **Basic Memory** (`basicmachines-co/basic-memory`) | Rich: content/discovery/graph/project/schema/cloud families | **AGPL-3.0** | v0.22.1 (2026-06-13), 86 releases | SQLite index over markdown (Postgres optional); index is derived/rebuildable ✅ **but** Entities/Observations/Relations schema is load-bearing to its identity | Its own MCP server (+ hosted cloud variant) | **Imitate taxonomy, do NOT vendor code** (AGPL) or run as our runtime (owns a load-bearing schema layer) |
| **cyanheads/obsidian-mcp-server** | 14 tools + 3 resources; pagination, structured errors, elicitation-gated delete | **Apache 2.0** | v3.2.9; Bun ≥1.3.11 / Node ≥24; MCP SDK ^1.29.0; targets spec **2025-11-25** | Obsidian Local REST API (app-dependent) ❌ as runtime | **STDIO + Streamable HTTP** | **Primary blueprint**; safe to vendor from once its Obsidian backend is swapped for direct-FS |
| **MarkusPfundstein/mcp-obsidian** | 7 tools, flat | not confirmed by fetch | widely cited | Obsidian Local REST API (app-dependent) ❌ | STDIO only | Floor-level reference; copy its `patch_content` anchor idea only |

#### Basic Memory — the richest taxonomy

<https://github.com/basicmachines-co/basic-memory>. Python-first (83.5% Python). The closest existing
all-in-one analogue: markdown knowledge base (Entities / Observations / wikilink Relations) exposed
entirely through MCP tools, backed by a disposable SQLite index for hybrid search + its own
knowledge-graph traversal. **Markdown stays canonical** (SQLite is rebuildable) — satisfies our hard
constraint *as an architecture*, but its Entities/Observations/Relations schema is layered onto the
markdown as a load-bearing part of its identity, not a passive cache, which is why we imitate rather
than adopt.

Tool families (the template for our surface):

- **Content (≈ capture + ingest):** `write_note`, `read_note`, `edit_note`, `move_note`,
  `delete_note`, plus `read_content`/`view_note` (raw vs. rendered). Note it **splits create/replace
  from surgical edit from move** into distinct tools — the pattern to copy for our ingest family
  (propose/apply as separate ops, not one do-everything mutation tool).
- **Discovery (≈ query):** `search`/`search_notes` (hybrid full-text + FastEmbed vector ranking in
  one tool), `recent_activity` (recency-biased — analogue for "what changed in the inbox lately"),
  `list_directory`.
- **Knowledge-graph:** `build_context` walks `memory://` URIs outward along wikilink relations to
  assemble a context bundle — direct analogue to a `wiki_query_backlinks`/related traversal; `canvas`
  emits an Obsidian `.canvas` graph file as a side output.
- **Project-management:** `list_memory_projects`, `create_memory_project`, `get_current_project`,
  `sync_status` — **multiple independent knowledge bases ("projects") addressed by name**. This is
  the concrete precedent for a team-shared server hosting more than one team's wiki behind one
  endpoint.
- **Schema:** `schema_infer`, `schema_validate`, `schema_diff` — treats frontmatter shape as a
  first-class diffable artifact; directly reusable for validating our closed page-type taxonomy
  (concept/practice/reference/source/map) and required frontmatter keys at ingest time.
- **Cloud:** `cloud_info`, `release_notes` — ships a hosted variant (relevant to the hosting cluster).
- All tools support `output_format="json"` and declare the four MCP behavior-hint annotations —
  confirmation that the annotation vocabulary is used in a shipped KB-MCP server, not just spec.

> **Gotcha / hard-constraint flag:** AGPL-3.0 means **vendoring or forking its server code obligates
> us to release our modifications under AGPL**. Borrowing the *naming/shape pattern* carries no such
> obligation. Do not run it as our runtime: it owns a load-bearing SQLite/embedding + Entity schema,
> which conflicts with "disposable layer, license-neutral, markdown-canonical."

#### cyanheads/obsidian-mcp-server — the primary blueprint

<https://github.com/cyanheads/obsidian-mcp-server>. The most MCP-idiomatic server surveyed: **14
tools + 3 resources**, folder-scoped access control, structured errors, pagination, elicitation-gated
deletes. Itself disqualified as our runtime (Obsidian-REST-API-backed → needs the desktop app), but
**nothing in its tool/resource/error design needs the app** — it translates directly onto a
direct-filesystem + graph-index backend.

Concrete facts:

- **Version 3.2.9; License Apache 2.0** (permissive — reusable/vendorable, unlike Basic Memory).
- **Transports:** STDIO and **Streamable HTTP**. Runtime: **Bun ≥1.3.11 or Node.js ≥24**;
  **MCP SDK ^1.29.0**. Pagination targets spec revision **2025-11-25** explicitly (confirms cursor
  semantics stable across 2025-06-18 → 2025-11-25, and that revision-pinning matters).
- **Connection env vars:** `OBSIDIAN_API_KEY` (bearer, required), `OBSIDIAN_BASE_URL` (default
  `http://127.0.0.1:27123`), `OBSIDIAN_VERIFY_SSL` (default false, for self-signed certs).
- **Server transport/auth env vars:** `MCP_TRANSPORT_TYPE` (`stdio`|`http`), `MCP_AUTH_MODE`
  (`none`|`jwt`|`oauth`), `MCP_HTTP_HOST`/`MCP_HTTP_PORT` (default `127.0.0.1:3010`) — **direct
  template for how our own server exposes HTTP + OAuth for team/cloud multi-user access** rather than
  stdio-only.

Read tools (split by output *shape*, not one generic get):

- `obsidian_get_note` — 4 output modes: raw / structured-with-frontmatter-tags-metadata / document
  map / single section.
- `obsidian_list_notes` — recursive listing; **default depth 2, max depth 20, 1000-entry cap**,
  extension/nameRegex filters. (Concrete numbers to benchmark our own listing defaults against.)
- `obsidian_list_tags` — vault-wide tag inventory with usage counts + hierarchical parents.
- `obsidian_search_notes` — three modes: plain substring, JSONLogic query evaluation, BM25-ranked
  (via Omnisearch plugin).

Write tools (split by mutation *semantics*):

- `obsidian_write_note` — create-or-replace-section; **refuses whole-file overwrite by default** (a
  safety default worth copying).
- `obsidian_append_to_note`.
- `obsidian_patch_note` — append/prepend/replace anchored on heading / block-ref / frontmatter field
  (same anchor idea as MarkusPfundstein's `patch_content`, more fully specified).
- `obsidian_replace_in_note` — regex/case/whole-word search-replace over the body.

Dedicated metadata tools (distinct from generic write — exactly what our ingest/lint need to touch
`type`/`tags`/`status`/`related` without rewriting the page body):

- `obsidian_manage_frontmatter` — atomic get/set/delete of individual frontmatter keys.
- `obsidian_manage_tags` — add/remove/list tags in frontmatter, inline, or both.

Gated/opt-in tools:

- `obsidian_delete_note` — **destructive-annotated AND gated behind `ctx.elicit`** confirmation.
  Concrete proof annotation + elicitation *compose* for exactly our destructive lint/ingest case.
- `obsidian_list_commands` / `obsidian_execute_command` — arbitrary command-palette dispatch, both
  locked behind opt-in env var `OBSIDIAN_ENABLE_COMMANDS=true` (precedent for keeping any broad
  escape-hatch tool off by default).

Resources — **exactly 3, not one-per-page:**

- `obsidian://vault/{+path}` — parameterized template for arbitrary note content+frontmatter+tags.
- `obsidian://tags` — vault-wide tag inventory as a *resource*, not just a tool.
- `obsidian://status` — server reachability / plugin version / manifest (health-check resource).

Access control — three folder-scoping env vars, prefix-match + implicit recursion:

- `OBSIDIAN_READ_PATHS`, `OBSIDIAN_WRITE_PATHS` (write implies read), `OBSIDIAN_READ_ONLY=true`
  (global kill switch for all writes + command dispatch). Denials return a typed `path_forbidden`
  error carrying the active scope so the model self-corrects rather than failing blind.

Richer-than-spec-minimum structured outputs:

- Mutation tools return `created:true/false` + `previousSizeInBytes`/`currentSizeInBytes` (lets the
  caller detect an accidental near-total overwrite *after the fact*).
- Search results return `totalCount` (post-access-policy), `nextCursor`, and `truncated:true` when a
  per-file cap (`maxMatchesPerHit`, default 10) is hit.
- **Error shape carries `data.recovery.hint`** on policy violations — "don't just say forbidden, say
  what scope would have worked." A concrete better-than-spec pattern worth copying wholesale.

> **Verdict — adopt as the primary blueprint template.** Mirror: tool-family split
> (read-by-shape / write-by-mutation-semantics / dedicated frontmatter+tag management / gated
> destructive ops / opt-in escape hatch); the 3-resource pattern (one parameterized page template +
> one aggregate metadata resource + one health resource); the folder/path-scoped access-control model
> (generalizable to team-boundary scoping in a multi-team server); and the richer structured outputs
> (size deltas, truncation flags, recovery hints). **Note:** a community fork
> `BoweyLou/obsidian-mcp-server-enhanced` already adds remote/Tailscale-secured access for Claude.ai
> — someone has taken the first step toward this cluster's exact team-shared goal on this codebase.

#### MarkusPfundstein/mcp-obsidian — floor-level reference

<https://github.com/MarkusPfundstein/mcp-obsidian>. The smallest useful set — the lower bound of "the
fewest tools that make a vault agent-usable."

- **7 tools:** `list_files_in_vault`, `list_files_in_dir`, `get_file_contents`, `search`,
  `patch_content` (insert relative to heading / block-ref / frontmatter field), `append_content`
  (append to new-or-existing file), `delete_file`.
- **No graph/backlink tools, no metadata/frontmatter-specific query, no pagination, no annotations,
  no resources or prompts** — pure flat list. Confirms the prior headless-hosting report's finding
  that link-graph and content-search are absent from thin REST-proxy servers.
- STDIO transport only; requires the Obsidian Local REST API plugin already running → inherits the
  exact "needs the desktop app open" disqualification.
- Env vars: `OBSIDIAN_API_KEY` (from plugin), `OBSIDIAN_HOST` (default `127.0.0.1`), `OBSIDIAN_PORT`
  (default `27124`) — via server-config JSON or `.env`.

> **Verdict — reference only.** Copy its `patch_content` anchor-targeting idea (heading / block-ref /
> frontmatter-field as an edit anchor) into our patch-style ingest tool; otherwise disqualified
> (app-dependent, no graph/metadata capability). License not confirmed by the fetch — check the repo
> LICENSE before any code reuse.

---

### 14.4 The concrete blueprint — our proposed surface

Synthesized from all of the above, under a **single pinned spec revision (recommend 2025-11-25)**.

**Proposed tool set** (verb-first naming from Basic Memory + shape-split families from cyanheads):

| Tool | Purpose | Annotations | Pagination | Structured output |
|---|---|---|---|---|
| `wiki_query_metadata` | frontmatter/tag filter | `readOnly:true, openWorld:false` | ✅ `cursor`/`nextCursor` | hit list + `outputSchema` |
| `wiki_query_backlinks` | uri in → linking pages out | `readOnly:true, openWorld:false` | ✅ | backlink list |
| `wiki_query_graph_health` | orphans / dead-ends / dangling-links | `readOnly:true, openWorld:false` | ✅ per category | category counts |
| `wiki_query_content` | BM25 + vector ranked search | `readOnly:true, openWorld:false` | ✅ | `resource_link` content + scored hit list |
| `wiki_capture` | append raw note into `inbox/` | `readOnly:false, destructive:false, idempotent:true, openWorld:false` | — | `created:true/false` |
| `wiki_ingest_propose` | dry-run diff: proposed atomic pages + merge candidates | `readOnly:true, openWorld:false` | — | proposed-page diff |
| `wiki_ingest_apply` | fold inbox → atomic pages | `readOnly:false, destructive:` per-call, `openWorld:false` | — | `created:true/false`, size deltas; **progress** |
| `wiki_lint_report` | orphans/dangling/contradictions/near-dupes | `readOnly:true, openWorld:false` | ✅ | findings list |
| `wiki_lint_apply_fix` | rewrite/delete files | `readOnly:false, destructive:true, openWorld:false` | — | per-fix result; **progress**; **elicitation** for deletes |

Key design decisions threaded through:

- **Ingest split propose / apply** (the karpathy-implementations precondition-hash pattern):
  `wiki_ingest_propose` is `readOnly:true` (returns the proposed atomic pages + merge candidates);
  `wiki_ingest_apply` takes a **precondition-hash argument** so concurrent edits fail loud rather
  than clobbering, reports `created:true/false` per page via `outputSchema` (so `destructiveHint`
  effectively varies per call), and gates ambiguous alias-merge decisions behind
  `elicitation/create` (enum of candidate page paths) with a **non-eliciting fallback** returning the
  candidate list as a normal result.
- **Resources:** `wiki:///{path}` as a **template** (bounded as the vault grows) + `wiki://tags`
  (aggregate) + `wiki://status` (index freshness/health) — mirrors cyanheads' 3-resource pattern
  exactly. Declare `subscribe:true` so a mid-session agent can watch a page it just proposed edits to.
- **Pagination:** every list-shaped tool takes optional `cursor` in / returns optional `nextCursor`
  out, opaque, server-encoded — copy the spec's field names *exactly* even though these are custom
  tools, so client pagination code written for the built-in `*/list` methods pattern-matches ours.
- **Progress:** attach to `wiki_ingest_apply` and `wiki_lint_apply_fix`, keyed on the caller's
  `_meta.progressToken`; `message` names the page being processed.
- **Error surface:** JSON-RPC protocol errors (`-32602` invalid params, `-32002` resource-not-found
  for `wiki:///` reads) only for malformed requests; `isError:true` tool-result errors for expected
  domain failures (duplicate alias, stale precondition hash, path outside allowed section) — always
  including a cyanheads-style `data.recovery.hint` showing what a correct retry looks like.
- **Structured output:** every query/lint tool declares an `outputSchema` and returns matching
  `structuredContent` (hit list / graph-health counts / lint findings) alongside a human-readable
  `text` summary — one call serves both agent and human reviewer.
- **Elicitation:** narrow use — ingest alias-merge disambiguation and destructive lint fixes only,
  always with a deterministic fallback (elicitation is optional per-client and spec-flagged as
  evolving).
- **Multi-team addressing:** Basic Memory's `list_memory_projects`/`create_memory_project` is the
  concrete precedent — carry a `wiki_project` argument threaded through every tool call, or use
  distinct resource-URI prefixes per project, once multi-team hosting is decided (deferred to the
  hosting cluster).

**Governance note:** Basic Memory (AGPL-3.0) — safe to imitate in naming/shape, **not** to vendor
code from without AGPL obligations. cyanheads/obsidian-mcp-server (Apache 2.0) — safe to vendor from
if its access-control or error-shape code proves directly reusable once its Obsidian-REST-API backend
is swapped for a direct-filesystem one.

---

### 14.5 Open questions (deferred to other clusters)

These are **not resolved here** — flagged for the compute-layer / hosting-platform clusters:

- **Which concrete graph/search backend** (obsidiantools, qmd, a custom index, or something new given
  the cloud+team reopening) actually implements `wiki_query_backlinks` / `wiki_query_content` /
  `wiki_query_graph_health` under this surface.
- How **multi-team project-scoping** (Basic Memory's project model) composes with the **folder/path
  access-control** model (cyanheads).
- Which **transport** (stdio vs. Streamable HTTP vs. SSE) the chosen cloud host supports, and whether
  it preserves the **out-of-band progress-notification duplex channel** (a naive request/response-only
  HTTP proxy would break progress).
- Whether **2025-06-18 vs. 2025-11-25** spec-revision differences beyond pagination/annotations (not
  fully diffed here) affect this design.
- Concrete **git-based concurrency/locking strategy** behind `wiki_ingest_apply`'s precondition-hash
  argument for a team-shared (not single-writer) server.

---

### Recommendation for this cluster

Build a **custom, direct-filesystem MCP server** whose tool/resource surface is copied wholesale from
**cyanheads/obsidian-mcp-server** (Apache 2.0 — the primary blueprint, safe to vendor from) with the
**taxonomy vocabulary of Basic Memory** (AGPL-3.0 — imitate naming only, never vendor). Neither is
adopted as the runtime: cyanheads is Obsidian-app-dependent and Basic Memory makes its own
Entities/Observations/Relations schema load-bearing, which conflicts with our
markdown-canonical/disposable-layer constraint. The thin REST proxies (MarkusPfundstein) contribute
only the `patch_content` anchor idea.

Concretely: pin spec revision **2025-11-25** in the `initialize` handshake; expose all four operations
as **tools** (never prompts), pages as a `wiki:///{path}` **resource template** plus `wiki://tags` and
`wiki://status`; annotate every tool with the four hints (treat this as required); paginate every
list-shaped tool with opaque `cursor`/`nextCursor`; split ingest into `propose`/`apply` with a
**precondition-hash** for safe concurrency; report progress on the two batch tools; use the two-tier
error channel with `data.recovery.hint`; and gate exactly two decisions (alias-merge, destructive
lint fix) behind **elicitation** with a deterministic fallback. This surface is backend-agnostic — the
graph/search implementation and the transport/hosting/multi-team-scoping choices are the *next*
clusters' work, and nothing decided here forecloses them. The hard constraint is honored throughout:
markdown files remain canonical, and every index the query tools sit on top of is a rebuildable,
disposable layer.
