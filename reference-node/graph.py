from __future__ import annotations

from collections import defaultdict
from math import isclose
from typing import Any


def analyze_precedence(graph: dict[str, Any]) -> dict[str, Any]:
    raw_nodes = graph.get("nodes", [])
    raw_edges = graph.get("edges", [])
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValueError("nodes and edges must be arrays")

    nodes: dict[str, dict[str, Any]] = {}
    for node in raw_nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise ValueError("every node must be an object with string id")
        node_id = node["id"]
        if node_id in nodes:
            raise ValueError(f"duplicate node id: {node_id}")
        duration = node.get("duration", 0)
        if not isinstance(duration, (int, float)) or duration < 0:
            raise ValueError(f"duration must be a non-negative number: {node_id}")
        nodes[node_id] = {**node, "duration": float(duration)}

    successors: dict[str, list[str]] = defaultdict(list)
    predecessors: dict[str, list[str]] = defaultdict(list)
    seen_edges: set[tuple[str, str]] = set()

    for edge in raw_edges:
        if not isinstance(edge, dict):
            raise ValueError("every edge must be an object")
        src, dst = edge.get("from"), edge.get("to")
        if src not in nodes or dst not in nodes:
            raise ValueError(f"edge references missing node: {src!r} -> {dst!r}")
        pair = (src, dst)
        if pair in seen_edges:
            continue
        seen_edges.add(pair)
        successors[src].append(dst)
        predecessors[dst].append(src)

    for values in successors.values():
        values.sort()
    for values in predecessors.values():
        values.sort()

    indegree = {node_id: len(predecessors[node_id]) for node_id in nodes}
    ready = sorted([node_id for node_id, degree in indegree.items() if degree == 0])
    topo: list[str] = []

    while ready:
        current = ready.pop(0)
        topo.append(current)
        for child in successors[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()

    if len(topo) != len(nodes):
        cyclic = sorted([node_id for node_id, degree in indegree.items() if degree > 0])
        return {
            "is_dag": False,
            "cycle_detected": True,
            "cycle_nodes": cyclic,
            "topological_order": [],
        }

    earliest_start: dict[str, float] = {}
    earliest_finish: dict[str, float] = {}
    for node_id in topo:
        es = max((earliest_finish[parent] for parent in predecessors[node_id]), default=0.0)
        ef = es + nodes[node_id]["duration"]
        earliest_start[node_id] = es
        earliest_finish[node_id] = ef

    terminals = sorted([node_id for node_id in nodes if not successors[node_id]])
    starts = sorted([node_id for node_id in nodes if not predecessors[node_id]])
    graph_duration = max((earliest_finish[node_id] for node_id in terminals), default=0.0)

    latest_finish: dict[str, float] = {}
    latest_start: dict[str, float] = {}
    for node_id in reversed(topo):
        lf = min((latest_start[child] for child in successors[node_id]), default=graph_duration)
        ls = lf - nodes[node_id]["duration"]
        latest_finish[node_id] = lf
        latest_start[node_id] = ls

    schedule: dict[str, dict[str, float | bool]] = {}
    critical_nodes: list[str] = []
    for node_id in topo:
        total_float = latest_start[node_id] - earliest_start[node_id]
        critical = isclose(total_float, 0.0, abs_tol=1e-9)
        if critical:
            critical_nodes.append(node_id)
        schedule[node_id] = {
            "duration": nodes[node_id]["duration"],
            "earliest_start": earliest_start[node_id],
            "earliest_finish": earliest_finish[node_id],
            "latest_start": latest_start[node_id],
            "latest_finish": latest_finish[node_id],
            "total_float": total_float,
            "critical": critical,
        }

    critical_edges = [
        {"from": src, "to": dst}
        for src, dst in sorted(seen_edges)
        if src in critical_nodes
        and dst in critical_nodes
        and isclose(earliest_finish[src], earliest_start[dst], abs_tol=1e-9)
    ]

    parallel_branches = [
        {"from": node_id, "to": successors[node_id]}
        for node_id in topo
        if len(successors[node_id]) > 1
    ]

    return {
        "is_dag": True,
        "cycle_detected": False,
        "topological_order": topo,
        "start_nodes": starts,
        "terminal_nodes": terminals,
        "parallel_branches": parallel_branches,
        "graph_duration": graph_duration,
        "schedule": schedule,
        "critical_nodes": critical_nodes,
        "critical_edges": critical_edges,
    }
