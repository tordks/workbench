---
name: wiki-capture
description: "Park an idea, note, or link into the wiki's inbox for later ingest. Use when you or an agent wants to bank a durable thought or source mid-task without stopping to file it."
---

Drop one raw thought into the wiki's `inbox/` and move on — capture, not filing.

**Load the rules first:** `obsidian read _schema.md` — it owns the inbox lifecycle and autonomy. The
skill runs wherever your agent runs, so every vault touch goes through the **Obsidian CLI**, which
reaches the live vault.

## Capture

Write **one file per capture** to the inbox:

```
obsidian create inbox/<kebab-slug>
```

Give it light frontmatter and the raw content — enough for `ingest` to work later without you:

- `captured:` today's date
- `kind:` `idea` | `note` | `link` | `source`
- `link:` the URL, if any
- body: the thought itself. For a URL, pull the readable content in now (so ingest needs no network)
  — `obsidian web <url>` or a fetch — and paste it under the frontmatter.

## Stay in your lane

Append-only and autonomous. Do **not** touch `sources/` or the synthesized wiki, do not search for
duplicates, do not synthesize — that is `wiki-ingest`'s job. Done when the thought is one file in
`inbox/` and nothing else changed.
