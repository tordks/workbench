## 11. Wiki Information Architecture — Taxonomy, Atomicity, and Multi-Team Namespacing

This cluster is not about servers or search engines; it decides the *organizing model* the
cloud-hosted, team-shared wiki must express so that markdown files stay canonical while many teams
edit one corpus. The core question it answers: **when multiple teams share one markdown wiki, what is
the stable handle a page is addressed by, and how do teams get their own space without forking the
vault?** Every scheme surveyed (Diátaxis, Johnny.Decimal, Zettelkasten, PARA, LYT/MOC, SKOS,
Backstage, org-multi-wiki) converges on one principle the repo's `[[blast-radius]]` rule already
names: *the handle a system points at must never be the thing that is convenient to reorganize.* None
of these are compute layers that could threaten the markdown-as-truth constraint — they are naming and
organizing conventions, so all are constraint-safe; the only adoption risk is inventing a **second
source of truth for identity** (a numeric ID scheme, a folder-per-team split), which this section
argues against.

**Takeaways:**
- Keep the existing closed 5-type taxonomy (`concept`/`practice`/`reference`/`source`/`map`) — it is
  already a coarse Diátaxis, an already-implemented LYT `map` layer, and an already-atomic Zettelkasten.
  No new page types.
- **Do not** adopt any numeric/positional ID scheme (Johnny.Decimal, Luhmann folgezettel) or
  folder-per-team namespacing (org-multi-wiki, PARA archive-by-move). Each couples identity to a
  mutable thing (number, position, path) and re-creates the drift the wiki is built to avoid.
- The **one missing piece** for multi-team scale is a single new frontmatter field: `owner:`, modeled
  directly on Backstage's `spec.owner`. Team space becomes a **per-team `map` page**, not a folder or a
  separate vault. One vault, one git repo, one flat tag vocabulary — the shared canon.
- Escalate to SKOS-style `broader`/`narrower` tag relations only if flat tags start colliding across
  teams; do not adopt preemptively.

---

### 11.1 Per-page classification — Diátaxis

- **What it is:** A documentation *framework* (not software) — <https://diataxis.fr/>,
  <https://diataxis.fr/start-here/>. Splits content into four types by user need on a 2×2 compass
  (action↔cognition × acquisition↔application): **tutorial** (action+acquisition, learning-oriented),
  **how-to guide** (action+application, task-oriented for a competent user), **reference**
  (cognition+application, information-oriented lookup), **explanation** (cognition+acquisition,
  understanding-oriented). Its central claim: mixing types in one document is the primary cause of bad
  docs.
- **Applies to this wiki:** A second axis *orthogonal* to the `type` taxonomy. The mapping:

  | Diátaxis type | Wiki `type` | Notes |
  |---|---|---|
  | reference | `reference` | direct match — propositional lookup |
  | explanation | `concept` | propositional, study-oriented |
  | how-to guide | `practice` | task-oriented procedure |
  | tutorial | *(none)* | intentionally absent — an internal team wiki is queried, not taught |

  The `source` and `map` types have no Diátaxis analogue (they are provenance and navigation, not
  content-for-a-reader), which is fine — Diátaxis governs content pages, not infrastructure pages.
- **Concrete details:** Originated in Django/Divio docs practice; now a standalone open framework, no
  license restriction on the pattern. Governs content/style/architecture only — *says nothing about
  folders, frontmatter, or storage*, so it composes with any taxonomy underneath. It provides **no
  navigation/scaling strategy** (that gap is what MOCs fill).
- **Gotcha / honest gap:** Diátaxis's reference-vs-explanation cut is *finer* than the wiki's single
  `concept`/`reference` split. Adopting it wholesale would fragment pages for no team-wiki benefit.
- **Verdict:** **Steal the idea, not the types.** Use Diátaxis as a per-page sanity check when
  authoring or linting — "is this page *stating a fact* (reference/explanation → `concept`/`reference`)
  or *telling someone what to do* (how-to → `practice`)?" This keeps `practice` pages from drifting into
  restating concepts. No new page types.
