#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# This is included in various REs to ensure that the end of the value is matched.
REP_VALID_END_OF_VALUE = r"(?=\Z|[,\r\n\t #])"

# Match the value separator for value lists.
RE_VALUE_SEPARATOR = re.compile(r",")

# Match the multi-line value list separator.
RE_MULTI_LINE_LIST_SEPARATOR = re.compile(r"\*")


def scan_for_value_list_separator(cursor: Cursor) -> Token | None:
    """Return a separator token if the cursor is positioned at a value separator."""

    if match := cursor.match(RE_VALUE_SEPARATOR):
        return cursor.token(TokenType.VALUE_LIST_SEPARATOR, match.group())
    return None


def validate_and_cleanup_digit_separators(cursor: Cursor, text: str, raw_text: str) -> str | Token:
    """
    Validate digit separators in a number and remove them.

    Enforces the digit separator rules that there must be no separator at the beginning or end of the number,
    and that there cannot be two consecutive separators.

    :param text: The number string potentially containing digit separators.
    :param raw_text: The original text used in error messages.
    :return: The cleaned number string or an error token if separators are invalid.
    """

    if text.startswith("'"):
        return cursor.error_token(raw_text, "A number cannot start with a digit separator")
    if text.endswith("'"):
        return cursor.error_token(raw_text, "A number cannot end with a digit separator")
    if "''" in text:
        return cursor.error_token(raw_text, "A number cannot contain two consecutive digit separators")
    return text.replace("'", "")
