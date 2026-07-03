## 07. Team Conventions & Governance

Once the wiki stops being a single-user WSL loopback and becomes a cloud-hosted,
team-shared MCP service, two questions that never mattered for one author suddenly
do: **who is allowed to change a given fact**, and **when is a fact presumed stale
enough to need re-review**. This cluster surveys how established documentation
systems (GitHub/GitLab CODEOWNERS, Confluence, Notion, Wikipedia, the Good Docs
Project, Diátaxis, MADR, Vale) answer those two questions, and maps each answer back
onto the wiki's hard constraint: **plain-markdown-files-as-truth, indexes/servers as
disposable layers**. None of the governance mechanisms below violate that constraint,
because governance here is metadata *about* the files (frontmatter fields, a
`CODEOWNERS` file, a lint rule) rather than a store that owns the content — the one
thing to watch is not letting a SaaS wiki (Confluence/Notion) become the canonical
copy, which is why every SaaS entry below is "steal-the-idea, don't adopt the
product."

**Takeaways:**

- **Ownership:** converge on **named-owner-per-scope**, expressed once in a root
  `CODEOWNERS` file (path → curator), not scattered per-page. This is itself
  blast-radius discipline. Wikipedia's ownerless-consensus model is the deliberately
  *rejected* alternative, appropriate only for open/adversarial editing at scale.
- **Staleness:** the one concrete gap versus today's schema is a *trigger*. The
  schema has `status: stale` but nothing sets it. Add `owner:` + `review_by:`
  frontmatter fields and let `wiki-lint` flag pages past their `review_by` date — no
  cron/CI needed at this scale.
- **SSoT:** add one explicit, citable "the wiki is the single source of truth"
  sentence to `wiki/_schema.md` (GitLab's phrasing precedent), giving contributors a
  tie-breaker to point at in a duplication dispute.
- **Process tiers:** the existing two-tier lint split (`pre-commit` syntactic vs
  `wiki-lint` semantic) already mirrors the industry "well-formed vs substantively
  correct" split; CODEOWNERS-style required PR review is the missing middle layer,
  relevant only once more than one human pushes to the vault.
- **Prose linting:** Vale (MIT, offline single binary) is a natural extension of the
  existing `pre-commit` tier for enforcing controlled-vocabulary tags and banning
  meta-commentary — but requires authoring a custom style.

---

### 7.1 Ownership: who may change a fact

#### GitHub CODEOWNERS

- **What:** a `CODEOWNERS` file mapping gitignore-style path patterns to
  usernames/teams; GitHub auto-requests those owners as PR reviewers when matching
  files change, and branch protection can *require* their approval to merge.
  <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners>
- **Why it fits this wiki:** maps directly onto the folder split. One line per folder
  (`concepts/ @curator-a`, `practices/ @curator-b`, per-topic subtrees as the wiki
  grows) gives every area a named reviewer **without touching page frontmatter** —
  ownership metadata lives in one file, not per-page, which is blast-radius discipline
  applied to governance itself.

Concrete details and gotchas:

| Aspect | Detail |
|---|---|
| File location (first found wins) | `.github/CODEOWNERS`, then repo root, then `docs/CODEOWNERS` |
| Pattern format | `path/pattern @username` or `path/pattern @org/team-name` |
| Pattern semantics | gitignore-style wildcards; `docs/*` is non-recursive, `docs/**` recurses; paths are case-sensitive |
| Precedence | **last-match-wins** — later lines override earlier ones for the same path; put most-specific rules last |
| Multiple owners | list on the same line; with required branch protection, approval from **any one** listed owner satisfies the check (not all) |
| Draft PRs | do **not** trigger owner review requests — owners are pinged only once the PR is marked ready |
| Invalid lines | **silently skipped**; repo settings expose an error list to check |
| Owner write access | owners must have explicit write access or the rule is ineffective |
| File size cap | **3 MB** — oversized files silently fail to load |
| Not supported | `!` negation and `[ ]` character-ranges (unlike real `.gitignore`) |

- **Cost/licensing:** free for public repos. Branch-protection required-reviews and
  multi-team rulesets require a **paid tier for private repos**. CODEOWNERS itself is a
  config file, not a licensed product.
- **Maturity:** GitHub core platform feature, stable syntax for years.
- **Verdict:** **adopt.** Put a `CODEOWNERS` at the wiki root mapping `concepts/`,
  `practices/`, `references/`, `maps/` (and per-topic subfolders later) to named
  curators; combine with required-reviewer branch protection so no page merges without
  its owner's sign-off. Does **not** violate the markdown-as-truth constraint —
  `CODEOWNERS` is a plain text file in the repo.

#### GitLab Code Owners

- **What:** GitLab's equivalent, with richer semantics — named **sections** (e.g.
  `[Documentation]`), optional sections, and per-section approval-count rules, enforced
  via protected-branch "Code Owner approval".
  <https://docs.gitlab.com/user/project/codeowners/>
