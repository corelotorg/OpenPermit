# ORI Status and Statutory Clock — v0.1 Draft

**Status: DRAFT (issue #140, item A3).** Schema: `spec/ori-status-clock-0.1.schema.json`. Conformance rule: `status-clock-record`. Label: *Reviewer evidence, not approval.*

The status record is the append-only history of one application, written as core `Event` objects (ori-core §3.18). The statutory clock is a core object. Its parameters (length, day basis, what happens at the end) come from a jurisdiction profile, never from the record author.

## Events

Each event has `seq` (1, 2, 3 … no gaps), `at`, `event_type` and `actor_role`. Events are never edited or removed; a correction is a new event. Event types cover intake (`submitted`, `accepted_complete`, `incomplete_notice`), review (`review_started`, `comments_issued`, `resubmitted`), outcome (`decision_recorded`, `withdrawn`) and the clock (`clock_started`, `clock_paused`, `clock_resumed`, `clock_stopped`, `clock_deemed`).

## Clock

| Field | Meaning |
|---|---|
| `parameters_source.profile_ref` | the jurisdiction profile supplying the parameters, or `unknown` |
| `duration_days`, `day_basis` | from the profile, else `unknown` |
| `deemed_outcome` | what the profile says happens when time runs out: `deemed_approved`, `deemed_denied`, `none`, or `unknown` |
| `state` | `not_started`, `running`, `paused`, `stopped`, `deemed`, `unknown` |

Allowed clock moves: start from not started; pause from running; resume from paused; stop from running or paused; deemed from running only.

## Rules checked

1. Schema valid; `is_approval` is `false`.
2. `seq` runs 1..n; times never go backwards.
3. Clock moves follow the table above; a pause gives a reason (`unknown` is allowed).
4. Only `decision_recorded` carries a `decision_ref`, and only an authority role records it.
5. With no jurisdiction profile, every clock parameter is `unknown` and the clock is never `deemed`. Missing information is `unknown`, not a failure and not a guess.
6. `clock.state` matches the event history (or is `unknown`).

A `deemed` clock state records that the profile's time limit was reached. It is not an ORI approval; any legal effect comes from the jurisdiction's own law and Decision.

## To finish

- Jurisdiction profile field names for clock parameters (issue #140 decision 1).
- Business-day calendars and holidays: profile data, not core.
- Computing `elapsed_days` from events, as a conformance test.
