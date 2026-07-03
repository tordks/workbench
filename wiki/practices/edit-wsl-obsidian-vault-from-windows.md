---
type: practice
title: Edit a WSL-hosted Obsidian vault from Windows
aliases: [wsl obsidian vault, obsidian wsl sync, wsl vault windows gui]
tags: [tooling]
created: 2026-07-03
updated: 2026-07-03
status: seed
source: ""
related: ["[[obsidian-cli-on-wsl]]", "[[unison]]"]
---

# Edit a WSL-hosted Obsidian vault from Windows

Keep a vault **canonical on the WSL (ext4) side** — so git stays fast — while editing it in the
**Windows Obsidian GUI**. Windows itself reads WSL files fine (Explorer, `Test-Path`, the CLI all
work); the obstacle is specifically that **Obsidian's file watcher won't run against a mapped WSL
drive**, and that watcher is not optional.

_Provenance: hands-on troubleshooting on one Windows 11 + WSL2 (Ubuntu) machine. The failing routes
below were observed directly; the working routes are reasoned recommendations unless noted._

## Why the obvious routes fail

- **Open the vault directly on `\\wsl.localhost\...\vault`** — Obsidian **refuses a raw UNC path** as a
  vault location.
- **Map a drive letter and open `Z:\...\vault`** — it mounts and reads, but Obsidian crashes on load
  with `EISDIR: illegal operation on a directory, watch '...'`. The exact cause is unconfirmed
  ^[inferred] — it's the Node/Electron directory watcher failing on the mapped WSL share, not a Windows
  read-access problem — but it was a hard, repeatable dead end here. (To map at all: `net use`, not
  `New-PSDrive -Persist`; map the distro share root with no trailing slash, e.g.
  `net use Z: \\wsl.localhost\Ubuntu`.)
- **Windows symlink (`mklink /D`) to the UNC target** — Obsidian canonicalizes it back to the UNC path
  and refuses again.

The common wall: the folder Obsidian watches has to sit on a filesystem its watcher accepts — which the
mapped WSL share isn't.

## Routes that work — pick by how you edit

1. **WSLg (run Obsidian on the Linux side).** Install the Linux build of Obsidian inside WSL; WSLg
   renders its window on the Windows desktop. Native inotify on ext4 → no crash, **live refresh works**,
   files stay on WSL, no second copy. Cleanest when WSLg cooperates on the host. ^[inferred]
2. **git worktree on NTFS.** `git worktree add /mnt/c/Users/<you>/vault -b vault-live`; Obsidian
   opens the NTFS copy and watches it natively. The object store and `.git` stay on WSL (worktrees share
   one database). Caveat: a worktree **cannot check out the branch your WSL working copy already has**,
   so it's a **separate branch** → commit-in-worktree then merge back each session, and it diverges if
   agents edit the main branch while you edit in Obsidian. Fine for **one-side-at-a-time** editing. ^[inferred]
3. **File sync (single branch, live).** Continuously mirror the `vault/` folder ↔ a native NTFS folder
   Obsidian watches. Same branch, both sides watchable, and **sync only `vault/`** so no `.git` is in the
   synced set. See below.

## The file-sync route

Because WSL sees **both** filesystems (`/home/...` ext4 and `/mnt/c/...` NTFS), run **one bidirectional
syncer inside WSL** between two local folders — not multi-device sync:

```
/home/<you>/.../vault   ←→   /mnt/c/Users/<you>/vault
  (canonical, git here)         (Obsidian watches this)
```

- **Unison** — bidirectional, three-way; already fine on stock Ubuntu. The working WSL command and its
  two gotchas (poll instead of `watch`; disable perms for NTFS) are in [[unison]].
- **Mutagen** — single binary, near-real-time; built for cross-filesystem dev sync. ^[inferred]
- **Syncthing** — robust, but device-to-device, so on one machine it needs two daemons: overkill here. ^[inferred]

Whichever tool, **exclude `.obsidian/workspace.json`** (and `workspace-mobile.json`) from the sync.
Obsidian rewrites it on every pane/tab/scroll change, so it churns constantly for no real content, and
it's per-view session state each side wants its own copy of — a prime source of pointless conflicts.
The rest of `.obsidian/` (plugins, appearance, hotkeys) *is* worth mirroring, so scope the exclusion to
`workspace*`, not the whole folder. In Unison that's `-ignore 'Path .obsidian/workspace*'`. Note the
file doesn't exist until the desktop app has opened the vault and saved a layout, so the rule is a no-op
until then.

## Conflict handling

A conflict only arises when the **same file** changes on **both** sides within one sync window (e.g. an
agent edits it on WSL while you edit it in Obsidian). Sync is fast, so the window is small, and all
three tools are **fail-safe — none destroys a version** — but their *default* behaviour differs. The
details below are from each tool's docs, not tested here. ^[inferred]

- **Unison** — **three-way** (archive of last-synced state), so it tells a one-sided edit from a
  both-sided one. Default is fail-loud: leaves **both** files untouched, reports `<-?->`, you resolve;
  `-batch` logs and moves on. Opt-in last-writer-wins is available. Flags in [[unison]].
- **Mutagen** — bidirectional with conflict detection. Default mode `two-way-safe` **halts** on a
  conflict: it propagates everything non-conflicting, leaves the conflicting file untouched on both
  sides, and flags it for you. Switch to `two-way-resolved` to make one endpoint (alpha) win conflicts
  automatically.
- **Syncthing** — does **not** halt: it auto-resolves by keeping the **most-recently-modified** version
  as the winner and renaming the loser to `<name>.sync-conflict-<date>-<time>-<id>.md`, so both survive
  and you reconcile the copy later.

Net: **Unison and Mutagen fail *loud*** (flag and wait) by default, **Syncthing fails *quiet*** (newest
wins, loser kept as a sidecar file). For a single-user vault, either is fine; pick loud if you'd rather
never have a silent auto-resolution.

## Recommendation

WSLg if it runs cleanly on the host; otherwise **file sync** (Unison or Mutagen) for a single-branch,
live-refresh setup. Use the **worktree** only if you accept the separate-branch merge cycle.
