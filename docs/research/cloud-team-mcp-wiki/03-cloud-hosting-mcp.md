## 03. Cloud Hosting for a Team-Shared MCP Wiki Server

This cluster decides **where the wiki's MCP server process runs** once it stops depending on the Obsidian desktop app — a persistent, team-reachable HTTP endpoint instead of a plugin inside one running WSL desktop. The compute platform is a **disposable layer**: it hosts the server and (optionally) a cache/index, but the canonical store must remain plain markdown files that are git-diffable and agent-editable. The single architectural fork this cluster forces is **"literal git checkout on a persistent disk" vs. "object-store-backed sync layer"** — the true-scale-to-zero serverless platforms structurally cannot offer the former, because a V8 isolate / ephemeral container has no writable POSIX disk that survives idling.

**Takeaways:**
- Nine general-purpose compute platforms split into three tiers: (1) **serverless with real scale-to-zero** (Cloudflare Workers+Durable Objects, Google Cloud Run) — cheapest at idle, but **no persistent local filesystem** so files must live in an object store (R2 / GCS) synced from git; (2) **container-PaaS with a real disk** (Fly.io, Railway, and with more assembly AWS ECS/Fargate+EFS) — the vault is a literal git-managed directory, at the cost of losing true scale-to-zero; (3) **ruled out** for this project (AWS Lambda+API Gateway, AWS App Runner, Render free tier).
- Two "managed-MCP-hosting" names — **Smithery** and **Gram** — plus **mcp.run** are NOT viable compute layers here: Smithery is confirmed to be a *registry/gateway* (you still host the server yourself); Gram's hosting mechanics could not be primary-source verified; mcp.run appears defunct/migrated.
- The **markdown-as-truth hard constraint is satisfiable on every viable platform** — but on serverless it requires a git→object-store sync layer (the files stay canonical in git; the object store is a disposable mirror), whereas on container-PaaS/VPS the git checkout *is* the store directly.
- **Lowest-delta path off Obsidian:** Plain VPS + Docker or Fly.io — the vault stays a folder of files on a real disk, exactly as today, minus the desktop-app dependency.

---

### Tier 1 — Serverless with real scale-to-zero (no persistent local disk)

#### Cloudflare Workers + Durable Objects (Agents SDK, remote MCP)

- **URL:** https://developers.cloudflare.com/agents/guides/remote-mcp-server/ · transport: https://developers.cloudflare.com/agents/model-context-protocol/transport/ · McpAgent API: https://developers.cloudflare.com/agents/model-context-protocol/apis/agent-api/
- **What it is:** Cloudflare's first-party remote-MCP stack. The Agents SDK's `McpAgent` class runs your MCP server logic inside a **Durable Object (one DO instance per session)**, giving built-in state persistence and both Streamable HTTP and SSE transports. A stateless alternative, `createMcpHandler()`, runs as a plain Worker with no DO.
- **Role for the wiki:** compute + session tier. Markdown files must live in **R2 (S3-compatible object storage, Workers-bindable)** or be synced from git into a DO's SQLite storage — Workers have **no writable POSIX filesystem**.
- **Key points:**
  - Streamable HTTP is the current MCP transport and fully supported; SSE is a fallback.
  - `McpAgent` = one Durable Object per session → multi-user/team stateful sessions are a native fit; each client session gets an isolated, persistent DO instance.
  - DOs now default to a **SQLite-backed storage API** (`ctx.storage.sql`), durable across restarts/evictions — real persistent storage, but it lives inside the DO's own storage, **not a shared filesystem**.
  - No cold-start-to-zero gap in the usual sense: Workers start in single-digit ms (V8 isolates, not containers); DOs hibernate when idle (no compute billed) and wake on the next request with SQLite already backing them.
  - For the shared markdown corpus, **R2** is the natural persistent store; a git-sync or scheduled job pushes commits into R2.
  - **Lock-in:** DO storage API and Agents SDK are Cloudflare-proprietary. The MCP server code is portable in spirit (Node/TS) but storage/session plumbing is not.
