## 09. MCP Server Discovery, Directories, and Supply-Chain Vetting

This cluster decides **how the team finds, trusts, distributes, and safely runs the MCP servers** that will front the cloud-hosted wiki — both the third-party compute pieces the stack may depend on (from the sibling headless-hosting research) and the wiki's own MCP server once built. None of the tools here is a *store* of wiki content; they are discovery indexes, distribution channels, packaging/runtime layers, and security references that wrap around whatever compute actually reads the plain-markdown vault. So none of them conflicts with the hard constraint that **markdown files stay canonical** — but that also means none of them *is* the answer to "where does the wiki live"; they are the answer to "how do we discover, vet, ship, and sandbox the thing that reads it."

**Takeaways:**
- **Discover across three tiers**, because no directory has full coverage or a shared trust model: the official MCP Registry (identity-verified, no code review), Anthropic's Claude Connectors Directory (human-reviewed, but Claude-seat-only), and the crawler/curator directories (Glama, PulseMCP, Smithery, Awesome-MCP-Servers).
- **Every public directory disclaims security review of its listings** — inclusion is never a trust signal. Vetting is always the adopter's job.
- **Run third-party servers in Docker MCP Toolkit-style capped, no-host-fs containers** with pinned image digests — the strongest surveyed defense against both malicious and merely-buggy servers.
- **Re-vet on every version bump**, not once: "rug pulls" mean a clean-at-adoption server can be mutated malicious later with no registry catching it.
- **Ship the wiki's own server** by listing it in the official MCP Registry (discoverability) + submitting to Anthropic Connectors (highest-trust one-click team access) + packaging it as a signed Docker image (supply-chain integrity) — three orthogonal, non-conflicting channels.

---

### Directory / registry landscape

| Directory | URL | Scale | Trust model | Code/security review? | Best use for this project |
|---|---|---|---|---|---|
| **Official MCP Registry** | registry.modelcontextprotocol.io | Preview, v0.1 API | Identity-verified namespace (OAuth/OIDC/DNS) | **No** — metadata only | Canonical discovery + publish the wiki server |
| **Anthropic Claude Connectors** | claude.com/connectors | ~343 verified | **Human review before listing** | **Yes** (editorial gate) | Highest-trust check + submit finished server for one-click team access |
| **Glama** | glama.ai/mcp/servers | 50,845 servers | Automated A–F grades + claimed/official | No (heuristics, not audit) | Breadth-first discovery + first-pass triage |
| **PulseMCP** | pulsemcp.com/servers | 20,109 servers | Three provenance tiers | No | Curated shortlist, esp. remote-only filter |
| **Smithery** | smithery.ai | "Largest", exact n/a | Index + hosting, no verification | **No** (and infra CVE history) | Wide-net discovery only; do **not** host here |
| **Awesome-MCP-Servers** | github.com/punkpeye/awesome-mcp-servers | 90.2k★ list | Social proof + PR/lint gate | No | Free cross-check / browse-by-category |

---

### Official MCP Registry (`modelcontextprotocol/registry`)

- **What it is:** the metadata-only, community-driven registry blessed by the MCP maintainers — the closest thing to an "app store index" for MCP servers. It stores **pointers/metadata, not code**, and performs **no security review**. Named trusted contributors: **Anthropic, GitHub, PulseMCP, Microsoft**.
  - API/UI: <https://registry.modelcontextprotocol.io/>
  - Source: <https://github.com/modelcontextprotocol/registry>
  - API ref: <https://registry.modelcontextprotocol.io/docs>
