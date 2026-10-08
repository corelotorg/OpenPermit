# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability reporting for this
repository (**Security → Report a vulnerability**). Do not open a public issue for a vulnerability.
If private reporting is not enabled, open a public issue that asks for a private contact and contains
no details of the vulnerability.

Include the affected file or component, the version or commit, steps to reproduce, and the impact you
expect. Maintainers acknowledge reports as soon as they can, agree a disclosure date with the
reporter, and credit the reporter unless asked not to.

## Scope

In scope: the reference node (`reference-node/`), the verification, ORI-CL and takeoff tools
(`verification/`), the conformance validator (`conformance/`), the BLDS adapter (`adapters/`), the
CI workflow and the static site files.

Also report, privately and in the same way:

- any secured material found in the repository or its history: permit data, donor red-line markup,
  training data, municipal permit data or per-municipality HUD rubric scores
  ([`docs/GOVERNANCE-BOUNDARY.md`](docs/GOVERNANCE-BOUNDARY.md));
- any reproduced building-code text that the automated check missed;
- any credential, token or personal data committed by mistake.

## Supported versions

ORI is pre-1.0. Only the current `main` branch receives fixes.

## Design notes

- The reference node needs no account. It binds to `0.0.0.0` (set `ORI_BIND_HOST` to change this) and
  accepts only localhost Host and Origin headers unless a public host is configured.
- Outside validators and compute providers are not trusted by default; registration is discovery,
  not trust.
- Machine output is evidence for a human reviewer, never approval.

Licence: CC BY-SA 4.0.
