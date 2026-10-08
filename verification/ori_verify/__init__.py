# SPDX-License-Identifier: Apache-2.0
"""ORI reference evaluator for deterministic rule units (DRAFT 0.1).

Every result this package emits is reviewer evidence, not approval. A pass
does not approve anything; only the building official's decision under the
adopted code is lawful approval. Missing, unreadable or unconfirmed
information always yields ``unknown`` (core outcome ``indeterminate``), never
``fail``.
"""

__version__ = "0.1.0"

EVIDENCE_LABEL = "Reviewer evidence, not approval"
LEGAL_BOUNDARY = (
    "Machine verification output is reviewer evidence. It is not a permit decision, "
    "not approval, and not a statement of the law. The adopted code (here the 2021 "
    "Virginia Residential Code under the USBC) and the building official govern."
)
