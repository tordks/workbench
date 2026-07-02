---
type: reference
title: Obsidian Local REST API + MCP
aliases: [obsidian-local-rest-api, obsidian-rest-api, obsidian-mcp]
tags: [tooling, ai]
created: 2026-07-02
updated: 2026-07-02
status: seed
source: "[[obsidian-local-rest-api-docs]]"
related: ["[[obsidian-cli-on-wsl]]"]
---

# Obsidian Local REST API + MCP

The `coddingtonbear/obsidian-local-rest-api` community plugin exposes the vault over a local REST API
**and a built-in MCP server**, both served from inside the running desktop app. The MCP server gives a
client structured tools; the REST API gives it raw HTTP endpoints over the same vault.

## What it serves

- **A plugin, not a binary.** It lives in the desktop app; the app must be running for the endpoints
  to answer.
- **Ports:** `https://127.0.0.1:27124` (self-signed cert) and optionally `http://127.0.0.1:27123`
  (must be enabled in the plugin settings). Both bind **loopback on the machine running Obsidian**.
- **Auth:** bearer token — `Authorization: Bearer <api-key>` — generated in
  **Settings → Local REST API**.

## MCP tools

Served at `/mcp/` over Streamable HTTP. The advertised tools:

| tool | does |
|---|---|
| `vault_read` | read a note |
| `vault_write` | write/replace a note |
| `vault_patch` | **surgical** edit — target a heading, block ref, or frontmatter field without rewriting the file |
| `search_query` | search the vault |
| `command_execute` | run an Obsidian command |

`vault_patch` is the standout: it edits a single frontmatter field or appends under one heading
without rewriting the whole note.

## REST surface (when a raw HTTP call is needed)

- `/vault/{path}` — file CRUD via `GET`/`PUT`/`PATCH`/`POST`/`DELETE`.
- `/active/` — the currently open note; `/periodic/{period}/` — daily/weekly/monthly notes.
- `/search/simple/` (full-text) and `/search/` (structured JsonLogic).
- `/commands/` — list and execute Obsidian commands; tag listing; open-file-in-UI.

## Compared to the Obsidian CLI

The [[obsidian-cli-on-wsl|Obsidian CLI]] drives the desktop app through a console binary, so a caller
scrapes stdout — which forces CRLF handling, PATH shims, and vault-by-name argument ordering. The MCP
returns structured results, removing that parsing fragility, at the cost of a network hop to the
loopback port instead of a local exec. Both require the desktop app to be running.
