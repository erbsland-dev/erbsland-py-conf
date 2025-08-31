#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.common_value import REP_VALID_END_OF_VALUE
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Match any supported boolean literal followed by a valid terminator.
RE_BOOL_LITERAL = re.compile(
    r"""(?xi)
    true | false |
    on | off |
    yes | no |
    enabled | disabled
    """
    + REP_VALID_END_OF_VALUE
)


def scan_for_bool(cursor: Cursor, match: re.Match) -> Token | None:
    """
    Return a boolean token for the matched literal.

    :param cursor: Cursor positioned at the start of the literal.
    :param match: Match object produced by :data:`RE_BOOL_LITERAL`.
    """

    value = match.group().lower() in ("true", "on", "yes", "enabled")
    return cursor.token(TokenType.BOOLEAN, match.group(), value)
