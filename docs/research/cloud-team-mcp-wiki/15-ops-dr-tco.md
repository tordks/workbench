## 15. Operations, Disaster Recovery, and Total Cost of Ownership

This cluster decides how the cloud, team-shared, markdown-as-truth MCP wiki stays alive, recovers from failure, and what it costs to run per month. The governing insight is that the [prime directive](../../../CLAUDE.md) — canonical store stays plain markdown, every index is disposable — is *also* the operational and DR strategy: because the markdown lives in git (already pushed to a remote), the wiki's real data is structurally backed up before any tool is added, and "disaster recovery" collapses into "wipe the box, `git clone`, rebuild the disposable index, confirm the MCP server is healthy." Everything below is therefore either (a) a convenience layer that buys *faster* recovery of the disposable index (Litestream, restic, B2), (b) monitoring that catches the one genuinely dangerous failure mode — a silently-stale index behind a server that still looks "up" (Uptime Kuma, healthchecks.io), or (c) the cost model that decides VPS sizing and LLM/embedding token spend (Hetzner, Voyage, OpenAI, Claude, qmd's local models).

**Takeaways:**

- **Git is the primary DR mechanism, at zero incremental cost.** The markdown is safe the moment it is pushed. Losing the index is a *rebuild-time* cost, never a data-loss event. Do **not** budget for an expensive index-database replication product as if the index were irreplaceable.
- **Backup ≠ DR here.** Litestream / restic / B2 exist only to make index recovery faster than a full re-ingest — optimizations on top of an already-safe baseline.
- **Cloud hosting (€5–20/month, Hetzner) and LLM token cost (single-digit-to-low-double-digit $/month with caching + Batch) are not the same order of magnitude, and neither dominates at single-team scale.** The largest swing factor is a VPS-sizing decision: whether to hold qmd's ~2GB local models resident.
- **Embedding cost is effectively $0** at wiki-corpus scale under Voyage AI's 200M-token/month free tier.
- **Monitoring must be two distinct signals:** "is the endpoint reachable now" (Uptime Kuma) and "did last night's scheduled job actually run and succeed" (healthchecks.io). Conflating them leaves the stale-index gap open.
- **Cost is a step function keyed to volume thresholds, not a per-seat multiplier.** Going from a 3-person to a 30-person team barely moves TCO until a free-tier threshold is crossed.

---

### 15.1 Disaster recovery — the architecture-specific reframing

For a conventional app, "DR" means database-restore drills. For this wiki it does not, because the canonical data is git-versioned markdown. Restating the three DR primitives explicitly:

| Layer | What protects it | Is it data-loss-risky? | The drill that matters |
|---|---|---|---|
| Canonical markdown (`wiki/`) | Git + remote (GitHub) — every clone is a full backup | No — structurally safe | N/A (git handles it) |
| Disposable index/graph/search (obsidiantools cache, FTS5, Meilisearch, vector store) | Rebuild from markdown; *optionally* Litestream/restic for speed | No — rebuildable, never canonical | "Delete index, rebuild from `git clone` + ingest, confirm MCP healthy" |
| The server itself (VPS, container) | Re-provision + re-clone + re-ingest | No data at stake, only wall-clock RTO | "Provision fresh box → clone → rebuild index → hit health endpoint" — time this = real RTO |

