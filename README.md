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

### `/kingbob:notion-pa`

A personal assistant over the private Notion workspace — threads, projects,
tasks, and memory.

```
/kingbob:notion-pa [what to capture, or a question about what's live]
```

*(Renamed from `/kingbob:add-to-notion-memory`, which absorbed into Route F. The old
invocation no longer resolves.)*

**The model it serves:** *threads* are the nouns — ongoing strands of life, each
with a written condition for what ends it. *Projects* are things built. *Tasks*
are the verbs, spread across several databases, each carrying its own `Thread`
relation. *Memory* is the scrapbook.

**Setup:** nothing about the workspace is committed. Every database is resolved
at runtime from `~/Developer/.env` (`chmod 600`):

```
NOTION_THREADS_URL=<link>
NOTION_PROJECTS_URL=<link>
NOTION_CLAUDE_MEMORY_URL=<link>
NOTION_TASKS_ENCODE_URL=<link>
NOTION_TASKS_PERSONAL_URL=<link>
NOTION_TASKS_SIMRAN_PHD_URL=<link>
```

`NOTION_TASKS_*_URL` is a **prefix convention, not a fixed list** — every
matching key is a Tasks database, so adding one later means adding a key rather
than editing the skill. A missing key or a missing connector stops the run with
the key name, rather than guessing at a database.

**Routes:**

| Route | For | Behaviour |
|---|---|---|
| **A — task** | "remind me to…" | Infers which Tasks database *and* which thread, states both in one line, writes. No round-trip on the frequent path. |
| **B — thread** | a new ongoing strand | Refuses to open one without a written `What Resolution Looks Like`, and confirms before writing. |
| **C — project** | something being built | Creates the row from the name, then stops — status, stack, timeline and links are facts about your work, so it asks rather than inferring. |
| **D — briefing** | "what's live?" | Hand-rolls the rollup Notion can't do: reads every Tasks database, joins to threads, leads with overdue and owed. |
| **E — hygiene** | "check my notion" | Unlinked tasks, threads with no resolution criteria, resolved threads with no outcome, and any Tasks database missing a key or a `Thread` relation. |
| **F — memory** | a tool, command, or fix | The former `add-to-notion-memory`, intact: house style, live tags, duplicate check, archive-never-delete. |

Each Tasks database has its **own** schema (one carries `Lead` and
`Uni / Affiliation`, others carry `Tags`), so the skill reads each schema live
and writes only properties that database actually has.

`references/notion-mechanics.md` carries the connector's sharp edges — the SQL
query quota and why view-mode reads are preferred, select options needing a
schema alter, `status` vs `select`, and the fact that there is no delete path at
all.

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
│   ├── fix-latex-errors/SKILL.md
│   └── notion-pa/
│       ├── SKILL.md
│       └── references/notion-mechanics.md
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
