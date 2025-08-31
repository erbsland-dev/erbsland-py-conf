#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.types import TokenList, TokenGenerator
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Match any combination of spaces and tabs.
RE_SPACING = re.compile(r"[\x20\t]+")

# Pattern to match the typical end-of-line sequence with optional spacing and a comment.
REP_END_OF_LINE = r"""
    (?P<eol_whitespace>    [\x20\t]*    )
    (?P<eol_comment>       \# .*        )? # optional comment
    (?P<eol_line_break>    \r? \n       )? # optional line break (may be the last token)
    """

# Match the end of a line.
RE_END_OF_LINE = re.compile(
    rf"""(?x)
    {REP_END_OF_LINE}
    \Z
    """
)

# Match an empty line.
RE_EMPTY_LINE = re.compile(
    rf"""(?x)
    \A # start of line
    {REP_END_OF_LINE}
    \Z
    """
)

# Match indentation at the beginning of a line.
RE_INDENTATION = re.compile(
    r"""(?x)
    \A
    (?P<indentation>    [\x20\t]+  ) # required indentation
    """
)


def scan_for_end_of_line(cursor: Cursor) -> TokenList | None:
    """Return tokens for the rest of the line, including comments and line breaks."""

    if match := cursor.match(RE_END_OF_LINE):
        return tokens_from_end_of_line(cursor, match)
    return None


def expect_end_of_line(cursor: Cursor, or_syntax_error: str) -> TokenGenerator:
    """Yield end-of-line tokens or raise a syntax error with the given message."""

    if match := cursor.match(RE_END_OF_LINE):
        yield from tokens_from_end_of_line(cursor, match)
    else:
        cursor.syntax_error(or_syntax_error)


def tokens_from_end_of_line(cursor: Cursor, match: re.Match) -> TokenList:
    """Create tokens for whitespace, comments, and line breaks at line end."""

    tokens: list[Token] = []
    if raw_text := match.group("eol_whitespace"):
        tokens.append(cursor.token(TokenType.SPACING, raw_text))
    if raw_text := match.group("eol_comment"):
        tokens.append(cursor.token(TokenType.COMMENT, raw_text))
    if raw_text := match.group("eol_line_break"):
        tokens.append(cursor.token(TokenType.LINE_BREAK, raw_text))
    return tokens


def handle_empty_line(cursor: Cursor, match: re.Match) -> TokenGenerator:
    """Generate tokens for an empty line and advance to the next line."""

    for token in tokens_from_end_of_line(cursor, match):
        yield token
    cursor.next_line()


def scan_for_spacing(cursor: Cursor) -> Token | None:
    """Return a spacing token if spaces or tabs are present."""

    if match := cursor.match(RE_SPACING):
        return cursor.token(TokenType.SPACING, match.group())
    return None


def scan_for_indentation(cursor: Cursor, must_match_exactly=False) -> Token | None:
    """Validate indentation and return an indentation token if found."""

    if match := cursor.match(RE_INDENTATION):
        if not cursor.indentation_pattern:
            cursor.indentation_pattern = match.group()
        else:
            if must_match_exactly:
                if match.group() != cursor.indentation_pattern:
                    cursor.indentation_error("Indentation pattern must match the one in the previous line")
            else:
                if not match.group().startswith(cursor.indentation_pattern):
                    cursor.indentation_error("Indentation pattern must match the one in the previous line")
        # The token only covers the indentation part, not all captured spacing!
        return cursor.token(TokenType.INDENTATION, cursor.indentation_pattern)
    return None
