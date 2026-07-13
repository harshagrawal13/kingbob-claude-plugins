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

### `/kingbob:session-limit-guard`

Run a long task without slamming into the 5-hour Claude session usage limit: pause automatically near the limit, sleep until the window resets, resume where it left off.

```
/kingbob:session-limit-guard [threshold%] <task to run>
```

**What it does:**
1. Reads real session usage (5-hour + 7-day `used_percentage` and `resets_at`) from a local cache written by your statusline command — Claude Code sends the `rate_limits` block to the statusline after every API response, so no credentials, network calls, or undocumented APIs are involved
2. Works on your task normally, re-checking usage after each subtask and every ~10–15 minutes
3. At ≥ threshold (default 90%, i.e. 10% before the limit): finishes the current step to a safe point, writes an `slg-progress.md` resume file, announces when it will resume, and sleeps in a background process until ~2 minutes past the window reset
4. On wake: verifies the window reset, re-reads the progress file, and continues — pausing again if a very long task spans multiple windows
5. If the **weekly** limit is what's nearly exhausted, it parks the task and asks you instead of sleeping for days

**One-time setup:** the skill needs a small cache block in your statusline script; on first run it installs this itself via `setup_statusline_cache.sh` (idempotent, keeps a `.bak`, prints manual instructions if your statusline isn't a plain shell script). Pro/Max subscriptions only — API-key sessions have no 5-hour limit.

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
│   └── session-limit-guard/
│       ├── SKILL.md
│       └── scripts/         # check_usage.sh, wait_for_reset.sh, setup_statusline_cache.sh
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
