---
name: notion-pa
description: Personal assistant over Harsh's private Notion — threads, projects, tasks, and memory. Captures a task into the right Tasks database and links it to the right thread; opens threads and projects; gives a briefing across everything that's live; and sweeps for drift (unlinked tasks, threads with no resolution criteria, a Tasks database missing its Thread relation). Also keeps the older "add this to notion memory" capture. Resolves every database from NOTION_* keys in ~/Developer/.env — nothing about the workspace is committed. Use when the user says "add a task", "remind me to", "what's live", "what am I on the hook for", "open a thread for", "add this to notion memory", "check my notion", or "/notion-pa ...".
argument-hint: "[what to capture, or a question about what's live]"
user-invocable: true
allowed-tools: Bash(grep:*), Bash(test:*), Read, WebFetch, AskUserQuestion, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-search, mcp__claude_ai_Notion__notion-query-data-sources, mcp__claude_ai_Notion__notion-create-pages, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-update-data-source
---

# notion-pa

A personal assistant over the Notion workspace. The model it serves:

- **Threads** are the *nouns* — ongoing strands of life, each with a written
  condition for what ends it. Everything else hangs off them.
- **Projects** are things built.
- **Tasks** are the *verbs*, spread across several databases, each carrying its
  own `Thread` relation.
- **Memory** is the scrapbook: a tool, a command, a fix worth keeping.

Read `references/notion-mechanics.md` before your first write in a session. It
carries the connector's sharp edges — query quotas, option creation, what has no
delete path — each of which has already broken this skill once.

## Input

<arguments>
$ARGUMENTS
</arguments>

Route on what the user is doing, not on keywords alone:

| They are…                                            | Route |
|------------------------------------------------------|-------|
| naming something to *do* ("remind me to", "I need to")| **A — task** |
| naming an ongoing strand with no single finish line   | **B — thread** |
| naming something they're *building*                   | **C — project** |
| asking what's live / what's owed / what's next        | **D — briefing** |
| asking to check, tidy, or audit the system            | **E — hygiene** |
| saving a tool, command, or fix worth keeping          | **F — memory** |
| ambiguous between capture routes                      | ask, once |