- **Why it might matter:** only if the wiki's git host ever moves to GitLab (or a
  self-hosted mirror). Sections let one file express both folder ownership (`concepts/`
  → curator A) and named review *classes* (`[Schema Changes]` requiring the schema
  maintainer specifically).

| Aspect | Detail |
|---|---|
| File location (first found wins) | `./CODEOWNERS`, `./docs/CODEOWNERS`, `./.gitlab/CODEOWNERS` |
| Approval semantics | can require **multiple distinct** Code Owner sign-offs per section (vs GitHub's one-of-many) |
| Sections | named `[Section]` groups; can be optional; integrate with separately-defined approval rules for expertise areas not tied 1:1 to paths |
| Bypass risk | users with "Allowed to push and merge" bypass the whole mechanism — protecting the branch is **not** sufficient; permissions must also be locked down |
| Enforcement gate | target branch must have "Code Owner approval" explicitly enabled under protected branches |
| Tier requirement | **GitLab Premium or Ultimate** (self-managed, Dedicated, or GitLab.com); Free tier does **not** support enforced Code Owner approval |

- **Verdict:** **evaluate only if migrating off GitHub.** Otherwise redundant with the
  GitHub entry; the transferable idea is the pattern itself (path → named reviewer,
  enforced via branch protection). Paid-tier requirement is a real adoption blocker
  unless already on Premium/Ultimate.

#### Wikipedia: Ownership of content policy (the rejected model)

- **What:** a core Wikipedia policy — **no editor owns an article** regardless of
  authorship or edit-count; all content is subject to collaborative consensus editing,
  and reverting another's edit is legitimate only when backed by a policy-based
  rationale, not by asserting authority.
  <https://en.wikipedia.org/wiki/Wikipedia:Ownership_of_content>
- **Key points:** "No one has the right to act as if they own a particular article"
  (even subject-matter authority confers no content control); legitimate reversion
  requires citing policy/prior discussion/concrete prose problems (repeated no-reason
  reverts are the diagnostic for a violation); disputes escalate to the talk page for
  consensus, not to a designated final-say individual.
- **Context:** this is a governance model **calibrated for millions of anonymous,
  unvetted editors** — an adversarial-trust environment.
- **Verdict:** **avoid as a direct model.** This wiki is small-team, trusted-
  contributor — the opposite of Wikipedia's open-editing-at-scale problem. Naming
  explicit page/folder owners (CODEOWNERS-style) is the correct call here. Cite this
  policy only as the **contrast case** explaining *why* gatekeeping is appropriate at
  this wiki's scale.

**The ownership axis, summarized:**

| Source | Ownership model | Fit for this wiki |
|---|---|---|
| GitHub CODEOWNERS | named owner per path, enforced via branch protection | **adopt** |
| GitLab Code Owners | named owner + sections, paid-tier enforced | evaluate only if on GitLab |
| Confluence Owner | person property per page, admin-settable | steal the field idea (§7.2) |
| Notion Owner | first-class person property per page | steal the field idea (§7.2) |
| Wikipedia | **ownerless** consensus editing | **reject** — the anti-model |

---

### 7.2 Staleness: when a fact is presumed out of date

This is the one concrete **gap** versus the current schema: `status: stale` exists but
nothing *triggers* the transition. Confluence and Notion independently converge on the
same fix — an explicit verification/expiry field plus an automatic trigger, not
eyeballing `updated:` dates.

#### Confluence Verified Pages + expiry automation

- **What:** a Confluence Cloud feature — a page owner or space/site admin marks a page
  "Verified" with an optional expiry; when verification lapses (time passes or the page
  goes untouched), Confluence auto-un-verifies it and can email the owner to re-review
  via a built-in Automation template.
  <https://community.atlassian.com/forums/Confluence-articles/Verified-Pages-Now-Available-in-Confluence/ba-p/2664827>
- **Key mechanics:** only the page owner or an admin can set/remove Verified (a
  controlled, not crowd-writable, signal); the Automation template targets pages that
  are Verified **and** inactive — un-verifies them and emails the owner, closing the
  loop without a human auditor; verification is a distinct boolean+expiry, **not**
  derived from last-edited timestamp alone.
- **Availability:** confirmed "actively rolling out to all Confluence customers" —
  **Confluence Cloud only**; no Server/Data Center confirmation found. *(open
  question — see §7.5.)*
- **Constraint / conflict flag:** Confluence itself owns its content store, so
  **adopting the product would violate the markdown-as-truth constraint**. Only the
  *mechanic* is portable.
- **Verdict:** **steal-the-idea, don't adopt Confluence.** The mechanic (owner-set
  verification + automatic time-based un-verify + notify) is directly implementable
  over frontmatter `status` + `updated` + a `review_by` field, giving the schema's
  existing staleness signal a real trigger.

