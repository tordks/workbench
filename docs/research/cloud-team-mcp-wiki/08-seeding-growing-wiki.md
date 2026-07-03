## 08. Seeding and Growing the Team Wiki

This cluster decides how a cloud, team-shared, markdown-as-truth MCP wiki gets *populated in the
first place* (bulk-ingest of existing docs, Slack, Confluence, PDFs) and how it *stays healthy as it
grows* (page-creation thresholds, stub control, health metrics, contributor onboarding). None of the
tools surveyed here become the store — every one of them is a **disposable extraction/conversion
layer** that hands plain text or markdown to this repo's own `wiki-ingest` skill, which remains the
sole place frontmatter (`type`/`tags`/`source`/`related`) is assigned. The hard constraint holds
cleanly throughout: markdown files stay canonical; each tool below either produces markdown or
produces structured intermediate data that the LLM ingest step atomizes into markdown, and none of
them is proposed as the source of truth.

**Takeaways:**
- Bulk-ingest is always **two separate steps** no single tool collapses: (1) format extraction (get
  raw text/markdown out of the source system) and (2) LLM atomization (split into typed atomic pages
  with frontmatter, dedup, cross-link). Step 2 is this repo's existing skill; this cluster only
  supplies step-1 front-ends.
- **`docling`** is the clear PDF/office-doc extractor. **`slackdump`** is the clear Slack extractor.
  **`confluence-to-llm-wiki`** is the closest Confluence template. All three are metadata/taxonomy-blind.
- The real choke point is **agent-ingest throughput**, not source connectivity — every extractor is
  fast; the LLM atomization pass is the bottleneck and the only step that touches the taxonomy.
- **`secure-llm-wiki`** adds the missing safety dimension: bulk-ingesting *untrusted* external
  content (old Slack banter, third-party PDFs) warrants a trust-tier + provenance-per-claim schema
  folded into the existing `source:` frontmatter field.
- **Wikipedia's stub thresholds** and **`llm-atomic-wiki`'s** real-run numbers give hard calibration
  points for page-creation gates (500 words = not a stub; 2–8 atoms/page; <200-page ceiling before
  vector search is needed; 60-item floor before a new taxonomy bucket).
- **Coverage-as-a-metric** (topics discussed-but-undocumented) has **no first-class tool anywhere** —
  it must be built bespoke.

---

### Step 1 — Format extraction (source → raw markdown/structured text)

These three tools each cover one source family. All run headless on a server and all stop *before*
atomization: they never emit typed pages or synthesize frontmatter.

