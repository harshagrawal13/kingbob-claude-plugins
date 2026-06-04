---
name: fix-latex-errors
description: Diagnose and fix LaTeX compilation errors and warnings. Optionally pass the exact error/warning text (pasted from the log); with no arguments it compiles the document, collects every error and warning, and explains how to fix each one. Applies safe fixes directly but asks for a greenlight before any big change. Use when the user has a LaTeX error, their document won't compile, or they say "/fix-latex-errors".
argument-hint: "[exact error or warning text] [main .tex file]"
user-invocable: true
allowed-tools: Bash(latexmk:*), Bash(pdflatex:*), Bash(xelatex:*), Bash(lualatex:*), Bash(tectonic:*), Bash(bibtex:*), Bash(biber:*), Bash(makeindex:*), Bash(kpsewhich:*), Read, Grep, Glob, Edit, AskUserQuestion
---

# fix-latex-errors

Fix LaTeX compilation problems — a single pasted error, or a full sweep of
every error and warning in the document.

## Input

<arguments>
$ARGUMENTS
</arguments>

The arguments may contain, in any order:

- **An error or warning** (optional): pasted verbatim from a log or editor,
  e.g. `! Undefined control sequence.` or
  `LaTeX Warning: Reference 'fig:foo' on page 3 undefined`.
- **A `.tex` file** (optional): the main document. If absent, detect it.

Pick the mode:

| Given             | Mode                                                        |
|-------------------|-------------------------------------------------------------|
| error/warning     | **Targeted mode**: diagnose and fix that one issue (Step 2 onward, scoped to it) |
| nothing           | **Sweep mode**: compile, collect every error and warning, triage all of them |

## Step 1 — Find the main document and how it builds

- Glob `**/*.tex` and pick the file containing `\documentclass` (if several,
  prefer one named `main.tex`/`paper.tex`/`thesis.tex` or referenced by a
  `latexmkrc`/`Makefile`; if still ambiguous, ask).
- Detect the intended engine and bibliography tool: `latexmkrc`, `Makefile`,
  magic comments (`% !TEX program = xelatex`), `\usepackage{fontspec}` →
  xelatex/lualatex, `biblatex` with `backend=biber` → biber.
- Never switch engines or build tools to "make the error go away" — that is a
  big change (see greenlight rules below).

## Step 2 — Reproduce

Compile to get a fresh, complete log:

```bash
latexmk -interaction=nonstopmode -file-line-error -halt-on-error=false <engine flag> main.tex
```

(Fall back to running the engine directly with
`-interaction=nonstopmode -file-line-error` if latexmk is unavailable. If no
TeX distribution is installed, say so and work statically from the sources
and any existing `.log` file instead.)

- **Targeted mode**: confirm the pasted error/warning actually appears in the
  fresh log. If it doesn't, say so — it may already be fixed or belong to a
  different file — and show what the log says instead.
- **Sweep mode**: keep the full log for Step 3.

## Step 3 — Collect and triage every issue (sweep mode)

Parse the `.log` (and `.blg` for bibliography runs) for, in priority order:

1. **Errors** — lines starting `!` (with `-file-line-error`, the
   `file:line: message` form). These block compilation; fix first. Note that
   one real error often cascades into dozens of bogus follow-ups — diagnose
   the *first* error, fix, recompile, repeat, rather than chasing the cascade.
2. **Undefined references / citations** — `LaTeX Warning: Reference ... undefined`,
   `Citation ... undefined`, `There were undefined references`. Check whether
   the label/key exists (Grep the sources and `.bib`); distinguish a typo'd
   key from a genuinely missing entry from a stale build needing another
   pass.
3. **Multiply-defined labels**, duplicate citation keys.
4. **Package and class warnings** — deprecations, option clashes, "loaded
   twice", float specifier changes.
5. **Layout warnings** — `Overfull \hbox`/`\vbox`, underfull boxes. Report
   the worst offenders (say, > 10pt) with their source location; tiny
   overfulls can be listed in one line as ignorable.
6. **Font warnings** — missing shapes/sizes, substitutions.

Produce a numbered report, one entry per *root cause* (deduplicate repeats of
the same warning), each with:

- severity (🛑 error / ⚠️ warning / ℹ️ cosmetic),
- `file:line`,
- a one-sentence explanation of what it means,
- the concrete proposed fix.

## Step 4 — Fix, with greenlights for big changes

Classify each proposed fix:

**Safe — apply directly** (after listing it in the report): single-site,
mechanical, content-preserving fixes. Examples: escaping a stray `%`/`&`/`_`,
closing an unclosed `$` or environment, fixing a typo'd `\ref`/`\cite` key,
adding a missing `\usepackage` for a command that clearly needs it, fixing a
malformed table column spec, renaming one duplicate label and its references.

**Big — greenlight first** via AskUserQuestion, presenting what would change
and why, with a do-nothing option. Anything that:

- touches many sites or does a project-wide find-and-replace,
- changes the preamble's packages/options beyond adding one obviously-missing
  package (swapping packages, reordering loads, changing class options),
- switches engine, bibliography backend, or build tooling,
- alters document content, wording, structure, or visual layout (e.g.
  rewriting a paragraph to kill an overfull box, resizing figures, changing
  margins),
- deletes anything beyond dead code that the fix itself makes unreachable.

Group related big changes into one question rather than asking five times.
If the user declines, leave that item in the report as "flagged, not fixed —
here's the manual fix" and move on.

## Step 5 — Verify and report

1. Recompile (twice, plus biber/bibtex, if references changed) and confirm the
   fixed issues are gone from the log. If a fix didn't take, say so — never
   report a fix as done on the strength of the edit alone.
2. Final report: issues fixed (with file:line of each edit), issues flagged
   awaiting the user's call, issues remaining (with the manual fix for each),
   and the document's end state (`compiles cleanly` / `compiles with N
   warnings` / `still fails at ...`).
3. Leave build artifacts (`.aux`, `.log`, …) alone — do not clean up unless
   asked.
