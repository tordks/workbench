## 04. MCP Authentication & Multi-Tenancy — Gating a Shared Wiki by Team

Once the wiki MCP server leaves the loopback-only, single-user Obsidian desktop setup and becomes a
**remote, cloud-hosted, HTTP-transport** service, it stops being trustworthy-by-locality and needs an
explicit authorization layer. This cluster decides two things: (1) which **wire contract** the server
must speak so that Claude Code, Cursor, and Claude Desktop can authenticate against it (answer: the MCP
Authorization spec — OAuth 2.1 + RFC 9728 Protected Resource Metadata + RFC 8707 Resource Indicators +
PKCE S256, non-negotiable), and (2) **where** the authorization-server role and the per-team scoping
logic live — an off-the-shelf IdP, a network-level gate, or a full MCP gateway/control-plane. None of
these touches the store: every option here is a **disposable access-control layer in front of the
git-diffable markdown files**, never a replacement for them, so all are compatible with the hard
constraint.

**Takeaways**

- The spec is fixed; the only real decision is the placement of the authorization server. Do not
  hand-roll anything that deviates from RFC 9728 + RFC 8707 + PKCE — every client and every provider
  assumes exactly that shape.
- **No vendor ships "per-team wiki scoping" as a turnkey feature.** Universally it is assembled from
  `(team/org claim in the token)` × `(a server-side authorization check per tool)`. Whatever you pick,
  the wiki MCP server's own code must still inspect a `team`/`org_id` claim before serving
  query/capture/ingest/lint.
- **Three combinable tiers:** (1) IdP-as-authorization-server (WorkOS, Stytch, Descope, Auth0/Okta,
  Clerk, self-hosted Ory Hydra); (2) network gate in front (Cloudflare Access); (3) full MCP
  gateway/control-plane with RBAC + per-team catalogs + audit (Gram, Obot, Docker MCP Gateway).
- **Gram and Obot** are the only surveyed tools that solve "gate a shared wiki by team" out of the box
  (explicit per-team/per-toolset sub-catalogs or RBAC roles). **Docker MCP Gateway is disqualified** for
  the cloud/team goal — it is a local, single-operator Docker Desktop tool with no team-auth model.
- **Client reality check:** Claude Code and Cursor (≥ v1.0, June 2025) both do spec-compliant remote-MCP
  OAuth today; Claude Desktop has historically lagged.

---

### The fixed contract — MCP Authorization spec

**[MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)**
(revisions `2025-11-25` and `2025-06-18`) is the normative section defining how HTTP-transport MCP
servers act as OAuth 2.1 **resource servers** and how MCP clients discover and authenticate against them.
It is not a product; every provider in this cluster is an implementation of it. Adopt it as the baseline
and build nothing that deviates.

Roles:

- **MCP server** = OAuth 2.1 **resource server** (validates tokens, serves tools).
- **MCP client** (Claude Code, Cursor) = OAuth 2.1 **client**.
- A separate **authorization server** issues tokens — co-hosted or a third party (WorkOS / Stytch /
  Descope / Auth0 / Okta / Ory / Clerk).

Mandatory mechanics the wiki server must implement:

| Requirement | Detail |
|---|---|
| **Protected Resource Metadata (RFC 9728)** | MUST serve a JSON doc with an `authorization_servers` field. Discoverable via the `WWW-Authenticate` header's `resource_metadata` param on a `401`, or at `.well-known/oauth-protected-resource(/<path>)`, falling back to root if the sub-path 404s. |
| **Authorization Server Metadata (RFC 8414) / OIDC Discovery** | The AS MUST expose one or both; clients MUST support both lookup forms. |
| **Resource Indicators (RFC 8707)** | Clients MUST send a `resource` param (canonical server URI, e.g. `https://mcp.example.com/mcp`) in **both** authorization and token requests, binding the token audience to that server. Servers MUST reject tokens not issued for them and MUST NOT pass client tokens through to upstream APIs (confused-deputy protection). |
| **PKCE S256** | Mandatory. Clients MUST verify `code_challenge_methods_supported` is present in AS metadata or refuse to proceed. |
| **Bearer usage** | `Authorization: Bearer <token>` header on every request — never in the URL query string. |
| **Error mechanics** | Invalid/expired token → `401`; insufficient scope at runtime → `403` with `WWW-Authenticate: Bearer error="insufficient_scope", scope="...", resource_metadata="..."` enabling step-up re-authorization. |

Client-registration mechanisms, tried in priority order:

