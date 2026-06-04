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

Generate and verify a citation for a piece of prose. Give it a link (DOI, doi.org URL, arXiv, bioRxiv, or publisher page) and optionally the sentence or paragraph the citation should support.

```
/kingbob:cite <link-or-doi> [prose to cite, or file:line]
```

**What it does:**
1. Resolves the link to a DOI (prefers the published version over an arXiv preprint, and tells you when it swaps)
2. Generates the BibTeX entry via doi.org content negotiation (doi2bib)
3. Verifies the entry against the Crossref/DataCite registrar record — title, authors, year, venue, entry type — and fixes obvious problems (noting every fix)
4. Reads the cited source (landing page, open-access PDF, or abstract) and judges whether it actually supports the prose — or whether it better fits a neighboring sentence — with a verdict (✅ supported / ⚠️ partial / ❌ not supported / ❓ cannot verify) backed by quoted evidence
5. Returns the ready-to-paste BibTeX, checks any `.bib` file in your project for duplicates, and offers to append

Without prose, it still generates and verifies the citation; the prose-support check is skipped.

## Project Structure

```
kingbob-claude-plugins/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest (name: kingbob)
│   └── marketplace.json     # Marketplace manifest
├── .github/workflows/
│   └── validate.yml         # CI: manifest + skill frontmatter validation
├── skills/
│   └── cite/SKILL.md
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
