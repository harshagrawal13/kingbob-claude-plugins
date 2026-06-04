---
name: cite
description: Generate and verify a citation for a piece of prose. Pass a link (DOI, doi.org URL, arXiv, or publisher page) and optionally the paragraph or line it should support — or pass prose alone and the skill spawns parallel web-search agents to discover candidate citations, flagging each one's semantic relevance to the claim. Fetches BibTeX via doi2bib, verifies the entry against Crossref, then reads the cited source to check it actually supports the prose. Use when the user asks to cite something, find a citation for a claim, verify a citation, or says "/cite ...".
argument-hint: "[link-or-doi] [prose to cite, or file:line]"
user-invocable: true
allowed-tools: Bash(curl:*), WebFetch, WebSearch, Read, Grep, Glob, Task, Agent, AskUserQuestion
---

# cite

Turn a link into a verified BibTeX citation — or, given only prose, discover
candidate citations with web-search agents — and check that the cited source
actually supports that prose (or whether it better fits the prose nearby).

## Input

<arguments>
$ARGUMENTS
</arguments>

The arguments may contain, in any order:

- **A link** (optional): a bare DOI (`10.1038/nature12373`), a
  `https://doi.org/...` URL, an arXiv link/ID, a bioRxiv/medRxiv link, or a
  publisher landing page.
- **Prose** (optional): the sentence or paragraph the citation should support,
  either inline (often quoted) or as a `path/to/file.tex:123`-style reference
  into a manuscript in the working directory.

Pick the mode from what was given:

| Given            | Mode                                                       |
|------------------|------------------------------------------------------------|
| link + prose     | Verify mode: Steps 1 → 5                                   |
| link only        | Verify mode, but skip the prose-support check in Step 4    |
| prose only       | **Discovery mode**: Step 1b first, then Steps 2 → 5 for the chosen source |
| neither          | Ask the user for one or the other                          |

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

## Step 1b — Discovery mode: find candidate citations for the prose

Only when prose was given without a link.

1. **Get the prose in context.** If the user gave a `file:line` reference,
   Read the surrounding paragraph. Distill the prose into its core claim(s) —
   that claim, not the raw sentence, is what the agents search for.

2. **Spawn search agents in parallel** (a single message with multiple Task
   tool calls — small, focused agents, not one mega-search). Give each agent
   the claim verbatim, a distinct search modality, and the same return format:

   - **Web agent** — WebSearch with 2–3 keyword variants of the claim
     (including a scholar-flavored query like `<claim keywords> paper study`),
     following promising hits with WebFetch.
   - **Scholarly-API agent** — query the open APIs with curl:
     `https://api.crossref.org/works?query.bibliographic=<keywords>&rows=10`,
     `https://api.semanticscholar.org/graph/v1/paper/search?query=<keywords>&fields=title,year,venue,abstract,externalIds&limit=10`,
     and `https://api.openalex.org/works?search=<keywords>&per-page=10`.
   - **Preprint agent** (only when the claim is in a preprint-heavy field —
     ML/physics → arXiv API, biology/medicine → bioRxiv/medRxiv) — search the
     relevant preprint server.

   Each agent must return **up to 5 candidates**, one per line:
   `DOI | title | year | venue | one-line abstract snippet | why it matches the claim`
   — and must only return papers it actually saw evidence for (a real DOI and
   a real abstract/snippet). No guessed or "probably exists" papers:
   hallucinated references are the one unforgivable failure of this skill.

3. **Merge and dedupe** candidates by DOI (an arXiv DOI and its published DOI
   count as the same paper — keep the published one).

4. **Judge semantic relevance** of each candidate (cap at the top ~5) against
   the claim. Fetch the abstract if the agent didn't return one (Semantic
   Scholar `DOI:<doi>` lookup). Topical overlap is NOT support — flag the
   difference explicitly. Rate each candidate:

   - 🎯 **Supports the claim** — the paper's own findings back the specific
     assertion in the prose.
   - 🟡 **Topically related** — same subject area, but it does not establish
     (or only tangentially touches) what the prose asserts.
   - 🔴 **Semantic mismatch** — keyword overlap only, or the paper actually
     undercuts the claim.

5. **Present the candidates** in a ranked table (rating, title, year, venue,
   one-line evidence) and ask the user which to cite via AskUserQuestion
   (offer multi-select when several 🎯 candidates genuinely co-support the
   claim). If nothing rates 🎯, say so plainly and recommend either weakening
   the prose or searching again with a reformulated claim — do not pass off a
   🟡 as a real citation without the user opting in.

6. Continue to Step 2 with the chosen DOI(s), running Steps 2–5 for each.

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

Only when prose was provided. In Discovery mode this deepens the Step 1b
relevance rating: that was judged from the abstract; now check against fuller
text where available.

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

Never soften a ❌ into a ⚠️ to be agreeable. If full-text reading downgrades a
Discovery-mode 🎯, say so and let the user reconsider before finishing.

## Step 5 — Report

Output, in order:

1. The final BibTeX in a ```bibtex code block (verbatim, ready to paste) —
   one block per chosen source.
2. A one-line citation-correctness summary (registrar checks + any fixes).
3. The prose-support verdict with quoted evidence (or "no prose given —
   support check skipped"). In Discovery mode, also list the rejected
   candidates with their ratings so the user can see what was considered.
4. If a `.bib` file exists in the working directory (Glob `**/*.bib`), check
   whether this DOI or citation key is already in it; offer to append if not,
   and point out the existing key if it is. Never write to the `.bib` file
   without the user agreeing.
