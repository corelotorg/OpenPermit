# SPDX-License-Identifier: Apache-2.0
"""Normalized facts: one value, where it came from, and where it is anchored.

The IFC path and the declared-values (PDF) path both produce ``Subject``
objects holding ``Fact`` values, so the same rule functions run on either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Origins a rule may use for pass/fail.
USABLE_ORIGINS = frozenset(
    {
        "ifc_geometry",          # measured from IFC geometry by this evaluator
        "ifc_property",          # read from an IFC property or attribute
        "applicant_declared",    # applicant's declared value tied to a sheet/page
        "applicant_confirmed",   # extracted value the applicant confirmed
        "reviewer_confirmed",    # extracted value a reviewer confirmed
    }
)
# Origins that are evidence but not usable until confirmed; they yield unknown.
UNCONFIRMED_ORIGINS = frozenset(
    {
        "vector_extracted_unconfirmed",  # parsed from PDF vector text/dimensions
        "ai_extracted_unverified",       # produced by an AI/ML extractor
    }
)
ALL_ORIGINS = USABLE_ORIGINS | UNCONFIRMED_ORIGINS


@dataclass(frozen=True)
class Fact:
    value: Any
    origin: str
    anchor: dict[str, Any] | None = None
    note: str | None = None

    def __post_init__(self):
        if self.origin not in ALL_ORIGINS:
            raise ValueError(f"unknown fact origin {self.origin!r}")

    @property
    def usable(self) -> bool:
        return self.origin in USABLE_ORIGINS and self.value is not None

    def as_record(self) -> dict[str, Any]:
        d = {"value": self.value, "origin": self.origin}
        if self.anchor:
            d["anchor"] = self.anchor
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Subject:
    """A thing a rule is evaluated against (a stair flight, space, window, deck, guard)."""

    kind: str  # stair_flight | space | eero | walking_surface | guard
    subject_id: str
    label: str
    facts: dict[str, Fact] = field(default_factory=dict)
    anchor: dict[str, Any] | None = None  # e.g. {"type": "ifc_element", "ifc_guid": ...} or sheet/page
    notes: list[str] = field(default_factory=list)

    def get(self, name: str) -> Fact | None:
        return self.facts.get(name)