- **Maturity:** Mature, stable, widely adopted (Django, Divio, Google/Cloudflare style guides). Not
  versioned software; free.

---

### 11.2 Stable-ID filing — Johnny.Decimal

- **What it is:** A numeric filing scheme — <https://johnnydecimal.com/documentation/areas-and-categories>,
  <https://johnnydecimal.com/documentation/ids>. Structure: **10 Areas** (ranges `10-19`, `20-29`, …),
  each holding up to **10 Categories** (two-digit numbers within the range, e.g. `11`–`19`), each
  Category holding up to **99 numbered IDs** (`category.counter`, e.g. `11.03`). Reserved area `00-09`
  is for system/admin (index) use. The **number is the permanent handle**: `11.03 Travel insurance` can
  be renamed to `11.03 Trip insurance` and relocated, and `11.03` still resolves.
- **Concrete details / caps:** ≤10 categories per area; **≤99 IDs per category** (confirmed on the IDs
  doc page). Example IDs on the site: `15.52 Trip to NYC`, `15.22 Travel insurance`, `11.03`.
- **Applies to this wiki:** JD's *only* real insight is the decoupling of a stable pointer from a
  mutable label. The wiki already achieves this **without numbers**: filenames are kebab-case titles,
  `type` is in frontmatter (never in the filename per `wiki/_schema.md`), and Obsidian resolves
  `[[links]]` by basename/alias — so re-typing or moving a page across `type` folders never breaks
  inbound links. The wiki's stable handle is *filename + `aliases:`*, and its mutable parts are `type:`,
  folder, and `owner:`.
- **Gotcha / why it is harmful here:** Adding JD numbers would introduce a **second identity system**
  alongside filenames — two sources of truth for "which page is this," a direct blast-radius violation.
  JD numbers also carry *positional* meaning (area/category), reintroducing the hierarchy-in-the-ID
  problem that links exist to eliminate.
- **Verdict:** **Steal the idea, reject the numbering.** The wiki already gets JD's benefit
  (survives renaming/reorganizing) for free. No literal numbers.
- **Constraints/maturity:** Free naming convention (optional paid iOS companion app "JDex" is
  irrelevant). Active community site, no software releases.

---

### 11.3 Atomicity + IDs — Zettelkasten / Luhmann

- **What it is:** The original "one idea per note" discipline — <https://zettelkasten.de/atomicity/guide/>.
  Luhmann's paper cards used branching alphanumeric IDs (`1`, `2`, `2a`, `2b1`, …) called *folgezettel*
  to physically sequence related cards. Digital implementations (and this wiki) replace that
  mechanism with **links**, because a digital note can appear in unlimited sequences via backlinks
  instead of one physical slot — see the forum thread
  <https://forum.zettelkasten.de/discussion/761/luhmann-s-use-of-unique-ids>.
- **Applies to this wiki:** Directly validates two existing `_schema.md` rules:
  1. **Atomicity as the split criterion** — "one idea per page."
  2. **Filenames need not encode position/hierarchy** — links do that now that the medium isn't cards.

  The wiki's rule ("if a claim only makes sense as a qualifier of an existing idea, it's an edit to
  that page, not a new page") *is* the Zettelkasten atomicity test.
