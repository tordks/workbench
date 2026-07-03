---
type: reference
title: Unison (file synchronizer)
aliases: [unison, unison sync]
tags: [tooling]
created: 2026-07-03
updated: 2026-07-03
status: seed
source: ""
related: ["[[edit-wsl-obsidian-vault-from-windows]]"]
---

# Unison (file synchronizer)

Unison keeps two directory trees in sync **bidirectionally**, comparing both against a stored *archive*
of the last-synced state (in `~/.unison/`) so it distinguishes a one-sided edit from a genuine
both-sided conflict. It fits mirroring one **local** tree to another — e.g. a WSL/ext4 folder ↔ a
Windows/NTFS folder under `/mnt/c`, the latter being natively watchable by Windows apps.

_Provenance: hands-on use on one Windows 11 + WSL2 (Ubuntu) machine, unison 2.53.8. Items marked
"verified" were reproduced directly; conflict-flag behaviour is from the Unison docs._

## Continuous local sync command (ext4 ↔ NTFS on WSL)

Seed once **without** `-repeat` to eyeball the initial direction (press `f` then `y`), then run with
`-repeat` for continuous sync:

```bash
unison <ext4-dir> <ntfs-dir> \
  -repeat 2 -batch -times -perms 0 -dontchmod -copyonconflict
```

- `-repeat 2` — re-sync every 2 s (poll; see the fsmonitor gotcha for why not `watch`).
- `-batch` — auto-propagate non-conflicting changes; conflicts are skipped and logged, not resolved.
- `-times` — preserve modification times.
- `-perms 0` / `-dontchmod` — required on NTFS; see the permissions gotcha.
- `-copyonconflict` — on a resolved conflict, keep the losing copy so nothing is destroyed.
- `-ignore 'Path <glob>'` (optional, repeatable) — skip volatile or app-generated files that shouldn't
  sync; give the glob relative to the sync root.

## Gotcha: no file-watcher on stock Ubuntu → poll, don't `watch`

`-repeat watch` needs a `unison-fsmonitor` helper. Ubuntu's `unison` (2.53.x) does **not** ship it and
there is **no `unison-fsmonitor` package**, so `-repeat watch` dies with *"No file monitoring helper
program found."* Use interval polling — `-repeat <seconds>` — which needs no helper. Bump the interval
(e.g. `-repeat 5`) if 2 s scans feel busy; the tradeoff is only how fast edits appear on the other side.
(Verified.)

## Gotcha: NTFS via drvfs can't hold Unix permission bits

Copying onto `/mnt/c` (drvfs) fails per item with *"Failed to set permissions … to rwxr-xr-x: the
permissions was set to rwxrwxrwx instead"* — the mount forces `0777` and can't store Unix modes. Fix:

- `-perms 0` — sync no permission bits (also stops a perpetual "props changed" re-sync every poll).
- `-dontchmod` — never call `chmod` (the call itself is what errors on drvfs).

The error also suggests a `fat` option; that's for real FAT volumes, not NTFS/drvfs — `-perms 0
-dontchmod` is the correct pair here. (Verified.)

## Conflicts and the archive

Default (no `-prefer`) is **fail-loud**: a both-sided edit is left untouched on both replicas and
reported `<-?->`; `-batch` logs it and moves on. Opt-in auto-resolve: `-prefer newer` + `-times`
(last-writer-wins) or `-prefer <root>` (one side always wins); `-copyonconflict` keeps the loser. ^[inferred]

The archive lives in `~/.unison/`. If a replica looks emptied relative to it, Unison aborts with a
**"root completely emptied"** safety check rather than mirror the deletion — rerun the seed sync to
re-establish the baseline. (Verified — triggered by recreating a synced root empty.)
