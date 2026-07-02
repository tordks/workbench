---
type: source
title: Obsidian CLI — official docs
aliases: [obsidian-cli-docs]
tags: [tooling]
created: 2026-07-02
updated: 2026-07-02
status: evergreen
---

# Obsidian CLI — official docs

Stub for the official documentation of the Obsidian command-line interface.

**URL:** https://obsidian.md/help/cli

Faithful excerpt of the load-bearing facts:

- Requires the Obsidian **1.12.7+** installer.
- Enabled from the desktop app: **Settings → General → "Command line interface"** toggle, then
  follow the prompt to register. PATH registration is automatic.
- On **Windows** the installer places a terminal redirector in the Obsidian install folder that wires
  the GUI to terminal I/O; registration adds Obsidian to the user PATH. **Restart the terminal** after
  registering for the PATH change to take.
- The command/binary is `obsidian`.
- The CLI **requires the desktop app to be running** — it drives the running app; the first command
  launches Obsidian if it is closed.
- Vaults are selected **by name**: `vault=<name>` as the first parameter *before* the command;
  otherwise the current-directory vault, then the active vault, is used.
- Command surface includes file ops (`read`, `create`, `delete`, `files`, `move`), link/graph
  analysis (`backlinks`, `links`, `unresolved`, `orphans`, `deadends`), `search`, `tags`, and `web` —
  where `web` opens a URL in Obsidian's in-app web viewer and does **not** fetch page content into a
  note.