#### Notion Wiki verification + ownership properties

- **What:** Notion's wiki-type databases carry four default properties — Owner
  (person), Last edited date, Tags, and a **Verification** property with an expiry date
  — plus a Create/Update page API to set verification programmatically, and a separate
  @-mention-date reminder mechanism in comments.
  <https://www.notion.com/help/guides/tips-to-keep-your-teams-notion-pages-up-to-date>

| Notion property | Type | Analogue in this wiki's frontmatter |
|---|---|---|
| Owner | person | proposed `owner:` field |
| Verification | verified / unverified / **expired** (end-date past auto-demotes) | proposed `review_by:` + `status:` |
| Tags | multi-select (controlled vocab) | existing `tags:` |
| Last edited time | timestamp | existing `updated:` |

- **Key points:** verification is a **three-state** model (verified/unverified/expired),
  not a boolean; it's exposed via API (Create/Update page endpoints) so an external
  script could drive an analogous field — meaning this wiki's own tooling could set it;
  Owner is first-class and distinct from last-edited-by; the reminder mechanism
  (@-date in a comment) is separate from the Verification property's own expiry
  notification.
- **Plan gating:** Last edited time / Created time / Created by / Last edited by
  properties are available on Personal Pro, Team, and Enterprise plans (per Notion's
  database-properties doc) — irrelevant since the wiki isn't hosted on Notion.
- **Verdict:** **steal-the-idea for frontmatter.** A second confirming data point
  (alongside Confluence) that **owner + verification-expiry + tags-as-controlled-
  vocabulary** is a converged industry pattern. This wiki is structurally *closer* to
  Notion's model than to free-text wikis — it already has tags and status/updated; the
  missing pieces are an explicit `owner:` and a `review_by:` expiry date.

#### MADR — YAML frontmatter as the place for this metadata

- **What:** the MADR (Markdown Architectural Decision Records) spec's own decision
  record (0013) explaining why it keeps decision metadata in YAML frontmatter rather
  than prose.
  <https://adr.github.io/madr/decisions/0013-use-yaml-front-matter-for-meta-data.html>
- **Key points:** frontmatter shortens the document body and eases tool automation over
  metadata; the flagged downside is **no standardized rendering of YAML frontmatter
  across Markdown parsers**, and status-field values can carry false precision; MADR's
  recommended minimal set is `status`, `decision-makers`, `date` — a smaller set than
  this wiki's `type/tags/status/source/related`, useful as a floor/comparison.
