# SPDX-License-Identifier: Apache-2.0
"""Load ORI rule units and resolve the effective parameters for a jurisdiction.

Resolution: start from the IRC base-model parameters (precedence 0). Apply each
jurisdiction layer for the requested jurisdiction in ascending precedence. A
layer with override_mode ``deletes`` makes the unit not applicable. Layer
parameters replace base parameters with the same name. Thresholds come from
the rule-unit data, never from constants in the rule functions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CH03_COLLECTION = REPO_ROOT / "rules" / "irc2021" / "ch03" / "va-vrc-2021-ch03.units.json"
VA = "urn:ori:jurisdiction:us-va"
BASE = "base:irc-2021"


@dataclass
class EffectiveUnit:
    unit: dict[str, Any]
    jurisdiction: str
    params: dict[str, dict[str, Any]] = field(default_factory=dict)
    param_layer: dict[str, str] = field(default_factory=dict)
    deleted: bool = False
    layers_applied: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.unit["id"]

    @property
    def function(self) -> str | None:
        impl = self.unit["evaluator"].get("implementation") or ""
        return impl.split("#", 1)[1] if "#" in impl else None

    def param(self, name: str) -> dict[str, Any] | None:
        return self.params.get(name)


def load_collection(path: Path = CH03_COLLECTION) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def all_units(collection: dict[str, Any]) -> list[dict[str, Any]]:
    return list(collection.get("units", [])) + list(collection.get("va_added_units", []))


def resolve(unit: dict[str, Any], jurisdiction: str | None) -> EffectiveUnit:
    eff = EffectiveUnit(unit=unit, jurisdiction=jurisdiction or BASE)
    base = unit["base_model"]
    if base.get("status", "present") == "present":
        for p in base.get("parameters", []):
            eff.params[p["name"]] = p
            eff.param_layer[p["name"]] = BASE
    eff.layers_applied.append(BASE)
    if jurisdiction is None:
        return eff
    layers = sorted(
        (l for l in unit.get("jurisdiction_layers", []) if l["jurisdiction"] == jurisdiction),
        key=lambda l: l["precedence"],
    )
    for layer in layers:
        eff.layers_applied.append(layer["layer_id"])
        if layer["override_mode"] == "deletes":
            eff.deleted = True
            eff.params.clear()
            continue
        for p in layer.get("parameters", []):
            eff.params[p["name"]] = p
            eff.param_layer[p["name"]] = layer["layer_id"]
    return eff


def implemented_units(jurisdiction: str | None = VA, path: Path = CH03_COLLECTION) -> list[EffectiveUnit]:
    col = load_collection(path)
    out = []
    for u in all_units(col):
        if u["evaluator"]["kind"] == "deterministic_function":
            out.append(resolve(u, jurisdiction))
    return out
