## 13. Human editing surface — how people read and write the wiki without Obsidian

This cluster decides how a human being — not the agent — looks at and (rarely) hand-edits the wiki
once the Obsidian desktop app is gone and the vault lives on a cloud, team-shared host. The hard
constraint governs the whole cluster: **the plain markdown files stay canonical**, so every candidate
is judged on whether it writes straight to repo files (allowed) or owns its own database as the source
of truth (disqualified as the store). The dominant finding is that read and write split cleanly —
**no single surveyed tool does live human browsing *and* git-diffable team writes *and* zero extra
services**, so the answer is a small composed stack, not one product.

**Takeaways:**

- **Baseline write surface (zero infra):** the plain git-PR flow — edit files in `github.dev` or any
  editor, commit to a branch, open a PR. It *is* git, so it is perfectly diffable and reuses the
  repo's existing auth/branch-protection. Every other write option is optional convenience on top.
- **Baseline read surface:** Perlite (already chosen in prior research) — read-only, Obsidian-like
  browse over the vault folder. It writes nothing, so it can never threaten the canonical store.
- **Governing discipline:** agent-only-writes (the Karpathy pattern this repo already follows) can
  shrink the human *write* requirement to near zero — most "writes" are agent-mediated ingests. If the
  team accepts this, the whole CMS evaluation may be moot: only a read UI + a git-PR escape hatch are
  strictly required.
- **If a guided form/preview editor is wanted:** Sveltia CMS is the recommended thin web editor — MIT,
  writes plain files, and (uniquely) needs **no always-on backend** for a small team via
  personal-access-token auth.
- **Disqualified outright:** HedgeDoc — its canonical store is its own database, not the repo files.
- **Flag, don't trust:** TinaCMS calls its DB an "ephemeral cache," but self-hosting runs that cache
  as a real always-on service in the write path; verify the "disposable layer" claim before adopting.

---

### 13.1 Read vs. write, and the "owns storage?" split

Two structural distinctions organize this entire cluster:

1. **Read surface vs. write surface.** Some tools only render (Perlite), some only edit
   (StackEdit, the CMSes), and none do both live-browse and git-write in one package. You compose.
2. **Does the tool own a canonical store?** This is the hard-constraint gate:
   - **Owns zero storage** (writes straight to repo files) → constraint-compatible: git-PR flow,
     Decap, Sveltia, Pages CMS, StackEdit, and TinaCMS *in theory*.
   - **Owns a database as canonical** → disqualified as the store: **HedgeDoc**.
   - **Uneasy middle:** **TinaCMS** — markets its DB as an ephemeral cache with files as source of
     truth, but self-hosting means running that cache as a standing dependency in the write path.

