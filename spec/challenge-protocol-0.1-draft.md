# ORI Challenge Protocol — v0.1 Draft

Challengeability is a required property of ORI. A challenge is not an edit to the challenged object; it is a new, addressable claim with its own evidence, provenance, history and disposition.

## Challengeable targets

At minimum:

- Assertion
- MappingAssertion
- Requirement interpretation
- Verification
- Evidence
- Decision
- Guidance alignment result
- Profile control or mapping

## Challenge object

Required semantics:

```yaml
id: stable identifier
type: Challenge
subject: challenged object id
challenged_by: actor/agent/authority id
grounds: typed or namespaced basis
statement: human/model-readable statement
evidence: [evidence ids]
status: open
created_at: datetime
```

A challenge MAY reference a prior challenge or response through `respondsTo`/`response_to` to create a rebuttal graph.

## Disposition

Resolution is a separate append-only object:

```yaml
id: stable identifier
type: ChallengeDisposition
challenge: challenge id
decided_by: actor/authority/agent id
disposition: answered | sustained | rejected | withdrawn | superseded
statement: rationale
evidence: [evidence ids]
created_at: datetime
```

A disposition does not erase the challenge or target. A sustained challenge SHOULD produce an explicit amendment, supersession, withdrawal, alternative mapping, corrected verification, or new authorized decision where appropriate.

## Required queries

A conforming implementation MUST support semantic equivalents of:

- retrieve challenge and target;
- retrieve provenance/source for the target;
- retrieve supporting and counter-evidence;
- retrieve responses/dispositions;
- list unresolved challenges affecting an object;
- traverse from a disposition to any amended/superseding object;
- reconstruct challenge history without relying on mutable comments.

## Authority boundary

A model, contributor or validator may challenge a conclusion without possessing governmental authority. Conversely, a challenge disposition by an arbitrary participant does not become legally binding merely because it is represented in ORI. Authority and scope remain explicit data.
