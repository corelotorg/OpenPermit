# ORI v0.1 release preparation — 2026-10-07

State: **review candidate; no final release or site deployment claimed**.

Owner: CORELOT release lane. Authorization: Jeremiah Horstick requested release preparation, repository update, and public-site routes on 2026-10-07. Canonical target is `corelotorg/OpenPermit`, base `test` at `0778ecfd1f23ce23ee3e940effbaea8b75b3217c`. Existing concerns: [canonicalization #116](https://github.com/corelotorg/OpenPermit/issues/116), [interoperability #115](https://github.com/corelotorg/OpenPermit/issues/115), and the earlier ORI review [#112](https://github.com/corelotorg/OpenPermit/issues/112).

## Source and reconciliation

The October 3 candidate archive is commit `462e51f648c5b60b33f83ef4391358f9e77939ad`: 322 files, source fingerprint `85171b947e71afae0b383de43b579ac303c18f89e02b9efe0a4fef56388d7b8c`. That fingerprint was reproduced from the archive before adaptation. The archive originally targeted the personal fork. This candidate continues in the established organization repository, preserving its commit history, Dependabot and hardened pipeline. Superseded recovery/source-index files and the real-jurisdiction worked profile are omitted from this release tree, but remain in repository history. The public benchmark uses the candidate's synthetic jurisdiction.

OpenPermit Model Verification names our assembly/evidence work. CraftBot appears only as attributed upstream research. Its root MIT license was read; no upstream code or reference manuals are included here. OpenCascade integration, STEP round-trip acceptance, and production reference-wall acceptance are future gates, not completed features of this release.

## Prepared changes

- Public repository links, machine discovery, contribution routes and clone instructions point to `corelotorg/OpenPermit` / `test`.
- Public site has reproducible `/docs/`, `/spec/`, `/benchmark/`, `/contribute/`, `/model-verification/` routes, suitable for root-domain or project-Pages hosting.
- Site CI builds, checks and uploads the artifact; it does not deploy or alter DNS.
- Reference-node inventory validation selects the inventory schema. Unknown types are rejected; duplicate IDs fail with source paths.
- Public reference mode cannot create or dispose of challenges, regardless of supplied actor strings. Authenticated writes are not implemented. The Python entrypoint defaults to loopback.
- Existing organization CI is retained; expanded conformance runs on `test`, release branches and pull requests.

## Local verification

Fresh environment from the release requirements on Python 3.12:

- `pytest reference-node adapters/blds rules verification/tests`: **237 passed, 3 skipped**.
- `conformance/validate.py`: passes schemas, fixtures and the public code-text lint.
- MCP in-process smoke: passes, including denied writes and no state-log creation.
- Site positive/negative tests: 2 passed; missing route, stale repository CTA and project-path regression are detected.
- Site build and complete local HTML target/fragment check: passes.

The three skipped tests need material outside this public tree: licensed local code copies for the strict six-word scan, the language-statistics study, and the private reviewer-pack generator. Earlier receipts do not substitute for rerunning the strict scan on this changed release tree.

## Before final release or cutover

1. Independent checker reviews this candidate and current CI receipts. Preserve maker/checker separation.
2. Rerun the strict six-word safeguard with licensed local code copies; record counts and hashes without publishing the text. Recheck the release secret scan and the changed licensing/attribution map.
3. Close the remaining reference-node graph integrity scope: declared-reference policy, dangling-pointer reporting and full graph/schema acceptance. Read-only default does not complete the earlier authenticated-write or concurrent durable-disposition acceptance.
4. Verify external model interoperability under #115; do not promote synthetic test results into engineering/code applicability or certification.
5. Establish Pages/domain source, DNS ownership, TLS, path preservation and deployed-revision receipts for `openpermit.io` and `openpermit.dev`. No domain cutover is claimed by this repository update.
6. Keep fork-network detachment/canonicalization scope on #116; this change does not detach the fork.

Disposition: **reviewable repository release preparation**. Final release readiness remains OPEN until the listed receipts exist. Next step: checker and CI review of the release PR, then complete the release-only receipts before promotion.

## Comparison scan follow-up — 2026-10-09

The mechanical comparison input gap was addressed using complete 2021 IRC and official Virginia 2021 amendment documents, extracted outside this repository: 1,109 and 195 pages respectively. This is base-plus-amendment comparison coverage, not a certified consolidated VRC or an open-content license grant. Publisher-authorized/license provenance remains unverified. The source texts remain outside the public tree.

The unchanged strict six-word scan initially found nine matches. Four were in original paraphrases or test material; those were rephrased. Five were in rights evidence: unrelated FEMA design guidance, historical commentary and statutory transfer provisions. Rights excerpts now retain only the relevant verbatim scope with their official source links; associated recorded hashes were refreshed. No scan exclusions or threshold changes were introduced.

Comparison text SHA-256 values:

- irc2021.txt: `eca4f685fe5a424f3ae050d92ea93126108d1ac1c61a7d08d98e068a8694cf7f` (682726 words).
- vcc2021-amendments.txt: `ff469d4bad9ca78295b4977fea434506d6901f55bbf6e90e816153b80ca2fa11` (76991 words).

Final verification receipts for this correction belong on the release PR. The independent checker must recheck the changed scope; graph and interoperability acceptance remain separate.
