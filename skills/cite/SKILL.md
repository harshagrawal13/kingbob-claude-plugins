---
name: cite
description: Generate and verify a citation for a piece of prose. Pass a link (DOI, doi.org URL, arXiv, or publisher page) and optionally the paragraph or line it should support. Fetches BibTeX via doi2bib, verifies the entry against Crossref, then reads the cited source to check it actually supports the prose. Use when the user asks to cite something, verify a citation, or says "/cite <link>".
argument-hint: "<link-or-doi> [prose to cite, or file:line]"
user-invocable: true
allowed-tools: Bash(curl:*), WebFetch, WebSearch, Read, Grep, Glob
---

# cite

Turn a link into a verified BibTeX citation, and — when prose is given — check
that the cited source actually supports that prose (or whether it better fits
the prose nearby).

## Input

<arguments>
$ARGUMENTS
</arguments>

The arguments may contain, in any order:

- **A link**: a bare DOI (`10.1038/nature12373`), a `https://doi.org/...` URL,
  an arXiv link/ID, a bioRxiv/medRxiv link, or a publisher landing page.
- **Prose** (optional): the sentence or paragraph the citation should support,
  either inline (often quoted) or as a `path/to/file.tex:123`-style reference
  into a manuscript in the working directory.

If there is no link, ask the user for one. If there is no prose, skip Step 4
and say so in the report — do not ask.

## Step 1 — Resolve the link to a DOI

- **Bare DOI / doi.org URL**: strip any `https://doi.org/` prefix.
- **arXiv**: every arXiv paper has the DOI `10.48550/arXiv.<id>`. But first
  check whether a published version exists — query
  `curl -s "http://export.arxiv.org/api/query?id_list=<id>"` and look for a
  `<arxiv:doi>` element or journal reference. If a published DOI exists,
  prefer it and tell the user you swapped the preprint for the published
  version (offer the preprint DOI as the alternative).
- **Publisher / bioRxiv landing page**: fetch the page and look for the DOI in
  `citation_doi` / `dc.identifier` meta tags or a `doi.org` link near the
  title. As a fallback, search Crossref by title:
  `curl -s "https://api.crossref.org/works?query.bibliographic=<title>&rows=3"`
  and pick the matching record — confirm with the user if the top hit is not
  an obvious match.

## Step 2 — Generate the BibTeX (doi2bib)

```bash
curl -s -L --max-time 10 -H "Accept: text/bibliography; style=bibtex" "https://doi.org/<DOI>"
```

Quote the URL (DOIs may contain `;`, `&`, `<`, `>`). If the response is empty,
HTML, or an error, report what came back and stop — do not fabricate an entry.

## Step 3 — Verify the BibTeX entry

Cross-check the entry against the registrar's metadata:

```bash
curl -s "https://api.crossref.org/works/<DOI>"
```

(If Crossref 404s, it may be a DataCite DOI — try
`curl -s "https://api.datacite.org/dois/<DOI>"`.)

Check that:

- Title, first author, year, and venue in the BibTeX match the registrar
  record.
- No critical field is empty or mangled (LaTeX-escaped unicode is fine;
  HTML fragments or `{}` titles are not).
- The entry type makes sense (`@article` for journal papers, `@inproceedings`
  for conference papers, `@misc` for arXiv preprints, …).

Fix obvious problems in the BibTeX (e.g. protect case-sensitive acronyms with
braces) and note every fix you made. If the registrar record disagrees with
the entry in a way you can't reconcile, flag it loudly instead of papering
over it.

## Step 4 — Verify the citation supports the prose

Only when prose was provided.

1. **Get the prose in context.** If the user gave a `file:line` reference,
   Read the surrounding paragraph (a few sentences either side) — the point is
   to judge the claim *and its neighborhood*.
2. **Read the cited source.** Try, in order, until you have enough text:
   - WebFetch the `https://doi.org/<DOI>` landing page (abstract is often
     enough).
   - For arXiv/bioRxiv/medRxiv: fetch the abs page or the full text.
   - Semantic Scholar:
     `curl -s "https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=title,abstract,tldr,openAccessPdf"`
     — if it lists an open-access PDF, fetch that for full-text checking.
   - If everything is paywalled and only the abstract is available, say so and
     verify against the abstract alone.
3. **Judge the fit.** Does the source actually support the specific claim?
   Distinguish: the paper *shows* X vs. *mentions* X vs. *reviews others
   showing* X vs. *contradicts* X. Also check whether the citation fits a
   **neighboring sentence better** than the one marked — misplaced citations
   are the most common real-world error.

Render one verdict, with short quoted evidence from the source:

- ✅ **Supported** — the source directly supports the claim as written.
- ⚠️ **Partially supported** — supports a weaker/narrower version, or actually
  belongs on a nearby sentence (say which one).
- ❌ **Not supported** — the source does not address, or contradicts, the
  claim.
- ❓ **Cannot verify** — only the abstract was reachable and it is not
  sufficient to judge.

Never soften a ❌ into a ⚠️ to be agreeable.

## Step 5 — Report

Output, in order:

1. The final BibTeX in a ```bibtex code block (verbatim, ready to paste).
2. A one-line citation-correctness summary (registrar checks + any fixes).
3. The prose-support verdict with quoted evidence (or "no prose given —
   support check skipped").
4. If a `.bib` file exists in the working directory (Glob `**/*.bib`), check
   whether this DOI or citation key is already in it; offer to append if not,
   and point out the existing key if it is. Never write to the `.bib` file
   without the user agreeing.
