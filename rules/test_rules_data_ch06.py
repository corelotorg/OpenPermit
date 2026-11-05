# SPDX-License-Identifier: Apache-2.0
"""Chapter 6 rule-unit data checks: generator sync, schema validity, sourcing labels."""

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CH06 = ROOT / "rules" / "irc2021" / "ch06"
_spec = importlib.util.spec_from_file_location("build_units_ch06", CH06 / "build_units.py")
build_units = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_units)

RULE_SCHEMA = json.loads((ROOT / "spec" / "ori-rule-unit-0.1.schema.json").read_text())
UNIT = Draft202012Validator(RULE_SCHEMA)
COL = json.loads((CH06 / "va-vrc-2021-ch06.units.json").read_text())


def test_committed_outputs_match_generator():
    j, m = build_units.render()
    assert j == (CH06 / "va-vrc-2021-ch06.units.json").read_text(), "run rules/irc2021/ch06/build_units.py"
    assert m == (CH06 / "CHAPTER-6-TABLE.md").read_text(), "run rules/irc2021/ch06/build_units.py"


def test_units_validate_and_carry_paraphrase_and_link():
    for u in COL["units"]:
        assert not list(UNIT.iter_errors(u)), u["id"]
        assert u["paraphrase"] and u["source_url"].startswith("https://")


def test_only_virginia_values_are_marked_verified():
    for u in COL["units"]:
        for layer in [u["base_model"]] + u["jurisdiction_layers"]:
            for p in layer.get("parameters", []):
                if p["value_status"] == "sourced_primary":
                    assert p["source"] == "source:va:13vac5-63-210", (u["id"], p["name"])
                else:
                    assert p["value_status"] == "estimate", (u["id"], p["name"])


def test_paraphrases_are_cc0_and_complete():
    para = json.loads((CH06 / "paraphrases-ch06.json").read_text())
    assert para["license"].startswith("CC0-1.0")
    assert len(para["paraphrases"]) == COL["unit_count"]
