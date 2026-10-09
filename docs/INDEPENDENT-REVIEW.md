# Independent release review

Review is a recorded check by someone other than the author, against an exact commit SHA. A separate maintainer or separately operated reviewer session can perform it. An external paid audit is not required. Author self-review and passing CI do not substitute for this receipt.

## Checker receipt

Record the reviewer identity, UTC time, commit SHA, scope, commands and CI links, findings with severity, disposition, and unresolved limitations on the release PR. Any subsequent change invalidates approval for the changed scope until rechecked.

1. Reproduce conformance, reference-node, adapter, rule, verification and site checks from a clean checkout. Explain every skip. Exercise negative controls, especially spoofed actor writes, duplicate IDs, unsupported types and invalid inventories.
2. Review the diff and public tree for secrets, private source locators, copied restricted code or standards text, licensing and attribution. Run the strict six-word safeguard using licensed local copies outside the public repo; publish only hashes, counts and findings. Neither the archive fingerprint nor the public text lint replaces that scan.
3. Verify public behavior: deployed revision, homepage, five routes, linked downloads, discovery and project-path links. The static site does not provide MCP or authenticated writes. Report broken URLs and unsupported feature claims.
4. Record whether blockers remain. Unresolved critical or high findings block final release; lower findings require an explicit disposition and owner. Review approval must name its scope and must not imply government, engineering or legal certification.

## Other final release gates

Independent review is separate from completing full graph-reference acceptance, external model interoperability, and domain/DNS/TLS cutover receipts. See [release readiness](RELEASE-READINESS-2026-10-07.md). These may be deferred only by explicitly narrowing the release claims and recording the disposition; merging code does not close them.
