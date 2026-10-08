# research/licenses: license evidence for the term merger study corpora (DRAFT)

Local copies of the license or public-domain evidence for every source listed in
research/data/ori-cl-open-corpora-DRAFT.json. Each manifest entry records `license_local_path`
and `license_sha256` (and `license_evidence` for extra copies); `verification/ori_cl/corpus_license.py`
checks that every in-repository copy exists and matches its SHA-256.

Only material that may be redistributed is kept here:

* Creative Commons legal codes and the Public Domain Mark deed (Creative Commons dedicates its
  legal code and deeds to the public domain under CC0; https://creativecommons.org/policies/).
* United States Code text (17 U.S.C. 105, 304) from https://uscode.house.gov/ and U.S. Copyright
  Office Circular 15A: works of the US government, not subject to copyright.
* The Cornell public-domain chart (Peter B. Hirtle, Cornell University Library), CC BY 4.0,
  with attribution in the file header.
* Rights facts: Internet Archive item metadata, the ERIC record, the OSHA 3124 public-domain
  notice, a Navy manual title-page header, Wikipedia revision ids.
* Lexical resource notices whose licenses permit redistribution (WordNet 3.0, Brown Corpus
  README header, wordfreq license).
* Notes where no license was found (Virginia localities) or the terms could not be captured
  (Internet Archive).

Copies of terms pages that may not be redistributed (NBS/Uniclass pages, Wikimedia Terms of Use,
locality pages, the Internet Archive shell) are kept outside the repository in
$ORI_CORPORA/licenses/; the manifest records their URL and SHA-256.

These are third-party legal texts, not building code text. Analysis to inform counsel, not a
legal conclusion.