| Tool / pattern | Read (browse) | Write (edit) | Writes plain files? (git-diffable) | Own DB? | Extra always-on service to self-host | License |
|---|---|---|---|---|---|---|
| **Git-PR flow** (github.dev / any editor) | Yes (repo UI) | Yes (in-browser VS Code) | Yes — it *is* git | No | **None** (uses existing git host) | Host tooling (n/a) |
| **Agent-only-writes** (discipline) | — (needs a read UI) | Via agent, not a UI | Yes (agent commits files) | No | None (it's a policy) | n/a |
| **Sveltia CMS** | Yes | Yes (form + raw md) | Yes | No | **None in PAT mode** (OAuth mode needs a tiny Worker) | MIT |
| **Decap CMS** | Yes | Yes (form + md widget) | Yes | No | **OAuth bridge server required** | MIT |
| **Pages CMS** | Yes | Yes (form + WYSIWYG) | Yes (Postgres is app state, not content) | No (content) | Next.js app + PostgreSQL + GitHub App | MIT |
| **TinaCMS** | Yes + **live visual preview** | Yes (GraphQL-backed) | Yes *in principle* (DB = cache) | **Cache DB in write path** | DB + Auth.js + serverless GraphQL API | Apache-2.0 |
| **StackEdit** | Yes (synced files) | Yes (single-file, live preview) | Yes | No | None (static app) — but unmaintained | Apache-2.0 |
| **HedgeDoc** | Yes | Yes + **real-time multi-cursor** | **No — DB is canonical** | **Yes (Postgres/SQLite)** | Node service + Postgres | AGPL-3.0 |
| **Perlite** | **Yes (read-only)** | **No** | Moot (writes nothing) | No | PHP app (read-only) | MIT |

---

### 13.2 The git-PR contribution flow (the zero-infrastructure baseline)

Docs: <https://docs.github.com/en/codespaces/the-githubdev-web-based-editor>

Not a product but a **pattern**: humans edit the markdown files in any editor — a local clone,
GitHub's in-browser `github.dev`, or GitHub's plain web file editor — commit to a branch, and open a
pull request against the wiki repo. **Merge is the publish step.** This is the zero-infrastructure
baseline for a git-diffable team wiki with no desktop app; every other item in this cluster is optional
convenience layered on top of it.

- **Read:** full repo browse and file view in any git host UI, signed-out for public repos.
- **Write:** `github.dev` opens a full VS Code-like editor in-browser — syntax highlighting,
  multi-file edit, in-editor search, commit, branch creation, and PR creation, **zero install**.
- **git-diffable:** by construction — it *is* git; there is no intermediate store to drift from the
  files.
- **Auth:** standard GitHub sign-in; permissions are exactly the repo's existing
  collaborator/branch-protection rules, so **team access control is free**.
- **Self-host:** trivially yes — Gitea, GitLab CE, and Forgejo all ship an equivalent web
  editor + PR (a.k.a. "merge request") flow; no extra service to run for editing itself.

**How to open `github.dev`:**

- Press `.` while viewing a GitHub repo, or press `>` to open in a new tab.
- Or edit the URL: change `github.com/<owner>/<repo>` → `github.dev/<owner>/<repo>`.
- Read-only browsing works signed-out (public repos); write requires GitHub sign-in.
- Syncs your VS Code settings if you're signed in.

**Gotchas:**

- **No terminal, no build/run.** It is edit-only — exactly right for markdown, but the repo's
  pre-commit hooks (`md-dead-link-check`, markdown-style lint) only run **at PR-time in CI**, not
  locally in-browser. Use GitHub Codespaces if you need compute.
- **Browser-storage for unsaved work** — you must commit before closing the tab or the work is lost;
  there is no autosave-to-server.
- Merge conflicts, history, and rollback are **normal git semantics** — no CMS-specific merge model
  to learn.

**Self-hosted equivalents:** GitLab Web IDE; Gitea/Forgejo built-in file editor + PR flow.

**Verdict:** **Adopt as the baseline.** Recommend as the primary human editing surface — zero new
infrastructure, perfectly git-diffable, reuses existing repo auth/branch-protection, no server the team
must operate. Add a thin web CMS only if editors want field-guided forms / live preview instead of raw
markdown + YAML frontmatter. **Constraints:** none beyond an existing git hosting account (GitHub free
tier, or self-hosted Gitea/GitLab); no license concerns. **Maturity:** shipped, stable GitHub feature
since 2021, actively maintained.

---

### 13.3 Agent-only writes (the Karpathy LLM-wiki discipline)

Source: <https://www.askglitch.com/blog/build-a-second-brain>

A **discipline, not a tool**: the human never edits wiki pages directly. All writes go through the
agent's capture/ingest operations; if a page is wrong, the human feeds the agent a *correcting source*
and lets it reconcile, rather than hand-editing the file. Popularized by Andrej Karpathy's 2026 "LLM
Wiki" post/gist. **This is already the design this repo's wiki follows** (capture/query/ingest/lint via
the agent).

- **Core rule:** *"resist editing the wiki yourself… if you start editing pages, you erode the
  contract and the agent won't trust its own work next session."*