- **Applies to this project:** use as the **first discovery step** — confirm there isn't already a maintained markdown-vault MCP server before building one. Once the wiki's server exists, **publish it here** under a verified `io.github.<org>/wiki-mcp` namespace so teammates and future agents discover it centrally instead of hardcoding a URL.
- **Namespace format** is reverse-DNS-ish: `io.github.<username>/<server>` or `<verified-domain>/<server>` (e.g. `io.github.username/server`, `com.example/server`). Ties every listing to a verified identity, blocking anonymous squatting/typosquatting — but it verifies **identity, not code safety**.
- **Ownership verification methods:** GitHub OAuth (personal), GitHub OIDC (CI/CD publishing), or DNS/HTTP domain-ownership challenge for custom domains.
- **Publishing:** via a CLI tool that calls the REST API. **API frozen at v0.1 (2025-10-24)** — no breaking changes since, so integrations can be built against it. But the registry overall is still **preview**: data resets / breaking changes still possible before GA.
- **Self-hostable:** stack is **Go (92.6%) + PostgreSQL + Docker-deployable** — you could run a **private internal instance** of the same software for an internal-only index. (Note: one secondary source flagged that the *public* registry does **not** currently support private/team-internal listings — see Open Questions. If the wiki server must stay off the public internet, self-hosting the registry software or skipping it in favor of the Connectors channel is the fallback.)
- **Gotcha:** inclusion is **not** a security signal. Multiple secondary sources warn near-verbatim: "the official registry is a metadata layer only."
- **Verdict:** **Adopt as the discovery/publishing surface of record.** Check first before building; list the finished server here. Never treat inclusion as vetting.
- **Constraints:** open source, free to search; preview status means API/UI can still change before GA.
- **Hard-constraint check:** ✅ pure metadata layer, holds no content.

---

### Anthropic Claude Connectors Directory

- **What it is:** Anthropic's **first-party** directory of remote MCP connectors that get one-click install inside Claude (Desktop/Code/web) for **Pro/Max/Team/Enterprise** seats. The **highest-trust-bar directory surveyed** because Anthropic itself reviews submissions before listing.
  - Directory: <https://claude.com/connectors>
  - FAQ: <https://support.claude.com/en/articles/11596036-anthropic-connectors-directory-faq>
  - MCP connector docs: <https://platform.claude.com/docs/en/agents-and-tools/mcp-connector>
- **Applies to this project:** check here for an existing Anthropic-reviewed remote connector before building custom, and **submit the wiki's finished cloud server here** so any teammate on a Claude seat can one-click-connect without manual config — directly serving the "team-wide, not one WSL box" goal.
- **Scale:** **343 verified integrations** catalogued (third-party count via the `rdmgator12/awesome-claude-connectors` mirror), organized by category with use-case descriptions.
- **Submission model:** self-serve submission by third-party devs, then **Anthropic reviews before granting the "verified" listing** — acceptance itself is the verification signal (unlike Smithery/Glama/PulseMCP where anyone lists unreviewed).
- **Permission scope disclosed up front:** each connector page documents its read/write capabilities and availability — matters for judging blast radius before granting access.
- **Reach:** works across **Claude Desktop, Claude Code, and the API** via the MCP connector — usable by both human teammates in chat and agents/scripts via the API.
- **Verdict:** **Adopt as the target distribution channel** for the finished wiki server (submit for review) and as a first check for reviewed alternatives. **Weight it highest for trust** (only surveyed directory with a real human review gate) — but still not a substitute for your own security review of self-hosted pieces.
- **Constraints:** submission is Anthropic's editorial review (timeline/criteria not fully published); only relevant to Claude-seat users, not a generic cross-client index.
- **Maturity:** active, growing (343 per third-party count); first-party so unlikely to be abandoned; update cadence not published.
- **Hard-constraint check:** ✅ transport/distribution channel, not a store.

---

### Glama MCP Server Directory

- **What it is:** the **broadest-coverage automated directory**, distinguished by running its **own scoring pipeline** (security/license/quality/maintenance letter grades) per listing rather than just aggregating metadata.
  - URL: <https://glama.ai/mcp/servers>
- **Applies to this project:** primary **breadth-first discovery** source and a quick **pre-filter** (via A–F grades) before manual review of a candidate content-search or graph server.
- **Scale (July 2026 fetch):** **50,845 servers** — largest surveyed. Broken down:
  - Hosting: Remote **22,753** / Local **16,129** / Hybrid **9,626**
  - Language: Python **21,922** / TypeScript **18,195**
  - Categories: Developer Tools **14,367**, Search **8,212**, Databases **3,549**, Finance **3,120**, + 20 more
