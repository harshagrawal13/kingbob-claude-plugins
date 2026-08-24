# Notion connector mechanics

Sharp edges in the `mcp__claude_ai_Notion__*` tools. Every entry here cost a
failed call at least once — none of it is theoretical.

## Querying

**SQL mode is metered; view mode is not.** On non-Business plans the workspace
has a shared quota for `query-data-sources` in SQL mode, and it *does* run out
mid-session:

> Your workspace has reached the usage limit for Query Data Source.

Once exhausted, every SQL query fails until it resets. **Prefer view mode**,
which has no tool-specific quota on any plan:

```
notion-query-data-sources → { "mode": "view", "view_url": "view://<id>" }
```

Get view URLs by fetching the **database** (not the data source) — the
`<views>` block lists them. View mode applies that view's own filters and sorts,
so pick a view whose filter matches what you need, or read a broad view and
filter in your head. Spend SQL only on questions no existing view answers.

**`IS NOT <literal>` does not parse.** SQLite accepts it as a null-safe `!=`;
Notion's parser rejects the whole query:

> Reason: the query could not be parsed safely.

Write the NULL arm out, and parameterise:

```sql
WHERE "Status" IS NULL OR "Status" != ?     -- params: ["archived"]
```

**Date properties are not queryable by their own name.** Use the expanded
columns — `date:Due:start`, `date:Due:end`, `date:Due:is_datetime` — for both
reads and writes. The bare `Due` column does not exist in SQL.

**Relation columns** come back as JSON arrays of page URLs, and are written the
same way: `{"Thread": ["https://app.notion.com/p/<page-id>"]}`. Page *names* are
never accepted — resolve a name to a URL first.

## Select and multi-select options

**Options are not created on the fly.** Passing an unknown value to
`notion-create-pages` is rejected outright:

> Invalid multi_select value for property "Tags": "claude-code".
> Value must be one of the following: … If a new multi_select option is needed,
> the data source must be updated to add it.

Add it to the schema first:

```
notion-update-data-source →
  ALTER COLUMN "Tags" SET MULTI_SELECT('tool':blue, …, 'claude-code':yellow)
```

**`ALTER COLUMN … SET` replaces the entire option list.** Enumerate every
existing option with its current colour — both are in the fetched schema — and
append the new one. Drop an option here and it is stripped off every row that
used it.

**`status` is a distinct type from `select`.** The Tasks databases use a real
`status` property, whose options live under `groups` (`to_do` / `in_progress` /
`complete`) rather than a flat `options` list. Read the actual option name out
of the right group; do not assume "Not started" or "Todo".

## Writing

**There is no delete.** The connector exposes `create-pages`, `duplicate-page`,
`update-page`, `move-pages`, `fetch`, `query-data-sources`,
`update-data-source`, `search` — and nothing that trashes or archives a *page*.
`update-page` has no `archived` command; `move-pages` only re-parents. A status
flip is the only reversible retire available. True deletion is a Notion-UI
action.

`update-data-source` *can* `DROP COLUMN` or trash a whole data source. Never
reach for it to retire a row — that is schema surgery on the entire database to
remove one entry.

**Titles are returned markdown-escaped.** A title starting with `~` comes back
as `\~` in the `properties` block of a fetch. That is the enhanced-markdown
encoding of the response, not a backslash stored in the title — the `title`
field in the result metadata shows the real text. Don't "fix" it.

**Creating in a database** needs the data source parent, not the database id:

```json
{ "type": "data_source_id", "data_source_id": "<uuid>" }
```

Never set `created_time` / `last_edited_time` properties; Notion manages them.