- **Key points / the actual test:**
  - Atomicity is **not about length** — "Hydrogen and Plutonium are both atoms, yet of very different
    size." The test is: can you *name* it easily, is it *understandable at a glance*, and does removing
    anything make the idea *incomplete*.
  - **Split trigger:** "if it feels like two things, make two notes" — a note mixing concepts can't be
    linked meaningfully because inbound links can't target "half" of it.
  - **Merge/structure trigger:** group notes into a *structure note* (≈ this wiki's `map`) when many
    small notes explore one aspect — cluster by "it means one thing," not by raw count.
  - Luhmann's folgezettel were a **physical-card necessity**; the forum explicitly notes digital tools
    replace them with "sequences on the fly through lists of links." Hierarchy-via-ID is obsolete once
    you have backlinks — exactly why the schema forbids encoding type/hierarchy in filenames.
- **Honest gap:** The source gives **no numeric size threshold** — deliberately, per the "atomicity is
  relative" argument. Do not invent one to cite; any page-size caps come from the
  `karpathy-wiki-implementations` survey already in the repo, not from Zettelkasten.
- **Verdict:** **Adopt as-is** — the wiki's atomicity rule already matches this literature. Cite it as
  the grounding rather than re-deriving a splitting heuristic.
- **Maturity:** zettelkasten.de is an active long-running reference; method dates to the 1950s–90s,
  extensively secondary-documented. A practice, not software; free.

---

### 11.4 Actionability filing — PARA (Projects / Areas / Resources / Archives)

- **What it is:** Tiago Forte's four-folder scheme — <https://fortelabs.com/blog/para/> (2017 blog post,
  expanded in *Building a Second Brain*, Atria Books 2022). Organizes by **actionability**, not topic:
  **Projects** (short-term, has a completion state), **Areas** (ongoing responsibility, never
  finishes), **Resources** (topics of interest), **Archives** (inactive items from the other three).
- **Applies to this wiki — mostly by contrast:** PARA is explicitly *personal-productivity*; the
  fetched source states outright it does not address team/shared knowledge bases (a promised follow-up
  on team PARA was not found published). Its actionability axis is **orthogonal to a durable reference
  wiki**: wiki pages are evergreen facts/conventions, not work items with a completion state, so the
  finished-vs-not-finished split doesn't map onto `concept/practice/reference/source/map`.
- **The one transferable idea — Archive-as-a-tier, done better:** PARA's Archives = inactive material
  kept for reference. This wiki plays the same role with the **`status: stale`** frontmatter marker —
  and does it *better*, because PARA archives by **moving the file to an Archive folder** (breaks
  paths/links) whereas `status:` archives **without moving anything** (path-stable). This is a concrete
  win for the blast-radius discipline.
- **Honest gaps:** No native multi-user or namespacing story — single-person by design; folder
  ownership across a team isn't part of the method. App-agnostic (Notion/Obsidian/filesystem).
- **Verdict:** **Avoid the folder scheme.** It confirms — by contrast — that the wiki's `status:`
  frontmatter field is the correct, path-stable expression of PARA's Archive concept. No folder move.
- **Maturity:** Very widely adopted personal-PKM pattern since 2017; no team/enterprise variant
  published by the originator as of the fetch. Concept free; book commercial but method unencumbered.

---

### 11.5 Navigation layer — LYT / Maps of Content (MOC)

- **What it is:** Nick Milo's PKM framework built on **MOCs** —
  <https://blog.linkingyourthinking.com/maps/>, <https://www.linkingyourthinking.com/>. An MOC is a
  "higher-order note" that is mostly links, acting as a hub/table-of-contents for a cluster of atomic
  notes, built through a **gather → collide → navigate** workflow. A note can belong to *many* MOCs at
  once; MOCs replace rigid folder hierarchies as the primary navigation layer.
- **Applies to this wiki:** This is the **direct ancestor of the wiki's `map` type** and its rule
  "navigation is by Maps of Content, not deep folders — a page can belong to many maps at once." LYT
  confirms the schema's choice is a named, established pattern and gives operational vocabulary for the
  `wiki-lint` structural checks.