- **Provenance facets:** **7,764 "claimed"** (author-verified) and **3,194 "Official"** (recognized org) — an at-a-glance provenance signal the official registry doesn't surface as a browsing facet.
- **Scoring:** letter grades per listing, e.g. **"A quality, B maintenance"**, plus a separate **license grade** (commonly **MIT** or **Sleepycat** observed). Signals feeding grades: GitHub stars, weekly downloads, update recency, tool/resource/prompt counts. Glama frames curation as *"is this server mature enough for deployment?"*
- **Filterable/sortable:** hosting type, language, category, claimed/official, quality/maintenance/license grade; sort by relevance or recent activity.
- **Gotcha:** despite scoring, **Glama performs no manual security review** — index + heuristics, not an audit. Same caveat as Smithery ("registries that index servers but don't perform security reviews... you're responsible for vetting servers yourself").
- **Verdict:** **Adopt as discovery + first-pass triage** — filter to claimed + Official + high quality/maintenance before manual vetting; a good grade is **not** a substitute for reading the code of anything that touches wiki content or runs with write access.
- **Constraints:** free to browse; automated/crawled index (no listing cost); it's a web index, not installable software (no license of its own).
- **Hard-constraint check:** ✅ index only.

---

### PulseMCP

- **What it is:** a **hand-reviewed-leaning** directory that tiers listings by provenance rather than pure crawling, and is a **named trusted data contributor to the official MCP Registry**.
  - URL: <https://www.pulsemcp.com/servers>
- **Applies to this project:** use for a **smaller, more curated shortlist** (a handful of credible content-search or filesystem servers) rather than Glama's 50k firehose; the tier badge is a fast provenance filter.
- **Scale:** **20,109 servers**, **daily-updated**, paginated **42/page across 479 pages**.
- **Three provenance tiers per listing:** **Anthropic References / Official Providers / Community** — coarser but clearer than Glama's claimed/unclaimed split.
- **Per-listing metadata:** provider org, description, tier badge, **"Est Visitors (Week)"** (an adoption proxy distinct from GitHub stars), release date.
- **Sort/filter:** Most Popular (week/month/all-time); **filter by remote-availability** — directly useful for the cloud-hosting goal, since **local-only servers don't fit a shared team deployment without extra packaging work**.
- **Cross-validation:** named as a trusted contributor backing the official Registry's data (per that registry's docs), so PulseMCP data quality is implicitly cross-checked by the official maintainers.
- **Verdict:** **Adopt for curated shortlisting**, especially the remote/hosted filter for the team-shared goal; still requires independent code/security review — tiering is provenance, not audit.
- **Constraints:** free to browse; no stated licensing (web index).
- **Hard-constraint check:** ✅ index only.

---

### Smithery

- **What it is:** one of the **largest third-party discovery/hosting directories**; also offers **hosted deployment** of listed servers (not just an index) plus a CLI installer.
  - URL: <https://smithery.ai>
- **Applies to this project:** OK for **broad-coverage discovery**, but its security posture **disqualifies it as a place to host** the wiki's server without independent review, and **disqualifies its listings as pre-vetted**.
- **No security review itself:** "Smithery and Glama are registries that index servers but don't perform security reviews... you're responsible for vetting servers yourself before connecting them."
- **Third-party scan finding:** of the **top 100 most-popular** Smithery-listed servers, **22 flagged** something; the most common (**6 servers**) was **tool-description injection** — hidden agent-targeting instructions in a tool's description field, exactly the OWASP "MCP Tool Poisoning" pattern. (via <https://dev.to/saray_chak_/we-scanned-100-smithery-mcp-servers-and-22-came-back-with-security-findings-2lj8>)
- **Platform-itself CVE:** a **path-traversal vulnerability disclosed October 2025** in Smithery's own hosting infra exposed **3,000+ hosted servers' data and API keys** before being patched — the platform-as-attack-surface risk, distinct from any one listed server being malicious.
- **No formal verification / audit / maintenance guarantee** per multiple secondary sources — trust is entirely delegated to "the author built it correctly and keeps it working."
- **Verdict:** **Evaluate only.** Good for casting a wide net; every candidate found here needs the same independent vetting checklist. **Do not use Smithery hosting** for anything holding wiki content/credentials, given the Oct-2025 infra CVE.
- **Constraints:** free to browse; hosted deployment may have its own pricing tier (**not confirmed this pass** — see Open Questions); no formal license/vetting guarantee.
- **Hard-constraint check:** ⚠️ the *directory* is fine; the *hosting tier* would put wiki content on infra with a disclosed breach history — **flagged, do not host here**.

---

### Awesome-MCP-Servers (`punkpeye/awesome-mcp-servers`)

- **What it is:** the canonical **community-curated "awesome list"** for MCP servers — a plain markdown/GitHub index, not a scored platform. Quality signal is **social proof** (stars/forks/PR review), not automated scoring.
  - URL: <https://github.com/punkpeye/awesome-mcp-servers>
