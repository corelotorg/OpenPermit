# SPDX-License-Identifier: Apache-2.0
import json
import sys
from pathlib import Path

import pytest

VERIFICATION = Path(__file__).resolve().parents[1]
REPO = VERIFICATION.parent
sys.path.insert(0, str(VERIFICATION))

from ori_verify import ifc_fixtures  # noqa: E402

FIXED_TIME = "2026-09-27T12:00:00Z"


@pytest.fixture(scope="session")
def ifc_models(tmp_path_factory):
    d = tmp_path_factory.mktemp("ifc")
    return {
        "pass": ifc_fixtures.write_fixture(ifc_fixtures.passing_spec(), d / "pass.ifc"),
        "fail": ifc_fixtures.write_fixture(ifc_fixtures.failing_spec(), d / "fail.ifc"),
        "incomplete": ifc_fixtures.write_fixture(ifc_fixtures.incomplete_spec(), d / "incomplete.ifc"),
    }


@pytest.fixture(scope="session")
def core_validator():
    from jsonschema import Draft202012Validator
    schema = json.loads((REPO / "spec" / "ori-core-0.1.schema.json").read_text())
    return Draft202012Validator(schema)


def states(report):
    """{(section, part, subject label): result_state}"""
    return {(r["metadata"]["section"], r["metadata"]["subsection_part"], r["metadata"]["subject"]["label"]): r["metadata"]["result_state"]
            for r in report["records"]}