- **Key points:**
  - MOC = mostly-links hub, deliberately not a folder — matches the wiki's "a page can belong to many
    maps" rule.
  - **Three-phase workflow:** *gather* related atomic notes → *collide* (juxtapose/develop connections
    inside the MOC) → *navigate* (use it as a day-to-day entry point).
  - **Observed MOC subtypes:** topic/concept, people/source, project/effort — a useful subdivision if
    the wiki's single `map` type ever needs finer grain (e.g. **map-per-team** vs map-per-topic — this
    is exactly the multi-team namespacing hook in §11.9).
  - LYT is a **synthesis** of Ahrens (*How to Take Smart Notes*), Forte (BASB), and Luhmann — not an
    independent invention.
- **Honest gap:** The primary source gives **no quantitative guidance** — no ideal MOC count, no
  nesting depth limit, no orphan-prevention algorithm. Those are left to tooling. The wider Obsidian
  practice (review Graph View / "unlinked mentions" to find zero-link nodes) relies on the desktop app
  — which this project **cannot** use headlessly, so orphan detection must be delegated to
  `obsidiantools` (already recommended in `docs/research/headless-wiki-hosting.md`) inside `wiki-lint`,
  not manual graph-view review.
- **Verdict:** **Adopt as-is** — the `map` type and multi-map-membership rule already implement LYT.
  Worth citing explicitly in `_schema.md`'s `map` row to document the lineage, and worth having
  `wiki-lint` operationalize "gather" by flagging orphans as MOC candidates.
- **Maturity:** Active output (blog/YouTube) since ~2020, widely adopted in the Obsidian community. MOC
  pattern is freely described (LYT sells a paid course); no tooling required.

---

### 11.6 Controlled vocabulary / lightweight ontology — SKOS

- **What it is:** W3C's Simple Knowledge Organization System — <https://www.w3.org/2004/02/skos/>, full
  reference at <https://www.w3.org/TR/skos-reference/>. An RDF/RDFS model for controlled vocabularies,
  thesauri, and taxonomies as linked data: concepts get URIs, with `skos:prefLabel`/`skos:altLabel`
  (preferred/alternate names) and `skos:broader`/`skos:narrower`/`skos:related` (hierarchy and
  association) between concepts.
- **Applies to this wiki:** The **formal model behind "controlled tag vocabularies + lightweight
  ontologies."** The wiki's tag list in `_schema.md` (a flat, non-hierarchical set: `meta`, `python`,
  `frontend`, `testing`, `tooling`, `architecture`, `workflow`, `ai`) is precisely a SKOS *concept
  scheme with zero broader/narrower/related relations* — i.e. a flat controlled vocabulary, not yet a
  taxonomy. The wiki already implements two SKOS ideas informally:

  | SKOS relation | Wiki mechanism | Status |
  |---|---|---|
  | `prefLabel` | the canonical tag string / page title | present |
  | `altLabel` | `aliases:` frontmatter (wikilink resolution) | present |
  | `related` | `related:` frontmatter (page level) | present |
  | `broader`/`narrower` | *(nothing at the tag level)* | absent — intentionally |
  | concept scheme | the flat tag list itself | present (single scheme) |

- **Key points / honest scope:**
  - SKOS's real mechanism is **RDF triples + URIs published as linked data** — far heavier than a
    markdown wiki needs. Borrow the **vocabulary/model** (pref/alt label, broader/narrower/related), not
    the RDF serialization.
  - The wiki's flat 8-tag list is intentionally small to avoid the taxonomy-drift problem SKOS exists to
    manage *at scale*. Adding SKOS hierarchy now would be premature machinery.
  - **Multi-team scale (the cluster's real question):** a flat shared tag list breaks once two teams
    want `deploy` to mean slightly different things. SKOS's answer is **scoped concept schemes** (each
    with a URI namespace) that still declare cross-scheme mappings. The wiki-scale analogy is a per-team
    tag **prefix** (`team-payments/deploy` vs a shared canonical `deploy`) rather than one global flat
    list — but only if drift actually appears.
- **Constraints:** Free open W3C standard (Recommendation since 2009). Full implementation needs RDF
  tooling (VocBench, PoolParty — enterprise/commercial) this project has no reason to adopt.