- **Context:** MADR dogfoods ADRs about its own template design — page 0013 is one
  numbered decision in its self-hosted ADR log at <https://adr.github.io/madr/>.
- **Constraint:** none — open template spec (CC0-style OSS convention), free to
  reference.
- **Verdict:** **steal-the-idea for a possible future addition.** None of the existing
  fields need to change, but if a `review_by:`/expiry field is added (per Confluence/
  Notion above), MADR's own trade-off writeup is the **citable rationale** for keeping
  it in frontmatter rather than growing prose fields.

**The staleness axis, summarized:**

| Source | Staleness signal | Trigger | Portable to markdown+lint? |
|---|---|---|---|
| Confluence Verified Pages | boolean + expiry | auto un-verify + email on lapse/inactivity | yes — cron/CI or `wiki-lint` over `review_by` |
| Notion Verification | 3-state + expiry date | end-date past → auto-expired; API-settable | yes — script sets frontmatter field |
| MADR | `status` field | none (manual) | already the model; rationale to cite |
| This wiki today | `status: stale` | **none — the gap** | fix: add `review_by:`, flag in `wiki-lint` |

---

### 7.3 Taxonomy & process precedents

#### Diátaxis — the closed-taxonomy precedent

- **What:** a documentation framework asserting exactly **four** content types —
  tutorial, how-to guide, reference, explanation — each on a distinct axis of
  (action vs cognition) × (study vs work), so a page's purpose is unambiguous from its
  type alone. <https://diataxis.fr/start-here/>
- **Axis mapping:** tutorials + explanation serve *study*; how-to guides + reference
  serve *work*. Tutorials + how-to guides inform *action*; reference + explanation
  inform *cognition*.
- **Key discipline:** four types only — the core discipline is **refusing to add a
  fifth**. The framework explicitly disclaims formal governance ("You can do what you
  like with Diátaxis… there is no exam") — it is a content taxonomy, not a review-
  process spec. Recommended adoption is incremental (one improvement at a time), not a
  big-bang restructure. No prescribed frontmatter, tags, or reviewer roles are defined
  by Diátaxis itself.
- **Verdict:** **steal-the-idea — no action needed.** This wiki already has its own
  closed taxonomy (concept/practice/reference/source/map); Diátaxis is the *same move*
  (a small closed set, no inventing new types) applied to end-user docs. It **confirms**
  the design choice rather than adding mechanics. Do **not** swap in Diátaxis's four
  types — tutorial/how-to/reference/explanation don't fit a personal/team knowledge
  base the way the existing five do.

#### The Good Docs Project — template contribution workflow

- **What:** an 8-phase, role-gated contribution pipeline for merging documentation
  templates into a shared OSS repo.
  <https://gitlab.com/tgdp/templates/-/blob/main/CONTRIBUTING.md>
- **The 8 phases:** Join Community → Adopt Template → Research → Draft Deliverables →
  Community Feedback → Editorial Review → Merge Request → Chronologue (usability)
  Testing.
- **Roles:** templateer (any contributor) · working group lead (schedules review, the
  required gate to advance phases) · mentor/buddy (assigned to new contributors) ·
  editorial team (final style/structure/completeness check, **distinct** from the
  content check) · repository maintainer (final merge authority).
- **Key gates:** you may only advance to Merge Request **after** the working group lead
  approves the draft (sequential, not parallel review); merge requires **at least one**
  template-repo maintainer approval (single-approval, not consensus); drafting happens
  in **Google Docs**, converted to Markdown only at the Merge Request phase — content
  review and format review are deliberately **decoupled** stages; substantial post-merge
  revisions **restart the entire 8-phase pipeline**. Definition of done bundles five
  artifacts (template file, template guide, process doc, resources file, usability
  example).
- **Verdict:** **steal-the-idea, don't adopt wholesale.** The 8-phase pipeline is too
  heavy for a small team wiki, but the **split between content-correctness review and
  structural/style review** as two distinct checks is worth keeping as a lint-then-merge
  two-step even at small scale — and it independently corroborates the tier split in
  §7.4.

#### GitLab documentation Single Source of Truth (SSoT) statement

- **What:** GitLab's style guide states as **policy**: "The GitLab documentation is the
  SSoT for all product information related to implementation, use, and troubleshooting"
  — one canonical docs tree declared authoritative over any other internal notes/wikis/
  tribal knowledge. <https://docs.gitlab.com/development/documentation/styleguide/>
- **Key point:** SSoT is a **policy statement, not a technical mechanism** — it doesn't
  prevent duplication, it gives a **tie-breaker**: when two sources conflict, the
  declared SSoT wins. The fetched style-guide page covers writing/grammar/formatting but
  explicitly does **not** define the review/approval workflow (approvers, tech-writer
  sign-off, SLAs) — that lives in GitLab's handbook, behind an auth wall. *(open
  question — see §7.5.)*
