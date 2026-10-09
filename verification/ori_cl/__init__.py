# SPDX-License-Identifier: Apache-2.0
"""ORI-CL 0.1 (DRAFT): ORI's controlled rule language.

parse (syntax) -> check + compile (compiler) -> evaluate (evaluator).
Spec: spec/ori-cl-0.1-draft.md. Grammar: spec/ori-cl-0.1.ebnf.
Vocabulary: vocab/ori-cl-vocab-0.1.json.
"""

from .compiler import OriClCompileError, compile_document, compile_text
from .syntax import OriClSyntaxError, parse

__all__ = ["parse", "compile_document", "compile_text", "OriClSyntaxError", "OriClCompileError"]
__version__ = "0.1.0"
