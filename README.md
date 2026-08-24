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

### `/kingbob:add-to-notion-memory`

Save something worth remembering — a tool, a command, a macOS setting, a fix —
into the private **claude memory** Notion database.

```
/kingbob:add-to-notion-memory [what to remember]
```

With no arguments it picks the memory-worthy result out of the current
conversation and tells you what it chose before writing.

**Setup:** the destination is never committed. Put the database link in
`~/Developer/.env` (and `chmod 600` it):

```
NOTION_CLAUDE_MEMORY_URL=<link to the claude memory Notion page>
```

Writes go through the Notion MCP connector; the skill stops loudly if either
the variable or the connector is missing rather than guessing a database.

**What it does:**
1. Reads only the `NOTION_CLAUDE_MEMORY_URL` line out of `~/Developer/.env`, then resolves that URL to the database's data source and its **live** schema — tag options and property names are re-read every run, never hardcoded
2. Works out what to actually remember, resolving vague references ("that command", "the tool we just used") to the real thing in the conversation
3. Drafts the row in the database's house style: emoji icon, `subject — what it does` title, a short body that leads with the source link and carries the exact runnable invocation, absolute dates. Any URL it didn't see in the conversation is fetched and confirmed before it's written — no plausible-looking dead links
4. Picks tags from the existing options whenever one fits, and asks before creating a brand-new one — which means altering the multi-select schema first, re-listing every existing option and colour, since Notion rejects unknown tags rather than creating them on the fly
5. Queries the database for near-duplicates by subject, skipping archived rows; if one is close, shows it alongside the draft and asks whether to merge into it or add a new row
6. Previews the entry, creates it as `active`, and reports the resulting Notion URL — reporting any write failure verbatim, draft included

**Archive, never delete.** Asking it to remove a memory flips that row's `Status` to `archived` instead of destroying it. The database's default view filters archived rows out, so it reads as deleted day to day, while the entry and its history survive in a separate Archived view. Real deletion is a Notion-UI action and the skill says so rather than doing it.

## Project Structure

```
kingbob-claude-plugins/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest (name: kingbob)
│   └── marketplace.json     # Marketplace manifest
├── .github/workflows/
│   └── validate.yml         # CI: manifest + skill frontmatter validation
├── skills/
│   ├── add-to-notion-memory/SKILL.md
│   ├── cite/SKILL.md
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
