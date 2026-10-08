# SPDX-License-Identifier: Apache-2.0
"""License and citation records for the term merger study's evidence corpora (DRAFT).

Every source in research/data/ori-cl-open-corpora-DRAFT.json must carry:

* a license record: ``license_id``, ``license_basis``, ``license_url``, ``license_fetched_at``;
* a local copy of the license evidence: ``license_local_path`` and ``license_sha256``. Copies
  that may be redistributed (CC legal codes, US Code text, US government notices, rights facts)
  live in the repository under research/licenses/. Copies of terms pages that may not be
  redistributed live outside the repository under ``$ORI_CORPORA/licenses/`` (the
  ``ORI_CORPORA`` environment variable names the local corpora directory); only their symbolic
  path, URL and SHA-256 are recorded;
* the original source: ``source_url`` and ``source_citation`` (author or agency, title,
  edition or year, publisher, identifier, archive URL, accessed date).

``entry_errors`` and ``manifest_errors`` are used by the conformance rule
``open-corpora-manifest``, by conformance/validate.py and by ``OpenCorpora.from_manifest``,
which refuses to ingest a source that fails them. The full corpus build inherits this rule.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from .vocab import REPO_ROOT

REPO_LICENSE_DIR = "research/licenses/"
EXTERNAL_LICENSE_DIR = "$ORI_CORPORA/licenses/"
CLASSES = ("public_domain", "open_license", "locality", "candidate_vocabulary")
ROLES = ("text_corpus", "lexical_resource", "search_counts", "vocabulary_candidate")
REQUIRED = ("id", "title", "class", "role", "source_url", "source_citation", "license_id", "license_basis",
            "license_url", "license_local_path", "license_sha256", "license_fetched_at", "license_confirmed")
CITATION_PARTS = ("author", "title", "year", "publisher", "identifier", "archive_url", "accessed")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class CorpusLicenseError(ValueError):
    """A corpus source lacks its license record, local license copy or citation."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_errors(sid: str, path: str, digest: str, repo: Path) -> list[str]:
    errs = []
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest or "")):
        errs.append(f"{sid}: license copy {path!r} needs a SHA-256")
    if path.startswith(REPO_LICENSE_DIR):
        f = repo / path
        if not f.is_file():
            errs.append(f"{sid}: license copy {path} is missing from the repository")
        elif digest and file_sha256(f) != digest:
            errs.append(f"{sid}: license copy {path} does not match its SHA-256")
    elif path.startswith(EXTERNAL_LICENSE_DIR):
        base = os.environ.get("ORI_CORPORA", "")
        f = Path(base) / path[len("$ORI_CORPORA/"):] if base else None
        if f is None:
            return errs  # external copies are checked only where ORI_CORPORA points at them
        if f.is_file() and digest and file_sha256(f) != digest:  # checked where the box copy exists
            errs.append(f"{sid}: external license copy {path} does not match its SHA-256")
    else:
        errs.append(f"{sid}: license copy must be under {REPO_LICENSE_DIR} or {EXTERNAL_LICENSE_DIR}")
    return errs


def entry_errors(e: dict[str, Any], repo: Path = REPO_ROOT) -> list[str]:
    sid = e.get("id", "<no id>")
    errs = [f"{sid}: missing {k}" for k in REQUIRED if e.get(k) in (None, "", [], {})]
    if errs:
        return errs
    if e["class"] not in CLASSES:
        errs.append(f"{sid}: class must be one of {CLASSES}")
    if e["role"] not in ROLES:
        errs.append(f"{sid}: role must be one of {ROLES}")
    for key in ("source_url", "license_url"):
        if not str(e[key]).startswith("https://"):
            errs.append(f"{sid}: {key} must be an https URL")
    if not _DATE.fullmatch(str(e["license_fetched_at"])):
        errs.append(f"{sid}: license_fetched_at must be YYYY-MM-DD")
    cit = e["source_citation"]
    if not isinstance(cit, dict):
        errs.append(f"{sid}: source_citation must be an object with {CITATION_PARTS}")
    else:
        errs += [f"{sid}: source_citation missing {k}" for k in CITATION_PARTS if not cit.get(k)]
        if cit.get("accessed") and not _DATE.fullmatch(str(cit["accessed"])):
            errs.append(f"{sid}: source_citation.accessed must be YYYY-MM-DD")
        if cit.get("archive_url") and not str(cit["archive_url"]).startswith("https://"):
            errs.append(f"{sid}: source_citation.archive_url must be an https URL")
    errs += _copy_errors(sid, str(e["license_local_path"]), e["license_sha256"], repo)
    for ev in e.get("license_evidence", []) or []:
        if not ev.get("url") or not ev.get("path"):
            errs.append(f"{sid}: each license_evidence item needs url and path")
            continue
        errs += _copy_errors(sid, ev["path"], ev.get("sha256"), repo)
    if e["license_confirmed"] is not True and not e.get("license_note"):
        errs.append(f"{sid}: an unconfirmed license needs license_note")
    if e["license_confirmed"] is not True and e.get("strong_evidence"):
        errs.append(f"{sid}: a source whose license is not confirmed is never strong evidence")
    if e["class"] == "locality" and e.get("strong_evidence"):
        errs.append(f"{sid}: locality material is cite-and-link and never strong evidence")
    if e["role"] == "text_corpus":
        for k in ("local_file", "sha256", "words"):
            if not e.get(k):
                errs.append(f"{sid}: text corpus needs {k}")
    return errs


def manifest_errors(m: dict[str, Any], repo: Path = REPO_ROOT) -> list[str]:
    errs = []
    seen = set()
    for e in m.get("corpora", []):
        if e.get("id") in seen:
            errs.append(f"{e.get('id')}: duplicate id")
        seen.add(e.get("id"))
        errs += entry_errors(e, repo)
    if not m.get("corpora"):
        errs.append("manifest lists no corpora")
    return errs


def require(e: dict[str, Any], repo: Path = REPO_ROOT) -> None:
    """Raise CorpusLicenseError unless the source has its license record, copy and citation."""
    errs = entry_errors(e, repo)
    if errs:
        raise CorpusLicenseError("; ".join(errs))


def citation_text(e: dict[str, Any]) -> str:
    c = e["source_citation"]
    parts = [str(c[k]).strip().rstrip(".") for k in ("author", "title", "year", "publisher", "identifier")]
    return ". ".join(parts) + f". {c['archive_url']} (accessed {c['accessed']})."
