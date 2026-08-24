---
name: add-to-notion-memory
description: Save something worth remembering to Harsh's private "claude memory" Notion database — a tool, a command, a setting, a fix. Pass the thing to remember inline; with no arguments it picks the memory-worthy result out of the current conversation and confirms before writing. Resolves the destination from NOTION_CLAUDE_MEMORY_URL in ~/Developer/.env, matches the database's house style, checks for near-duplicates, and previews the row before creating it. Also retires entries on request by flipping their status to archived — never by deleting them. Use when the user says "add this to notion memory", "remember this in notion", "save that to my notion memory", "archive/remove that notion memory", or "/add-to-notion-memory ...".
argument-hint: "[what to remember]"
user-invocable: true
allowed-tools: Bash(grep:*), Bash(test:*), WebFetch, AskUserQuestion, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page
---

# add-to-notion-memory

Write one entry into the private **claude memory** Notion database — the place
where a tool, a command, a macOS setting, or a hard-won fix goes so it survives
past the session that produced it.

## Input

<arguments>
$ARGUMENTS
</arguments>

| Given                          | Mode                                                                 |
|--------------------------------|----------------------------------------------------------------------|
| A thing to remember            | **Direct mode**: draft that entry (Steps 1 → 6)                      |
| Nothing                        | **Infer mode**: Step 3a first — pull the memory-worthy item out of the conversation, confirm it, then Steps 1 → 6 |

Steps 1 and 2 are cheap and always required; run them before drafting.

## Step 1 — Resolve the destination

The database URL is private and is **never** committed to this repo. Read only
the one line you need — `~/Developer/.env` may hold unrelated secrets:

```bash
grep -m1 '^NOTION_CLAUDE_MEMORY_URL=' ~/Developer/.env
```

Strip the `NOTION_CLAUDE_MEMORY_URL=` prefix and any surrounding quotes.

**Fail loudly** if the variable or file is missing — do not guess a URL, do not
search Notion for a database that looks right, and do not fall back to a
different database. Print exactly this and stop:

> `NOTION_CLAUDE_MEMORY_URL` is not set in `~/Developer/.env`. Add a line like
> `NOTION_CLAUDE_MEMORY_URL=<link to the claude memory Notion page>` (chmod 600
> the file) and re-run.

Likewise, if the Notion MCP connector is unavailable, say so verbatim and stop.
This skill has no other write path.

## Step 2 — Resolve the data source and its live schema

`notion-fetch` the URL from Step 1. It may point at either the wrapper page or
the database itself:

- **A page** → its content contains `<database ... data-source-url="collection://…">`.
  Take that `collection://` URL.
- **A database** → the fetch result lists its data sources directly. Take the
  `collection://` URL. If there is more than one, ask which to use.

Then `notion-fetch` the `collection://` URL to get the schema. Resolve it every
run rather than hardcoding it — the ID is private (same reason as the URL), and
the tag options change over time.

