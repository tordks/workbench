# workbench

An opinionated engineering setup and workflow. Two halves that fit together:

- a **karpathy-style LLM wiki** (`wiki/`)
- the **skills** (`skills/`) unique to this workflow


## Quickstart

```
# Install the skills — the general engineering set, then this repo's workflow skills on top
npx skills@latest add mattpocock/skills     # select all the default skills
npx skills@latest add tordks/workbench      # pick the wiki and/or workflow group when prompted

# Per repo, once — set up the general conventions, then converge to these on top
/setup-matt-pocock-skills
/setup-skills

# To edit the wiki: open `wiki/` (not the repo root) as an Obsidian vault, then `pre-commit install`
# The wiki-* skills reach the vault over MCP — see "Connecting the agent to the vault" below
```


## The workflow

The path most work travels, from idea to shipped code. Each named step is a skill. Some defined in
this repo and some from the matt pocock skills. At a glance the steps are:

1. **Sharpen the idea** — interview until the plan/spec holds together; prototype when a question needs a runnable answer.
2. **Split the work** — a multi-session build becomes a PRD, then independently grabbable issues; a single session goes straight to implementation.
3. **Pick what's next** — `/backlog` presents the open issues in dependency order.
4. **Build** — `/orchestrate` delegates each unit to a subagent sequentially, or you implement a single unit directly with `/implement`.
5. **Review** — `/code-review` for code against standards and spec, `/review-docs` for docstrings/comments/prose. Run automatically after each unit by `/orchestrate`
6. **Bank the learnings** — `/wiki-capture` parks durable findings to the wiki inbox; `/wiki-ingest`
   folds them into the wiki.

For the full sett of skills and how to use them see [`workflow`](wiki/practices/workflow.md).


## The wiki

A [karpathy-style LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): a
knowledge base **written and read mainly by agents**, so durable learnings from one project carry
into the next. It has three layers — immutable **raw sources** (`sources/`), an agent-owned
**synthesized wiki**, and a **schema doc** (`wiki/_schema.md`) that teaches an agent how to maintain
it — plus an `inbox/` staging lane for raw captures. The agent works it through four operations, one
skill each: **capture** (`inbox/`), **query**, **ingest**, **lint**. Step 6 of the workflow captures
and ingests into it; later work queries it.

**The tooling is still in progress on both sides.** The `wiki-*` skills the agent uses to read and
edit the wiki reach the vault through the **Obsidian Local REST API MCP server** (so they run
wherever the agent runs, and depend on Obsidian being open — see below); they are unreviewed and
unfinished, and the human-facing side is thin: for now you can open the `wiki/` folder as an Obsidian
vault to read and hand-edit it; a minimal `.obsidian/` config is committed.

Two lint tiers guard against decay:
- **Syntactic (automated):** `pre-commit install`, then every commit runs dead-link, broken-anchor,
  and markdown-style checks.
- **Structural + semantic (on demand):** the `wiki-lint` skill — an MCP `search_query` over the note
  graph finds orphans and dead-ends (dangling links need a content diff); the agent reads for
  contradictions, near-duplicates, stale claims, provenance drift, and tag drift (no tool does the
  reading).

### Connecting the agent to the vault (Obsidian Local REST API + MCP)

The `wiki-*` skills call the MCP tools served by the
[Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin (v4.1.3+).
The plugin runs **inside one vault** and serves *that* vault — there is no vault argument; its paths
are relative to the vault root. So to point the skills at the wiki, register the plugin instance
running in the `wiki/` vault:

1. Open `wiki/` (not the repo root) as an Obsidian vault. In **Settings → Community plugins**, install
   and enable **Local REST API**.
2. In **Settings → Local REST API**, copy the **API key**. The HTTPS endpoint is
   `https://127.0.0.1:27124` (self-signed cert); the plugin serves MCP at `/mcp/` over Streamable
   HTTP + bearer token.
3. Register it with Claude Code under the name **`obsidian`** (this name sets the tool prefix
   `mcp__obsidian__*` the skills assume):

   ```
   claude mcp add --transport http obsidian https://127.0.0.1:27124/mcp/ \
     --header "Authorization: Bearer <API_KEY>"
   ```

Gotchas:
- **Self-signed cert.** The HTTPS port uses a cert the plugin generates; trust it, or enable the
  plugin's non-encrypted HTTP port `27123` and register that endpoint instead.
- **WSL → Windows.** The plugin binds **loopback on the machine running Obsidian**. If Claude Code
  runs in WSL while Obsidian runs on Windows, `127.0.0.1` inside WSL does not reach it — use WSL
  [mirrored networking](https://learn.microsoft.com/windows/wsl/networking#mirrored-mode-networking)
  (`networkingMode=mirrored` in `.wslconfig`) so `127.0.0.1` is shared, or forward the port.
- **Multiple vaults.** Run the plugin in each on a **distinct port** and register each as its own MCP
  server (`obsidian`, `obsidian-work`, …) pointing at its port — the server name is just a label; the
  vault it reaches is fixed by the port.