A single invocation may legitimately run more than one route ("add a task and
tell me what else is due" → A then D). Nothing here is exclusive.

## Step 0 — Resolve the workspace

Always, before any route. Read only the keys you need — `~/Developer/.env` holds
unrelated secrets:

```bash
grep -E '^NOTION_[A-Z_]+_URL=' ~/Developer/.env
```

| Key                       | What it points at                    |
|---------------------------|--------------------------------------|
| `NOTION_THREADS_URL`      | Threads database                     |
| `NOTION_PROJECTS_URL`     | Projects database                    |
| `NOTION_TASKS_<NAME>_URL` | **one per Tasks database**           |
| `NOTION_CLAUDE_MEMORY_URL`| Memory database                      |

`NOTION_TASKS_*_URL` is a **prefix convention, not a fixed list**. Every key
matching it is a Tasks database; `<NAME>` is its label (`ENCODE` → "Encode").
Never hardcode the set — enumerate whatever keys exist, so a Tasks database
added later is picked up by adding a key rather than by editing this skill.

`notion-fetch` each URL to get its `collection://` data source and **live
schema**. Resolve every run; the IDs are as private as the URLs, and the option
lists drift. The Tasks databases are **not** interchangeable — they carry
different properties (one has `Lead` and `Uni / Affiliation`, others have
`Tags`). Read each one's own schema and write only properties it actually has.

**Fail loudly.** A missing key, or a missing Notion connector, stops the run
with the key name and what to add. Never guess a URL, never search Notion for a
database that looks right, never fall back to a different one.

## House rules

These bind every route.

- **Resolve vague references.** "That command", "the thing we just fixed", "the
  prof Simran met" — chase it back to the real thing before writing. A row that
  says *"the fix we discussed"* is worth nothing in six months.
- **Never fabricate.** Not a URL, not a status, not a date, not a fact about the
  user's own work. Any URL you did not see in this conversation gets fetched and
  confirmed first; if it doesn't resolve, drop it and say so. If a field would
  be a guess, leave it empty and say which ones you left.
- **Preview, then write.** Print what you're about to create, then create it,
  then report the resulting Notion URL. No approval round-trip for a routine
  capture — a wrong guess is one click to fix, and stopping every time makes the
  frequent path expensive. Four things *do* stop first: creating a **new select
  option**, **updating an existing row**, **opening a thread**, and **anything
  that would fill a project's factual fields**.
- **Prefer view-mode queries.** SQL mode is metered per workspace and *will* run
  out; view mode is not. See `references/notion-mechanics.md`.
- **Archive, never delete** (Route F, and anything else asked to be removed).
- **Report failures verbatim** — Notion's error plus the draft you tried to
  write, so nothing is lost. Never report a success you did not observe.

## Route A — Capture a task

The highest-frequency path. Keep it fast.

1. **Pick the Tasks database** from the content: whose work is it, and which
   world does it live in? Match against the labels in the `NOTION_TASKS_*_URL`
   keys and each database's existing rows.
2. **Pick the thread.** Read the Threads database and match against threads that
   are `Active` or `Simmering`. One thread, the one whose resolution the task
   actually moves.
3. **State both choices in one line**, then write. Don't ask. If two threads fit
   equally, or none does, that's the exception — say so and ask.
4. **Draft** using only properties that database has:
   - Title: imperative and concrete — *"Email Rodrigo Ledesma"*, not *"Rodrigo"*.
   - `Status`: the "not started" option (a **status** type, not a select — read
     its real option name from the schema).
   - `Due`: only if a real date was given or clearly implied. Dates need the
     expanded `date:Due:start` form.
   - `Thread`: an array containing the thread's **page URL**.
   - `Details`: the context that made this a task, if there is any.
5. If no thread fits, write the task **unlinked** and say so plainly. Do not
   invent a thread to hang it on — offer Route B instead.

## Route B — Open a thread

Structural, and rarer. This one confirms before writing.

A thread needs a written **`What Resolution Looks Like`** — a concrete
description of the state that ends it. If the user hasn't given one, ask for it;
do not write the thread with that field blank and do not invent one. A thread
with no finish line becomes a permanent background hum, which is the exact
failure this database exists to prevent.

Also set `Area`, `Priority`, `Started` (today, absolute), `Status` (`Active`
unless told otherwise), and push for `Resolve By` — accept blank if the user
genuinely has no horizon, but ask once.

Preview the whole thing and get a yes before creating it.

## Route C — Project

Create the row from the name. Then stop.

`Status`, `Type`, `Timeline`, `Stack`, `For`, `Link`, `Repo` and
`What I Learned` are **facts about the user's own work** — never infer them from
a repo name, a vibe, or a half-memory. Ask, or leave them empty and list exactly
which fields are waiting.

Link a project to a thread **only when that project has an active push**. A
finished project standing alone is correct, not an omission — under noun/verb,
the relation means "this thread is currently pushing this project", not "this
project once existed".

## Route D — Briefing

Read-only. This is where the skill earns its keep, because Notion cannot roll up
across separate Tasks databases — so do it by hand.

1. Read the Threads database: everything `Active` or `Simmering`.
2. Read **every** Tasks database from Step 0 — all of them, every time. A
   database you skip is a silently wrong briefing.
3. Join tasks to threads on the `Thread` relation and report:
   - **Overdue** — past `Due`, not Done. Loudest, first.
   - **Due next 7 days**, by date.
   - **Threads past their `Resolve By`** but still `Active`.
   - **Active threads with no open task** — alive on paper, unfed in practice.
   - **Unlinked open tasks** — invisible to the thread system.
4. Lead with what is wrong or owed. Do not pad with what is fine.

Anchor every date to today's real date and state dates absolutely.

## Route E — Hygiene sweep

Route D's reads plus the structural checks:

- Threads missing `What Resolution Looks Like` or `Resolve By`.
- Threads `Resolved`/`Dropped` with an empty `Outcome` — the learning was lost.
- Projects with a name and nothing else.
- Open tasks with no `Thread`.
- **The option-A trap**: `notion-search` for databases whose title starts with
  `Tasks`, and compare against the `NOTION_TASKS_*_URL` keys. Any Tasks database
  that has **no key**, or has a key but **no `Thread` relation** in its schema,
  is invisible to the whole thread system. This is the standing cost of keeping
  Tasks split across databases, and it recurs every time one is added — check it
  every sweep.

Report findings grouped by fix, and offer to apply them. Fix nothing structural
unprompted.

## Route F — Memory

The scrapbook. Full routine, unchanged in spirit from the old
`add-to-notion-memory`:

1. Draft in house style: an emoji icon, a `subject — what it does` title, a
   short body leading with the source link and carrying the exact runnable
   invocation with real paths and flags, absolute dates. No title inside the
   body.
2. `Status`: `active`, always, explicitly — the default view filters on it and a
   blank status is a row nobody sees.
3. `Tags`: from the live options when one fits. A new option must be added to
   the schema first (see `references/notion-mechanics.md`) and confirmed with
   the user before creating.
4. Check for a near-duplicate among non-archived rows, matched on subject rather
   than wording. If one is close, show both and ask: merge into it, or add a new
   row. Never silently overwrite.
5. Preview, write, report the URL.

**Retiring anything — archive, never delete.** When asked to remove, delete, or
drop a memory, set its status to `archived`. The default view filters archived
rows out, so it reads as deleted while the entry and its history survive. Say
you archived rather than deleted it. If the user insists on true deletion, it
has to happen in the Notion UI — say so and leave it to them.
