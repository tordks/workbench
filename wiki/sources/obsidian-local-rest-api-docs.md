---
type: source
title: Obsidian Local REST API — plugin docs
aliases: [obsidian-local-rest-api-docs, obsidian-rest-api-docs]
tags: [tooling]
created: 2026-07-02
updated: 2026-07-02
status: evergreen
---

# Obsidian Local REST API — plugin docs

Stub for the `coddingtonbear/obsidian-local-rest-api` community plugin: a REST API and built-in MCP
server for accessing the vault programmatically.

**URL:** https://github.com/coddingtonbear/obsidian-local-rest-api

Faithful excerpt of the load-bearing facts:

- Runs as a **plugin inside the Obsidian desktop app** — the app must be running to serve requests.
- Listens on **`https://127.0.0.1:27124`** (HTTPS, self-signed cert) and optionally
  **`http://127.0.0.1:27123`** (HTTP, if enabled in settings).
- **Auth:** all requests need a bearer token — `Authorization: Bearer <api-key>`. The key is generated
  by the plugin and shown in **Settings → Local REST API**.
- **REST surface:**
  - File CRUD on `/vault/{path}` — `GET`, `PUT`, `PATCH`, `POST`, `DELETE`.
  - `/active/` — operate on the currently open note.
  - `/periodic/{period}/` — daily/weekly/monthly notes.
  - `/search/simple/` (full-text) and `/search/` (structured JsonLogic).
  - `/commands/` — list and execute Obsidian commands.
  - Tags listing (with usage counts); trigger the UI to open a file.
  - **PATCH** performs surgical edits: target a specific heading, block reference, or frontmatter
    field without rewriting the whole file.
- **Built-in MCP server** at **`/mcp/`**, Streamable HTTP transport, integrates with Claude Code,
  Cursor, and other MCP clients. Tools include `vault_read`, `vault_write`, `vault_patch`,
  `search_query`, `command_execute`.