- **Verdict:** **adopt the policy-statement pattern.** Add an explicit one-line SSoT
  declaration to `wiki/_schema.md`. The CLAUDE.md prime directive (blast-radius, one-
  canonical-fact) already states the *substance*, but not as a single **citable
  declarative sentence** a contributor can point to when resolving a duplication
  dispute.

---

### 7.4 Convention enforcement: Vale prose linter

- **What:** an open-source, offline, single-binary (Go) prose linter checking
  Markdown/AsciiDoc/reStructuredText/HTML against configurable style rules (banned
  words, sentence length, capitalization, vocab lists), driven by a `.vale.ini` config
  and YAML rule files organized into "Styles" folders. <https://vale.sh/>
- **Why it fits:** a concrete mechanism to enforce this wiki's conventions
  programmatically beyond the existing pre-commit dead-link/markdown-style checks. A
  custom Vale style could:
  - flag banned near-synonym tags / enforce the controlled-vocabulary tag list from
    `_schema.md`,
  - catch **meta-commentary language** (references to tickets/task IDs) that CLAUDE.md
    forbids,
  - all as a **CI/pre-commit gate** rather than manual review — the same integration
    point the repo's existing `pre-commit` hook already uses.

| Aspect | Detail |
|---|---|
| License | **MIT** — free, self-hosted/offline, no cost or lock-in |
| Architecture | single Go binary, **no runtime dependencies**, cross-platform (macOS/Windows/Linux) |
| Config | single `.vale.ini` at repo root defining `StylesPath` + which styles/rules apply to which file globs |
| Rules | plain YAML — no code/plugin compilation needed |
| Ready-made styles | Microsoft, Google, community packages ship out of the box |
| Vocabulary | paired `accept.txt` / `reject.txt` word-list files per vocab directory |
| Integration | CLI into git pre-commit hooks or CI (GitHub Actions etc.) |
| Distribution | standalone binary, Docker image, editor extensions (VS Code etc.) |
| Adoption | 5.5K+ GitHub stars, 8M+ downloads, 2M+ Docker pulls, 50+ contributors (per vale.sh) |
| Production adopters | Microsoft, AWS, GitLab, Cloudflare, Red Hat, Datadog, Docker, Grafana Labs |

- **Constraint fit:** runs fully offline/locally, so it satisfies the "no third-party
  *service* dependency" constraint — it adds a **Go-binary tool** to the pre-commit
  config (acceptable, since pre-commit hooks already pull in non-Python tools). It does
  **not** touch the markdown-as-truth constraint — it only reads the files.
- **Gotcha:** **no ready-made style covers a personal-wiki schema** — adopting Vale for
  this wiki's specific rules (controlled-vocab tags, meta-commentary ban) requires
  **authoring a small custom Vale style in YAML**. That authoring cost is the whole
  decision.
- **Verdict:** **evaluate.** A natural extension of the existing `pre-commit` lint tier
  (currently dead-link + markdown-style per CLAUDE.md) to also enforce controlled-
  vocabulary tags and ban meta-commentary phrasing. Worth a spike once a concrete list
  of bannable phrasings exists; not urgent while the wiki is single-author.

**Where Vale sits in the existing two-tier lint model:**

