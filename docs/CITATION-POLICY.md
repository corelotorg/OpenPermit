# ORI citation policy: cite, interpret, link, never reproduce

Status: **in force for this repository** from 2026-09-28 (a rule Jeremiah Horstick set on
2026-09-28). Enforced in part by conformance rule `no-code-text` and by the repo-wide code-text
lint in `conformance/validate.py`. Licence of this document: CC0.

## 1. Why

Virginia's Uniform Statewide Building Code (USBC) incorporates the International Codes by reference
(13VAC5-63-10). The 2021 Virginia Residential Code (VRC) is the 2021 IRC as amended by
13VAC5-63-210 §310.8. The International Code Council holds copyright in the IRC text and
enforces it actively. ORI therefore works as an index and analysis layer: it says where a rule
is, what it does in ORI's own words, and where the official text can be read. It is never a
copy of the code.

This policy is ORI's working rule and is not legal advice. It is deliberately stricter than
what might be defensible, because the goal is to never need that defence.

## 2. Allowed

| Allowed | Example |
|---|---|
| Section, table and figure numbers, edition and chapter | `R311.7.5.1`, `Table R302.1(1)`, 2021 VRC Ch. 3 |
| ORI's own paraphrase of what a requirement does | "No riser in a flight may be taller than the maximum." |
| Bare numeric thresholds that a rule needs, with units | `max_riser_height <= 8.25 in` |
| Short names of defined terms, and the short undefined term at issue (4 words or fewer) | "habitable attic", "enclosed", "usable space" |
| ORI descriptions of a unit (not the code's heading) | "Exterior door landings: size and slope" |
| Links to official sources | see §5 |
| Provenance of a source ORI read: URL, fetch date, SHA-256, method | `sha256: 0dae8f91…` |

## 3. Not allowed

- Verbatim or near-verbatim code sentences or clauses, in any file: data, docs, tests,
  fixtures, commit messages or comments. Near-verbatim means following the code's sentence with
  small edits. The test: would a reader recognise the code's own sentence?
- Tables of section numbers paired with the code's own section headings (a copied table of
  contents). ORI unit titles describe effect in ORI's words.
- Substantive quotations from ICC text, including definitions.
- Code text copied from third-party viewers (UpCodes, PDFs, images), including OCR output or
  cached HTML, committed to the repository. Keep only the URL, fetch date and hash.
- Code text in test fixtures. Where a test needs code-like wording, use an obviously fictional
  sentence (see `conformance/negative/no-code-text-verbatim-quote.json`).

## 4. Virginia's own text and Review Board records

Virginia's regulation (13VAC5-63) is public law, and SBCTRB decisions and DHCD documents are
public records. ORI still **prefers paraphrase** for them:

- Paraphrase the amendment's effect ("Virginia raises the maximum riser to 8-1/4 in").
- Quote only when the exact words are the point (for example, the undefined term the Board
  had to interpret). Keep it short, cite the item or record, and link it.
- Document titles and headings may be named as titles (for example, the booklet's cover title).

## 5. How to cite and link

### 5.1 Virginia regulation (primary for the Virginia layer)

- Cite: `13VAC5-63-210, VCC §310.8 item 20 (amends IRC R311.7.5.1)`.
- Link: `https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section210/`
  (other sections follow `.../chapter63/section<NNN>/`, for example `section10` for VCC Chapter 1).
- Record the read date. Item numbers are ORI's count until a human confirms them.

### 5.2 ICC model code and the VRC as published

- Cite: `2021 IRC R311.7.5.1` for the model code, or `2021 VRC R311.7.5.1` for the adopted text.
- Link to ICC Digital Codes (free view):
  - 2021 VRC Chapter 3: `https://codes.iccsafe.org/content/VARC2021P1/chapter-3-building-planning`
  - 2021 IRC Chapter 3: `https://codes.iccsafe.org/content/IRC2021P1/chapter-3-building-planning`
  - Other chapters follow `https://codes.iccsafe.org/content/<BOOK>/chapter-<n>-<slug>`.
- ICC Digital Codes returns HTTP 403 to automated fetches. The chapter URLs above were
  confirmed through a search index on 2026-09-28. Section-level anchors have **not** been
  verified, so ORI links at chapter level and states the section number beside the link.
- ICC Committee Interpretations are members-only. Do not summarise them into the public graph
  without membership and a licence review.

### 5.3 DHCD, SBCTRB and local records

- Link the DHCD page or PDF (`https://www.dhcd.virginia.gov/...`) or the locality's own URL.
- Give the record's number, date and body, and summarise the holding in ORI's words (600
  characters or fewer in the interpretability schema).
- Keep verification provenance (fetched_at, method, sha256), not the text.

### 5.4 Secondary publications

UpCodes and handouts may be read to locate a value. Cite them as secondary sources in
provenance and never copy their text. The unit's `source_url` still points to the official
source.

## 6. What the data model requires

Every rule unit (`spec/ori-rule-unit-0.1.schema.json`) carries:

- `title`: an ORI description of effect;
- `paraphrase`: 20–400 characters in ORI's own words;
- `source_url`: an https link to an official source (codes.iccsafe.org, law.lis.virginia.gov or
  dhcd.virginia.gov);
- `source_links` (optional): more official links, for example the Virginia regulation where
  Virginia changes the section.

Conformance rule `no-code-text` rejects a unit that:

- lacks a paraphrase or an official source URL;
- quotes more than 4 words in any prose field;
- uses the code's normative "shall" register in ORI prose;
- uses an "ambiguous term" field that is really a clause.

The repo-wide lint rejects quoted spans of 6 or more words in "shall" register in docs, research,
rules, spec, verification, profiles, reference-node and conformance files.

These checks catch the common failures. They cannot prove that a paraphrase is not
near-verbatim, because proving that would need the ICC text, and ORI does not store it.
Human review of new prose is still required. An optional local check compares repo text with a
licensed or cached copy that is kept **outside** the repository (set `ORI_CODE_TEXT` to the local copies; the
strict check runs in `verification/tests/test_strict_safeguard.py`).

## 7. Writing paraphrases

1. Say what the rule does, not how the code words it: who, what, when, and the measurable
   limit.
2. Use plain verbs ("must", "may not", "needs"), never "shall".
3. Use a different sentence structure from the code, and read the code only to check the
   meaning, not while drafting.
4. Replace lists copied from the code with a summary ("the listed locations"), unless a short
   list of common nouns is needed for the meaning.
5. Put values in parameters, with the paraphrase naming "the maximum" or "the minimum".
6. Flag uncertainty. A paraphrase is ORI's reading, not an interpretation, and never approval.

## 8. Existing history

ORI working commits made before this policy contained some reproduced code text. That working
history is not part of this repository's published history.