- **Pricing / limits:**
  - Workers free tier: 100,000 requests/day, 10 ms CPU/invocation; DOs available but SQLite-backend only on free tier.
  - Workers paid: **$5/mo min**; 10M requests/mo included then $0.30/additional million; 30M CPU-ms included then $0.02/additional million CPU-ms; max 5 min CPU/invocation (15 min for cron/queue consumers).
  - Durable Objects (https://developers.cloudflare.com/durable-objects/platform/pricing/): free plan 100,000 req/day + 13,000 GB-s/day compute + 5GB SQLite storage; paid 1M req/mo included then $0.15/million, 400,000 GB-s/mo included then $12.50/million GB-s, SQLite storage 5 GB-month included then $0.20/GB-month (row reads 25B/mo + $0.001/million; row writes 50M/mo + $1.00/million). **Note:** "Storage billing for SQLite-backed Durable Objects will be enabled in January 2026" per the docs at fetch time.
  - R2 (https://developers.cloudflare.com/r2/pricing/): Standard $0.015/GB-month, Infrequent Access $0.01/GB-month; free tier 10GB + 1M Class A ops + 10M Class B ops/mo; Class A (mutating) $4.50/million, Class B (read) $0.36/million; **zero egress fees** when reading via Workers/S3 API/r2.dev.
  - Full walkthrough tutorial: https://mcpanalytics.blog/blog/cloudflare-remote-mcp-server-tutorial/
- **Constraints:** Cloudflare-proprietary APIs; **TypeScript/JavaScript runtime (V8 isolate, not a general container)** — a Python/Go MCP server (e.g., one wrapping the prior research's `obsidiantools`/`qmd`) needs a rewrite or the less-mature Python-on-Workers path. No persistent local filesystem at all.
- **Maturity:** Actively developed first-party product; McpAgent/Agents SDK shipped 2025, with streamable-HTTP/elicitation/task-queue updates as recently as the Aug 2025 changelog.
- **Verdict:** **Adopt for the compute+session tier** — best-in-class native Streamable HTTP + per-session stateful MCP with a genuinely usable free tier for small-team traffic. Pair with **R2 (not DO storage)** as the canonical git-synced markdown store to keep files portable and outside Cloudflare's proprietary DO format.
- **Markdown-as-truth check:** ✅ *satisfiable* — git stays canonical; R2 is a disposable mirror. ⚠️ Do NOT make DO SQLite storage the source of truth (proprietary format, violates the constraint).

#### Google Cloud Run

- **URL:** https://docs.cloud.google.com/run/docs/host-mcp-servers · tutorial: https://docs.cloud.google.com/run/docs/tutorials/deploy-remote-mcp-server · Google-hosted managed variant: https://docs.cloud.google.com/run/docs/use-cloud-run-mcp
- **What it is:** Google's serverless container platform with a **documented first-party path for hosting MCP servers** over Streamable HTTP or SSE, scaling per request and to zero when idle.
- **Role for the wiki:** genuinely serverless, pay-per-request compute. Canonical markdown must live outside the container (Cloud Storage FUSE volume mount, or external DB/bucket).
- **Key points:**
  - Supports **Streamable HTTP and SSE**; explicitly does **NOT support stdio** (rules out the simplest "wrap a CLI tool" MCP servers unless rewritten to speak HTTP).
  - Scale-to-zero is native and free when idle; optional `min-instances` avoids cold starts by paying for always-warm capacity.
  - Persistent storage options: **Cloud Storage volume mounts (FUSE-backed object-store filesystem view), NFS volumes (e.g., Filestore), and in-memory (tmpfs) volumes** — **no local block disk that survives a full scale-to-zero cycle**.
  - Session affinity (sticky routing to the same instance) is a general Cloud Run feature that *can* support MCP's optional stateful `Mcp-Session-Id` mode — **but the docs reviewed did not confirm it's wired up for MCP out of the box** (open question).
  - Deployable straight from source (Node.js/Python buildpacks) or from a container image.
- **Pricing / limits** (general Cloud Run, https://cloud.google.com/run/pricing — MCP page omits numbers): free tier 2M requests/mo, 360,000 GB-seconds/mo memory, 180,000 vCPU-seconds/mo, 1GB egress/mo; beyond: ~$0.000024/vCPU-second, ~$0.0000025/GB-second (us-central1), $0.40 per additional million requests. Cold starts typically sub-2s for lightweight containers; `min-instances` keeps warm instances (billed continuously).
- **Constraints:** No stdio transport; no native persistent block disk (route through Cloud Storage/NFS); GCP account/IAM setup overhead vs. Fly/Railway's simpler DX.
- **Maturity:** Mature GA product; MCP-hosting guidance is a 2025/2026-era docs addition, actively maintained.
- **Verdict:** **Adopt as a strong serverless candidate**, especially if the markdown files are mirrored into a **GCS bucket mounted via the Cloud Storage volume type** — real scale-to-zero economics plus Google's ecosystem (IAM, Cloud Build). Weaker fit if the team wants a literal writable git checkout on local disk.
- **Markdown-as-truth check:** ✅ *satisfiable* via git→GCS sync (files stay canonical in git). ⚠️ FUSE-mounted GCS has object-store semantics (not true POSIX rename/lock) — fine as a read-mostly mirror, a gotcha for a heavy multi-writer path.

---

### Tier 2 — Container-PaaS with a real persistent disk (literal git checkout)

#### Fly.io (Machines + Volumes)

- **URL:** https://fly.io/docs/volumes/overview/ · pricing: https://fly.io/docs/about/pricing/ · autostop: https://fly.io/docs/launch/autostop-autostart/
- **What it is:** Container hosting on **Firecracker microVMs ("Machines")** with attachable persistent block-storage volumes and traffic-based autostart/autostop scaling.
- **Role for the wiki:** the closest managed analogue to "just run it on a box" — run any off-the-shelf MCP server (any language/runtime, plain Docker) with the vault mounted as a **real writable directory on a persistent volume**.
- **Key points:**
  - Volumes are true persistent local disks, **one-to-one with a single Machine** — ideal for a git-checked-out markdown folder a long-lived MCP process reads/writes directly (no S3/API layer).
  - **No automatic cross-volume replication** — Fly explicitly warns "Fly.io does not automatically replicate data among the volumes." Fine for one canonical copy (single volume, single writer); rules out easy multi-region HA without LiteFS or an external DB.
  - Autostop/autostart (`auto_stop_machines`, `auto_start_machines`, `min_machines_running`) lets a Machine fully stop when idle and restart on traffic; community-reported cold start ≈ **5 seconds** from stopped-to-serving, faster with `"suspend"` mode than `"stop"` (with some Machine-type limits).
  - Supports long-lived Streamable-HTTP MCP processes and stateful sessions natively — a regular container process on a regular disk, no serverless statelessness constraints.
  - Legacy free allowance (deprecated) existed (3 shared-cpu-1x 256MB VMs + 3GB volume); **current pricing is fully pay-as-you-go, no ongoing free tier for new accounts (2026)**.
- **Pricing / limits:**
  - Volumes: **$0.15/GB-month**, billed hourly, charged even when the attached Machine is stopped; automatic daily snapshots (5-day retention) on by default, adjustable/disableable. Snapshots $0.08/GB-month, first 10GB free/month.
  - Compute: shared-cpu-1x/256MB ≈ $0.0028/hr (~$2.02/mo continuous); shared-cpu-2x/512MB ≈ $0.0056/hr (~$4.04/mo); performance-1x/2GB ≈ $0.0447/hr (~$32.19/mo); extra RAM ~$5/mo per GB.
  - Egress: $0.02/GB NA/Europe, $0.04/GB Asia-Pacific, $0.12/GB Africa/India; static egress IP $0.005/hr (~$3.60/mo).
  - Config keys (`fly.toml`): `auto_stop_machines = "stop"` (or `"suspend"`), `auto_start_machines = true`, `min_machines_running = 0`.
  - **Realistic cost:** a small always-on MCP box (1 shared-cpu Machine + a few GB volume) ≈ **$5–15/month**; typical "production" Fly apps run $20–40+/month.
- **Constraints:** No free tier for new accounts; single-writer volume model → no built-in multi-region replication (acceptable for one canonical wiki, manual concern if geo-distributing).
- **Maturity:** Mature, widely used PaaS; Firecracker Machines have been the core primitive since ~2022.
- **Verdict:** **Adopt as the strongest "run any Docker container with a real persistent disk" option** if the team wants a plain git-checkout-on-disk architecture. Best fit when the MCP server is an arbitrary existing tool (e.g., wrapping `obsidiantools`/`qmd` from prior research) rather than something written for Workers.
- **Markdown-as-truth check:** ✅ *cleanest satisfaction* — the vault is literally a git directory on disk; no storage abstraction to reason about.

#### Railway

- **URL:** https://docs.railway.com/pricing/plans
- **What it is:** A PaaS (Docker/Nixpacks deploys) with usage-based billing and first-class persistent volumes attachable to any service.
- **Role for the wiki:** same category as Fly.io — a boring, always-on container host with a real disk — but a smaller free/entry tier and a simpler single-dashboard, GitHub-connected mental model.
- **Key points:**
  - Persistent volumes on every plan tier including Free (tiny default allocations).
  - **No documented scale-to-zero** for the always-on plans — the docs consulted didn't describe automatic sleep/wake for Hobby/Pro (unlike Render's free-tier spin-down). Cost is flat, not usage-elastic during idle.
  - Docker/container deploys standard; any existing MCP image runs unmodified.
  - Free plan ($1/mo rolling credit, 0.5GB volume) is toy/demo only, not a real team service.
- **Pricing / limits:**
  - Plans: **Free** $0/mo, $1/mo non-rollover credit, 0.5GB volume, 1 vCPU/0.5GB RAM, 1 project, 3 services/project; **Hobby** $5/mo, $5 included usage, 5GB volume; **Pro** $20/mo, $20 included usage, up to 1TB volume (self-serve); **Enterprise** custom, 5TB volume.
  - Trial (new accounts): one-time $5 credit for 30 days, more generous limits (2 vCPU, 1GB RAM, 5 projects).
  - Volume overage: **$0.15/GB/month** beyond allocation — but **one source cited $0.25/GB/month** for "databases and file storage"; treat as approximate/plan-dependent, **confirm at billing time** (open question). Volumes billed 24/7 whether the service runs or is stopped.
  - Realistic entry point: **Hobby, $5/month base + usage**.
- **Constraints:** $5/month realistic minimum for a serious service; volumes billed continuously regardless of service state; no clearly documented scale-to-zero.
- **Maturity:** Actively developed, well-established PaaS, large community usage.
- **Verdict:** **Evaluate as a Fly.io alternative** — same category with simpler UX but a much thinner free tier and no clear scale-to-zero, so cost is flat rather than usage-elastic when idle.
- **Markdown-as-truth check:** ✅ *satisfiable* — literal git checkout on the persistent volume, same as Fly.io.

---

### Tier 3 — Ruled out (or heavier assembly) for this project

#### AWS Fargate (ECS) for MCP

- **URL:** https://aws.amazon.com/blogs/containers/deploying-model-context-protocol-mcp-servers-on-amazon-ecs/
- **What it is:** AWS's official pattern for running MCP servers as always-on or auto-scaled container tasks on ECS with the Fargate serverless-container launch type.
- **Role for the wiki:** best AWS-native fit for a long-lived, stateful Streamable-HTTP MCP server needing warm caches or persistent connections — the blog explicitly favors this over Lambda for that reason.
- **Key points:**
  - Streamable HTTP in **both stateless mode** (each tool call self-contained → simple horizontal scaling across task replicas) **and stateful mode** (`Mcp-Session-Id` header) for multi-step workflows.
  - AWS framing: *"AWS Lambda works well for lightweight, stateless tool endpoints with bursty traffic… Amazon ECS lets you run your MCP server as a long-lived service with warm caches, persistent streaming connections, sidecars, and any language or runtime."*
  - The reference architecture reads data **from Amazon S3 rather than a mounted disk** — the AWS-recommended pattern treats the container as stateless and pushes durable state to S3/DynamoDB. **EFS** is a documented AWS option (POSIX-shared storage across tasks, unlike Fly/Railway single-Machine volumes) but wasn't detailed in this MCP blog.
  - **Does not scale to zero** in the demonstrated setup (min task count 1, autoscale up to 4 on CPU); can scale to 0 tasks in principle but then has no listener, so it's paired with an always-up ALB.
  - Pricing is per-vCPU/memory-second while running (Fargate pay-per-second) + ECR storage + data transfer + CloudWatch Logs; no flat MCP-specific pricing.
- **Concrete refs:** stateless-vs-stateful patterns https://deepwiki.com/aws-samples/sample-serverless-mcp-servers/1.1-stateful-vs.-stateless-architecture · sample repo https://github.com/aws-samples/sample-serverless-mcp-servers · autoscaling example `minTaskCount=1, maxTaskCount=4`.
- **Constraints:** **No AWS free tier for Fargate compute**; needs an **ALB (~$16+/month fixed)** or API Gateway for HTTP ingress; more moving parts (task definitions, ECR, optionally EFS) than a PaaS.
- **Maturity:** GA, heavily used; MCP-specific guidance is a current 2025-era blog post.
- **Verdict:** **Evaluate** — the most "you don't manage the OS" AWS option for a long-lived stateful MCP; good if the team is already on AWS. Heavier ops for likely similar-or-higher cost than the alternatives for a small-team wiki.
- **Markdown-as-truth check:** ✅ *satisfiable via EFS* (literal POSIX git checkout, shared across tasks) — but the AWS-blessed pattern (S3-backed) makes S3 a mirror, which is fine only if git stays canonical.

#### AWS Lambda + API Gateway (serverless MCP)

- **URL:** https://repost.aws/questions/QUSqZD0G2RTviEILi5YDzg3w/streaming-limitations-of-api-gateway-rest-apis-for-long-running-mcp-workloads
- **What it is:** MCP tool endpoints as individual Lambda functions fronted by API Gateway (REST/HTTP API), using Streamable HTTP.
- **Key points / gotchas:**
  - **No cross-instance session persistence:** as of the sources checked, **none of the official MCP SDKs support external session persistence** (Redis/DynamoDB). Session state lives only on the instance that created it; Lambda gives no guarantee of routing follow-ups to the same warm instance → the community pattern is to run **stateless and disable `Mcp-Session-Id` entirely**. AWS's own sample explicitly notes: *"on Lambda we deliberately disable this and run stateless."*
  - **API Gateway streaming ceiling:** throughput capped at **2 MBps past the first 6MB** of a stream; connections can time out client↔API Gateway or API Gateway↔Lambda while the Lambda keeps executing (wasted compute / inconsistent behavior).
  - **No persistent storage at all** — Lambda `/tmp` is ephemeral per invocation/instance; durable store must be external (S3, EFS mount, DynamoDB).
  - **True scale-to-zero and pay-per-invocation** — the cheapest idle-cost option surveyed when traffic is bursty/low.
- **Concrete refs:** https://www.ranthebuilder.cloud/post/mcp-server-on-aws-lambda · sample stateless impl https://github.com/madhurprash/streamable-mcp-serverless
- **Constraints:** No official session persistence across instances; API Gateway streaming cap past 6MB; ephemeral `/tmp` only.
- **Verdict:** **Avoid as the sole compute layer** for a stateful team MCP given the explicit lack of session persistence and streaming ceiling. *Steal the idea* for a stateless subset (e.g., a pure read-only content-search Lambda behind the main server) if idle cost-per-request must hit near-zero.
- **Markdown-as-truth check:** ⚠️ only via external S3/EFS; the stateless design suits read-mostly single-shot queries, not a multi-writer editing session.

#### AWS App Runner

- **URL:** https://aws.amazon.com/apprunner/pricing/
- **What it is:** AWS's simplified container PaaS (build from source or image, automatic LB/TLS), positioned between Lambda and full ECS/Fargate.
- **Key points / gotchas:**
  - **Does NOT scale to zero:** *"when your active container instances are idle, App Runner scales back to your provisioned container instances (the default is 1 provisioned container instance)"* — always ≥1 running (billed at the lower idle/provisioned rate, not zero).
  - **No documented persistent storage** — implies external store (S3, RDS, EFS via VPC connector where supported).
  - Billed per-second, split into **active** (vCPU + memory) and **provisioned/idle** (memory-only) rates. Simpler than ECS (no task defs/ALB) at the cost of that always-on floor.
- **Pricing:** idle/provisioned **$0.007/GB-hour** (US East/West, Ireland; $0.009 Tokyo); active **$0.064/vCPU-hour + $0.007/GB-hour** (US; $0.081 + $0.009 Tokyo); per-second billed rounded up, one-minute minimum vCPU charge per startup; build fee $0.005/build-minute; automatic-deployment fee ~$1/app/month.
- **Verdict:** **Avoid** — the always-on provisioned floor removes the scale-to-zero cost benefit without buying ECS/Fargate's flexibility or Cloud Run/Lambda's true elasticity. **Cloud Run is a strictly more attractive equivalent.**
- **Markdown-as-truth check:** ⚠️ no native persistent storage; would need external S3/EFS anyway.

#### Render

- **URL:** https://render.com/docs/free
- **What it is:** A PaaS with a genuine free web-service tier (with cold spin-down) and paid tiers that add persistent disks.
- **Key points / gotchas:**
  - Free web services **spin down after 15 min idle**, take **~1 minute to wake** — genuine scale-to-zero but a real (not sub-second) cold start.
  - **Free tier has an ephemeral filesystem — no persistent disk** — any git checkout or rebuilt index vanishes on restart/redeploy/spin-down. **This directly defeats the markdown-as-truth requirement** on free tier.
  - Persistent disks require a **paid web service (Starter from $7/month)** and cost extra: **$0.25/GB-month**, only attachable to paid services.
  - Free Postgres/Redis available but **free Postgres expires 30 days after creation** — not a durable store.
- **Pricing:** free tier 750 instance-hours/workspace/mo, 100GB outbound bandwidth, 500 build-pipeline minutes.
- **Verdict:** **Avoid** for the canonical always-available team wiki — needs a paid plan the moment persistent files are required, and the free tier's ephemeral disk defeats git-diffable-markdown-as-truth. The paid Starter+disk combo ($7+/mo + $0.25/GB/mo) works but isn't clearly better than Fly.io/Railway here.
- **Markdown-as-truth check:** ❌ *violated on free tier* (ephemeral disk); ✅ only on paid Starter+disk.

---

### Baseline / fallback

#### Plain VPS + Docker

- **URL (transport spec to satisfy):** https://modelcontextprotocol.io/docs/concepts/transports
- **What it is:** Rent a Linux VM (DigitalOcean, Hetzner, bare EC2/GCE, etc.), run the MCP server (any language) plus the git-checked-out wiki folder in Docker or on the host, expose Streamable HTTP behind a reverse proxy/TLS terminator.
- **Key points:**
  - **Full control:** any MCP framework, any language, a real persistent filesystem, standard git workflows (cron `git pull`/`git commit` or webhook-triggered sync) — **no vendor storage abstraction at all**.
  - **No scale-to-zero, no managed autoscaling** — you pay for the box 24/7 and own patching/monitoring/TLS renewal/process supervision (systemd, Docker restart policies).
  - Persistent disk is just the VM's own disk (or attached block volume) — **no distinction between "canonical store" and "server storage,"** the simplest mental model surveyed.
  - **Cheapest raw compute at small scale** — a **$4–6/month VPS** (Hetzner/DigitalOcean-class) comfortably runs a low-traffic MCP server — but that price excludes ops time (patches, backups, uptime monitoring).
  - Provider-agnostic; any reverse proxy (Caddy/Nginx/Traefik) with a valid TLS cert in front of the container works.
  - **This is the same architecture the current setup already approximates** (WSL box running Obsidian + local-rest-api plugin), minus the desktop-app dependency — the **lowest-delta path off Obsidian** while staying on "a machine you administer."
- **Constraints:** No managed scaling, TLS/cert renewal, or backups — the team owns all of it (real ongoing maintenance the PaaS/serverless options absorb).
- **Maturity:** N/A — a well-understood deployment pattern; every piece (Docker, systemd, reverse proxies) is mature.
- **Verdict:** **Adopt as the baseline/fallback** if the team wants zero platform lock-in and is comfortable with basic Linux ops — the most direct translation of "stop depending on the Obsidian desktop app" into "run the same folder-of-markdown behind an always-on HTTP MCP server," no new storage abstraction.
- **Markdown-as-truth check:** ✅ *purest satisfaction* — the vault is a git directory on disk, full stop.

---

### Managed-MCP-hosting names that are NOT compute layers

#### Smithery (MCP registry/gateway)

- **URL:** https://smithery.ai/docs/build · registry: https://smithery.ai/servers
- **What it is:** An MCP server **registry and discovery hub (5,000+ community servers)** with a gateway that can front an already-deployed remote MCP server for discovery, analytics, and auth-modal generation — **confirmed by direct fetch NOT to be a hosting provider itself.**
- **Key points:**
  - From Smithery's own build docs: developers who *"already deployed an MCP server elsewhere"* can *"publish it directly on Smithery via the URL method"* — Smithery consumes a **Streamable HTTP URL or an MCPB bundle** (for local stdio servers); it does **not provide compute/hosting**.
  - Provides a dedicated server page, protocol-compliance handling, metadata enrichment/caching, usage analytics, and automatic auth-modal generation for servers needing API keys.
  - **No hosting infrastructure, persistent storage, hosting pricing, or cold-start/scale-to-zero details** — because it is not a hosting layer.
  - Accepts two server types only: (1) Streamable HTTP via URL (you host it, on any platform above), or (2) MCPB bundles for local stdio servers (client-side install).
- **Verdict:** **Avoid as a hosting solution** — solves discovery/marketplace, not "run this persistently on a server." Only additive on top of a real hosting platform if the wiki MCP server ever needs public/cross-org discoverability — **out of scope for a private team wiki.**

#### Gram (getgram.ai, by Speakeasy) — UNCONFIRMED

- **URL:** https://getgram.ai
- **What it is:** A commercial MCP hosting/tooling platform from Speakeasy, described in **secondary sources** as full-stack MCP hosting with serverless-style deployment, "Toolsets" for grouping tools, "Gram Elements" React UI components, and an agents API.
- **Gap (honest):** The **primary-source fetch of `getgram.ai/docs` 308-redirected to Speakeasy's marketing homepage** (https://www.speakeasy.com/), not hosting-specific docs. **Deployment mechanics, storage model, session/state handling, pricing, and scale-to-zero could NOT be independently confirmed.**
- **Comparison source (secondary, unverified):** https://hasmcp.com/alternatives/smithery-vs-gram — positions Gram as a *hosting* platform vs. Smithery's *registry/discovery*, i.e., complementary not substitutes.
- **Verdict:** **Evaluate only after a direct primary-source re-check** (target a `/gram` or `/docs/gram` path on speakeasy.com). Do not adopt or rule out on this pass — no authoritative capability/pricing data obtained. **Open question.**

#### mcp.run — LIKELY DEFUNCT / MIGRATED

- **URL:** https://www.mcp.run/
- **What it is:** Originally a hosted registry for WASM-plugin-based MCP servers/tools (per general community knowledge).
- **Gap (honest):** Direct fetch of `https://www.mcp.run/` **301-redirected to an unrelated site (`turbomcp.ai`)**, suggesting the original product was retired, rebranded, or the domain changed hands. A general web search for "mcp.run hosted MCP servers wasm pricing" returned nothing about mcp.run. Capability is **ABSENT/unconfirmable from this pass** — not asserted from stale pre-training knowledge.
- **Verdict:** **Avoid / do not rely on** — status unconfirmed and likely defunct or migrated. Do not cite as an available option without a fresh re-check of whatever the domain now resolves to. **Open question.**

---

### Vercel Functions (Fluid compute) — serverless, no persistent disk

Included here as a fourth serverless option (same "external store required" caveat as Tier 1).

- **URL:** https://vercel.com/docs/mcp/deploy-mcp-servers-to-vercel · Fluid compute: https://vercel.com/docs/fluid-compute · pricing: https://vercel.com/docs/functions/usage-and-pricing
- **What it is:** Vercel's official first-party path to host an MCP server as a Next.js/Vercel-Functions API route using the **`mcp-handler` npm package**, running on **Fluid compute** (hybrid serverless with in-function concurrency and instance reuse).
- **Key points:**
  - **Streamable HTTP is the first-class transport** (`createMcpHandler` from `mcp-handler`), including an MCP-Inspector-tested example and **OAuth (`withMcpAuth`)** for securing tool access — directly reusable for this project's auth needs.
  - Fluid compute optimizes for MCP's traffic shape (long idle, bursty calls) via dynamic scaling and instance sharing, billing **"Active CPU" only while code executes** (I/O wait doesn't bill CPU, though memory keeps billing) — Vercel claims up to **85–90% cost cuts** vs. traditional serverless for idle-heavy/AI workloads.
  - **No persistent storage mentioned anywhere in the MCP deploy guide** — Vercel Functions are stateless/ephemeral; docs point to **Vercel Blob** for storage, unconfirmed whether Blob supports the POSIX-style directory semantics a markdown vault needs.
  - Production features for a shared endpoint: Instant Rollback, Deployment Protection on previews, Vercel Firewall.
- **Pricing:** Active CPU billed per vCPU-ms of actual execution (~$0.128/hour-equivalent rate, secondary source); Provisioned Memory in GB-hours at under 10% of the Active CPU rate (~$0.0106/GB-hour, secondary source), plus per-invocation counts. Fluid compute has been the **default for new Vercel projects since April 23, 2025**.
- **Example client config** (from docs): `.cursor/mcp.json` pointing at `https://my-mcp-server.vercel.app/api/mcp` with `"url"` transport — confirms Streamable HTTP works end-to-end against real MCP clients.
- **Constraints:** No native persistent filesystem; JS/TS (Next.js/Vercel Functions) centric; per-request pricing harder to predict than a flat PaaS price at very high query volumes.
- **Maturity:** Actively maintained first-party feature; MCP deploy docs dated 2026-03-19 at fetch time.
- **Verdict:** **Evaluate** — excellent DX and cost model for the compute/session layer *specifically if paired with an external persistent store* (git repo synced into a DB/blob store, or fetched live from the GitHub API per request) rather than expecting local disk.
- **Markdown-as-truth check:** ✅ *satisfiable* only via external store; ⚠️ Vercel Blob's directory semantics for a vault are unconfirmed.

---

### Comparison table

| Platform | Streamable HTTP | Scale-to-zero | Persistent local disk | Stateful sessions | Idle cost | Entry cost (real team use) | Markdown-as-truth |
|---|---|---|---|---|---|---|---|
| **Cloudflare Workers + DO** | ✅ native (first-party) | ✅ true (DO hibernate) | ❌ (R2 / DO SQLite only) | ✅ 1 DO/session | ~$0 (free tier) | $5/mo min | ✅ via git→R2 sync |
| **Google Cloud Run** | ✅ (also SSE; no stdio) | ✅ true | ❌ (GCS FUSE / NFS / tmpfs) | ⚠️ session affinity, MCP-wiring unconfirmed | ~$0 (2M req free) | usage-based | ✅ via git→GCS sync |
| **Fly.io** | ✅ (any container) | ⚠️ autostop, ~5s cold start | ✅ real volume | ✅ native | volume billed even stopped | ~$5–15/mo | ✅ literal git checkout |
| **Railway** | ✅ (any container) | ❌ not documented | ✅ real volume | ✅ native | flat (volumes 24/7) | $5/mo (Hobby) | ✅ literal git checkout |
| **AWS ECS/Fargate** | ✅ (stateless+stateful) | ❌ (min 1 task) | ✅ via EFS | ✅ `Mcp-Session-Id` | ALB ~$16+/mo floor | heavy assembly | ✅ via EFS (git checkout) |
| **AWS Lambda + API GW** | ✅ but streaming-capped | ✅ true | ❌ (`/tmp` ephemeral) | ❌ no cross-instance persistence | ~$0 (per-invocation) | near-zero idle | ⚠️ external S3/EFS only |
| **AWS App Runner** | ✅ (any container) | ❌ (min 1 provisioned) | ❌ none documented | ✅ (long-lived) | provisioned floor | ~$0.007/GB-hr floor + | ⚠️ external store only |
| **Render** | ✅ (any container) | ✅ free (15min, ~1min wake) | ❌ free / ✅ paid disk | ✅ (paid) | free spins down | $7/mo (Starter+disk) | ❌ free / ✅ paid disk |
| **Vercel Fluid** | ✅ native (`mcp-handler`) | ✅ true | ❌ (Vercel Blob only) | ⚠️ ephemeral | Active-CPU only | usage-based | ⚠️ external store only |
| **Plain VPS + Docker** | ✅ (any container) | ❌ (24/7) | ✅ the VM disk | ✅ native | flat (box runs 24/7) | $4–6/mo | ✅ purest (git = store) |
| **Smithery** | N/A — registry/gateway, not hosting | — | — | — | — | — | N/A |
| **Gram** | unconfirmed | unconfirmed | unconfirmed | unconfirmed | unconfirmed | unconfirmed | unconfirmed |
| **mcp.run** | likely defunct at URL | — | — | — | — | — | — |

---

### Open questions carried forward

- **Gram hosting mechanics/storage/pricing** — primary docs redirected to Speakeasy marketing; needs a targeted re-fetch of Speakeasy's Gram product-docs path before Gram is evaluable.
- **mcp.run status** — domain now redirects to `turbomcp.ai`; unclear if shut down, rebranded, or lapsed/re-registered. Fresh check needed only if the team wants a WASM-plugin hosted registry.
- **Cloud Run session affinity ↔ MCP `Mcp-Session-Id`** — whether the generic sticky-routing feature actually respects MCP stateful-session semantics was not confirmed; needs a Cloud Run + MCP stateful-session test.
- **Railway volume overage rate** — $0.15 vs. $0.25/GB/month ambiguity across sources; confirm at railway.com/pricing or in-console before budgeting.
- **Object-store-as-git-diffable staleness** — whether any "no persistent disk" platform (Cloudflare, Cloud Run, Vercel) has a clean, low-latency pattern for treating an object-store-backed corpus as truly git-diffable for a multi-editor team (does a GitHub webhook → object-store sync introduce unacceptable staleness?) was not investigated and is a natural follow-up for whichever compute layer is chosen.

---

### Recommendation for this cluster

For a **cloud, team-shared, markdown-as-truth MCP wiki**, the decision hinges on the one fork this cluster surfaces — *literal git checkout on disk* vs. *object-store sync layer* — and the team's tolerance for Linux ops.

1. **Fly.io (top pick for the file-on-disk architecture).** It most directly satisfies the hard constraint: the vault is a real git-managed directory on a persistent volume, no storage abstraction to reason about, and it runs any existing MCP server (including one wrapping the prior research's `obsidiantools` + `qmd` Python stack — which the JS-only serverless platforms cannot host without a rewrite). Autostop keeps idle cost near a few dollars/month; the ~5s cold start is acceptable for a team wiki. **Adopt as the default.**

2. **Plain VPS + Docker (baseline / zero-lock-in fallback).** The purest satisfaction of markdown-as-truth and the **lowest-delta path off the Obsidian desktop dependency** — it's the current WSL architecture minus the desktop app. Cheapest raw compute (~$4–6/mo) but the team owns patching, TLS renewal, and backups. Choose this over Fly.io only if avoiding all platform lock-in outweighs wanting managed ops.

3. **Cloudflare Workers + Durable Objects (top pick if the team will accept an object-store sync layer and a JS/TS server).** Best-in-class native Streamable HTTP, genuine per-session stateful DOs, and a real free tier. Requires accepting **R2 as a git-synced mirror** (git stays canonical) and rewriting/authoring the server in TS. Best when the team wants true scale-to-zero economics and is comfortable with the git→R2 sync introducing some staleness.

4. **Google Cloud Run (serverless alternative to Cloudflare, if already on GCP).** Same object-store-sync caveat (GCS FUSE mount), hosts any container (not JS-only), true scale-to-zero. Slightly heavier IAM/setup than Fly; the MCP↔session-affinity wiring is an unverified risk for stateful sessions.

5. **Railway** — evaluate as a simpler-UX Fly.io alternative if flat, predictable pricing is preferred over usage-elastic idle cost. **AWS ECS/Fargate+EFS** — only if the team is already deep in AWS and accepts the ALB floor (~$16+/mo) and assembly overhead.

**Ruled out for this project:** AWS Lambda+API Gateway (no cross-instance session persistence per AWS's own samples; streaming ceiling), AWS App Runner (never scales below one provisioned instance — captures no serverless cost benefit while lacking persistent storage; Cloud Run strictly dominates it), and Render's free tier (ephemeral filesystem directly violates markdown-as-truth). **Vercel Fluid** is a strong DX/cost option but carries the same external-store requirement as Cloudflare/Cloud Run with less MCP-specific tooling maturity than Cloudflare's first-party stack. **Smithery / Gram / mcp.run** are not compute layers: Smithery is a discovery registry (additive only, and out of scope for a private wiki), Gram is unverified, mcp.run is likely defunct.

**Bottom line:** pick **Fly.io** (or **VPS+Docker** for zero lock-in) if you want the vault to stay a literal git checkout on disk — the cleanest read of the hard constraint; pick **Cloudflare Workers+DO** (or **Cloud Run**) only if the team deliberately accepts a git→object-store sync layer in exchange for true scale-to-zero, and confirms that sync staleness is tolerable for multi-editor use (the key open question above).