**GitHub as the git-history DR baseline** (<https://github.com>): the existing remote *is* the primary backup. Git's distributed model means every clone — a teammate's laptop, a CI runner that checked it out, GitHub's servers — is a complete point-in-time-versioned copy. Cost: **$0 incremental** (it is the repo you already push). This is why the prime directive is also the cheapest DR strategy: rebuilding a lost index is compute time, not a data-loss event.

**The real disaster to drill is losing the SERVER, not the DATA.** Recommended drill script:

```
git clone <remote> fresh/
# re-run whichever index-build the chosen stack uses:
#   obsidiantools:  Vault().connect().gather()
#   qmd:            qmd ingest ...
#   Meilisearch:    JSON-ingest step
# then:
curl <mcp-server>/health          # confirm reachable
# run a known wiki-query / wiki-lint and assert expected results against a known page
```

Time this end-to-end; treat the wall-clock as the **RTO (recovery time objective)**. Recommended cadence: **quarterly full-restore drill onto a throwaway Hetzner box** (a few dollars, one hour), documented as a runbook so it is not tribal knowledge. **Open question:** who owns the drill and where the runbook lives is a process decision needing a named owner + calendar cadence (see §15.7).

---

### 15.2 Backup tooling for the disposable layer

These buy *faster* recovery than a full re-ingest. They protect the index, not the truth.

#### Litestream — continuous SQLite replication

<https://litestream.io/how-it-works/> · <https://github.com/benbjohnson/litestream> · open source (backed by Fly.io's Ben Johnson), mature multi-year project.

- **What it is:** a streaming replication *daemon* (not a server) that runs alongside a SQLite DB and continuously ships WAL pages to S3 / Azure Blob / SFTP / local files. Near-real-time, not interval-based.
- **Mechanism:** takes over SQLite's WAL checkpointing via a long-running read transaction, copies new WAL frames to a "shadow WAL" staging area, ships them to the configured replica(s). Backups are organized into **generations** (a snapshot + the contiguous WAL frames to restore from it); a new generation starts automatically if WAL continuity breaks.
- **Retention:** two-phase — periodic full snapshots at a configurable `snapshot-interval`, then a `retention` window (**default 24h**) that prunes older snapshots/WAL while always keeping ≥1 valid snapshot. "Snapshot daily, retain a week" is one config knob.
- **Restore:** `litestream restore` reconstructs the DB file from S3 even if the local file is gone entirely — this is the DR-drill primitive. Requires exactly a snapshot + all subsequent WAL frames.
- **Config extras:** replicate to multiple destinations simultaneously (e.g. S3 + local file) for redundancy in one config.
- **Cost:** no license fee; cost is 100% the storage backend (see B2, §15.3) plus negligible sidecar CPU/network. No per-request write fees on B2.
- **Applies to:** any **SQLite-backed** disposable layer — a custom FTS5 content index, Basic Memory's own index, a SQLite-backed vector store. **Does NOT apply to Meilisearch** (LMDB storage — use its own snapshot/dump), or Postgres.

> **Constraint / gotcha:** SQLite-only. This is a disposable-layer backup, never the canonical store's backup. Losing it just means a slower index rebuild from markdown — never data loss.

#### restic — encrypted, deduplicating filesystem backup

<https://restic.net/> · <https://github.com/restic/restic> · BSD-2-Clause, mature, large community.

- **What it is:** content-addressable, client-side-encrypted, deduplicating backup for arbitrary files/dirs. The standard tool for snapshotting anything git doesn't naturally version well.
- **Applies to:** an **extra** safety net for the markdown tree beyond git (git remains primary), plus large binary attachments, `.obsidian/` local state if ever retained on the server, or a raw filesystem snapshot for fast full-VM restore.
- **Dedup:** repeated snapshots of a slowly-changing markdown tree cost near-zero incremental storage.
- **DR posture:** community 3-2-1 rule (3 copies, 2 media types, 1 offsite) or 3-2-1-1 (add one offline/immutable copy to survive ransomware). Maps directly to "wiki markdown lives on the server + git remote + restic snapshot to object storage."
- **Commands:** `restic backup <path>` / `restic restore <snapshot> --target <path>` are the DR-relevant pair; `restic check` validates repository integrity (run weekly via cron).
- **Discipline:** community guidance — *"a backup you've never restored is just hope."* Best practice: snapshot current state before any restore-test so a bad restore can itself be rolled back.
- **Backend:** first-class Backblaze B2 support (§15.3, ~$6/TB/month). No license cost.

> **Named operational risk:** the restic password is the **sole** key to the repository — losing it means the backup is unrecoverable. Store it in a secrets manager, not a sticky note. Single point of failure for the encrypted repo.

**Litestream vs restic — when to use which:**

| | Litestream | restic |
|---|---|---|
| Target | Live SQLite index (continuous) | Files/dirs (point-in-time snapshots) |
| Cadence | Near-real-time WAL streaming | Scheduled `restic backup` runs |
| Best for | The disposable SQLite index layer | Markdown belt-and-suspenders + non-git state + binaries |
| Encryption | Via backend | Client-side, built in |
| Key risk | None beyond backend | Password loss = unrecoverable |
| License | Open (ISC-adjacent) | BSD-2-Clause |

#### Backblaze B2 — the backup storage backend

<https://www.backblaze.com/cloud-storage/transaction-pricing> · established commercial S3-compatible object storage, priced well below AWS S3.

- **Storage:** **$0.006/GB/month (~$6/TB/month)** — lowest confirmed per-GB rate among major S3-compatible providers as of mid-2026.
- **Egress:** **free up to 3× the monthly average storage volume**; unlimited free egress via partnered CDNs/compute (e.g. Cloudflare); direct egress beyond the free allowance is $0.01/GB. A DR restore of a multi-GB wiki fits inside the free ceiling even on a monthly cadence.
- **Free tier:** first **10 GB** of account storage free outright — enough to trial the whole backup pipeline at $0 before committing.
- **API:** **no charge for `b2_upload_file`** — write-heavy continuous replication (Litestream) accrues no per-request PUT fees the way S3 can. S3-compatible API; both Litestream and restic support it natively, no adapter code.
- **Larger tiers (irrelevant at wiki scale):** B2 Reserve (~35% cheaper, multi-TB commitment); B2 Overdrive ($15/TB/month, unlimited egress, PB-scale).
- **Realistic bill:** a full wiki (markdown + rendered indexes + N historical restic snapshots) totals low single-digit GB even for a large multi-team wiki → **backup storage cost is sub-$1/month in practice** (well under $1–5/month regardless of provider).

> **Constraint:** commercial (not FOSS), but pay-as-you-go with no minimum at this scale. Lock-in risk is low — both Litestream and restic treat it as a generic S3 target, so swapping providers is a config change, not a re-architecture.

---

### 15.3 Monitoring — two distinct signals

The most operationally dangerous failure mode for this architecture is **a stale or broken index behind a server that still LOOKS "up."** Endpoint pollers cannot see it; cron-completion monitors can. Use both.

#### Uptime Kuma — "is the endpoint reachable right now?"

<https://github.com/louislam/uptime-kuma> · MIT, self-hosted, very large community, stable.

- **What it monitors:** HTTP/HTTPS URLs, TCP ports, HTTP(S) JSON queries (hit an MCP server's `/health` endpoint — qmd's daemon mode exposes one), ping, DNS records, Docker containers directly.
- **Notifications:** Slack-compatible webhooks, Discord, email, Telegram, generic webhooks, SMS gateways — the practical team-ops set.
- **Status page:** ships out of the box — useful for a genuinely team-wide wiki where multiple consumers want a single availability glance without dashboard access.
- **Deployment:** one container — official Docker image, **default port 3001**, single volume for its own SQLite state. `docker run` with the official image. TS/Vue frontend + Node backend (same ecosystem as qmd's Node daemon, easing ops if the team already runs Node).
- **Cost:** free/MIT, zero licensing regardless of monitor count (unlike UptimeRobot / Better Uptime / Pingdom).

> **Constraint / irony:** self-hosted only, no managed SaaS tier — the team must keep Uptime Kuma itself alive, its own small DR concern. Mitigate by treating its data dir as another Litestream/restic target, or accept that losing monitoring *history* is low-stakes.

#### healthchecks.io — "did last night's scheduled job actually run and succeed?"

<https://healthchecks.io/pricing/> · dead-man's-switch / cron monitoring; BSD-licensed core, self-hostable, or hosted SaaS. Long-running, actively maintained.

- **Model:** the monitored job pings a unique URL at start/success/fail; healthchecks.io alerts the moment a scheduled ping is late or missing. Matches "did the index rebuild run and succeed" — which uptime pollers cannot cover, because there is no long-running endpoint, only a "did it run on time" signal.
- **Covers:** index-rebuild jobs, nightly Litestream snapshot verification, restic backup runs, DR-drill reminders, lint cron.
- **Free Hobbyist tier:** **20 checks, 3 team members** — comfortably covers the wiki's full cron surface (backup, rebuild, drill-reminder, lint) at $0.
- **Paid:** Business **$20/month** (100 checks, 10 members); Business Plus **$80/month** (1000 checks) — unlikely to be reached for one wiki.
- **Self-host:** BSD source on GitHub — removes the third-party dependency for the team's own DR alerting at the cost of one more service to run.
- **Discount:** Business plan is **free for open-source projects and nonprofits** — relevant if the wiki tooling itself is open-sourced.

**Monitoring split — the gap conflation would leave:**

| Signal | Tool | Question answered | Misses |
|---|---|---|---|
| Endpoint reachability (always-on poll) | Uptime Kuma | "Is the MCP server up right now?" | Silent index-rebuild failure (server up, index stale) |
| Scheduled-job health (ping on completion) | healthchecks.io | "Did last night's rebuild/backup run?" | Live request-path outages |

Both are free/near-free at this scale. Using only an uptime poller leaves the stale-index gap — the most dangerous failure mode — unmonitored.

---

### 15.4 The content-query cost tradeoff — local models vs hosted APIs

This is the one genuine cost *decision* in the cluster. It is, per the cross-cutting note, **a VPS-sizing decision wearing an embedding-cost costume.**

#### qmd local embedding/rerank models (the local side)

<https://github.com/tobi/qmd> · MIT (free). ~2GB resident GGUF models in `qmd mcp --http --daemon` mode (BM25 + vector + LLM-rerank), per the [prior single-machine research](../headless-wiki-hosting.md).

- **Per-query cost:** **$0** once running — the entire embedding+rerank cost is the *fixed* cost of a VPS large enough to hold ~2GB resident models + OS/process overhead.
- **The real cost it imposes:** a Hetzner CX22 (2 vCPU / 4GB) does **not** comfortably hold a 2GB-resident daemon alongside OS, MCP server, and graph/lint tooling. This realistically pushes the box up to a **CPX-class ~8GB tier** — that upsizing *is* the dollar cost of the local-model choice, not a per-query fee.
- **Structural advantage:** **data-residency / no egress** — content never leaves the box to be embedded. Matters if the wiki holds anything the team won't send to a third-party inference provider. Security/compliance tradeoff, not a pure dollar one.
- **TCO framing:** shifts cost from "pay per token forever" to "pay for a bigger VPS tier once, as a fixed monthly line." Favors local at **high** query volume across a large team; favors hosted APIs at **low-to-moderate** volume typical of a single-team wiki.

#### Voyage AI embeddings + reranking (the hosted side, default recommendation if not running qmd)

<https://docs.voyageai.com/docs/pricing> · commercial, now MongoDB-owned, current voyage-4 model line as of 2026.

| Model | Price /M tokens | Free tier | Note |
|---|---|---|---|
| voyage-4-large | $0.12 | 200M/month | |
| voyage-4 | $0.06 | 200M/month | |
| voyage-4-lite | $0.02 | 200M/month | ties OpenAI text-embedding-3-small |
| voyage-context-3 | $0.18 | 200M/month | contextual — arguably best fit for markdown+wikilinks |
| voyage-code-3 | $0.18 | 200M/month | code-specialized |
| voyage-finance-2 / law-2 / code-2 | $0.12 | only 50M/month | specialized |
| rerank-2.5 | $0.05 | 200M/month | ~$0.0025/typical query |
| rerank-2.5-lite | $0.02 | 200M/month | ~$0.001/typical query |

- **Reranking pricing formula:** (query tokens × document count) + all document tokens.
- **Batch API:** **33% discount**, 12-hour completion window — fits a nightly full re-embed after ingest; **not** applicable to interactive query-time reranking (needs synchronous response).
- **Files API storage** (batch input): $0.05/GB/month, 30-day retention.
- **Worked estimate:** a **5M-token wiki corpus** (a few thousand atomic pages) costs **$0 to fully embed once** with any current model (under the 200M free tier), and re-embedding after every edit stays free at this corpus size for the foreseeable future of a single-team wiki. Reranking a modest query volume (hundreds/day) stays **under $1/month** even on non-lite rerank.

> **Constraint:** pay-per-token beyond the free tier; requires network egress per embedding/rerank call — a departure from qmd's fully-local, no-third-party design. Now under MongoDB (platform-dependency note). The real tradeoff vs qmd is **not cost** but operational simplicity (no 2GB resident process) vs latency/network dependency + data-residency (content leaves the box).

#### OpenAI text-embedding-3-small (comparison baseline only)

<https://developers.openai.com/api/docs/models/text-embedding-3-small> · stable, widely cited.

- **$0.02/M tokens standard; $0.01/M via Batch API** (50% discount). **No free tier** equivalent to Voyage's 200M/month.
- 1,536-dimensional vectors. Input-token cost only (no output cost).
- **No native reranker** comparable to Voyage's rerank-2.5 — a full hosted replacement for qmd would still need a separate reranker (Voyage, Cohere, or self-hosted cross-encoder) to match qmd's BM25+vector+rerank pipeline.
- **Worked estimate:** a 5M-token corpus costs **~$0.10 standard / ~$0.05 batch** — trivial absolutely, but note the lack of a free tier makes **Voyage strictly cheaper** at this corpus size.

**Crossover verdict:** for a single team's realistic volume, **Voyage's free tier very likely wins on raw dollars AND avoids upsizing the VPS to hold qmd resident.** But qmd keeps content on-box and has zero external dependency once running. **Re-run this comparison if usage crosses ~10K queries/month** (multiple teams) — local models amortize better at volume, and that is roughly where hosted per-token cost starts approaching the VPS-upsizing cost it currently beats.

| Option | Per-query $ | Fixed $ impact | Data leaves box? | Reranker included? | License |
|---|---|---|---|---|---|
| qmd local | $0 | Forces ~8GB VPS tier (+€) | No | Yes (built-in) | MIT |
| Voyage AI | ~$0 (200M free) | Keeps VPS in cheap tier | Yes | Yes (rerank-2.5) | Commercial |
| OpenAI embed | ~$0.10/corpus | Keeps VPS in cheap tier | Yes | **No** — needs separate | Commercial |

---

### 15.5 Cloud hosting cost baseline — Hetzner

<https://www.hetzner.com/cloud> · established EU budget provider, a fraction of hyperscaler price. Actively priced through 2026 (including a **documented April 2026 increase** — budget the post-increase rates, not older cached figures).

- **Three product lines:** Cost Optimized (shared vCPU, cheapest — fits an I/O-bound MCP server mostly waiting on file reads + occasional LLM calls); Regular Performance (shared vCPU, better price/perf); General Purpose (dedicated vCPU — only needed if qmd's models or a heavy rebuild saturate CPU regularly).
- **All plans bundle 20TB outbound traffic + 1 IPv4** regardless of tier — bandwidth is a **non-issue** at wiki-request volumes; no surprise egress bill.

| Tier | Specs | Post-Apr-2026 price | Was | Fits |
|---|---|---|---|---|
| CX22 (Cost-Optimized) | 2 vCPU / 4GB / 40GB | ~€4.49–4.59/mo | €3.29–3.79 | MCP server + Uptime Kuma + cron scripts. **NOT** enough for qmd's ~2GB models + overhead |
| CPX11 (Regular Perf) | shared vCPU | ~€5.49/mo | €3.85 | lean stack |
| CPX22 (DE/FI) | shared vCPU | ~€7.99/mo | €5.99 | **realistic tier if running qmd local models** |
| CPX-class range | — | €7.99–10.49/mo | — | qmd-resident box |
| General Purpose | dedicated vCPU | above the above | — | CPU-bound rebuild-heavy — unlikely needed |

- **Budget:** roughly **€5–8/month** for a lean stack (MCP server + graph/lint tooling + monitoring, no local models), or **€8–20/month** if also running qmd's local embedding/rerank models on the same box.

> **Constraint:** EU-based (data-residency consideration for non-EU compliance). Pay-as-you-go, no long-term contract at this scale. Either way, **cloud hosting is a rounding error next to LLM token spend at team scale — the TCO conversation should center on token costs and the qmd-VPS-sizing decision, not the VPS bill itself.**

---

### 15.6 LLM token cost — Claude for ingest/query/lint

<https://platform.claude.com/docs/en/pricing> — this is the cost of the *agent reasoning over retrieved content*, distinct from the retrieval/embedding step (§15.4). Pricing per the bundled `claude-api` skill reference (cached 2026-06-24; the direct platform path 404'd on fetch, cross-verified against the skill's table).

| Model | Input /M | Output /M | Use for |
|---|---|---|---|
| Haiku 4.5 | $1.00 | $5.00 | cheap pre-filter / classification (e.g. "does this inbox item duplicate an existing page — yes/no") |
| Sonnet 5 | $3.00 ($2.00 intro) | $15.00 ($10.00 intro) | **default** for high-volume wiki-query + wiki-ingest |
| Opus 4.8 | $5.00 | $25.00 | reserve for wiki-lint's semantic contradiction / near-duplicate judgment |

> **Sonnet 5 introductory rate ($2/$10) expires 2026-08-31.** Flag in any cost model built before that date so the long-term budget uses the post-discount $3/$15.

**The two biggest cost levers:**

1. **Prompt caching — ~90% savings on repeated context.** Directly applies to wiki-query: a large stable system prompt (schema description + retrieved page set) recurring across a session caches the read side at **~0.1× base rate**. Cache **writes** cost ~1.25× (5-min TTL) or ~2× (1-hour TTL) base — so caching only pays off after **2 reads (5-min TTL)** or **3 reads (1-hour TTL)** of the same prefix. **Gotcha:** verify the actual hit rate via `usage.cache_read_input_tokens` in responses — a silent-invalidator bug shows as this field staying at **zero** across repeated requests with an identical prefix. Do not *assume* caching works; confirm it.
2. **Batch API — flat 50% discount** on all token usage for non-latency-sensitive work. Directly applies to **wiki-ingest's fold-inbox-into-pages step** (not interactive; runs as an overnight/scheduled batch). Limits: up to 100,000 requests or 256MB per batch, most complete within 1 hour (max 24h), results retained 29 days.

**Worked estimates at team scale:**

- **wiki-query:** a query against a cached ~10K-token retrieved-context prompt + ~200-token question, answered by Sonnet 5 with a ~500-token response ≈ **under half a cent per query once the cache is warm.** Even thousands of calls/month land **well under $10–20/month** in pure Sonnet-5 token cost — prompt caching being the deciding factor vs a much higher uncached cost.
- **wiki-ingest via Batch API:** folding a day's inbox (~20K input tokens raw notes/links + ~5K output tokens drafted pages) through Sonnet 5's batch-discounted rate ≈ **~4.5 cents/day, under $1.50/month** for daily runs.

**Model routing recommendation:** Sonnet 5 (intro rate through 2026-08-31) as default for wiki-query + wiki-ingest; Haiku 4.5 for a cheap duplicate-detection pre-filter in ingest; Opus 4.8 reserved for wiki-lint's harder semantic-contradiction/near-duplicate calls where reasoning quality outweighs cost. At single-to-modest-multi-team volumes, LLM token cost is a **single-digit-to-low-double-digit $/month** line — smaller than the VPS bill unless usage scales into a much larger org, **provided prompt caching is correctly configured (verify via `cache_read_input_tokens`, do not assume).**

---

### 15.7 Consolidated monthly TCO model (single team)

| Line item | Tool | Monthly cost | Notes |
|---|---|---|---|
| Canonical-store DR | GitHub git remote | **$0** | Primary DR — already in place |
| Cloud hosting (lean) | Hetzner CX22/CPX11 | **€5–8** | No local models |
| Cloud hosting (qmd resident) | Hetzner CPX22+ | **€8–20** | +8GB RAM for ~2GB models |
| Index backup | Litestream → B2 | **~$0** | SQLite layers only; B2 storage sub-$1 |
| Markdown/FS backup | restic → B2 | **~$0** | Belt-and-suspenders; B2 sub-$1 |
| Backup storage | Backblaze B2 | **<$1** | Low-single-digit GB; 10GB free tier |
| Uptime monitoring | Uptime Kuma | **$0** | One container, MIT |
| Cron monitoring | healthchecks.io | **$0** | Free tier: 20 checks / 3 members |
| Embedding/rerank | Voyage AI | **~$0** | 200M-token/month free tier |
| — or — local models | qmd | **$0 per-query** | Cost is the VPS upsizing above |
| LLM reasoning | Claude Sonnet 5 (+Haiku/Opus) | **$1–20** | With caching + Batch; caching is the lever |

**Net: roughly €5–20 hosting + $1–20 LLM tokens + sub-$1 storage ≈ under ~$40/month all-in for a single team**, with the swing dominated by (a) whether qmd runs locally (VPS tier) and (b) query/ingest volume driving Claude token spend.

**Per-seat economics (cross-cutting note 5):** cost is a **step function keyed to volume thresholds, not a linear per-seat multiplier.** Adding team members adds ~$0 marginal cost until volume grows enough to (a) exceed Voyage's 200M-token free embedding tier, or (b) push healthchecks.io / Meilisearch past their free-tier job/document counts. **TCO barely moves from a 3-person to a 30-person team** until a threshold is crossed — unlike typical SaaS per-seat pricing. Model the curve as a step function, not a headcount multiplier.

---

### 15.8 Hard-constraint check

Nothing in this cluster touches the canonical store:

- **Litestream, restic, B2** back up the *disposable index* and (for restic) provide a *secondary* copy of markdown — git remains the source of truth. ✅ Compliant.
- **Uptime Kuma, healthchecks.io** are observability only, no store. ✅
- **Voyage / OpenAI / qmd** produce disposable embeddings/indexes over the markdown, never canonical. ✅
- **Claude** reasons over retrieved content; writes go back as markdown edits. ✅
- **GitHub** *is* the canonical-store host. ✅

No option here proposes owning the wiki content in a proprietary format. No violations.

---

### 15.9 Open questions carried forward

1. **Which index stack is chosen** determines the backup mechanism: **Litestream fits SQLite-backed layers** (Basic Memory's index, a custom FTS5 layer); **Meilisearch's LMDB storage needs its own snapshot/dump commands, not Litestream.** This cluster assumed a SQLite-compatible layer — revisit if Meilisearch or another non-SQLite engine is the final pick.
2. **Actual query/ingest volume** at target scale was not given; estimates use illustrative figures (thousands of queries/month, low-single-digit-million-token corpus). If the real target is an order of magnitude larger (dozens of teams, tens of thousands of queries/month), re-run the qmd-vs-hosted-embedding crossover and the Claude Batch/caching model with real numbers.
3. **Data-residency / compliance** was not specified. If wiki content must never leave the VPS, that rules out Voyage/OpenAI hosted embeddings and any Claude call that sends wiki content off-box — tilting toward qmd's fully-local models. Note: agent reasoning over retrieved content via Claude API presumably remains required regardless, so **full data-residency is likely unachievable without an on-prem/self-hosted LLM** — flag explicitly to the user if it becomes a stated requirement.
4. **DR-drill cadence and ownership** (who runs the quarterly restore drill, where the runbook lives) is a process decision needing a **named owner + calendar cadence** to actually happen.
5. **GitHub Actions (free scheduled-job minutes)** as an alternative to persistent-VPS cron for nightly ingest-batch / backup-verification was not investigated in depth — worth a follow-up if the team wants to minimize the always-on VPS footprint by offloading batch jobs to CI runners.

---

### Recommendation for this cluster

**Adopt, in priority order:**

1. **GitHub git remote as the named, primary DR mechanism (rank 1, $0).** State it explicitly in the runbook and *do not* buy an expensive index-replication product — the index is disposable. The drill that matters is "wipe box → clone → rebuild index → confirm MCP healthy," with a timed RTO, run quarterly onto a throwaway Hetzner box.
2. **Hetzner for hosting (rank 1 on cost axis).** CX22-class (~€5/month) for a lean stack; step up to CPX22+ (~€8–20/month) *only if* running qmd's local models resident. Budget the post-April-2026 rates.
3. **Voyage AI for embeddings/reranking (rank 1 for a single team) over qmd-local**, on raw-dollar grounds: the 200M-token free tier makes embedding effectively $0 and keeps the VPS in the cheap tier. **Prefer qmd-local instead if** data-residency forbids content egress, or once shared query volume crosses ~10K/month. OpenAI text-embedding-3-small is a comparison baseline only — no free tier, no bundled reranker.
4. **Claude Sonnet 5 as the default reasoning model** (intro rate through 2026-08-31, budget $3/$15 long-term), Haiku 4.5 for a duplicate-detection pre-filter, Opus 4.8 for wiki-lint's hard semantic calls. **Prompt caching + Batch API are the deciding cost levers — configure and verify them (`cache_read_input_tokens`), do not assume.**
5. **Uptime Kuma + healthchecks.io as two distinct monitoring signals (both free, both adopt).** Endpoint reachability + cron-job completion. Conflating them leaves the stale-index gap — the most dangerous failure mode — unmonitored.
6. **Litestream + restic → Backblaze B2 as convenience backups (adopt, sub-$1/month), NOT as the DR guarantee.** Litestream for a SQLite index layer, restic for markdown belt-and-suspenders + non-git state, B2 as the cheap S3-compatible landing zone. These buy *faster* recovery, never *safer* recovery — git already provides safety.

The single most important framing to carry into the runbook: **backup ≠ DR here, because git is the canonical store.** Everything else is convenience or observability layered on an already-safe baseline, and total spend for a single team lands under roughly $40/month all-in — dominated by the qmd-VPS-sizing decision and Claude token volume, not by any storage or per-seat cost.
