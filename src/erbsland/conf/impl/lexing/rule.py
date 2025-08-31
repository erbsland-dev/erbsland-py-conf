#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.token import Token


# A handler function that takes a cursor and a match and returns a token generator.
HandlerGenerator = Callable[[Cursor, re.Match], TokenGenerator]

# A handler function that takes a cursor and a match and raises an error.
HandlerError = Callable[[Cursor, re.Match], None]

# A scanner function that takes a cursor and a match and returns a token or None.
Scanner = Callable[[Cursor, re.Match], Optional[Token]]


@dataclass(frozen=True, slots=True)
class GeneratorRule:
    """Rule that yields tokens based on a regular-expression pattern."""

    pattern: re.Pattern
    handler: HandlerGenerator | HandlerError | None


@dataclass(frozen=True, slots=True)
class ScanRule:
    """Rule that creates a single token from a regular-expression match."""

    pattern: re.Pattern
    scanner: Scanner
