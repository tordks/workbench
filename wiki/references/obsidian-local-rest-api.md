---
type: reference
title: Obsidian Local REST API + MCP
aliases: [obsidian-local-rest-api, obsidian-rest-api, obsidian-mcp]
tags: [tooling, ai]
created: 2026-07-02
updated: 2026-07-03
status: draft
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

Served at `/mcp/` over Streamable HTTP. The tools (from the plugin's `openapi.yaml`):

| tool | does |
|---|---|
| `vault_read` | read a note (returns `NoteJson` with metadata) |
| `vault_write` / `vault_append` | write/replace, or append to, a note |
| `vault_patch` | **surgical** edit — target a heading, block ref, or frontmatter field without rewriting the file |
| `vault_delete` / `vault_move` | delete or move/rename a note |
| `vault_list` | list files/subdirs at a path |
| `vault_get_document_map` | a note's headings, block refs, frontmatter fields |
| `search_simple` | full-text, **fuzzy + ranked** — the only ranked path |
| `search_query` | structured **JsonLogic** over each note's `NoteJson` |
| `tag_list` | all tags in the vault with usage counts |
| `command_list` / `command_execute` | list and run Obsidian commands |
| `active_file_get_path` / `periodic_note_get_path` / `open_file` | active/periodic note, open in UI |

`vault_patch` is the standout: it edits a single frontmatter field or appends under one heading
without rewriting the whole note.

### `search_query` — the `NoteJson` fields

JsonLogic evaluates against each note's `NoteJson`. The top-level `var`s are `tags`, `frontmatter`,
`content`, `path`, `links` (resolved outlinks), `backlinks` (resolved inlinks), and `stat`
(`ctime`/`mtime`/`size`). Aliases and title are **not** top-level — reach them as
`frontmatter.aliases` / `frontmatter.title`; any frontmatter key is `frontmatter.<field>`. Dangling
`[[links]]` resolve to nothing and leave no trace in `links`/`backlinks`.

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
