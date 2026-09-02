# ORI Precedence Graph — v0.1 Draft

A `PrecedenceGraph` is an explicitly acyclic slice of the broader ORI regulatory graph used to represent process prerequisites and timing. The overall regulatory graph is not assumed to be acyclic.

## Input model

```json
{
  "type": "PrecedenceGraph",
  "nodes": [
    {"id": "action:a", "duration": 3},
    {"id": "action:b", "duration": 5}
  ],
  "edges": [
    {"from": "action:a", "to": "action:b", "relationship": "precedes"}
  ]
}
```

`duration` is optional and represents an explicitly declared or measured duration in a profile-defined unit. Derived critical-path values are calculations, not source facts.

## Required behavior

A conforming ORI-Graph implementation MUST:

1. reject duplicate node identifiers;
2. reject edges referencing missing nodes;
3. detect cycles and refuse to label a cyclic slice a `PrecedenceGraph`;
4. produce a deterministic topological order;
5. identify zero-predecessor start nodes and zero-successor terminal nodes;
6. identify parallel branches;
7. expose unsatisfied prerequisites for a supplied completion/state set;
8. when non-negative durations are supplied, compute earliest start/finish;
9. compute latest start/finish relative to the graph's longest completion time;
10. derive total float and critical nodes/edges;
11. preserve declared duration/source separately from derived schedule values.

## Critical path

For a DAG with declared non-negative node durations:

- `earliest_start(v)` is the maximum earliest finish of all predecessors, or `0` for a start node.
- `earliest_finish(v) = earliest_start(v) + duration(v)`.
- project/graph duration is the maximum earliest finish among terminal nodes.
- `latest_finish(v)` is the minimum latest start of successors, or graph duration for a terminal node.
- `latest_start(v) = latest_finish(v) - duration(v)`.
- `total_float(v) = latest_start(v) - earliest_start(v)`.
- nodes with float within the implementation's declared numerical tolerance of zero are critical.

If durations are not supplied, implementations still MUST support cycle detection, topological order, prerequisites, blocking analysis and parallel-branch discovery.

## Regulatory interpretation

Critical-path output is operational analysis. It does not override statutory sequencing, authority, mandatory waiting periods, appeal rights or jurisdictional rules. Any proposed removal, parallelization or deduplication of a review is an Assertion/Challenge until the relevant authority and sources support the change.
