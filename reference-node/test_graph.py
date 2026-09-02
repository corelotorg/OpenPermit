from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "reference-node" / "graph.py"
spec = importlib.util.spec_from_file_location("ori_graph", GRAPH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_critical_path() -> None:
    result = module.analyze_precedence(
        {
            "nodes": [
                {"id": "a", "duration": 2},
                {"id": "b", "duration": 5},
                {"id": "c", "duration": 3},
                {"id": "d", "duration": 2},
            ],
            "edges": [
                {"from": "a", "to": "b"},
                {"from": "a", "to": "c"},
                {"from": "b", "to": "d"},
                {"from": "c", "to": "d"},
            ],
        }
    )
    assert result["is_dag"] is True
    assert result["graph_duration"] == 9.0
    assert result["critical_nodes"] == ["a", "b", "d"]
    assert result["schedule"]["c"]["total_float"] == 2.0


def test_cycle_detection() -> None:
    result = module.analyze_precedence(
        {
            "nodes": [{"id": "a"}, {"id": "b"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
        }
    )
    assert result["is_dag"] is False
    assert result["cycle_detected"] is True
    assert result["cycle_nodes"] == ["a", "b"]