| Tool | Source family | Output | License | Native markdown? | Frontmatter/taxonomy? | Maturity |
|---|---|---|---|---|---|---|
| [docling](https://github.com/DS4SD/docling) | PDF/DOCX/PPTX/XLSX/HTML/EPUB/audio/email/images/LaTeX | Markdown, HTML, lossless JSON | MIT | Yes | No (metadata "coming soon") | Very active, IBM Research, monthly releases |
| [slackdump](https://github.com/rusq/slackdump) | Slack workspaces | Archive / Slack-export / per-channel JSON / SQLite | AGPLv3 | **No** (needs a converter) | No | Very active, 2.7k stars, 108 releases |
| [confluence-to-llm-wiki](https://github.com/iYasha/confluence-to-llm-wiki) | Confluence spaces | Markdown + YAML frontmatter | MIT | Yes | Partial (provenance only; own taxonomy) | Small, focused, single-purpose |

#### docling (IBM Research) — the PDF/office-doc extractor

[github.com/DS4SD/docling](https://github.com/DS4SD/docling) parses the broadest input set of any
extractor surveyed: PDF, DOCX, PPTX, XLSX, HTML, EPUB, WAV, MP3, WebVTT, EML, MSG, PNG/TIFF/JPEG,
LaTeX, plain text, ODT/ODS/ODP, XBRL. It exports directly to Markdown (plus HTML, WebVTT, DocLang,
DocTags, and a lossless structured JSON `DoclingDocument` that preserves semantic hierarchy rather
than flattening it). The Markdown output is what a `wiki-ingest` pass would consume.

- **Install:** `pip install docling` — Python 3.10+ required (Python 3.9 support dropped at v2.70.0).
- **Version at fetch:** v2.108.0 (July 1, 2026), roughly monthly release cadence.
- **License:** MIT. Free, self-hosted, no cloud dependency required.
- **Table quality:** the TableFormer sub-model reports ~88% F1 on table-structure extraction — markedly
  better than lighter converters, which matters for table-heavy spec/design docs.
- **Deployment as a shared service:** ships a bundled MCP server and an API-server mode, so it can sit
  as a headless conversion service an ingest skill calls over MCP rather than shelling out to a CLI —
  a natural fit for the cloud/team-shared model of this whole report.
- **Ecosystem:** named plug-and-play integrations for LangChain, LlamaIndex, CrewAI, Haystack.
- **Gotcha (mark plainly):** automatic metadata extraction (title/authors/references/language) is
  flagged **"coming soon" — i.e. NOT available today.** docling does **not** hand you YAML
  frontmatter. Frontmatter for wiki pages must still be synthesized by the LLM ingest step afterward.
  docling is a pure format converter with zero taxonomy awareness.
- **Production split (from comparative reviews):** use docling for table/formula/multi-column-heavy
  docs; [MarkItDown](https://github.com/microsoft/markitdown) (Microsoft, MIT) as a fast-path fallback
  for clean digital PDFs; Marker (Datalab, GPU-hungry) reserved for the academic-paper subset needing
  maximum accuracy.

**Verdict:** adopt as the PDF/office-doc → markdown pre-processing step feeding `wiki-ingest`. Run it
*before* LLM atomization, never as a replacement for it (no frontmatter/type/tag synthesis of its own).

#### slackdump (rusq) — the Slack extractor

[github.com/rusq/slackdump](https://github.com/rusq/slackdump) is a Go CLI/library that archives Slack
workspaces (public/private channels, DMs, threads, files, users, emoji) **without requiring Slack admin
privileges** — it authenticates as a normal user via personal token/cookie. This matters because
workspace-owner-triggered native exports gate private channels/DMs behind paid tiers.

- **Install:** `brew install slackdump` (macOS) or a pre-built binary from GitHub releases.
- **Version at fetch:** v4.4.1 (June 2026). 2.7k stars, 2,310 commits, 108 releases — the most
  mature/battle-tested Slack-export tool surveyed.
- **License:** **AGPLv3 (copyleft).** Fine to run as an external CLI tool; do **not** vendor its Go
  source into this repo's Python-stdlib-only skill scripts. The copyleft constrains redistribution of
  slackdump itself, not this repo's own scripts that merely invoke it.
- **Output shapes:** "Archive" (its own optimized/universal format), "Export" (Slack-native-compatible,
  including a Mattermost-import mode), "Dump" (one file per channel), plus JSON+GZIP and a SQLite DB.
- **Incremental / continued growth:** supports incremental archiving and archive merging/deduplication
  — re-run against a channel without re-processing history already captured (directly relevant to the
  re-ingest-cost problem this cluster's growth patterns must solve for chat sources).
- **Deployment as a shared service:** ships a bundled MCP server so an agent can query an archived
  workspace directly, plus a built-in viewer that renders an export as a static HTML site.
- **Gotcha (mark plainly):** **no native markdown export.** The documentation does not mention a
  markdown output mode, so a `wiki-ingest` pipeline needs a conversion step between slackdump's archive
  and markdown+frontmatter — either a community tool (`slack-export-to-md`, `slack2md`) or feed the
  JSON/SQLite output directly to the LLM ingest step.
- **Hard external limit:** Slack free plans cap API-visible history at **90 days** regardless of
  exporter. No tool bypasses this — a ceiling on how much history is even recoverable for seeding if
  the team never upgraded.

**Verdict:** adopt as the Slack-extraction front-end for a "from Slack" source adapter, paired with a
small markdown-conversion pass (community slack2md-style script, or JSON/SQLite straight to the LLM
ingest step), since slackdump stops at structured archive, not atomic wiki pages.

#### confluence-to-llm-wiki (iYasha) — the Confluence template

[github.com/iYasha/confluence-to-llm-wiki](https://github.com/iYasha/confluence-to-llm-wiki) is a
two-stage cold-start pipeline whose split maps almost exactly onto this repo's `sources/` (immutable)
vs `wiki/` (atomized) division:

- **Stage 1 (`fetch_confluence.py`):** walks a Confluence space recursively via the REST API and
  exports every page as markdown with YAML frontmatter, preserving hierarchy (leaf → `<slug>.md`,
  parent → `<slug>/index.md`). Handles Confluence-specific noise: rewrites page-reference macros/inline
  cards to relative local links, flattens link macros to real anchors, auto-skips empty pages. Built-in
  exponential backoff on HTTP 429; idempotent re-runs (safe after partial failure).
- **Stage 2 (Claude, driven by `prompts/convert-to-wiki.md`):** reads the immutable `original-spec/`
  files and builds `llm-wiki/` organized into semantic folders (entities/concepts/processes/APIs/
  decisions/sources); every claim carries a citation back to its Confluence origin.
- **Three named workflows** baked into the prompt contract: cold-start ingest (whole space),
  incremental updates (changed pages only), and linting.
- **Install:** `uv sync` (Python ≥3.13; deps: requests, markdownify, python-dotenv, beautifulsoup4).
- **Config (`.env`):** `CONFLUENCE_BASE_URL=https://yourorg.atlassian.net`, `CONFLUENCE_API_TOKEN=...`,
  `CONFLUENCE_AUTH=auto|basic|bearer`, `CONFLUENCE_SPACE_KEY=NE`. Classic tokens use Basic auth
  (email+token); scoped tokens use Bearer (email optional, needs `read:page:confluence` scope).
- **Commands:** `uv run python fetch_confluence.py --space NE` (whole space) or
  `--root-page-id 4975525892` (subtree only).
- **Reusable frontmatter provenance:** each file preserves Confluence page ID, space ID, Confluence
  URL, version, and updated timestamp — a direct template for this repo's `source:` provenance field.
- **License:** MIT.
- **Gotchas:** does not auto-delete local files when the upstream Confluence page disappears (manual
  reconciliation needed); >1000-page spaces may hit rate limits (workaround: re-run, the fetch is
  idempotent). Python ≥3.13 required. The convert stage is **not fully automated** — it needs Claude
  (or an equivalent agent) to run the prompt contract.
- **Taxonomy mismatch:** targets its own entities/concepts/processes/APIs/decisions taxonomy, **not**
  this repo's `concept/practice/reference/source/map` types.

**Verdict:** steal-the-idea, do not adopt verbatim. Its fetch-then-atomize two-stage shape and its
frontmatter provenance fields (space/page-id/version/updated) are a direct template for a
Confluence-specific `wiki-ingest` source adapter. Tip: copy `prompts/convert-to-wiki.md` into the
target wiki as `CLAUDE.md` so the conversion contract persists across agent sessions (adapt to this
repo's type set).

---

### Step 2 — LLM atomization (owned by this repo's `wiki-ingest` skill)

No tool in this cluster collapses extraction and atomization into one. The atomization step — split
raw text into typed atomic pages, assign frontmatter, dedup against existing pages, cross-link — is
the job `wiki-ingest` already owns, per the mechanics already documented in
`karpathy-wiki-implementations.md` (ekadetov backlink-audit, green-dalii alias-merge, hermes-agent
page-creation-threshold). Those are **cited, not re-derived here.** Two repos in this cluster give
useful *implementation-reference* detail for that step:

#### llm-atomic-wiki (cablate) — growth-run reference numbers

[github.com/cablate/llm-atomic-wiki](https://github.com/cablate/llm-atomic-wiki) extends Karpathy's
LLM-wiki gist with an explicit atom layer, distilled from an actual from-zero run — the most directly
relevant prior-art for "growth/maturity patterns" and "page-creation thresholds" in this cluster.

- **Pipeline:** `raw/` (untouched sources) → `atoms/` (one claim per file, organized into topic-branch
  folders like `ai-agent/`, `mcp/`) → `wiki/` (flat, compiled pages prefixed by branch, e.g.
  `wiki/<branch>-<subtopic>.md`). Atoms are the immutable source of truth; **wiki pages are disposable
  derived compilations, re-buildable from atoms** — aligned with this report's hard constraint.
- **Atom frontmatter:** `source`, `type` (claim/concept/procedure), `depth`
  (introductory/intermediate/advanced), `tags`, `date`.
- **Compilation ratio (real-run norm):** **2–8 atoms per compiled wiki page** — a concrete benchmark
  for "is this page too thin or too bloated."
- **Two-layer lint:** `scripts/lint.sh` runs deterministic checks first (ghost/dangling links, orphan
  pages, format violations); a separate LLM pass handles semantic issues (contradictions, expired
  claims). Mirrors this repo's own pre-commit-vs-`wiki-lint` tiering — confirming that split scales.
- **Parallel-compile lock:** pre-locks the slug namespace before parallel ingestion so concurrent
  agents can't create near-duplicate filenames (`mcp-plus-skills.md` vs a variant spelling) — a cheap,
  concrete mechanism for the "concurrent ingest subagents clobber a slug" failure mode named in the
  prior karpathy research.
- **Real growth numbers:** 584 source posts + 8,668 replies → 70–90% of posts retained after noise
  filtering but only ~13% of replies retained (replies are mostly noise) → 630 atoms → 11 topic
  branches → **83 compiled wiki pages.** Lint health improved 47 warnings → 16 after tightening
  detection regexes — a concrete "warnings-per-pass trending down" data point.
- **Operational commands:** `./scripts/gen-index.sh` (rebuild index), `./scripts/lint.sh`,
  `./scripts/log-append.sh "msg"` — analogous to this repo's log/index conventions.
- **Explicit ceiling:** authors state the architecture is right for **<200 wiki pages** and update
  cadence of days/weeks (not minutes); beyond ~200 pages you need vector search rather than browsing
  flat `wiki/`. (Consistent with the prior `headless-wiki-hosting.md` recommendation of qmd for content
  retrieval.)
- **141 stars / 25 forks.** Framework (docs/templates/scripts) is versioned in git; user content
  (`raw/`, `atoms/`, `wiki/`) is gitignored by design — the framework ships, the instance-specific
  knowledge does not.
- **Stated precondition:** single owner with a consistent point of view, quality over exhaustive
  coverage — an **explicit admission this pattern is NOT yet validated for a multi-contributor team
  wiki at scale.**
- **License gotcha:** framework script/template license not independently confirmed in the fetch —
  treat as "steal the idea, verify license before vendoring any script."

**Verdict:** adopt the atom-layer + topic-branch mechanics as an implementation reference for
`wiki-ingest`'s fan-out step, and adopt the 2–8-atoms/page ratio plus the <200-page ceiling as
calibration numbers for page-creation-threshold and index-sharding decisions. Its single-owner
precondition means the team-scale concurrent-write angle still needs *this repo's own* locking answer,
not a copy of the parallel-compile lock.

#### secure-llm-wiki (NicoBleh) — the ingest-safety layer

[github.com/NicoBleh/secure-llm-wiki](https://github.com/NicoBleh/secure-llm-wiki) is the only surveyed
tool that treats indirect prompt injection during bulk-ingest as a first-class threat. Seeding a team
wiki from external sources means ingesting content nobody fully trusts (old Slack threads, third-party
PDFs, stale Confluence pages) — this is the safety half of the cluster's mandate.

- **7-layer pipeline** enforcing one invariant end-to-end (untrusted input never reaches a trusted
  channel): (1) ingestion sanitizing strips zero-width chars, bidi text, HTML, base64, instruction-like
  patterns; (2) extraction pulls atomic claims with provenance via nonce-delimited prompts;
  (3) trust-tiering assigns a trust level per source URI pattern, and the weakest tier propagates when
  sources conflict; (4) adversarial review by an independent second model; (5) a five-check write-gate
  (sanitizing, provenance validation, trust-tier verification, review verdict, semantic consistency)
  must all pass before a claim is written; (6) wiki-store commits markdown+YAML to a separate git repo;
  (7) read-time hygiene re-wraps stored content in nonce-delimited markers so the wiki can never be read
  back as hidden instructions.
- **4-eyes by default:** extraction and adversarial-review use *different* models (llama3.1 + mistral on
  Ollama, or claude-haiku + claude-sonnet on Anthropic) so one jailbroken model can't pass both gates.
- **Provenance schema per claim:** source ID, source URI, content hash, trust tier, review-verdict
  timestamp — a concrete field set to fold into this repo's `source:` discipline for untrusted material.
- **Trust tiers** are assigned by a URI-pattern registry (internal wiki > Confluence > Slack > arbitrary
  scraped PDF), not per-document manual tagging.
- **79 regression tests** mapping 8 attack vectors to OWASP LLM Top 10 and MITRE ATLAS, all mocked (no
  live LLM calls) — a reusable test-taxonomy reference even if the tool isn't adopted.
- **CLI:** `secure-wiki ingest source.pdf --trust semi-trusted`, `secure-wiki list --quarantine`,
  `secure-wiki query --min-trust trusted`, `secure-wiki clear --reset --keep-history`.
- **License:** MIT. Author frames it as a portfolio/red-teaming reference, not a production dependency.
- **Cost/ops gotcha:** requires two distinct LLMs per ingested claim (cost/latency roughly doubles vs
  single-model extraction) plus a separate git repo for wiki-store — a nontrivial addition for a team
  just seeding from zero.
- **Store conflict (flag against hard constraint):** it owns its own CLI/store shape, which conflicts
  with this repo's Obsidian-vault-as-truth model. Do **not** adopt wholesale.

**Verdict:** steal-the-idea for the ingest-safety layer only. Fold trust-tiering + provenance-per-claim
+ nonce-delimited read-time hygiene into `wiki-ingest` whenever a bulk source is external/untrusted.
Tag ingested pages with a trust tier at capture time and treat "how much do we trust this fact" as an
explicit, inherited property.

---

### Growth control — page-creation thresholds and stub management

#### Wikipedia stub-management discipline

[Wikipedia:Stub](https://en.wikipedia.org/wiki/Wikipedia:Stub) is the most battle-tested precedent
anywhere for deciding when a short page is a legitimate keeper vs stub-bloat noise — run at a scale
(millions of articles, two decades) far beyond any team wiki. Its numbers are directly reusable as
calibration points.

| Threshold | Value | Translation to this wiki |
|---|---|---|
| Stub too-long heuristic | ~10 sentences | A page past ~10 sentences is clearly no longer a stub |
| Soft per-article stub cutoff | ~250 words | Below this, likely still a stub |
| Automated stub-tag removal (AutoWikiBrowser) | 500 words | ">500 words = definitely not a stub anymore" |
| New taxonomy-node (stub category) ideal size | 100–300 articles | Don't split out a new type-node until well-populated |
| New taxonomy-node hard floor | 60 articles | Absolute minimum before a new sub-bucket is worth creating |

- **Anti-bloat maintenance action:** undersized categories that will never reach the 60-article floor
  are actively **upmerged or deleted**, not left to linger — a creation gate *and* a cleanup rule.
- **Persistent-equilibrium reality:** even at Wikipedia's scale with two decades of process, **32.1% of
  all articles (~2.3 million) remain stubs** as of July 2026 — evidence that stub-bloat is a state to
  manage continuously, not a one-time problem solved at seeding.

**Verdict:** adopt the numeric calibration, not the process. Translate "500 words = not a stub" and
"60-item floor before a taxonomy bucket is worth creating" into this repo's page-creation-threshold
guidance. Do **not** import Wikipedia's bot/category machinery (different scale and governance model).

#### Health metrics — the two-tier maturity split (and a plain gap)

- **Hard, lived numbers:** Wikipedia's stub/category thresholds and `llm-atomic-wiki`'s real lint-warning
  trend (47 → 16) are the only operational health data points found.
- **Graph-health is a graph-tool problem:** orphan (no inlinks), dead-end (no outlinks), and
  dangling/unresolved `[[link]]` detection is an obsidiantools-class job (per the prior
  `headless-wiki-hosting.md` finding), **not** something generic "KB health" tooling measures.
- **Negative finding — generic KB health tooling is SEO-oriented, not graph-oriented:**
  [Document360's health-check metrics](https://document360.com/blog/knowledge-base-article-health-check-metrics/)
  turned out to be meta title/description length, word count ≥300, readability score — readability, not
  orphan/staleness/coverage. Cited only to document that gap.
- **Coverage-as-a-metric is a genuine literature gap:** the aspiration ("topics the team discusses in
  Slack but never documented") appears only in [Falconer's marketing content](https://falconer.com/guides/enterprise-llm-wiki-karpathy/)
  with **no operational definition or threshold given anywhere.** No tool or writeup gives a computable
  "coverage %" formula for a markdown wiki. This is a real gap, not a missed source.
- **Pragmatic bespoke approximation** under this repo's constraints:
  `coverage_gap = (Slack/Confluence topics mentioned N+ times) − (topics with an existing wiki page/alias)`,
  reusing hermes-agent's already-cited "2+ mentions or source-centrality" page-creation threshold as the
  same knob for the coverage gate. This must be **built as a bespoke script**, not adopted.

---

### Onboarding human contributors

#### Wikipedia Growth-team newcomer research

[MediaWiki Growth / Newcomer experience](https://www.mediawiki.org/wiki/Growth/Newcomer_experience_projects)
is the most-studied real-world precedent for turning a first-timer into a repeat contributor at scale —
and the closest transferable prior art, because team-scale onboarding for *this cluster's specific
artifact* (typed atomic markdown + `inbox/` staging) has almost **no direct prior art**. Every
wiki-adjacent tool here and in the prior karpathy report assumes a single agent-operator, not a
multi-human team.

- **Onboarding flow:** (1) ask interests at signup → (2) surface a personalized queue of small,
  well-scoped tasks matched to those interests (e.g. "add a link", "add an image") → (3) walk the user
  through each step of the first task → (4) mobile-friendly throughout. An operationalized "good first
  task" queue, not an open-ended "go edit anything" invitation.
- **Core retention failure mode (research-backed):** the long decline in active editors (falling since
  2007) is attributed substantially to hostile first contact — newcomers' edits reverted by established
  editors for breaking an ever-longer rulebook, without explanation.
- **Research-backed retention levers:** welcome messages, direct assistance/mentorship, constructive
  (not merely corrective) criticism, user-friendly tools, and protected safe-spaces for practice edits
  all measurably raise retention; reverting without guidance drives newcomers away.
- **In-context help:** short tutorials triggered by what the user is currently doing, not one upfront
  training session before the first edit.

**Verdict:** steal-the-idea. Give a new team contributor a small, well-scoped, interest-matched first
`wiki-capture` task (not "go write pages"); respond to their first capture/ingest with constructive
guidance rather than a silent revert/rewrite; keep first-edit friction near zero. This repo's own
`inbox/` append-and-review lane **already matches** the "low-stakes first contribution" pattern —
newcomers get a zero-stakes drop point instead of having to author a finished typed page on day one.

---

### Open questions carried forward

- **No computable coverage metric exists** for a markdown wiki (topics discussed-but-undocumented) —
  must be built bespoke (cluster Slack/Confluence topic mentions, diff against existing page
  titles/aliases). Not adoptable from any surveyed tool.
- **Confirm Confluence and Slack are actually in scope** before investing in either adapter. If the
  team's material is mostly local files/PRDs, `docling` (PDF/DOCX/PPTX) plus this repo's existing
  capture/ingest skills may already suffice — no Confluence or Slack connector needed at all.
- **Multi-contributor concurrent-capture UX for humans** (not subagents) is untested. The prior
  locking research (AgriciDaniel's `wiki-lock.sh`, jrcruciani's precondition-hash propose→apply→receipt)
  was scoped to concurrent *agents*; whether the same mechanism fits concurrent *humans* dropping
  captures into `inbox/` was not validated in either prior report or this one.

---

### Recommendation for this cluster

For a cloud, team-shared, markdown-as-truth MCP wiki, the seeding pipeline is a **two-step assembly of
disposable front-ends feeding this repo's own `wiki-ingest` skill** — nothing here becomes or replaces
the store.

1. **Adopt `docling` (MIT, v2.108.0) as the default and often *only* extractor.** It covers the
   PDF/DOCX/PPTX/XLSX/HTML/EPUB majority of any team's legacy docs, exports clean Markdown, and can run
   as a shared MCP/API service. If the team's material is mostly local files/PRDs, `docling` + existing
   capture/ingest skills is the whole pipeline. This is the highest-leverage, lowest-risk adoption.
2. **Add `slackdump` (AGPLv3, external CLI only — never vendor) *only if* Slack is confirmed in scope**,
   paired with a small markdown-conversion pass. Respect the 90-day free-tier history ceiling.
3. **Use `confluence-to-llm-wiki` (MIT) as a template, not a dependency, *only if* Confluence is in
   scope** — copy its fetch-then-atomize shape and its provenance frontmatter fields into a
   Confluence source adapter, retargeted to this repo's `concept/practice/reference/source/map` types.
4. **Fold `secure-llm-wiki`'s trust-tier + provenance-per-claim + nonce read-time hygiene into
   `wiki-ingest` whenever a bulk source is external/untrusted** — do not adopt its CLI/store (it
   conflicts with the vault-as-truth constraint). Its 79-test OWASP/MITRE-ATLAS taxonomy is a reusable
   reference regardless.
5. **Adopt the calibration numbers wholesale:** `llm-atomic-wiki`'s 2–8-atoms/page ratio and <200-page
   vector-search ceiling, plus Wikipedia's 500-word "not-a-stub" and 60-item taxonomy-node floor, become
   this repo's page-creation-threshold and index-sharding guidance. `llm-atomic-wiki`'s parallel-compile
   slug-lock is a concrete reference for the concurrent-ingest clobber problem, but its single-owner
   precondition means the team-scale concurrent-write answer stays this repo's own.
6. **Onboard humans via the Wikipedia Growth pattern** — small interest-matched first `wiki-capture`
   tasks and constructive (non-reverting) response — which the existing `inbox/` lane already supports.
7. **Build the coverage metric bespoke** — no tool provides it. The `hermes-agent` "2+ mentions"
   threshold is the reusable knob.

The single durable insight: **source connectivity is easy and cheap; the bottleneck is agent-ingest
throughput at the one taxonomy-aware step.** Every extractor here is metadata/taxonomy-blind by design,
so invest engineering effort in the LLM atomization pass (dedup, frontmatter synthesis, cross-linking),
not in chasing more source connectors.