- **Verdict:** **Steal the idea only.** Keep the flat controlled vocabulary for single-team use; if/when
  multi-team namespacing is implemented, document broader/narrower/related informally in `_schema.md`
  rather than adopting RDF. See §11.9 step 5.
- **Maturity:** Stable, widely implemented in library/GLAM/enterprise taxonomy software; not versioned
  in the software sense.

---

### 11.7 Multi-team ownership at org scale — Backstage TechDocs + Software Catalog

- **What it is:** Spotify's open-source developer portal —
  <https://backstage.io/docs/features/techdocs/how-to-guides/>,
  <https://backstage.io/docs/features/techdocs/creating-and-publishing/>. Docs live as markdown beside
  the code (`docs/` + `mkdocs.yml`); each documented unit declares an **`owner:`** (a team/group) plus a
  `backstage.io/techdocs-ref` annotation in a `catalog-info.yaml`. TechDocs statically builds and serves
  all teams' docs into one unified portal.
- **Why it is the most relevant precedent:** Backstage answers the **multi-team namespacing question**
  with **per-component ownership *metadata* + an aggregating render layer**, *not* one shared folder tree
  every team edits, and *not* a fork-per-team. This is exactly the "frontmatter ownership over
  folder-per-team" argument at organization scale.
- **Key points:**
  - Ownership is declared in a small metadata file (`catalog-info.yaml`), **not by folder location** —
    the precise "frontmatter over folder" pattern this cluster investigates.
  - **Two monorepo patterns:** *combined* (whole repo = one entity, one `catalog-info.yaml`, one
    TechDocs build) when one team owns everything, vs *split* (each sub-component gets its own
    entity/build) when multiple teams share a repo. This is the "shared canon vs per-team space"
    decision — resolved by *whether ownership is uniform or mixed*, not by an a-priori folder
    convention. Source: <https://roadie.io/blog/backstage-monorepo-guide/>.
  - **Cross-entity reuse without duplication:** the `backstage.io/techdocs-entity` annotation lets one
    entity point at another's already-built docs — the namespacing equivalent of one canonical page
    linked from many teams' maps, zero copying.
  - `backstage.io/techdocs-ref: dir:.` is the recommended default (docs live beside their code),
    reinforcing "docs travel with their owning unit."
- **Concrete details:** Ownership annotation from the fetch: `spec.owner: group:payments-team`.
  Backstage is **Apache-2.0**, CNCF-incubating; TechDocs is a core plugin (no separate license/cost).
- **Gotcha / honest constraint:** Backstage is a **full developer-portal platform** (React frontend +
  plugin backend + entity database, needs hosting). It is **too heavy** for a markdown-only wiki with no
  code-catalog need. **Borrow the ownership-metadata pattern only, not the platform.**
- **Verdict:** **Steal the idea.** Adopt the resolved pattern: an **`owner:` frontmatter field per page**
  (extending `source:`/`related:`) + a per-team `map`/hub filtered by `owner`, instead of a
  folder-per-team split. This is the concrete mechanism behind §11.9.
- **Maturity:** Very active, CNCF incubating, Spotify + large OSS community; TechDocs is core and stable.

---

### 11.8 Folder-per-namespace prior art — org-multi-wiki

- **What it is:** An Emacs org-mode wiki extension — <https://github.com/akirak/org-multi-wiki> —
  supporting multiple named namespaces in one session. Each namespace maps to its own directory
  (declared once in `org-multi-wiki-namespace-list`), and cross-namespace links use the syntax
  `NAMESPACE:[subdir/]TITLE[::#customid]`; a bare link resolves within the current namespace.
- **Applies to this wiki:** A small, directly-analogous example of the **opposite** approach —
  "folder-per-namespace + explicit prefix in link syntax" — worth citing as evidence the pattern works,
  even though it is Emacs/org-mode-specific and not portable to an Obsidian/markdown vault.
