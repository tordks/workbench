---
type: practice
title: Running the Obsidian CLI on WSL
aliases: [obsidian-cli-wsl, obsidian on wsl]
tags: [tooling]
created: 2026-07-02
updated: 2026-07-02
status: seed
source: "[[obsidian-cli-docs]]"
related: []
---

# Running the Obsidian CLI on WSL

How to make the `obsidian` command reach a vault when the vault lives on **WSL** but Obsidian runs on
**Windows**, so the command resolves to the right vault from any working directory.

## The mental model

The official Obsidian CLI is a **Windows** binary that **talks to the running desktop app** and
selects vaults **by name** — it is not a file editor and it is not cwd-aware. So on WSL you install it
Windows-side, reach it over **interop**, and wrap it so the current directory never decides which
vault you hit.

## Windows side — the human prerequisite

These operate **Windows-side** and cannot be scripted from within WSL; do them by hand once:

1. Upgrade Obsidian to **1.12.7+** (the CLI ships with that installer).
2. In Obsidian: **Settings → General → enable "Command line interface"**, then follow the prompt to
   register. PATH registration is automatic; a terminal redirector is added to the install folder.
3. **Restart the terminal.** If you also change WSL interop settings, `wsl --shutdown` from a Windows
   shell and reopen, so the new Windows PATH is imported into WSL.

Until this is done, `obsidian.exe` does not exist inside WSL and nothing downstream runs. ^[inferred]

## WSL side — the wrapper

Reach the Windows binary over interop and wrap it so the current directory never decides the vault.
Once, in WSL:

1. Confirm interop reaches it: `obsidian.exe version` prints a version. If `command not found`, ensure
   `/etc/wsl.conf` has the following (the default) and that Obsidian is on the Windows PATH, then
   `wsl --shutdown` and reopen.

   ```ini
   [interop]
   appendWindowsPath = true
   ```
2. Find the vault name: `obsidian.exe vaults` lists them; note the exact name of the vault you want.
3. Create `~/bin/obsidian`, executable, pinning the vault and stripping CRLF:

   ```bash
   #!/bin/bash
   vault="${OBSIDIAN_VAULT:-<NAME>}"
   obsidian.exe "vault=$vault" "$@" 2>&1 | tr -d '\r'
   ```

   The `vault=` selector must be the first argument — the CLI wants it before the command, so a call
   from any working directory still hits the right vault. ^[inferred] `<NAME>` is the baked-in default;
   `OBSIDIAN_VAULT` overrides it for a single call (`OBSIDIAN_VAULT=other obsidian read foo.md`) without
   editing the script. `tr -d '\r'` strips the carriage returns the Windows console appends, which
   otherwise corrupt every parse.
4. Put `~/bin` ahead on PATH (`export PATH="$HOME/bin:$PATH"` in `~/.zshrc`) so `obsidian` resolves to
   the wrapper, not the bare `.exe`.
5. Verify from an arbitrary directory: `obsidian read <some-note>.md` prints the note clean (no stray
   `\r`), proving the vault pin and CRLF strip both hold.

## Gotchas

- `obsidian web <url>` opens the URL in Obsidian's in-app web viewer; it does **not** fetch page
  content into a note.
- The desktop app must be running — the CLI drives it; the first command launches it if closed.
- The Windows GUI watching WSL files may not live-refresh edits made directly on disk, but CLI changes
  route through the running app, so what the CLI writes stays consistent with the GUI. ^[inferred]
