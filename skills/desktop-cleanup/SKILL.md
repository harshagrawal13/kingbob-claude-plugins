---
name: desktop-cleanup
description: Scan Downloads, Developer, Documents, and Desktop for stale, loose files, then propose where each one should go — a source-of-truth folder (Media, Books, Personal Docs), a new local subfolder, or Trash. Skips anything inside a git repo. Every move or delete requires explicit approval, one at a time; deletes always go through Trash, never rm. Use when the user asks to clean up their desktop/downloads, organize loose files, declutter their Mac, or says "/desktop-cleanup".
user-invocable: true
allowed-tools: Bash(python3:*), Bash(mv:*), Bash(trash:*), Read, Write, Glob, AskUserQuestion
---

# desktop-cleanup

Find stale, loose files across `~/Downloads`, `~/Developer`, `~/Documents`,
`~/Desktop` and propose, one file at a time, where each should go. Nothing
moves or deletes without your explicit approval.

All bookkeeping (directory walk, staleness math, scan history) is handled by
`scripts/scan.py`, bundled with this skill — run it with `python3
<skill-dir>/scripts/scan.py <subcommand>` (the skill's base directory is
announced when it loads). Never re-derive the walk/exclusion/staleness logic
yourself in bash; always go through this script so the history file stays
consistent.

## Step 0 — Load or create the destination config

```bash
python3 <skill-dir>/scripts/scan.py config
```

This prints `~/.desktop-cleanup/config.json` (or `{}` if it doesn't exist yet).
It holds three paths:

- `media` — movies/shows source of truth
- `books` — books source of truth
- `personal_docs` — personal documents source of truth

**If it's empty** (fresh machine), ask the user for these three paths via
`AskUserQuestion`, pre-filled with the maintainer's own defaults as the
suggested option so it works out of the box for them, but editable for anyone
else installing this plugin:

- Media: `/Users/harsh/Library/CloudStorage/GoogleDrive-harshagrawal.1312@gmail.com/My Drive/Media`
- Books: `/Users/harsh/Library/CloudStorage/GoogleDrive-harshagrawal.1312@gmail.com/My Drive/Books`
- Personal Docs: `/Users/harsh/Library/Mobile Documents/com~apple~CloudDocs/docs`

Then write it:

```bash
python3 <skill-dir>/scripts/scan.py init-config --media "<path>" --books "<path>" --personal-docs "<path>"
```

## Step 1 — Scan

```bash
python3 <skill-dir>/scripts/scan.py scan
```

This walks all four roots and returns a JSON list of stale candidates. A file
only appears here if it is genuinely stale — `scan.py` already applied:

- **Repo skip**: any directory containing `.git` (at any depth) is skipped
  wholesale, tracked or untracked files inside are never touched or listed.
- **Standard exclusions**: dotfiles/dotfolders, `node_modules`, `.venv`,
  `__pycache__`, `dist`, `build`, `.next`, and `.app` bundles (treated as
  opaque, never entered).
- **Staleness rule**: mtime age past the folder's threshold (Downloads 30
  days; Developer/Documents/Desktop 180 days) **and** seen in at least 2 prior
  scans — so nothing gets flagged on the first run it's noticed, and anything
  you previously declined stays quiet unless its mtime changes.

If the scan returns no candidates, say so plainly and stop — don't invent
things to clean up.

## Step 2 — Classify each candidate

For each candidate, decide a proposed action using extension + filename
heuristics:

- **Media** (`.mkv`, `.mp4`, `.avi`, `.mov`, `.srt`, plus a show/movie-shaped
  filename — season/episode markers, a year in parens, etc.) → the `media`
  destination.
- **Books** (`.epub`, `.mobi`, `.azw3`, or a `.pdf`/`.txt` whose filename
  reads like a title+author) → the `books` destination.
- **Personal Docs** (resumes, forms, scans, non-project `.pdf`/`.docx` that
  read as personal rather than project-related) → the `personal_docs`
  destination.
- **No confident match**: propose either a new same-root local subfolder if
  several stale candidates share an obvious grouping (e.g. a dozen
  `Screenshot 2026-*.png` → `Desktop/Screenshots/`), or Trash if it looks like
  disposable cruft (old installers, superseded exports, already-extracted
  archives). If neither fits, say so plainly and let the user decide — never
  force a guess.

Mark each classification's confidence. Low-confidence guesses must still be
surfaced with their best-guess destination, not silently decided.

### Learning the destination's naming convention

Before proposing a Media/Books/Personal-Docs placement for the first time in
a run, check `~/.desktop-cleanup/history.json` (via `scan.py config` won't
show it directly — read the file with `Read`) for a cached `conventions`
block. If missing or stale (doesn't match what's actually there), sample the
real structure:

```bash
python3 <skill-dir>/scripts/scan.py sample-dest --path "<destination>" --limit 40
```

This only lists relative paths (metadata, no content reads — safe for
cloud-only/not-yet-downloaded Google Drive or iCloud files). Infer the
pattern (e.g. `Movies/{Title} ({Year})/{Title} ({Year}).{ext}` or
`{Author}/{Title}.{ext}`) and write it back into `history.json`'s
`conventions` object with `Read`/`Write` so later runs reuse it. Apply the
learned convention to propose the renamed destination path for each file.

## Step 3 — Check for collisions

Before proposing any move into `media`/`books`/`personal_docs`, check whether
the destination path already exists:

```bash
python3 <skill-dir>/scripts/scan.py compare --a "<source>" --b "<destination>"
```

This compares by size only — it never reads file content or forces a cloud
download.

- **Sizes match** → propose Trashing the source as a duplicate (destination
  already has it).
- **Sizes differ, or either side can't be stat'd** (e.g. a cloud placeholder)
  → surface both paths to the user explicitly and let them decide; never
  silently overwrite or auto-rename.

## Step 4 — Approve and execute, one at a time

For each candidate, present via `AskUserQuestion`: the file (path, size, age),
the proposed action (move to `<destination>` as `<renamed path>` / move to
new local subfolder `<path>` / Trash) with its confidence, and a decline
option. Do this **one file at a time** — do not batch multiple files into a
single approval prompt.

On approval, execute immediately before moving to the next candidate:

- **Move**: `mv "<source>" "<destination>"` (create any new subfolder first
  if it doesn't exist).
- **Trash**: `trash "<source>"`.
- Then record the outcome so history stays in sync:
  ```bash
  python3 <skill-dir>/scripts/scan.py record --path "<source>" --decision moved|trashed
  ```

On decline:

```bash
python3 <skill-dir>/scripts/scan.py record --path "<source>" --decision declined
```

This suppresses re-asking about that exact file until its mtime changes.

## Step 5 — Report

A simple action count: how many moved (broken down by destination), how many
trashed, how many new local subfolders created. Nothing more elaborate.
