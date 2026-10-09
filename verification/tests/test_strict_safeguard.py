# SPDX-License-Identifier: Apache-2.0
"""Strict 6-word safeguard over the whole repository (the enforced rule since 2026-09-28).

Every tracked or untracked (not ignored) text file is compared with the analyst's local code
copies; any run of 6 or more words shared with them fails. The code copies stay outside the
repository and are never published, so the test is skipped where they are absent (for example CI
or a fresh clone); set ORI_CODE_TEXT to a colon-separated list of paths to the local copies. Only counts, file names, line numbers and
SHA-256 digests are reported, never text. The refined run classification is not consulted."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from ori_cl import term_merger as tm

REPO = Path(__file__).resolve().parents[2]
CODE = [Path(p) for p in os.environ.get("ORI_CODE_TEXT", "").split(":") if p]
SKIP_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".ifc", ".zip"}


def _repo_files() -> list[Path]:
    r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=REPO,
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        out = r.stdout.split("\n")
    else:  # not a git checkout (for example an exported tree): scan every file
        out = [str(p.relative_to(REPO)) for p in REPO.rglob("*")
               if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts]
    return [REPO / f for f in out if f and Path(f).suffix.lower() not in SKIP_SUFFIXES and (REPO / f).is_file()]


@pytest.mark.skipif(not CODE or not all(p.is_file() for p in CODE), reason="local code copies not present")
def test_repository_has_no_six_word_run_shared_with_code_copies():
    texts = [p.read_text(encoding="utf-8", errors="ignore") for p in CODE]
    hits = tm.scan_paths(_repo_files(), texts, set())
    report = [f"{Path(h['file']).relative_to(REPO)}:{h['line']} run={h['length']} sha256={h['sha256'][:12]}" for h in hits]
    assert not hits, "strict safeguard: shared 6-word runs with the code copies:\n" + "\n".join(report)