Expected shape (verify, don't assume): a title property, a multi-select tag
property, a single-select status property (`active` / `archived`), and
auto-managed created/last-edited timestamps. Read the **actual** property names
out of the schema and use those; if the schema has drifted from what this skill
expects, report what you found rather than forcing a write.

## Step 3 — Work out what to remember

From the arguments, plus the conversation around them. Strip the framing —
"add this thing to notion memory" is instruction, not content.

Resolve every reference before drafting. If the user says "that command" or
"the tool we just used", find the actual command or tool in the conversation
and record the real thing. A memory that says *"the fix we discussed"* is worth
nothing six months from now.

### Step 3a — Infer mode (no arguments)

Scan back over the conversation for the one item worth keeping: a tool that was
installed, a command that finally worked, a setting that fixed something, a
non-obvious gotcha. Prefer the most recent concrete result over an abstract
lesson.

State what you picked in one line before drafting. If nothing in the
conversation is memory-worthy, say so and stop — do not invent an entry.

## Step 4 — Draft the row

Match the house style of the database. Read two or three existing rows (Step 5's
query returns them) if you need a refresher; the shape is:

**Icon** — a single emoji that fits the entry.

**Title** — `<subject> — <what it is / what it does>`, e.g.
`Mole — deep-clean macOS`. Specific enough to recognize in a list view; no
trailing punctuation.

**Tags** — pick from the options in the schema you fetched in Step 2 whenever
one fits. Only propose a **new** option when nothing genuinely does, and show it
to the user for a yes/no before creating it (Notion creates multi-select options
on the fly, so a typo becomes a permanent option). Several tags are fine; zero
is fine.

**Status** — always `active` on a new entry. Set it explicitly rather than
leaving it blank; the database's default view filters on this property, and a
blank status is a row nobody sees. See *Retiring an entry* below for the only
time it should be anything else.

**Body** — short and concrete. In practice:

- Lead with a markdown link to the source when there is one (repo, docs, post).
- One or two lines of what it is and why it earned a place here.
- A fenced code block for anything runnable, with the exact invocation —
  real paths, real flags. This is the part future-you actually needs.
- Absolute dates (`2026-08-24`), never "today" or "last week".
- No page title at the top of the body; the title property carries it.

**Never fabricate a link.** If you are writing a URL you did not see in this
conversation, `WebFetch` it first and confirm it resolves to what you claim. If
it doesn't, drop the link and say so — a plausible-looking dead link is worse
than no link.

## Step 5 — Check for a near-duplicate

Query the data source for existing rows before writing:

```sql
SELECT url, "<title-prop>", "<tags-prop>", "<created-prop>"
FROM "collection://<id>"
WHERE "<status-prop>" IS NOT 'archived'
```

Archived rows are excluded on purpose: if a near-match was archived, it was
retired deliberately, and the right move is a fresh `active` row rather than
reviving a retired one. Rows with no status set still count — better a false
duplicate prompt than a silent double entry.

Compare the draft against the returned titles on subject, not wording — a new
flag for a command already recorded is the *same* memory, not a new one.

If something is close:

1. `notion-fetch` that page so you are comparing against its real body.
2. Show the user the existing entry and the draft.
3. `AskUserQuestion`: **update the existing page** (merge the new detail into
   it via `notion-update-page`, preserving what's there) or **create a new
   row**. Never silently overwrite.

If nothing is close, continue.

## Step 6 — Preview, write, report

Print the draft first — icon, title, tags, body — as it will appear. Then
create it with `notion-create-pages`, parented to the data source:

```json
{ "type": "data_source_id", "data_source_id": "<id from Step 2>" }
```

Set the title, tag, and status properties by their real schema names — status
`active` (Step 4). Do **not** set the created/last-edited timestamps; Notion
manages them.

No approval round-trip is needed for a normal add — write it, then report the
resulting Notion page URL so the user can click through and correct anything.
Two things do warrant stopping first: creating a **new tag option** (Step 4) and
**updating an existing page** (Step 5).

Report failures verbatim. If the write is rejected, print Notion's error and
the draft you tried to write, so nothing is lost — never report success you
did not observe.

## Retiring an entry — archive, never delete

When the user asks to remove, delete, drop, or get rid of a memory, **do not
destroy it**. Set its status property to `archived`:

```
notion-update-page → command: update_properties → { "<status-prop>": "archived" }
```

The database's default view filters archived rows out, so archiving is what
"deleted" looks like day to day — but the entry, its body, and its history
survive, and a separate Archived view still reaches it. Say plainly that you
archived rather than deleted it, and where it went.

Two supporting facts, so this isn't mistaken for timidity:

- The Notion connector has **no** delete, trash, or archive-page tool at all —
  `create-pages`, `duplicate-page`, `update-page`, `move-pages`, `fetch`, and
  `query-data-sources` are the whole write surface. A status flip is the only
  reversible retire available, and there is no destructive path to fall back to.
- `notion-update-data-source` *can* drop a column or trash the whole data
  source. Never reach for it to retire a row — that is schema surgery on the
  entire database to remove one entry.

If the user insists on real deletion, say it has to happen in the Notion UI
(row → **Delete**, or **⋯ → Move to Trash**) and leave it to them.
