<!-- Everything in a pull request (title, description, branch name, commits, comments) stays public, even if the PR is closed. Write it as permanent public record. -->

## Summary

<!-- What does this change do, in plain words? One or two sentences. -->

## Area

- [ ] Specification or schema
- [ ] Controlled rule language (ORI-CL) or vocabulary
- [ ] Regulatory graph / reference node
- [ ] Conformance suite (positive and negative fixtures)
- [ ] Verification tools or benchmark examples
- [ ] Licence, attribution or documentation

## Content checks

- [ ] Only ORI's own work: specs, rule logic, tools, tests and synthetic examples. No permit records, plan markup, training data, scores about specific municipalities, or copied local documents.
- [ ] Code and standards are **cited and linked, never reproduced**: section numbers, ORI paraphrase, numeric thresholds and official links only (see `docs/CITATION-POLICY.md`).
- [ ] IFC appears only as an input format (schema references and synthetic fixtures), not as real project models.
- [ ] Every new rule unit has a `paraphrase` and an official `source_url`.
- [ ] Machine output is described as evidence for a reviewer, never as an approval. Missing information gives "unknown", not "fail".
- [ ] No statement of endorsement, partnership or participation by any government, standards body or company.

## Licence and attribution

- [ ] New files follow the licence map in `LICENSE-SPEC.md` (Apache-2.0 code with an SPDX header; CC BY-SA 4.0 prose; CC0 1.0 schemas, vocabulary and fixtures).
- [ ] Third-party material is credited in `NOTICE.md` and `CREDITS.md` with its licence; nothing is included that its licence does not allow.

## Tests

- [ ] `python conformance/validate.py` passes.
- [ ] The test suite passes; new behaviour has positive and negative fixtures.

## Public record

- [ ] Commits are signed off (`git commit -s`, Developer Certificate of Origin).
- [ ] Title, description, branch name and commit messages contain no personal data, credentials, internal paths or private references.