| Tier | Tool today | Checks | Vale's place |
|---|---|---|---|
| Syntactic (hook) | `pre-commit` (md-dead-link-check, markdown-style) | dead links, markdown formatting | **add Vale here** — vocab + banned phrasing |
| PR review (missing middle) | — | substantive correctness | CODEOWNERS required review (§7.1) |
| Semantic (agent) | `wiki-lint` skill | orphans, dangling links, contradictions, near-duplicates, **staleness** (`review_by`) | unchanged |

---

### 7.5 Gaps, open questions, and the novelty note

- **Open (could not confirm):** GitLab's technical-writing review-tier/SLA specifics —
  `handbook.gitlab.com/handbook/product/ux/technical-writing/workflow/` sits behind an
  auth-gated redirect; not reported from memory. Retry via a different fetch path or a
  cached mirror if the detail matters.
- **Open:** whether Confluence's Verified-Pages **automation template** is available on
  Server/Data Center or Cloud-only — **only Cloud confirmed**.
- **Treat as illustrative, not standard:** the "12-month sunset / 90-day audit" review-
  cadence numbers cited in some secondary discussion came from a marketing blog
  (AFFiNE), **not a primary spec** — use as an industry-convention illustration only,
  not a verified standard, if precision matters.
- **Novelty note (important):** **nobody documents a CODEOWNERS-equivalent specifically
  for a personal knowledge wiki** (concept/practice/reference/source/map schema, atomic
  markdown pages, wikilinks, inbox staging lane). Every governance source found targets
  either large OSS docs repos (GitLab, Good Docs Project) or SaaS team wikis
  (Confluence, Notion). **The team-conventions practice for this specific wiki shape is
  itself the novel synthesis point** — the sources above are analogies to adapt, not
  off-the-shelf fits.

---

### Recommendation for this cluster

For a cloud-hosted, team-shared, markdown-as-truth MCP wiki, adopt governance in this
priority order — all of it lives in the repo as plain files, so none of it threatens
the canonical store:

1. **Adopt now — `CODEOWNERS` at the wiki root** (GitHub). One line per top-level
   folder (`concepts/`, `practices/`, `references/`, `maps/`), per-topic subtrees as
   the wiki grows. This is the single highest-leverage, lowest-blast-radius move: one
   file expresses all ownership, and it slots straight into GitHub's required-reviewer
   branch protection. Cost note: required reviews on a *private* repo need a paid tier.

2. **Adopt now — an explicit SSoT sentence in `wiki/_schema.md`** (GitLab's phrasing
   precedent). Near-zero effort; turns the implicit blast-radius directive into a
   citable tie-breaker for duplication disputes.

3. **Adopt soon — `owner:` + `review_by:` frontmatter fields**, with `wiki-lint`
   flagging pages past `review_by` (the Confluence/Notion converged pattern; MADR is
   the rationale for keeping it in frontmatter). This closes the one real schema gap:
   `status: stale` finally gets an automatic trigger. Given the wiki's small scale and
   agent-run lint model, **no cron/CI is needed** — the agent-driven `wiki-lint` pass is
   the trigger.

4. **Evaluate — Vale in the `pre-commit` tier** for controlled-vocabulary tags and
   banned meta-commentary. MIT, offline, fits the existing hook integration point, but
   gated on authoring a custom style; do a spike once a concrete bannable-phrasing list
   exists. Not urgent while single-author.

5. **Steal-the-idea only (no adoption):** Diátaxis (confirms the closed-taxonomy choice,
   no action), the Good Docs Project's content-vs-style review split (already mirrored by
   the two-tier lint model), Confluence/Notion products (borrow the field design, never
   the store — adopting either as canonical would violate the markdown-as-truth
   constraint).

6. **Reject as a direct model:** Wikipedia's ownerless-consensus policy — cite it only
   as the contrast case that justifies named ownership at this wiki's small, trusted-
   team scale.

7. **Defer entirely:** GitLab Code Owners (only relevant on a host migration; paid-tier
   enforcement is a blocker).

Net: the ownership and SSoT pieces are cheap, additive, and file-native — do them first.
The staleness fields are the one genuine capability upgrade. Everything else is either
already satisfied by existing structure or a "wait for a second human contributor"
concern.