- The human's job narrows to two things: **deciding what's worth capturing**, and
  **reviewing/prompting** — not authoring prose.
- The agent owns cross-linking and page hygiene on every ingest, which is why the wiki stays
  maintained at near-zero marginal cost.
- **Consequence for this cluster:** if the discipline holds strictly, the team may **not need a human
  write surface at all** beyond the agent conversation — only a human **read** surface (Perlite)
  becomes a hard requirement once Obsidian desktop is gone.
- **Team-wide version:** anyone who wants to correct something talks to the agent (chat, ticket, or a
  captured note), not a markdown editor — shrinking editing-surface requirements to "agent access" +
  "read UI" rather than "write UI."

**Concrete:** Karpathy's framing went viral (~16M views) with a companion GitHub Gist that passed
5,000+ stars within days (April 2026). The practical mechanism already used here is `/sync`-style
reconciliation — ingest a new source that *contradicts* an existing page rather than hand-patching it.

**Verdict:** **Adopt as policy, not infrastructure** — the cheapest possible editing surface (none
needed), provided the team accepts that corrections flow through the agent. Pair with a read-only UI
(Perlite) for browsing; keep the git-PR escape hatch for the rare hand-fix the agent can't reach (repo
housekeeping, not wiki content). **Constraints:** social/process, not technical — needs team buy-in;
one member who reflexively hand-edits fragments the discipline. **Maturity:** popularized 2026; not
versioned software; already the pattern `wiki-capture`/`wiki-ingest` implement.

---

### 13.4 Sveltia CMS — the recommended thin web editor

Repo: <https://github.com/sveltia/sveltia-cms> · Auth proxy:
<https://github.com/sveltia/sveltia-cms-auth> · Docs:
<https://sveltiacms.app/en/docs/backends/github>

A free, MIT, open-source **Git-based headless CMS** — a from-scratch, actively maintained successor to
Netlify CMS / Decap CMS (addresses 300+ inherited issues). Ships as a **single-page web app served
straight from a CDN**; no build step, no server component of its own. It is the strongest "thin
embeddable web markdown editor + git-backed CMS" candidate here: it can run with **literally zero
backend of its own** for a small team via personal-access-token auth, and stays compatible with Decap's
`config.yml` shape, so config effort transfers if the team ever migrates.

- **Read:** lists/searches all entries instantly via the **GitHub GraphQL API** (one query, avoiding
  the per-file REST calls and rate-limit issues that plague Decap).
- **Write:** form-based (frontmatter fields) + raw markdown editing, rich-text/markdown widgets; saves
  a commit via GraphQL mutation (fast, single round-trip).
- **git-diffable:** yes — writes plain markdown/YAML/JSON to the repo; **the CMS holds no independent
  database.**
- **Auth — two modes:**
  1. **OAuth app + a deployed token-exchange proxy** (their "Sveltia CMS Authenticator," a small
     Cloudflare Workers script, free tier). Needed because GitHub's OAuth flow requires a confidential
     client secret that can't live in a browser SPA.
  2. **Personal access token ("Sign In with Token")** — for a single dev or small team; **no OAuth
     app, no proxy server, no config change at all.** Recommended explicitly *"if you or a small team
     of developers are the only users."*