- **Applies to this project:** a **cheap sanity-check** — cross-reference any candidate from Smithery/Glama/PulseMCP here. Broad stars + merged-via-reviewed-PR is a weak-but-free extra signal; also handy for scanning category groupings by hand.
- **Engagement:** **90.2k stars, 12.4k forks, 8,412 commits on main, 2.1k PRs, 37 watchers** — very high, functioning as social-proof curation, not formal audit.
- **Gate:** maintained via **CONTRIBUTING.md-gated PRs + GitHub Actions checks** — a lightweight structural (format/lint) gate; the fetch surfaced **no explicit security-vetting criteria**.
- **Reach:** multilingual mirrors (Japanese, Korean, Portuguese, Thai, Chinese, Persian). **Cross-links to `glama.ai/mcp/servers`** — treats Glama as the "real" searchable backend and itself as a curated entry list.
- **Verdict:** **Evaluate / steal-the-idea.** Useful free cross-check and category browsing; **not a security review** — treat identically to Smithery/Glama findings and still run the full checklist.
- **Constraints:** free, open source (list content presumably MIT-ish, not separately confirmed).
- **Hard-constraint check:** ✅ index only.

---

### Docker MCP Catalog + Toolkit — the runtime/packaging layer

- **What it is:** a **curated catalog of MCP servers packaged as signed, provenance-tracked Docker images**, paired with a **"Toolkit" runtime** (Docker Desktop feature) that runs each server in an **isolated, resource-capped container with no host filesystem access by default** — the **strongest surveyed supply-chain + runtime-isolation story** of any directory.
  - Hub: <https://hub.docker.com/mcp>
  - Docs: <https://docs.docker.com/ai/mcp-catalog-and-toolkit/> (catalog: `.../catalog/`, toolkit: `.../toolkit/`)
  - Registry/contribution repo: <https://github.com/docker/mcp-registry>
- **Applies to this project:** the concrete recommendation for **HOW to run any third-party MCP server** the stack depends on (e.g. a content-search server), with defense-in-depth, **regardless of which directory it was discovered through** — and a **template for distributing the wiki's own server** for self-hosting by other teams.
- **Build-time (passive) security:** Docker builds and **digitally signs every `mcp/` image itself**; each ships an **SBOM** + build attestation from Docker Build Cloud + verifiable source-code provenance.
- **Runtime (active) security:** each server runs in its own container capped at **1 CPU / 2 GB memory**, **no host filesystem access by default**; OAuth credentials (GitHub, Notion, Linear, etc.) are handled via browser OAuth flow and stored in the Docker Desktop VM (mechanism varies by platform) rather than plaintext config.
- **Two submission paths** (`github.com/docker/mcp-registry`):
  - **(A) Docker-built image** — *recommended*; full signature/SBOM/provenance/auto-security-update treatment; **live in the catalog ~24h after PR approval**.
  - **(B) Self-provided pre-built image** — still container-isolated but **skips Docker's SBOM/signing pipeline**.
