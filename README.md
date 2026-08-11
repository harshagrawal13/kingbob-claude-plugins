# kingbob-claude-plugins

Harsh's personal plugins and skills for [Claude Code](https://claude.com/claude-code).

## Install

From within a Claude Code session, add the marketplace and install the plugin:

```
/plugin marketplace add harshagrawal13/kingbob-claude-plugins
/plugin install kingbob@kingbob-claude-plugins
```

Or add directly to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "kingbob-claude-plugins": {
      "source": {
        "source": "github",
        "repo": "harshagrawal13/kingbob-claude-plugins"
      }
    }
  },
  "enabledPlugins": {
    "kingbob@kingbob-claude-plugins": true
  }
}
```

Invoke skills as `/kingbob:<skill-name>` — e.g. `/kingbob:cite`.

To update or remove:

```
/plugin update kingbob
/plugin remove kingbob
```

To test a local checkout or branch without installing it globally:

```bash
claude --plugin-dir /path/to/kingbob-claude-plugins
```

## Skills

### `/kingbob:cite`

Generate and verify a citation for a piece of prose. Give it a link (DOI, doi.org URL, arXiv, bioRxiv, or publisher page) and optionally the sentence or paragraph the citation should support — or give it **prose alone** and it will discover candidate citations for you.

```
/kingbob:cite [link-or-doi] [prose to cite, or file:line]
```

**What it does (with a link):**
1. Resolves the link to a DOI (prefers the published version over an arXiv preprint, and tells you when it swaps)
2. Generates the BibTeX entry via doi.org content negotiation (doi2bib)
3. Verifies the entry against the Crossref/DataCite registrar record — title, authors, year, venue, entry type — and fixes obvious problems (noting every fix)
4. Reads the cited source (landing page, open-access PDF, or abstract) and judges whether it actually supports the prose — or whether it better fits a neighboring sentence — with a verdict (✅ supported / ⚠️ partial / ❌ not supported / ❓ cannot verify) backed by quoted evidence
5. Returns the ready-to-paste BibTeX, checks any `.bib` file in your project for duplicates, and offers to append

**Discovery mode (prose without a link):**
1. Distills the prose into its core claim and spawns small parallel search agents — a web-search agent, a scholarly-API agent (Crossref / Semantic Scholar / OpenAlex), and a preprint agent (arXiv / bioRxiv) when the field fits
2. Agents may only return papers they saw real evidence for (DOI + abstract) — never guessed references
3. Dedupes candidates and rates each one's **semantic relevance** to your claim: 🎯 supports the claim / 🟡 topically related but doesn't establish it / 🔴 keyword overlap only or contradicts it
4. Presents the ranked candidates and lets you pick which to cite; if nothing rates 🎯, it says so and suggests weakening the prose rather than passing off a topical match
5. Runs the chosen source(s) through the full verify pipeline above

Without prose, it still generates and verifies the citation; the prose-support check is skipped.

### `/kingbob:desktop-cleanup`

Scan `~/Downloads`, `~/Developer`, `~/Documents`, and `~/Desktop` for stale, loose files and propose where each one should go — one file at a time, nothing moves or deletes without your approval.

```
/kingbob:desktop-cleanup
```

**What it does:**
1. Loads (or, on first run, asks you to set up) three source-of-truth destinations: Media, Books, and Personal Docs
2. Walks all four folders recursively via a bundled `scan.py` helper, skipping anything inside a git repo (any directory containing `.git`, at any depth, is never entered) plus standard build/dependency clutter (`node_modules`, `.venv`, `dist`, `.app` bundles, dotfiles)
3. Flags a file as stale only once it's past its folder's age threshold (Downloads: 30 days; Developer/Documents/Desktop: 180 days) **and** has shown up in at least two scans — tracked in `~/.desktop-cleanup/history.json`, which also remembers anything you've already declined so it won't re-ask unless the file changes
4. Classifies each stale file by extension/filename heuristics into Media, Books, Personal Docs, a new local subfolder, or Trash — surfacing low-confidence guesses rather than deciding silently, and learning your destination folders' existing naming conventions so files get renamed/placed consistently
5. Before any move into a source-of-truth folder, checks for a same-name collision by file size only (never forces a cloud download to checksum) — proposing to Trash true duplicates and surfacing real conflicts to you
6. Presents each file individually via a yes/no/decline prompt; approved moves happen immediately, approved deletes always go through Trash (never `rm`)
7. Ends with a simple count of what moved, what got trashed, and what new folders were created

### `/kingbob:fix-latex-errors`

Diagnose and fix LaTeX compilation errors and warnings — one pasted error, or a full sweep of the document.

```
/kingbob:fix-latex-errors [exact error or warning text] [main .tex file]
```

**What it does:**
1. Detects the main `.tex` file and the intended engine/bibliography tool (latexmkrc, magic comments, fontspec → xelatex, biblatex → biber) — and never switches tooling just to make an error go away
2. Recompiles with `-file-line-error` to get a fresh log; with a pasted error it confirms the error actually reproduces before diagnosing
3. **Sweep mode** (no arguments): triages every issue by root cause — errors first (fixing the *first* error and recompiling rather than chasing cascades), then undefined references/citations, duplicate labels, package warnings, overfull boxes, font warnings — into a numbered report with severity, `file:line`, explanation, and concrete fix
4. Applies safe, single-site mechanical fixes directly; **asks for a greenlight** before anything big — multi-site changes, preamble/package surgery, engine swaps, or anything touching content, wording, or layout
5. Recompiles to verify each fix actually took, then reports: fixed / flagged awaiting your call / remaining with manual instructions, and the document's end state

## Project Structure

```
kingbob-claude-plugins/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest (name: kingbob)
│   └── marketplace.json     # Marketplace manifest
├── .github/workflows/
│   └── validate.yml         # CI: manifest + skill frontmatter validation
├── skills/
│   ├── cite/SKILL.md
│   ├── desktop-cleanup/
│   │   ├── SKILL.md
│   │   └── scripts/scan.py
│   └── fix-latex-errors/SKILL.md
├── scripts/
│   └── validate.py
├── CLAUDE.md                # Contributor rules: versioning + releases
└── README.md
```

## Adding New Skills

Create `skills/<skill-name>/SKILL.md` with frontmatter:

```yaml
---
name: my-skill
description: What the skill does and when to invoke it
argument-hint: "<expected arguments>"
user-invocable: true
allowed-tools: Bash(curl:*), Read, Grep
---
```

Then document it in this README, run `python3 scripts/validate.py`, bump the version in `.claude-plugin/plugin.json` (new skill → major bump, polish → minor bump; see `CLAUDE.md`), and cut a matching GitHub release.