- **Key points:**
  - Namespace = directory, declared in **one config list**, not per-file frontmatter — assignment is
    purely structural/positional, the *opposite* of the frontmatter approach this cluster favors.
  - Cross-namespace links require an **explicit prefix** (`ops:some-title`); same-namespace links stay
    unprefixed — the prefixed link is the deliberate, visible seam where one team reaches into another's
    space.
  - Namespaces are **filesystem-isolated**: one team's edits cannot collide with another's files
    (different roots) — trades **path-stability-across-teams** (a folder move is needed to change a
    page's namespace) for **hard isolation**.
- **The decisive gotcha:** Directory *is* identity here, so **renaming/moving a team's folder breaks
  every cross-namespace link that named it** — exactly the path-stability fragility the wiki's
  blast-radius principle is designed to avoid.
- **Verdict:** **Steal the idea only.** It confirms folder-per-namespace-with-explicit-prefix is a
  workable, precedented design, but its directory-=-identity coupling is the wrong trade for this wiki.
  Frontmatter ownership (Backstage-style, §11.7) is the better fit.
- **Constraints/maturity:** GPL Emacs package, not portable to markdown/Obsidian regardless. Small
  niche project, single maintainer, low activity — cited for the pattern, not as a dependency.

---

### 11.9 Cross-cutting synthesis + the namespacing recommendation

**The convergent principle.** Every scheme surveyed says the same thing: *the stable handle a system
points at should never be the thing that's convenient to reorganize.*

| Scheme | Stable handle | Mutable thing | Coupling risk |
|---|---|---|---|
| Johnny.Decimal | the number (`11.03`) | the label after it | number is a 2nd identity system |
| Zettelkasten (modern) | the link target | note's position/sequence | folgezettel coupled ID to sequence (rejected) |
| PARA | (n/a — actionability) | folder (Archive move) | move breaks paths |
| LYT/MOC | the link | which MOCs list it | none — links survive reorg |
| SKOS | the concept URI | prefLabel/altLabel | scoped schemes avoid arbiter |
| Backstage | `owner:` metadata | repo/folder layout | none — ownership is metadata |
| org-multi-wiki | directory path | the folder name/location | move breaks cross-namespace links |

The wiki **already has the pieces** to do this at multi-team scale, purely in frontmatter, without
inventing mechanics: `type` (page kind), `tags` (flat controlled vocabulary = SKOS `prefLabel`),
`aliases` (SKOS `altLabel`, and what makes wikilinks rename-resilient), `related`/`source` (SKOS
`related`), `status` (PARA Archive). **The one field missing for multi-team scale is `owner:`.**

**Concrete namespacing recommendation** (the durable answer for "multiple teams share one wiki"):

1. **One shared vault, one git repo, one flat controlled tag vocabulary** — the "shared canon" that
   Backstage's *combined-monorepo* pattern models when ownership is roughly uniform. Do **not** fork
   into per-team vaults/repos: that recreates the "wiki multiple teams can use" problem as N wikis, and
   cross-team `[[links]]` would need cross-repo federation machinery **no surveyed headless tool
   provides** — `qmd`, `obsidiantools`, and Basic Memory each operate on a **single vault** (see
   `docs/research/headless-wiki-hosting.md`). This keeps the HARD CONSTRAINT intact: canonical store
   stays plain markdown files in one repo.
2. **Add one frontmatter field, `owner:`** — single value, controlled vocabulary of team names (same
   discipline as `tags`), modeled on Backstage's `spec.owner`. It declares which team maintains a page's
   accuracy **without constraining where the file lives**. Reassigning ownership is a frontmatter edit,
   never a file move — preserving blast-radius.
3. **Folders stay organized by `type` (concepts/practices/references/sources/maps), never by team.** A
   `practice` page about team-payments' deploy process lives in `practices/`, tagged with the shared
   vocabulary, `owner: team-payments`, and linked from **both** a shared top-level map and a
   team-specific map. This is LYT's "a note belongs to many maps" + Backstage's cross-entity reference:
   one canonical page, multiple hub entry points, zero duplication.
4. **Each team gets its own `map` page** (e.g. `maps/team-payments.md`) curating "pages owned by or
   relevant to this team." **The map is the namespace — not the folder, not a separate vault.** This is
   SKOS's "scoped concept scheme" applied at the map layer: a team's map is its local *view* into the
   shared canon. Cross-team links are ordinary `[[wikilinks]]` — **no prefix syntax needed**, because
   there is only one namespace of filenames; collisions are handled the same way the wiki already
   handles them (search-before-create, per `_schema.md`'s ingest rule).
5. **Tag-vocabulary growth:** extend `_schema.md`'s "reuse an existing tag, don't coin a near-synonym"
   rule with a lightweight SKOS escape hatch **only if/when** flat tags start colliding across teams
   with different meanings — at that point document (in `_schema.md`, not per-page) which tags are
   broader/narrower/related, rather than introducing prefixed or per-team tag namespaces. **Do not adopt
   this preemptively** — the current 8-tag flat vocabulary shows no sign of needing it.
6. This deliberately keeps the wiki a **single git repo / single Obsidian vault serving all teams** —
   consistent with markdown-as-truth and avoiding the cross-vault-federation problem no surveyed
   headless tool solves.

**Open questions (unresolved by this research, flagged honestly):**
- Whether the Obsidian local-rest-api / MCP layer (or its cloud-hosted replacement) can filter/query by
  `owner:` as cheaply as by `tags:` — an *implementation* question for the hosting cluster, not IA.
- At what team-count or page-count the flat-vocabulary / single-vault design would need SKOS-style
  broader/narrower escalation — no source gave a numeric threshold, and none should be invented.
- Whether `owner:` should be single-value or allow **co-ownership** (a list) for jointly-maintained
  pages. Backstage's model is single-owner (`spec.owner`), the simpler default recommended here; shared
  pages may need a documented tie-break rule (e.g. "first-listed team resolves contradictions") if it
  arises in practice.

---

### Recommendation for this cluster

For a cloud, team-shared, markdown-as-truth MCP wiki, the information-architecture decision is
**mostly to keep what exists and add exactly one field.** Ranked:

1. **Backstage's ownership-metadata pattern → adopt as `owner:` frontmatter (top pick).** It is the only
   surveyed scheme that solves multi-team namespacing *without* coupling identity to a mutable path, and
   it composes with the existing type-based folders and single-vault constraint. Adopt the pattern, not
   the platform.
2. **LYT/MOC and Zettelkasten atomicity → already adopted; cite, don't change.** The `map` type,
   multi-map membership, and one-idea-per-page rule are these frameworks by another name. The only new
   work is a per-team `map` page as the namespace unit and documenting the lineage in `_schema.md`.
3. **Diátaxis → steal as a per-page authoring/lint check**, not new page types. The 5-type taxonomy is
   already a sufficient, coarser Diátaxis for a queried team wiki.
4. **SKOS → hold in reserve.** Keep the flat controlled vocabulary; borrow `broader`/`narrower`/`related`
   *informally* only if cross-team tag collisions actually appear.
5. **PARA → adopt only the Archive concept, already better-served by `status: stale`.** Reject the
   actionability folder scheme.
6. **Johnny.Decimal and org-multi-wiki → reject as mechanisms, cite as evidence.** Both couple identity
   to a mutable thing (a number; a directory path), which the wiki's blast-radius discipline and its
   alias-resolved wikilinks already avoid. Adopting either would create a second source of truth for
   identity or reintroduce path-fragility.

None of these threaten the markdown-as-truth constraint — they are all naming/organizing conventions
with no store of their own. The net change to the wiki is **one new frontmatter field (`owner:`), one
new `map` page per team, and a few citations in `_schema.md`** — everything else the wiki already does
correctly.