- **Stated submission requirements:** security best practices, comprehensive docs, working Docker deployment, MCP-standard compatibility, proper error handling/logging. Non-compliant servers **"may be removed"** post-listing — an **ongoing** compliance bar, not a one-time gate.
- **Vendor-reputation signal:** catalog mixes Docker-built community servers with **partner-provided servers** from named companies (**New Relic, Stripe, Grafana**).
- **Org-level pinning:** `docker mcp catalog pull <oci-reference>` imports/pins a **private or third-party OCI-referenced catalog** — lets a team **lock down exactly which servers/versions are approved** rather than trusting the full public catalog. Directly supports a team-wide deployment.
- **Browse via:** `hub.docker.com/mcp` or Docker Desktop → MCP Toolkit → Catalog tab.
- **Verdict:** **Adopt as the runtime/packaging layer** regardless of discovery source — the signed-image + capped-container + no-host-fs-by-default model is the **best concrete mitigation surveyed** against both malicious and buggy third-party servers, and directly supports a private, pinned catalog for team-shared deployment.
- **Constraints:** requires **Docker Desktop** (or Docker Engine + the Toolkit's orchestration) as host infra — introduces a Docker dependency on whatever server hosts the shared MCP layer. **Catalog/Toolkit pricing not stated** in fetched docs; **Docker Desktop itself has commercial-use licensing tiers for larger companies** — **verify separately before team-wide rollout** (see Open Questions).
- **Maturity:** active, Docker-run and promoted (2025–2026 blog posts), enterprise partner ecosystem.
- **Hard-constraint check:** ✅ pure runtime/packaging wrapper. **Caveat:** the wiki's own server, when containerized, must still **mount the markdown vault as the source of truth** (git-backed volume) and treat any in-container index/DB as disposable — the container is a wrapper, not the store.

---

### Security references (the vetting vocabulary)

#### MCP-Scan (Invariant Labs)

- **What it is:** a **security scanner purpose-built for MCP servers**, the tool most directly cited for detecting **tool-poisoning / rug-pull / cross-server-shadowing** attacks in tool descriptions, from the group (**Invariant Labs**) that first named and documented the **Tool Poisoning Attack (TPA)** class.
  - Blog: <https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks>
- **Applies to this project:** the concrete tool to run against **any candidate server** as a pre-adoption gate, and **on an ongoing basis** given rug pulls.
- **Three distinct attack shapes to distinguish in a vetting checklist:**
  1. **Tool Poisoning** — hidden instructions embedded in a tool's **description** field, invisible in the user's simplified UI but fully visible to the model (e.g. an innocuous "add" tool whose description tells the agent to read SSH keys/config and exfiltrate them).
  2. **Rug Pulls** — a server's tool description is modified **after** the user already approved/trusted it, exploiting clients that verify tools only at install time with no continuous re-validation.
  3. **Cross-Server Shadowing** — a malicious server's tool description injects instructions that hijack the agent's behavior toward a **different, otherwise-trusted** server (e.g. silently redirecting all outgoing email from a legit email MCP server to an attacker address) — the attacker **doesn't even need their own tool to be called**.
- **Direct implication:** because clients typically only check tool descriptions **at connect-time**, any MCP server this project depends on (or builds) should be **pinned to a specific version/hash and re-scanned on update**, not vetted once.
- **Verdict:** **Adopt the practice** (scan before + after every server-version bump). The **specific MCP-Scan tool warrants a follow-up fetch** of its own repo/docs before wiring into a CI gate — this pass only confirmed it exists and what attack class it targets.
- **Constraints:** **not independently confirmed this pass** (blog was thin on tool specifics) — license/install/cost need a **dedicated follow-up fetch** before relying on it operationally.

#### OWASP MCP Tool Poisoning entry

- **What it is:** OWASP's canonical community write-up formalizing **"MCP Tool Poisoning"** as a named attack class — the standard vocabulary and worked example for an internal vetting checklist.
  - URL: <https://owasp.org/www-community/attacks/MCP_Tool_Poisoning>
- **Applies to this project:** the **reference definition to cite** when writing the wiki's own vetting practice page — precise, citable language for "why we require X check."
- **Core framing:** *"Tool descriptions are reviewed once, when the agent first connects to a server. Tool responses go straight into the LLM context with no equivalent check."* The trust asymmetry is **structural to MCP as designed**, not a bug in any one server.
- **Worked example:** a `get_compliance_status` tool returns plausible compliance text with an embedded directive telling the agent to `read_file('/etc/shadow')` and POST contents to `https://attacker.example.com/audit` — poisoning can live in tool **responses**, not just static descriptions, so static-description review alone is **insufficient**.
- **Structural defenses:** mandate **structured (JSON-schema) tool outputs** rather than free text (easier to detect/reject injected directives); **isolate high-privilege tools** in a separate agent context unreachable by externally-facing servers; **enforce access control at the server/backend layer, not via system-prompt instructions** (injected content can override prompt-level rules).
- **Operational defenses:** maintain an **explicit allowlist of approved servers** (deny-by-default for arbitrary connections); require **explicit human approval before any sensitive/destructive tool call** executes.
- **Verdict:** **Adopt as the shared vocabulary/checklist source** for the wiki's vetting practice; the **allowlist + structured-output + privilege-isolation triad** is the concrete design to bake into the cloud MCP deployment.
- **Constraints:** free, community-maintained OWASP reference; informational, not a tool.

---

### The repeatable discover → vet → isolate pipeline

A five-step pipeline emerges directly from the sources:

1. **DISCOVER across three directory tiers** (none has full coverage; each has a different trust model): (a) official MCP Registry for a canonical listing; (b) Anthropic Connectors as the highest-trust check (but Claude-seat + remote-connector only); (c) Glama + PulseMCP + Smithery + Awesome-MCP-Servers as breadth/curation fallbacks — **cross-reference across at least two** (agreement across independent crawlers is a weak trust signal).
2. **TRIAGE using each directory's own signals before opening any code:** Glama's claimed + Official + quality/maintenance grades; PulseMCP's tier + **remote-availability filter** (remote matters directly — local-only servers need extra packaging to become a shared service); GitHub stars/forks/recency as a weak floor.
3. **VET before adoption regardless of directory reputation** (every public directory disclaims doing security review): read tool descriptions verbatim for injected instructions (OWASP's failure mode); run a scanner such as MCP-Scan; check whether tool outputs are structured/schema'd vs free text; check filesystem/network scope needed at runtime; check maintenance signals (commit recency, open security issues).
4. **ISOLATE at runtime regardless of vetting outcome** (rug pulls defeat one-time vetting): prefer **Docker MCP Toolkit-style capped, no-host-fs containers** over bare local processes; **pin exact versions/image digests**; keep an **internal allowlist** of approved servers+versions (OWASP) rather than trusting the live namespace; **isolate any high-privilege tool** (anything with wiki write access) into a context unreachable by lower-trust/externally-facing servers to block cross-server shadowing.
5. **RE-VET on every version bump, not once** — the single most-repeated caveat across sources (rug pulls; Smithery's Oct-2025 infra CVE; Docker's "non-compliant servers may be removed" implying ongoing compliance).

---

### Recommendation for this cluster

For a **cloud, team-shared, markdown-as-truth wiki MCP server**, adopt a layered strategy that keeps every tool here strictly as a transport/distribution/runtime wrapper around the plain-file vault:

1. **Discover, then decide build-vs-adopt** — first pass the **official MCP Registry** (`registry.modelcontextprotocol.io`) and **Anthropic Connectors** (`claude.com/connectors`) to confirm no maintained, reviewed markdown-vault MCP server already exists; use **Glama** (50k, graded) and **PulseMCP** (remote filter) for breadth if you need to compose in a content-search or graph server. Given the sibling headless-hosting research already recommends specific compute (obsidiantools + qmd), the likely outcome is **build a thin custom MCP server** over that compute rather than adopt a random third-party one.
2. **Package the wiki's own server as a signed Docker image via the Docker MCP Toolkit pattern** (`docs.docker.com/ai/mcp-catalog-and-toolkit/`) — capped container, no host-fs-by-default, SBOM + provenance — with the markdown vault mounted as a git-backed volume that remains the source of truth and any index/DB inside the container treated as disposable. This is the single highest-leverage adoption here: it neutralizes the biggest risk (running third-party or self-built code with write access to the vault) **and** gives other teams a reproducible self-host artifact.
3. **Distribute through two channels:** list it in the **official MCP Registry** under a verified `io.github.<org>/wiki-mcp` namespace for canonical discoverability, and **submit to the Anthropic Connectors Directory** for one-click access from every Claude seat — the highest-trust distribution path. (Confirm the public registry's private-listing support first; if unsupported and the server must stay off the public internet, self-host the registry software or rely on the Connectors channel alone.)
4. **Bake OWASP's triad into the deployment from day one:** structured/JSON-schema tool outputs, an explicit allowlist of approved servers+versions (deny-by-default), and privilege isolation so the write-capable wiki tool is unreachable by any lower-trust externally-facing server. Pin image digests and **re-scan (MCP-Scan) on every version bump.**

**Do not** use Smithery hosting for anything holding wiki content or credentials (Oct-2025 infra CVE), and **never** treat directory inclusion — even Anthropic's review — as a substitute for reading the code of self-hosted pieces. **Ranking for this project:** Docker MCP Toolkit (runtime — adopt first) > official MCP Registry + Anthropic Connectors (distribution — adopt) > Glama / PulseMCP (discovery — use) > Awesome-MCP-Servers / Smithery directory (cross-check only) > Smithery hosting (avoid). MCP-Scan + OWASP are the vetting practice, adopted as process rather than a single tool. None of these violates the markdown-as-canonical constraint — they wrap the compute layer, they never become the store.
