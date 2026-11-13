# SPDX-License-Identifier: Apache-2.0
"""ORI Inspection Request 0.1 draft: committed examples validate; known-bad payloads do not."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec" / "ori-inspection-request-0.1.schema.json").read_text())
EX = ROOT / "verification" / "examples" / "inspection"
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def load(name):
    return json.loads((EX / name).read_text())


def valid(doc):
    return not list(VALIDATOR.iter_errors(doc))


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("name", ["request-footing.json", "event-scheduled.json", "event-disapproved.json"])
def test_examples_validate(name):
    assert valid(load(name))


def mutate(name, fn):
    doc = copy.deepcopy(load(name))
    fn(doc)
    return doc


@pytest.mark.parametrize("case,doc", [
    ("missing permit", mutate("request-footing.json", lambda d: d.pop("permit"))),
    ("missing readiness attestation", mutate("request-footing.json", lambda d: d.pop("readiness"))),
    ("plaintext access code field", mutate("request-footing.json", lambda d: d["site_access"].__setitem__("lockbox_code", "1234"))),
    ("label claims approval", mutate("request-footing.json", lambda d: d.__setitem__("label", "Approved"))),
    ("no address and no parcel", mutate("request-footing.json", lambda d: d.__setitem__("site", {"unit": "A"}))),
    ("third party without credential", mutate("request-footing.json", lambda d: d.__setitem__("modality", "third_party"))),
    ("scheduled without a window", mutate("event-scheduled.json", lambda d: d.pop("scheduled_window"))),
    ("result on a non-completed event", mutate("event-scheduled.json", lambda d: d.__setitem__("result", "approved"))),
    ("completed without native result", mutate("event-disapproved.json", lambda d: d.pop("native_result"))),
    ("disapproved without corrections", mutate("event-disapproved.json", lambda d: d.pop("corrections"))),
    ("cancelled without a reason", mutate("event-scheduled.json", lambda d: (d.__setitem__("status", "cancelled"), d.pop("scheduled_window")))),
    ("mapped status only, native dropped", mutate("event-scheduled.json", lambda d: d.pop("native_status"))),
])
def test_bad_payloads_rejected(case, doc):
    assert not valid(doc), case
