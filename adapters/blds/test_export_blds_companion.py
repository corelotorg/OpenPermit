# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "blds" / "export_blds_companion.py"
# The synthetic example inventory (CC0) is always present; real public-source inventories are tested
# too when they exist in the tree.
EXAMPLE = ROOT / "profiles" / "examples" / "example-city" / "residential-new-construction-example.json"
PROFILES = [EXAMPLE] + sorted((ROOT / "profiles" / "jurisdictions").rglob("*.json"))

spec = importlib.util.spec_from_file_location("blds_adapter", ADAPTER)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


profile_paths = pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.parent.name)


@profile_paths
def test_rows_match_inventory_counts_and_carry_provenance(path: Path) -> None:
    profile = load(path)
    rows = adapter.export([path])
    expected = len(profile["approvals"]) + len(profile.get("fees", [])) + len(profile.get("inspections", []))
    assert len(rows) == expected
    source_locators = {s["id"]: s["locator"] for s in profile["sources"]}
    for row in rows:
        assert set(row) == set(adapter.FIELDNAMES)
        assert row["Link"], row["ORI_Id"]
        assert row["Link"] in source_locators.values()
        assert row["ORI_SourceIds"]
        assert row["IssuedDate"] == ""  # inventory rows are not issued permits
        assert row["StatusMapped"] == ""
        assert row["ORI_LegalDetermination"] == "false"


@profile_paths
def test_fee_amount_and_rate_are_copied_not_computed(path: Path) -> None:
    rows = {r["ORI_Id"]: r for r in adapter.export([path])}
    profile = load(path)
    for fee in profile["fees"]:
        row = rows[fee["id"]]
        assert row["PermitTypeMapped"] == "FeeScheduleItem"
        if "amount" in fee:
            assert row["Fee"] == str(fee["amount"])
        else:
            assert row["Fee"] == ""
            assert row["ORI_Rate"] == str(fee["rate"])
            assert row["ORI_RateUnit"] == fee["rate_unit"]
            assert row["ORI_Minimum"] == str(fee["minimum"])


@profile_paths
def test_undeclared_source_is_refused(path: Path) -> None:
    profile = copy.deepcopy(load(path))
    profile["fees"][0]["source"] = "source:does-not-exist"
    with pytest.raises(adapter.ProvenanceError):
        adapter.rows_for_profile(profile)


@profile_paths
def test_missing_source_is_refused(path: Path) -> None:
    profile = copy.deepcopy(load(path))
    profile["inspections"][0].pop("source")
    with pytest.raises(adapter.ProvenanceError):
        adapter.rows_for_profile(profile)


@profile_paths
def test_cli_writes_csv(tmp_path: Path, path: Path) -> None:
    out = tmp_path / "companion.csv"
    assert adapter.main([str(path), "--out", str(out)]) == 0
    with out.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == adapter.FIELDNAMES
        assert len(list(reader)) == len(adapter.export([path]))