1. **Pre-registered client** (an existing relationship / shared secret).
2. **Client ID Metadata Documents (CIMD)** — the client hosts an HTTPS JSON doc whose URL *is* its
   `client_id`; no prior relationship needed. The **emerging default** for "no prior relationship" MCP
   scenarios, added in the `2025-11-25` revision. Required fields: `client_id` (an https URL matching the
   doc's own location), `client_name`, `redirect_uris`; `grant_types`/`response_types`/
   `token_endpoint_auth_method` optional.
3. **Dynamic Client Registration (RFC 7591)** — fallback/legacy.

Concrete discovery snippets to build against:

```
# Protected-resource metadata lookup (falls back to root on 404):
GET https://mcp.example.com/.well-known/oauth-protected-resource/<mcp-path>

# 401 challenge:
WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource", scope="files:read"

# 403 step-up (insufficient scope):
WWW-Authenticate: Bearer error="insufficient_scope", scope="files:read files:write", resource_metadata="..."
```

For an **issuer with a path** (multi-tenant path style, e.g. `/tenant1` — relevant if per-team tenants
are modeled as issuer path segments), AS-metadata discovery order is:
`/.well-known/oauth-authorization-server/tenant1` → `/.well-known/openid-configuration/tenant1` →
`/tenant1/.well-known/openid-configuration`.

**The multi-tenancy gap:** the spec has **no native team/tenant concept**. Scoping to a team must be
implemented via OAuth scopes/claims (e.g. a `team` or `org_id` claim in the access-token JWT) that the
server's tool layer checks. This is exactly the gap every provider below tries to fill — and none fully
does. Conventions beyond core live in the extensions registry:
[`modelcontextprotocol/ext-auth`](https://github.com/modelcontextprotocol/ext-auth).

- **License/cost:** spec only, none.
- **Gotcha:** STDIO transport (today's Obsidian-MCP-in-desktop setup) is explicitly **out of scope** —
  STDIO servers pull creds from the environment. Going remote is precisely what forces this layer.
- **Maturity:** actively evolving. `2025-06-18` made PRM mandatory and removed default-endpoint
  fallbacks; `2025-11-25` added CIMD as the preferred no-prior-relationship path. Track
  `modelcontextprotocol.io` before building.

---

### Tier 1 — IdP as authorization server

You host a thin resource-server shim in front of the wiki MCP server; the IdP issues and validates
tokens. All of these require you to assemble team-scoping yourself from the vendor's Organizations
primitive plus a custom token claim.

#### WorkOS AuthKit for MCP

**[WorkOS AuthKit for MCP](https://workos.com/docs/authkit/mcp)** extends WorkOS's hosted AuthKit
(built on WorkOS Connect) to act as the OAuth 2.1 authorization server for an MCP resource server. The
fastest path to a spec-compliant OAuth layer without writing an authorization server.

- **Three integration modes:** (1) build-your-own OAuth; (2) "WorkOS as a bridge" — WorkOS runs the
  OAuth dance while your app keeps its own user store; (3) AuthKit handles login end-to-end.
- **Your server only needs to:** verify AuthKit JWTs (via JWKS) and expose the discovery metadata
  endpoint (`.well-known/oauth-protected-resource`). WorkOS does the AS side.
- **Setup:** enable **CIMD** in the WorkOS Dashboard (Connect → Configuration) and register the MCP
  server's canonical URL as a **Resource Indicator** so tokens bind per RFC 8707.
- **Team hook:** WorkOS has first-class **Organizations** (teams) with directory sync/SSO; access tokens
  can carry an `org_id` claim — the natural per-team scoping hook. **But** the AuthKit-for-MCP page does
  **not** spell out org-scoping steps; you combine it with WorkOS's general multi-tenant Organizations
  feature yourself.
- **Compat caveat:** WorkOS documents that "not every client may support the latest version of the
  spec" and recommends a backward-compat proxy endpoint for clients lacking PRM support.
- **Docs:** product [workos.com/mcp](https://workos.com/mcp); walkthrough
  [how-to-add-authentication-to-your-mcp-server](https://workos.com/blog/how-to-add-authentication-to-your-mcp-server).
- **Pricing:** usage-based, **no per-seat fees, publicly listed** (per WorkOS's own comparison,
  [best-mcp-server-authentication-providers](https://workos.com/blog/best-mcp-server-authentication-providers)) — contrast with Auth0's quote-based pricing.
- **Constraints:** SaaS/proprietary, **no self-host**; per-team MCP scoping not documented step-by-step.
- **Maturity:** actively maintained, MCP-specific docs published 2025; established Series-funded vendor.
- **Verdict:** top candidate for gating by team — best-documented MCP-specific onboarding of the SaaS
  IdPs, transparent pricing, and Organizations give a ready-made team primitive to bind into claims.

#### Stytch — Connected Apps / hosted MCP server

**[Stytch Connected Apps](https://stytch.com/docs/guides/connected-apps/mcp-server-overview)** turns
Stytch into either the IdP embedded in your MCP server or a delegated authorization server your app
already trusts, purpose-built for the MCP OAuth flow.

- **Two architectures:** *Embedded* (the MCP server itself becomes the OAuth IdP) vs *Delegated* (your
  existing app is the IdP for both the web app and the MCP server).
- Bearer token in the `Authorization` header, issued via Connected Apps after end-user consent; server
  rejects missing/invalid/expired tokens with `401`. Full **DCR** and **PRM** support.
- **Team hook:** a distinct **B2B product line**
  ([b2b/guides/connected-apps/mcp-server-overview](https://stytch.com/docs/b2b/guides/connected-apps/mcp-server-overview))
  already models **Organizations/teams/roles** as first-class — arguably a *more direct* fit for "gate a
  shared wiki by team" than WorkOS, separate from the B2C flow
  ([consumer overview](https://stytch.com/docs/connected-apps/guides/mcp-auth-overview)).
- **Hosted reference:** `mcp.stytch.dev` is a live hosted hostname that lets you configure OAuth flows
  for your own MCP server programmatically, no dashboard.
- **Cloudflare pairing:** ships a
  [Workers walkthrough](https://stytch.com/blog/building-an-mcp-server-oauth-cloudflare-workers/) — pairs
  naturally with hosting the wiki server on Workers.
- **Constraints:** SaaS/proprietary, **no self-host**. **Pricing in flux** — Stytch was acquired by
  Twilio; WorkOS's comparison flags eventual re-bundling into Twilio pricing. Treat current published
  pricing as provisional.
- **Maturity:** active; Connected Apps + MCP docs current as of 2025 spec revisions; `mcp.stytch.dev` is
  a live reference deployment.
- **Verdict:** evaluate alongside WorkOS — B2B Organizations/roles are the more direct team fit, but
  post-Twilio pricing stability is a near-term risk.

#### Descope — MCP Auth / Agentic Identity Hub

**[Descope MCP Auth](https://docs.descope.com/mcp)** provides an OAuth 2.1 discovery endpoint plus
per-language SDKs (Python, Express) that make Descope the authorization server, with the most explicit
**per-tool scope model** of any surveyed provider.

- MCP server = Resource Server, Descope = Authorization Server; the `.well-known` OpenID config exposes
  authorization, token, JWKS, and (if enabled) DCR endpoints.
- **Recommends one OAuth scope per MCP tool or tool group** — scopes land in the access token so the
  server checks which operations a team may invoke. This is a clean fit for scoping **wiki-query vs
  wiki-capture vs wiki-ingest vs wiki-lint** separately (read vs write gating per team).
- **"Connections"** stores per-user or per-tenant OAuth credentials for downstream APIs the tools call,
  each with its own scopes and auto-refresh — useful if the wiki server must call a hosted git remote
  per team.
- Client registration: manual (Descope Console) or automatic via CIMD/DCR.
- SDKs: Python MCP SDK (token validation with scope + audience enforcement) and an Express SDK
  (spec-compliant authorization middleware).
- **Docs:** [Agentic Identity Hub](https://docs.descope.com/agentic-identity-hub);
  [MCP-servers management](https://docs.descope.com/agentic-identity-hub/mcp-servers). Their self-authored
  [comparison of 5 MCP auth solutions](https://www.descope.com/blog/post/mcp-authentication-solutions)
  (read with vendor bias).
- **Team gap:** no explicit team/tenant hierarchy beyond "Connections" per-tenant credentials — team
  scoping again via custom claims (e.g. `tenant_id`), not turnkey.
- **Constraints:** SaaS/proprietary; **pricing not surfaced** in fetched docs — check the pricing page
  before commitment.
- **Maturity:** active; MCP docs + SDKs current, positioned as a core product line, not a bolt-on.
- **Verdict:** evaluate specifically for **per-tool scope granularity** — if the wiki gate must differ
  between read and write operations per team, Descope's scope-per-tool convention is the most directly
  reusable pattern surveyed.

#### Auth0 (by Okta) — Auth for MCP

**[Auth0 Auth for MCP](https://auth0.com/ai/docs/auth-for-mcp)** is a **GA** product providing OAuth 2.1
authorization-server support for MCP resource servers, layered on Auth0's enterprise IdP (orgs, RBAC,
enterprise connections).

- Standard pattern: Auth0 = AS, your MCP server = RS, same PRM/DCR/PKCE flow. Quickstart:
  [authorization-for-your-mcp-server](https://auth0.com/ai/docs/mcp/get-started/authorization-for-your-mcp-server).
- **Team hook:** Auth0 **Organizations** are a documented multi-tenant primitive mapping onto "gate by
  team." Main win is SSO reuse if the org already standardizes on Auth0/Okta for workforce identity.
- **Rate limits:** Auth0's Management API rate limits apply when the Auth0 MCP server is used
  administratively — separate from limits on a custom server merely using Auth0 for auth.
- **Distinct from Okta's own MCP server:**
  [`okta/okta-mcp-server`](https://github.com/okta/okta-mcp-server) is a self-hosted MCP server for
  *managing Okta itself* (OAuth Device Authorization Grant or Private-Key JWT), **not** a generic auth
  layer for hosting someone else's MCP server. Its **scope convention is reusable**, though: env var
  `OKTA_SCOPES` (e.g. `okta.users.read`) maps 1:1 to tool availability, enforced **twice** — a startup
  filter that silently removes tools the caller's scopes don't cover, plus a runtime scope-guard
  decorator. Directly reusable for gating wiki tools per scope. For gating the wiki, the relevant piece
  is Okta-as-IdP via Auth0 or Okta's
  [configure-mcp-authentication guide](https://developer.okta.com/docs/guides/configure-mcp-authentication/main/).
- **Pricing:** enterprise/quote-based beyond a free developer tier — WorkOS's comparison calls it
  "opaque… making budgeting difficult during evaluation" ([auth0.com/pricing](https://auth0.com/pricing)).
- **Constraints:** SaaS/proprietary; free dev tier exists but production features (enterprise
  connections, FGA, advanced MFA) are quote-based.
- **Maturity:** GA 2025-2026; mature, widely-deployed, Okta-owned.
- **Verdict:** evaluate **only if the org already runs Auth0/Okta** as workforce IdP (SSO reuse is the
  win); otherwise WorkOS/Stytch are more MCP-native and cheaper to start given Auth0's opaque pricing.

#### Clerk — @clerk/mcp-tools

**[Clerk MCP OAuth](https://clerk.com/docs/guides/ai/mcp/build-mcp-server)** is an open-source helper
package (`@clerk/mcp-tools`) plus framework guides (Express, Next.js) providing OAuth-protected-resource
middleware and metadata handlers for a server backed by Clerk-issued JWTs. Best fit if the team's app
already uses Clerk.

- `mcpAuthClerk` middleware auto-verifies the `Authorization` header against Clerk OAuth access tokens.
- `protectedResourceHandlerClerk` is an Express handler serving the PRM document
  (`.well-known/oauth-protected-resource`) with configurable supported scopes.
- Clerk issues OAuth access tokens as **self-contained JWTs** by default — verifiable without a network
  round-trip to Clerk.
- **Vercel/Next.js:** `withMcpAuth()` wraps an MCP handler using Clerk's `auth()` + `verifyClerkToken()`
  to extract session/org context from the token.
- **Cursor** integration works with just a URL — OAuth handled transparently by the MCP handshake, no
  separate stdio/command config.
- **Team hook:** Clerk **Organizations** (roles/permissions) are first-class; combine with the token's
  org claim for per-team scoping — **not** spelled out as a dedicated "MCP + Organizations" doc page in
  what was fetched.
- **Repos:** library [`clerk/mcp-tools`](https://github.com/clerk/mcp-tools) (npm `@clerk/mcp-tools`,
  framework-agnostic core + Express/Next.js adapters); reference
  [`clerk/mcp-demo`](https://github.com/clerk/mcp-demo).
- **Constraints:** Clerk backend is SaaS/proprietary (the MCP helpers are open source); pricing follows
  Clerk's per-MAU tiers (not independently confirmed this pass).
- **Maturity:** active; MCP support shipped mid-2025 (Express MCP changelog 2025-07-29); demo + docs
  current.
- **Verdict:** adopt as a **lightweight code-first option** if hosting the wiki server as a small
  Node/TS service (Vercel/Workers) rather than wanting a managed AS dashboard — cheaper/simpler than
  WorkOS/Auth0 for a small team, at the cost of writing more glue yourself.

#### Ory (Hydra / Ory Network) — the self-host-first option

**[`@ory/mcp-oauth-provider`](https://github.com/ory/mcp)** is Ory's TypeScript OAuth-provider
implementation for MCP, backed by either **self-hosted Ory Hydra** (open-source OAuth2/OIDC server) or
the managed **Ory Network** SaaS. The one surveyed option offering a genuinely **open-source,
self-hostable** OAuth2/OIDC server purpose-fitted with an MCP adapter — relevant if the "canonical files,
disposable layers" philosophy should extend to auth (no vendor lock-in on identity either).

- The npm package ([`@ory/mcp-oauth-provider`](https://www.npmjs.com/package/@ory/mcp-oauth-provider))
  implements the authorization-code + PKCE flow, client registration/management, and token
  introspection/verification, pointable at either backend via config.
- **Ory Hydra** itself is a standalone, **certified** OAuth2/OIDC provider (not MCP-specific); the MCP
  package is a thin adapter on top.
- **End-to-end walkthrough:** ["Ory Hydra + Claude Code + ChatGPT"](https://getlarge.eu/blog/securing-mcp-servers-with-oauth2-ory-hydra-claude-code-chatgpt/)
  (mirrored on dev.to) shows self-hosted Hydra securing an MCP server against both Claude Code and
  ChatGPT as clients.
- **Team gap:** no native team/tenant concept surfaced — Hydra issues standard OAuth2 tokens; team
  scoping via custom claims/consent-flow logic, same as the rest.
- **License/pricing:** Hydra product page [ory.com/hydra](https://www.ory.com/hydra) — open source
  (Apache-2.0-family historically; **confirm on the repo before relying on it**) with a paid Ory Network
  hosted tier (pricing not confirmed this pass).
- **Constraints:** if self-hosting Hydra you operate and secure an OAuth2 server yourself — real ops
  burden vs. SaaS.
- **Maturity:** Hydra is mature and widely deployed; the **MCP adapter is newer (2025-era) and thinner**
  — treat the MCP glue as less battle-tested than Hydra itself.
- **Verdict:** adopt as the **self-host-first candidate** if avoiding SaaS lock-in on auth is a priority
  consistent with "files are canonical, everything else disposable" — run Hydra alongside the wiki
  server, keep OAuth as replaceable infrastructure rather than a vendor relationship.

---

### Tier 2 — Network-level gate

#### Cloudflare Access + Workers OAuth Provider

**[Cloudflare remote MCP](https://developers.cloudflare.com/agents/guides/remote-mcp-server/)** is two
related offerings: (1) **deploy** the MCP server on Cloudflare Workers using the `workers-oauth-provider`
library with a custom OAuth handler, and (2) **front** any MCP server with **Cloudflare Access** as a
zero-trust SSO gate, independent of the app's own auth.

- **Workers path:** you write a custom OAuth handler (e.g. `GitHubHandler`) inside Cloudflare's
  `OAuthProvider` framework. Cloudflare does **not** supply a turnkey MCP-specific auth server — you
  wire up the chosen upstream IdP yourself. Documented to work with "any OAuth provider that supports
  the OAuth 2.0 specification, including GitHub, Google, Slack, Stytch, Auth0, WorkOS, and more" — i.e.
  `OAuthProvider` is **IdP-agnostic middleware, not itself an IdP**. Deploy via **Wrangler CLI** to a
  `*.workers.dev` subdomain or custom domain — self-hosted on your own Cloudflare account, not a shared
  SaaS auth server.
- **Access path** (separate product,
  [secure-mcp-servers](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/secure-mcp-servers/))
  acts as an identity aggregator in front of the endpoint, verifying email/IdP signals (GitHub, Google,
  …) plus device posture/IP, **entirely orthogonal** to whatever auth the MCP server implements — it
  gates access before a request ever reaches the app. Cloudflare's docs state "Cloudflare Access handles
  the full OAuth flow automatically — the MCP server does not need to implement any authorization logic"
  when used this way, i.e. Access can **fully substitute** for building in-app OAuth.
- **MCP server portals**
  ([mcp-portals](https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/))
  present a curated, per-user/per-group catalog of MCP servers behind Access — a plausible mechanism for
  **per-team wiki-server visibility**.
- **Joint walkthrough:** [Auth0 + Cloudflare](https://auth0.com/blog/secure-and-deploy-remote-mcp-servers-with-auth0-and-cloudflare/).
- **Pricing:** Workers has a generous free tier for small-scale use; **exact Access pricing/seat costs
  not confirmed** this pass — check [cloudflare-one](https://developers.cloudflare.com/cloudflare-one/)
  pricing before committing.
- **Constraints:** Access pricing/seat limits unconfirmed; Workers OAuthProvider requires you to write
  the IdP integration yourself (no managed dashboard).
- **Maturity:** active first-party Cloudflare product with a dedicated "AI controls" doc section as of
  2025-2026; widely used, referenced by Auth0's own blog.
- **Verdict:** adopt **Cloudflare Access as the network-level team gate regardless** of which OAuth/IdP
  you pick for the token layer — a clean, IdP-agnostic way to say "only members of Team X's IdP group can
  even reach `mcp.example.com`," complementary to (not a replacement for) spec-compliant PRM/OAuth inside
  the app when fine-grained per-tool scopes are also needed.

---

### Tier 3 — Full MCP gateway / control-plane

These bundle OAuth brokering + RBAC + per-team catalog scoping + audit + routing to many upstream MCP
servers, of which the wiki would be just one. Heavier to adopt than "just OAuth" — but the only ones with
**documented turnkey per-team scoping**. All remain disposable layers governing *access to tools/servers*,
never the markdown store's format.

#### Gram (Speakeasy)

**[Gram](https://github.com/speakeasy-api/gram)** (Speakeasy) is a "complete MCP cloud" — a control plane
for building, hosting, securing, and monitoring MCP servers/tools/skills, generated from REST APIs or
hand-written TypeScript, **open-sourced AGPL-3.0** with both a hosted SaaS (`app.getgram.ai`) and a
self-host path. **Closest surveyed match to "a wiki multiple teams can use."**

- **Multi-tenant governance:** "permission down to the server, toolset, or individual tool" plus
  "provision sub-catalogs so every team and role sees only what they should" — **the most explicit
  documented per-team scoping of any tool surveyed.**
- **Centralized IdP:** "Plug your IdP into one place, and every MCP server behind the gateway inherits
  their auth." Supports OAuth 2.1, DCR, PKCE **even for upstream MCP servers that don't natively support
  OAuth** (Gram back-fills spec compliance). Named IdP integrations: **Okta, Azure AD, Google
  Workspace**. Enforces RBAC; every tool call / permission change / access event is logged and
  searchable.
- **Certs:** claims **SOC 2 Type II and ISO 27001** for the hosted offering.
- **Self-host:** via a `./zero` script in the repo (exact flags unconfirmed — read the repo's setup docs
  first); hosted billing mentions "Polar" for usage-based billing.
- **Codebase:** Go (63.6%) + TS (30.3%); 4,327 commits, 556 releases, 251 stars / 32 forks at check —
  active but a **relatively small community** vs Docker's ecosystem.
- **Docs:** [why-gram](https://www.speakeasy.com/docs/mcp/why-gram);
  [product](https://www.speakeasy.com/product/gram);
  [choosing-an-mcp-gateway](https://www.speakeasy.com/blog/choosing-an-mcp-gateway) (positions itself vs
  Docker MCP Gateway, Composio, Arcade, TrueFoundry — useful landscape map, treat as marketing).
- **Pricing:** no hosted-tier figures surfaced this pass — check `app.getgram.ai/pricing`.
- **Constraints:** **AGPL-3.0** copyleft — check acceptability if you *modify and redistribute Gram
  itself*, though merely running it as infrastructure in front of the wiki is not a distribution concern;
  hosted pricing unconfirmed; smaller OSS community so operational maturity less proven.
- **Maturity:** active (frequent releases), still early by star count; positions as enterprise-ready
  (SOC2/ISO) for the hosted tier.
- **Verdict:** **adopt for a serious pilot** — the only surveyed tool bundling OAuth 2.1 +
  per-team/per-toolset sub-catalogs + RBAC + audit in one place, directly matching "gate a shared wiki by
  team," and AGPL self-host keeps a non-SaaS escape hatch. Gram is only the disposable access/gateway
  layer in front of the markdown files, never the store.

#### Obot

**[Obot](https://github.com/obot-platform/obot)** is an open-source, **Kubernetes-native** "complete MCP
platform" — hosting, registry, gateway, and its own chat client — centralizing OAuth, RBAC, and audit for
a curated catalog of MCP servers reachable by Claude, Cursor, VS Code, and custom agents. Direct
alternative to Gram, distinguished by an explicit RBAC-roles model and IdP-group→registry mapping.

- Sits between AI clients and any MCP server (local, remote, hosted), enforcing OAuth, applying policies,
  auditing every call.
- **Centralized OAuth** with built-in IdP integrations: **Google, GitHub, Okta, JumpCloud, Microsoft
  Entra** (Auth0 **not** listed in fetched material, unlike Gram/Docker).
- **Explicit RBAC roles:** Admin, Auditor, Owner, plus **per-user AND per-team policies** defining which
  servers each person/team can access, plus tool-level permissions beneath server-level access.
- **"IdP-mapped registries":** connect IdP groups directly to MCP-catalog availability — team membership
  in the IdP (an Okta/Entra group) is the scoping mechanism, rather than a bespoke team object inside
  Obot.
- Token brokering, scope enforcement, and rotation are handled centrally by the gateway, not each MCP
  server.
- **Multi-user config patterns documented:** (a) shared credentials (one org-wide API key all users
  leverage) vs (b) self-authenticating servers where OAuth/multi-tenancy is handled by the upstream MCP
  server itself — the design choice for whether the wiki server bakes in its own per-user OAuth or relies
  on Obot's brokered single credential.
- **Deployment:** fully self-hostable on any Kubernetes cluster (**Open Source Edition, free**), or
  Obot's hosted/cloud SaaS with "dedicated environment" enterprise framing. A paid **Enterprise Edition**
  adds Okta/Entra support and other features on top of self-hosted — **implying the free OSS edition's
  IdP support may be more limited** than enterprise. **Verify exact feature gating** against
  [docs.obot.ai](https://docs.obot.ai/functionality/mcp-servers/) before relying on Okta/Entra in the
  free tier.
- **Docs/pages:** [obot.ai](https://obot.ai/);
  [mcp-gateway-platform](https://obot.ai/mcp-gateway-platform/);
  [mcp-auth-solution](https://obot.ai/mcp-auth-solution/).
- **Pricing:** no Enterprise/hosted figures surfaced — check obot.ai directly.
- **Constraints:** Enterprise feature gating and both Enterprise + hosted-SaaS pricing unconfirmed;
  requires **Kubernetes** for self-host — a nontrivial ops dependency if the team has no k8s. Obot core
  license terms not confirmed this pass — verify the repo's LICENSE.
- **Maturity:** active (`obot-platform` org); a complete platform (hosting + registry + gateway + chat)
  — broader scope than Gram but more infrastructure to operate.
- **Verdict:** **adopt as the other top-tier candidate alongside Gram** — Kubernetes-native self-host
  plus explicit RBAC roles and IdP-group→catalog mapping is a better operational fit for a team already
  running k8s, and it is unambiguously open source at the base tier.

#### Docker MCP Gateway — disqualified for this goal

**[Docker MCP Gateway](https://github.com/docker/mcp-gateway)** runs each MCP server in its own container
behind a single local gateway process; handles OAuth token acquisition/refresh for servers that call
third-party APIs and enforces Bearer auth on the gateway's own endpoint. **Least suited of the gateways
to "cloud, team-shared"** — explicitly a local/self-hosted, single-operator **Docker Desktop-centric**
tool with **no multi-tenant/team-auth model.**

- Architecture: `AI Client → MCP Gateway → MCP Servers (each in its own container)`; the gateway is the
  single point that owns secrets/OAuth tokens so server containers never see raw credentials.
- `docker mcp oauth authorize <server>` triggers a browser-based OAuth flow per upstream service; Docker
  Desktop's secrets manager stores the tokens (not env vars).
- Built-in **Caddy** reverse proxy enforces Bearer auth on the exposed API even if the port is
  accidentally public.
- **No per-team/tenant scoping** — `docker mcp profile create/list/show/remove` groups **servers**, not
  users/teams. Single-operator tool.
- A community variant, [`hwdsl2/docker-mcp-gateway`](https://github.com/hwdsl2/docker-mcp-gateway)
  (MCPHub + Caddy, multi-arch amd64/arm64), packages a self-hosted multi-server hub with Bearer auth for
  streaming HTTP/SSE — closer to a minimal shared gateway, but still **not multi-tenant/team-aware** out
  of the box.
- **License:** MIT, free; **self-hosted only**; requires **Docker Desktop 4.59+**. 1,012 commits, 1.5k
  stars at check.
- **Commands:** `docker mcp profile …`; `docker mcp gateway run --profile <name>`;
  `docker mcp tools ls/call`; `docker mcp client connect <client-name>`; `docker mcp secret …`;
  `docker mcp oauth authorize <server>`. Docs:
  [mcp-gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/).
- **Verdict:** **avoid as the shared-team gateway** — no team auth model, and the Docker Desktop
  dependency reinforces the "runs on someone's machine" problem this research is meant to escape.
  Steal-the-idea only: the gateway-owns-the-secrets architecture and Caddy-enforced Bearer auth if
  building a custom gateway.

---

### Transport bridges — not auth solutions

#### mcp-proxy (sparfenyuk and TBXark variants)

**[sparfenyuk/mcp-proxy](https://github.com/sparfenyuk/mcp-proxy)** and TBXark's variant are two
**unrelated** projects sharing a name. Neither implements team scoping or spec-compliant PRM/DCR;
relevant only for the narrow case of exposing a **stdio-only** MCP server (e.g. today's Obsidian-MCP) over
HTTP so a gateway/OAuth layer can sit in front.

- **sparfenyuk/mcp-proxy** (Python, [PyPI `mcp-proxy`](https://pypi.org/project/mcp-proxy/)): bridges
  `stdio ↔ SSE/StreamableHTTP`; supports optional auth headers and OAuth2 **client-credentials**
  (client-id/secret/token-url as CLI args). Crucially this authenticates the proxy **outbound to an
  upstream server** — it is **not** the proxy acting as a resource server validating **inbound** client
  tokens. Ships a container image; named backend servers via CLI/JSON.
  **[Open issue #108](https://github.com/sparfenyuk/mcp-proxy/issues/108)** requests API-key auth to
  secure the proxy's own endpoints — as of that issue, **no first-class inbound-auth/multi-tenant story.**
- **TBXark/mcp-proxy** ([docs](https://tbxark.github.io/mcp-proxy/)): a separate Go project that
  aggregates multiple upstream MCP servers behind one HTTP endpoint — an aggregation/fan-out gateway,
  distinct codebase and purpose despite the shared name.
- **Constraints:** open source (license not independently confirmed — check repo LICENSE before
  adoption); no SaaS, no team/tenant model.
- **Maturity:** sparfenyuk's is widely referenced (mcpservers.org, Awesome MCP Servers) but the
  missing-auth issue signals inbound security is still immature.
- **Verdict:** **avoid as an auth/multi-tenancy solution.** Steal-the-idea only if the wiki server stays
  stdio-based and needs a thin HTTP bridge — pair it with a real OAuth-terminating reverse proxy
  (Cloudflare Access, Caddy+Bearer, or a Tier-3 gateway) in front, since it provides no inbound
  authentication by default.

---

### Capability comparison

| Tool | Tier | Self-host | Native per-team scoping | License | Pricing (this pass) | Cloud/team-shared fit |
|---|---|---|---|---|---|---|
| MCP Auth spec | contract | — | No (must add claim + server check) | none | none | The mandatory baseline |
| WorkOS AuthKit | 1 IdP | No | Assemble (Organizations + custom claim) | Proprietary | Usage-based, public, no per-seat | Strong — best MCP docs |
| Stytch Connected Apps | 1 IdP | No | Assemble (B2B Orgs/roles — closer) | Proprietary | In flux (Twilio acq.) | Strong (B2B) — pricing risk |
| Descope | 1 IdP | No | Assemble (`tenant_id` claim); best per-tool scopes | Proprietary | Not surfaced | Good for read/write gating |
| Auth0 / Okta | 1 IdP | No | Assemble (Auth0 Organizations) | Proprietary | Quote-based, opaque | Only if already on Auth0/Okta |
| Clerk | 1 IdP | No (helpers OSS) | Assemble (Organizations + org claim) | Proprietary + OSS helpers | Per-MAU (unconfirmed) | Lightweight code-first |
| Ory Hydra / Network | 1 IdP | **Yes (Hydra)** | Assemble (custom claims) | OSS (verify) + paid tier | Network unconfirmed | Self-host-first, anti-lock-in |
| Cloudflare Access + Workers | 2 net gate | Yes (own CF acct) | Group→portal visibility; IdP-agnostic | Proprietary | Workers free tier; Access unconfirmed | Stack under any Tier-1 |
| **Gram (Speakeasy)** | 3 gateway | **Yes (`./zero`)** | **Turnkey sub-catalogs + RBAC** | **AGPL-3.0** | Hosted unconfirmed | **Direct fit (pilot)** |
| **Obot** | 3 gateway | **Yes (k8s)** | **Turnkey RBAC roles + IdP-group→registry** | OSS base + paid Enterprise | Unconfirmed | **Direct fit (needs k8s)** |
| Docker MCP Gateway | 3 gateway | Yes (Docker Desktop) | **No** | MIT | Free | **Disqualified — local, no team auth** |
| sparfenyuk/mcp-proxy | bridge | Yes | **No (no inbound auth)** | OSS (verify) | Free | Not an auth solution |
| TBXark/mcp-proxy | bridge | Yes | **No** | OSS (verify) | Free | Aggregation only |

---

### Recommendation for this cluster

**First, adopt the fixed contract unconditionally.** Whatever else is chosen, the cloud wiki MCP server
must implement RFC 9728 PRM + RFC 8707 Resource Indicators + OAuth 2.1 + PKCE S256, and — because **no
vendor ships per-team scoping turnkey** — its own tool layer must check a `team`/`org_id` claim before
serving query/capture/ingest/lint. Budget for that server-side authorization check regardless of vendor.

**Ranking for this wiki:**

1. **Gram (Speakeasy) — top pilot candidate.** It is the only surveyed tool that bundles OAuth 2.1 +
   per-team/per-toolset sub-catalogs + RBAC + audit in one product, directly matching "gate a shared wiki
   by team," and its AGPL self-host path (`./zero`) keeps a non-SaaS escape hatch consistent with the
   canonical-files philosophy. Verify AGPL acceptability and hosted pricing; confirm it treats the wiki
   server purely as a governed upstream (it does — it governs access to tools, not file format).
2. **Obot — co-top candidate, better if the team runs Kubernetes.** Explicit Admin/Auditor/Owner RBAC and
   IdP-group→registry mapping make team scoping first-class; open source at the base tier. Cost: a k8s
   ops dependency and unconfirmed Enterprise-tier gating for Okta/Entra — verify which IdP integrations
   are in the free edition before committing.
3. **WorkOS AuthKit (+ optionally Cloudflare Access in front) — lightest spec-compliant path** if a full
   gateway is overkill for one wiki server. Best-documented MCP onboarding, transparent usage-based
   pricing, and Organizations as the team primitive. You assemble org-scoping yourself, but the surface
   is small. **Stack Cloudflare Access** in front as an IdP-agnostic network gate ("only Team X's IdP
   group can reach `mcp.example.com`") — cheap defense-in-depth over any Tier-1 choice, and Workers is a
   viable cheap host for the server itself.
4. **Ory Hydra — pick this over WorkOS if avoiding SaaS lock-in on auth is a hard priority** consistent
   with "files canonical, everything else disposable." You run and secure the OAuth2 server yourself; the
   MCP adapter is thinner/newer than Hydra's mature core.
5. **Descope — a specialist pick** when read (query) vs write (capture/ingest/lint) must be gated per team
   at the tool level; its scope-per-tool convention is the most directly reusable pattern.
6. **Stytch (B2B), Clerk, Auth0/Okta — situational.** Choose the one you already run for app/workforce
   identity to reuse SSO; otherwise they are strictly behind WorkOS on MCP-nativeness, pricing clarity,
   or (Stytch) pricing stability.
7. **Docker MCP Gateway and both mcp-proxy variants — do not use as the shared layer.** Docker MCP
   Gateway is a local single-operator tool with no team auth; mcp-proxy variants are transport bridges
   with no inbound auth (open issue #108). Reuse only their patterns: Docker's gateway-owns-the-secrets +
   Caddy Bearer enforcement, and mcp-proxy's stdio↔HTTP bridge if the wiki must temporarily stay
   stdio-based behind a real OAuth-terminating proxy.

Every option is a **disposable access-control layer in front of the git-diffable markdown files** — none
becomes the store, so all satisfy the hard constraint. The heavier platforms (Gram, Obot) govern access
to *tools and servers*, not the content format, so even they leave the markdown canonical.
