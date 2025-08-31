#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

"""Tokenization helpers for names and name-path separators."""

import re

import erbsland.conf.impl.lexing.section
from erbsland.conf.error import Error
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name

NAME = re.compile(
    r"""(?xi)
    (?P<name>
        @?              # Accept @ prefix for meta-names
        [a-z]           # Names must start with a letter to prevent early matching of numbers.
        (?:             # Capture letter, underscore, or space groups
            [a-z0-9_]
            |
            \x20(?=[a-z0-9_])   # Prevent capturing a space after the name.
        )*
    |
        " (?: [^\\"\n\r] | \\. )*  # Capture a loosely valid string (checked later)
        (?: " | \Z )   # Also capture unterminated strings for error reporting.
    )
    """
)


def scan_for_name_path_separator(cursor: Cursor) -> Token | None:
    """Scan for a name-path separator token."""

    if match := cursor.match(erbsland.conf.impl.lexing.section.RE_SECTION_NAME_SEPARATOR):
        return cursor.token(TokenType.NAME_PATH_SEPARATOR, match.group())
    return None


def scan_for_name(cursor: Cursor) -> Token | None:
    """
    Scan for a name token.

    Supports meta-names prefixed with ``@`` and quoted names.

    :raises Error: If the name is invalid.
    """

    match = cursor.match(NAME)
    if match is None:
        return None
    try:
        raw_text = match.group()
        if raw_text.startswith('"') and (len(raw_text) == 1 or not raw_text.endswith('"')):
            return cursor.error_token(raw_text, "Text name with missing closing quote")
        name = Name.from_document(raw_text)
        return cursor.token(TokenType.NAME, raw_text, name)
    except Error as error:  # Only capture language errors, let others bubble up.
        raise error.with_source(cursor.create_location()) from error