- GitHub plans **client-side PKCE** support, after which even the OAuth path won't need a backend
  proxy (already true for Sveltia's GitLab backend).
- **Self-host:** the SPA needs only static hosting (or `npx sveltia-cms` / a CDN `<script>` tag); only
  the OAuth path needs the extra Workers script — the PAT path needs nothing extra.
- **Config:** YAML `config.yml` defining collections → folders → field schemas — same shape as Decap,
  so per-folder page-type schemas (`concepts/`, `practices/`, `references/`, `sources/`, `maps/`) map
  directly onto Decap-compatible "collections."

**Version at fetch:** v0.170.0 (2026-07-03), **581 releases** (near-weekly cadence), ~2.5k stars;
markets itself as "maintenance-free" from the user's perspective.

**Verdict:** **Adopt as the recommended thin web editor** if the team wants a field-guided/live-preview
UI beyond raw git-PR editing — best infra-to-capability ratio of the CMS options: PAT mode needs zero
extra services for a small team, MIT-licensed, actively developed, git-diffable by construction (no
database). **Constraints:** MIT, no cost; OAuth (non-PAT) mode currently requires the small Cloudflare
Worker auth proxy — removed once GitHub ships PKCE.

---

### 13.5 Decap CMS (formerly Netlify CMS)

Repo: <https://github.com/decaporg/decap-cms> · Self-host walkthrough:
<https://blog.fullmeter.com/posts/self-hosting-decap-cms/> · Editorial workflow:
<https://decapcms.org/docs/editorial-workflows/>

The **original/most battle-tested** Git-based CMS: a React SPA admin UI (served at `/admin`) that
reads/writes Markdown/YAML/JSON in a git repo per a YAML config, with the **broadest backend support**
of any tool surveyed (GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, plus Git Gateway). A viable but
**heavier** alternative to Sveltia — same config shape, more backends, but you must run your own OAuth
proxy (no PAT shortcut) and development has slowed since the 2023 community handoff.

- **Read/Write:** browses/searches per collections config; form fields + markdown widget editor.
- **git-diffable:** yes — writes directly to repo files, no CMS-owned database.
- **Auth:** requires you to **host your own OAuth handshake server** — no first-party PAT login like
  Sveltia. Needs its own subdomain, TLS cert, and a Node OAuth provider bridging Decap↔GitHub;
  documented as fiddly ("chicken-and-egg" between the GitHub App and the callback server).
- **Editorial Workflow:** set `publish_mode: editorial_workflow` and the GitHub/git-gateway backend
  **opens a pull request per unpublished entry**, adding draft/review/ready staging in the UI on top of
  the PR — the closest of the CMS options to a native "contribution goes through review" model.

**Config to enable PR-based workflow:**

```yaml
publish_mode: editorial_workflow
backend:
  name: github
  repo: <owner>/<repo>
  branch: main
  auth_endpoint: /api/auth
  squash_merges: true
```

**Self-host requirements (community walkthrough):** dedicated auth subdomain (e.g.
`auth.example.com`), Nginx reverse proxy, Let's Encrypt TLS, a Node OAuth bridge process, a GitHub App
with Contents + Pull Requests read/write permission, and a build pipeline that triggers on PR merge
(not just push). Deployment of the admin UI itself is a lightweight CDN `<script>` include or an
npm install for customization. **Git Gateway** backend is a Netlify-hosted proxy — SaaS-only
convenience, not usable if avoiding Netlify.

**2026 state:** "the editorial UI has not kept pace," YAML config "shows its age," post-rebrand pace is
slower than Sveltia/Keystatic — but still proven and zero-cost.

**Verdict:** **Evaluate only if the PR-per-entry Editorial Workflow specifically is wanted** and the
team will run/maintain the OAuth bridge; otherwise prefer Sveltia (config-compatible, actively
developed, no self-run OAuth server in PAT mode). **Constraints:** MIT, free — but the real operational
cost is a small always-on OAuth-bridge service (extra process + subdomain + TLS), exactly the kind of
standing dependency this migration is trying to shed, just moved from Obsidian to a homegrown proxy.
**Maturity:** since 2016 (Netlify CMS, renamed 2023), MIT, community-maintained, slower cadence than
Sveltia.

---

### 13.6 Pages CMS

Repo: <https://github.com/pages-cms/pages-cms> · Hosted: <https://app.pagescms.org>

An open-source (MIT) CMS purpose-built for managing content in a **GitHub repository** via a single
`.pages.config.yml` config file, aimed at static-site/content repos (Jekyll, Hugo, Next.js, Astro,
VuePress, and plain markdown). A **middle-weight** option — simpler config than Decap/Tina (one YAML
file) but a heavier self-host footprint than Sveltia's PAT path.

- **Read:** polished UI to browse markdown/YAML/JSON/media without touching git.
- **Write:** field-driven editing per the `.pages.config.yml` schema (content types, fields,
  editable/media folders), plus a companion **Notion-like WYSIWYG rich-text component**
  (`pages-cms/editor`, built on TipTap/ProseMirror/shadcn) usable standalone.
- **git-diffable:** yes — edits commit straight to the repo; **PostgreSQL holds app/session state, not
  content**, so the content store is still the files.
- **Auth:** requires installing a **GitHub App** (not a plain OAuth app); ships a
  `npm run setup:github-app` helper to automate registration.
- **Self-host:** Next.js (TypeScript) app + **PostgreSQL 16** + Node/npm runtime; deployable to
  Vercel/Netlify or run locally — heavier than Sveltia, **no zero-backend PAT-only path documented**.
- **Hosted SaaS alternative** exists (`app.pagescms.org`) if self-hosting the app+DB is unwanted, at
  the cost of a third party touching the repo via the GitHub App grant.

**Stack detail:** Next.js + TypeScript, drizzle ORM against PostgreSQL 16 (per `drizzle.config.ts`).
Config file `.pages.config.yml` at repo root defines content types/fields and editable files.

**Verdict:** **Evaluate if a Notion-like WYSIWYG feel matters more than raw markdown** and the team is
fine running a small Next.js+Postgres service; otherwise Sveltia is lighter-weight for the same
git-backed thin-editor need. **Constraints:** MIT, free software, but self-hosting cost is a running
Postgres instance plus a Next.js app process — more moving parts than Sveltia or the git-PR flow.
**Maturity:** active (hunvreus/pages-cms), companion editor maintained separately; smaller community
than Decap/Tina, positively reviewed in 2025 (CSS-Tricks, Hacker News).

---

### 13.7 TinaCMS — the heaviest option, and the "disposable layer" caveat

Repo: <https://github.com/tinacms/tinacms> · Self-host docs:
<https://tina.io/docs/self-hosted/overview>, <https://tina.io/docs/self-hosted/manual-setup> ·
License: <https://github.com/tinacms/tinacms/blob/main/LICENSE> (Apache-2.0)

An open-source, git-backed headless CMS with a **live-preview visual editor** for Markdown, MDX, and
JSON, fronted by a GraphQL "Data Layer" that serves the files. The **heaviest-infrastructure option**
here — full self-hosting means running your own database, auth provider, and a Node serverless API.

- **Read:** yes, plus **live visual preview of the rendered page while editing** — its headline
  differentiator over Decap/Sveltia/Pages CMS.
- **Write:** via the GraphQL API backed by markdown/JSON files.
- **git-diffable:** yes *in principle* — Tina states *"the database acts as more of an ephemeral cache;
  your Markdown/JSON files remain the single source of truth."* **But** self-hosting means that cache is
  a real, always-on dependency **in the write path.** This aligns with the project's "disposable layer,
  not source of truth" rule **only if you verify the cache truly stays disposable/rebuildable and never
  becomes load-bearing** — the one item in this cluster where the docs' claim should be tested in
  practice, not taken on faith.
- **Auth:** pluggable; default self-hosted setup uses **Auth.js with a database-backed user
  collection** — another moving part beyond the git host's own auth.
- **Self-host:** requires a Node serverless environment (Vercel/Netlify Functions or equivalent)
  exposing a single GraphQL route (e.g. `/pages/api/tina/[...routes].ts`), a database adapter
  (MongoDB, Postgres, etc. — your choice), and a Git provider module for persistence. Three pluggable
  modules to stand up: **Auth Provider** (default Auth.js), **Database Adapter**, **Git Provider**.
- Some TinaCloud-hosted SaaS features are unavailable when self-hosting (per Tina's FAQ).

**Verdict:** **Avoid for this wiki unless live WYSIWYG preview is specifically wanted** — most
infrastructure-heavy of the surveyed CMSes (own DB + own auth provider + serverless API), working
against the goal of shedding a standing dependent-service architecture (it trades "Obsidian desktop
app" for "database + auth service + serverless function"). **Constraints:** Apache-2.0, no direct cost,
but real operational cost is a DB + an Auth.js auth service + a Node serverless target just to self-host
the write path. **Maturity:** actively developed, widely used in Jamstack/Next.js; "GitHub's #1
headless CMS" per its own marketing — mature but heavyweight.

---

### 13.8 StackEdit — single-file convenience editor

Repo: <https://github.com/benweet/stackedit> · Hosted: <https://stackedit.io/>

A long-running, full-featured **in-browser Markdown editor** (built on PageDown, the Stack Overflow
markdown library) with a split editor/live-preview pane and cloud sync to GitHub, Google Drive, and
Dropbox. A **thin per-file editor**, not a folder-aware CMS — good for one person polishing one page's
prose/math/diagrams with live preview, weak as a team's primary write surface because it has no concept
of the vault as a whole (no frontmatter schema, no collections, no wikilink awareness).

- **Read/Write:** opens files synced from a connected GitHub repo; edits **raw markdown text
  directly** — so YAML frontmatter and `[[wikilinks]]` pass through **untouched as plain text**
  (StackEdit has no special handling for either, and equally **no breakage**). Live preview supports
  KaTeX math, Mermaid diagrams, tables.
- **git-diffable:** yes — syncs plain markdown files to a GitHub repo; no intermediate format.
- **Auth:** OAuth against GitHub/Google/Dropbox/WordPress, via API keys in the self-hosted deployment.
- **Self-host:** yes — **Apache-2.0**, deployable via a provided **Helm chart** to any Kubernetes
  cluster, or plain Node/Nginx/Apache hosting of the static app.
- **No multi-user/collaboration model, no PR workflow, no team access control** beyond whatever the
  connected GitHub OAuth app grants — it edits files, full stop.
- **Sync targets:** GitHub, Google Drive, Dropbox (content); Blogger/WordPress/Zendesk (publish-only).

**Maintenance flag:** last tagged release **v5.14.0 was 2019-07-02** (13 total releases); 23k stars
reflect historical popularity, not current activity. **Treat as feature-frozen.**

**Verdict:** **Avoid as the primary/only surface** (unmaintained since 2019, no team workflow, no
folder/frontmatter model) but fine as an **optional convenience** — a bookmarklet-grade single-file
editor with nice math/diagram preview, layered on top of the git-PR flow rather than instead of it.
**Constraints:** Apache-2.0, free, self-hostable; the real constraint is **6+ years since last
release** — a meaningful maintenance risk for a team-wide tool.

---

### 13.9 HedgeDoc — disqualified (owns its own store)

Repo: <https://github.com/hedgedoc/hedgedoc>

A self-hosted, **real-time collaborative** markdown editor (successor to CodiMD/HackMD-the-OSS-branch)
— Google-Docs-style simultaneous multi-cursor editing of a note in the browser. **Explicitly the wrong
shape for this project's hard constraint.**

- **Read/Write:** yes, with live preview; its standout feature is **true real-time multi-user
  collaborative editing** — the one thing none of the git-PR-based tools offer.
- **git-diffable: NO, by default.** Notes are stored in **HedgeDoc's own database** (Postgres, or
  SQLite for lightweight installs), not as files in git; version history is HedgeDoc's own revision
  log, **not git commits**. A note can be exported as a standalone markdown file, but that is a
  manual/scripted **bridge**, not native git-backed storage — reintroducing a second source of truth.
- **Auth:** LDAP, OAuth2 providers, or username/password — flexible for self-hosting.
- **Self-host:** Docker images (`/docker` in repo), Node service + Postgres (or SQLite).
- **License:** **AGPL-3.0** — network-use share-alike, relevant if exposed as a service to other
  teams/orgs (same caveat flagged for Basic Memory in the prior headless-hosting research).

**Stable line:** 1.11.0 (maintenance-only); `main` = in-progress v2 rewrite, incomplete per the repo's
own README.

**Verdict:** **Avoid as the wiki's write surface — fails the hard git-diffable-canonical-store
constraint outright** (it owns its own DB and revision history, not the repo's files). Could only serve
as a **real-time-collab scratch pad** for drafting a page collaboratively before a human/agent commits
the final text into the actual markdown file — never as where pages live. **Constraints:** AGPL-3.0
copyleft + network-use clause if run as a shared service; **disqualified structurally regardless of
license.**

---

### 13.10 Perlite — the read complement (already recommended)

Repo: <https://github.com/secure-77/Perlite>

A self-hosted **PHP web app** that serves an Obsidian vault folder live in a browser — markdown
rendering, graph view, backlinks, tags, search — with **zero conversion/build step**. Already
recommended in this repo's prior headless-hosting research as the human-browse layer.

- **Read:** yes — live Obsidian-like rendering, graph view, backlinks, tags, search, directly over the
  vault folder.
- **Write:** **no — read-only by design.** This is exactly why it belongs here only as the *complement*
  to a write surface, never a candidate for editing.
- **git-diffable:** trivially yes/moot — it writes nothing, so it cannot threaten the canonical store.
- **Already fully sourced** in `docs/research/headless-wiki-hosting.md` §4 ("Recommended concrete stack
  for this wiki" → "Human-browsable server UI (optional)") — Docker setup, `metadata.json` artifact,
  and **MIT license** are documented there and **not re-derived here** per the "don't redo" mandate.

**Verdict:** **Adopt (already recommended) as the read complement** — combine with the git-PR flow
and/or Sveltia CMS for writes, and/or the agent-only-writes discipline, for a complete
human-editing story with no desktop app. **Maturity:** per prior research, a live, actively used
self-hosted PHP app, MIT-licensed.

---

### 13.11 Cross-cutting notes

- **Read and write never come in one box.** Nothing surveyed does live human-browsing *and*
  git-diffable team writes *and* zero extra services. You compose at least two pieces, mirroring the
  metadata/graph/content split found in the headless-hosting research. The best-fit stack for
  "no desktop app, git-diffable, team-shared": **(1)** git-PR flow as the zero-infra baseline everyone
  already has; **(2)** Sveltia CMS on top for anyone wanting a guided form / live preview without hand
  YAML; **(3)** Perlite as the pure-read browsing surface; **(4)** the agent-only-writes discipline
  governing how much of (1)/(2) actually gets used — under that discipline most "writes" are
  agent-mediated ingests, not a human opening an editor.

- **The "owns storage?" gate is load-bearing.** Zero-storage tools (Decap, Sveltia, Pages CMS,
  TinaCMS-in-theory, StackEdit — all write straight to repo files) satisfy the constraint; a tool that
  owns a database as canonical (HedgeDoc) is disqualified outright regardless of how good its UX is.
  **TinaCMS sits in an uneasy middle** — it calls its DB "ephemeral cache," but self-hosting runs that
  cache as a real always-on dependency in the write path; verify the "disposable layer" claim in
  practice, don't take it on faith.

- **Auth is the recurring hidden cost of every git-backed CMS.** GitHub's OAuth flow needs a
  confidential secret that can't live in a browser SPA, so every SPA-based tool (Decap, Sveltia) needs
  either **(a)** a small OAuth-token-exchange proxy server, or **(b)** a personal-access-token shortcut
  for small/trusted teams. **Sveltia is unique among the surveyed CMSes in offering (b) with no config
  change**, which is why it beats Decap on "# of always-on services the team must operate" despite being
  architecturally similar. Pages CMS and TinaCMS go further (GitHub App and/or full DB+serverless) —
  each standing service is exactly the dependency this migration is trying to shed (trading "must have
  Obsidian open" for "must keep an OAuth proxy / Postgres / serverless function alive").

- **The editing widget is a solved problem; the plumbing is where tools differ.** CodeMirror (or a
  similar embeddable component) underlies most of these UIs' actual text-editing widget — StackEdit's
  PageDown-derived editor, Decap/Sveltia's markdown widgets, Pages CMS's TipTap/ProseMirror editor. If
  the team ever wants to build a custom thin editor, the widget layer is off-the-shelf; the hard parts
  are the **git/auth/config plumbing**.

---

### 13.12 Open questions

- **Per-type frontmatter schema vs. one-schema-per-collection.** Does the wiki's varying per-type
  frontmatter (`concept`/`practice`/`reference`/`source`/`map`, each with different expected fields per
  `_schema.md`) map cleanly onto Decap/Sveltia/Pages-CMS's "one field-schema per folder-collection"
  config model? Or is the schema loose enough that a **raw-markdown-only** surface (StackEdit-style, or
  plain git-PR) is actually a *better* fit than a form-driven CMS — which would need per-type YAML field
  definitions kept **in sync with `_schema.md`**, i.e. a *second* schema config to maintain, arguably
  contradicting the single-source-of-truth mandate for the schema itself?
- **Does the team want any human write surface beyond the git-PR baseline at all?** The agent-only-
  writes discipline already governs this repo's actual workflow. If it holds for the team too, the CMS
  evaluation (Sveltia/Decap/Pages/Tina) may be **moot** — only the read surface (Perlite) plus the
  git-PR escape hatch are actually needed.

---

### Recommendation for this cluster

**Compose a small stack, do not adopt one product.** Ranked for *this* wiki (cloud, team-shared,
markdown-as-truth, no Obsidian):

1. **Adopt — git-PR flow (§13.2) as the write baseline** + **Perlite (§13.10) as the read surface** +
   **agent-only-writes discipline (§13.3) as the governing policy.** This trio needs **zero new
   always-on services beyond what the team already runs** (git host + the already-planned read UI), is
   perfectly git-diffable, reuses existing repo auth/branch-protection, and matches the workflow this
   repo already practices. For most of the team, "editing" is talking to the agent; the git-PR path is
   the escape hatch for the rare hand-fix.
2. **Adopt if a guided form / live-preview editor is genuinely wanted — Sveltia CMS (§13.4)**, layered
   on top of the above in **PAT mode** so it adds **no backend** for a small team. Best
   infra-to-capability ratio of every CMS surveyed, MIT, actively developed, git-diffable by
   construction. First resolve the open question of whether maintaining per-type collection schemas
   (a second copy of `_schema.md`'s field expectations) is worth it versus raw-markdown editing.
3. **Evaluate only for a specific feature — Decap CMS (§13.5)** if the PR-per-entry Editorial Workflow
   is specifically wanted (accepting a self-run OAuth bridge); **Pages CMS (§13.6)** if a Notion-like
   WYSIWYG feel outweighs running Next.js+Postgres; **StackEdit (§13.8)** as an optional single-file
   convenience editor (but note it is unmaintained since 2019).
4. **Avoid — TinaCMS (§13.7)** unless live WYSIWYG preview is a hard requirement; it re-creates the very
   standing-service dependency this migration exists to remove, and its "DB is just a cache" claim needs
   verification before it can be trusted against the hard constraint.
5. **Disqualified — HedgeDoc (§13.9):** its canonical store is its own database, not the repo files. It
   fails the hard constraint outright and can serve only as an off-to-the-side real-time-collab
   scratchpad, never as where pages live.
