#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import re

from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.name import scan_for_name_path_separator, scan_for_name
from erbsland.conf.impl.lexing.spacing import scan_for_spacing, scan_for_end_of_line
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.limits import MAX_NAME_PATH_LENGTH
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name


# Match a name path separator.
RE_SECTION_NAME_SEPARATOR = re.compile(r"\.")

# Match a section start marker.
RE_SECTION_START = re.compile(
    r"""(?x)
    ^ # start of line
    (?P<section_marker>
        -* # optional decoration
        \*? # list section marking
        \[ # section start
    )
    """
)

# Test for a common error to improve the error message.
RE_SECTION_ERROR_INDENTATION = re.compile(
    r"""(?x)
    ^ [\x20\t]+ # Error: Section must not be indented
    -* \*? \[
    """
)

# Match a section end marker.
RE_SECTION_END = re.compile(
    r"""(?x)
    (?P<in_section_spacing> [\x20\t]* ) # spacing
    (?P<section_marker> \] \*? -* ) # section end marking
    """
)


def handle_tokens_from_section(cursor: Cursor, match: re.Match) -> TokenGenerator:
    """
    Yield tokens for a section header until the end of the line.

    :param cursor: Cursor positioned at the start of the section.
    :param match: Match object produced by :data:`RE_SECTION_START`.
    """

    is_list_section = False
    begin_marker = match.group("section_marker")
    if "*" in begin_marker:
        is_list_section = True
        yield cursor.token(TokenType.SECTION_LIST_OPEN, begin_marker)
    else:
        yield cursor.token(TokenType.SECTION_MAP_OPEN, begin_marker)
    last_token_type = TokenType.END_OF_DATA
    token: Token  # for type checking
    tokens: list[Token]  # for type checking
    name_count = 0
    while True:
        if token := scan_for_spacing(cursor):
            yield token
        if tokens := scan_for_section_end(cursor, is_list_section):
            break
        if token := scan_for_name_path_separator(cursor):
            if last_token_type == TokenType.NAME_PATH_SEPARATOR:
                cursor.syntax_error("A name path separator must not be followed by another name path separator")
            last_token_type = token.type
            yield token
            continue
        if token := scan_for_name(cursor):
            if token.type == TokenType.ERROR:
                yield token
                return  # pragma: no cover
            assert isinstance(token.value, Name)
            if last_token_type == TokenType.NAME:
                cursor.syntax_error("A name must not be followed by another name")
            name_count += 1
            if name_count > MAX_NAME_PATH_LENGTH:
                cursor.limit_exceeded(f"A section must not contain more than {MAX_NAME_PATH_LENGTH} names")
            name = token.value
            if name.is_meta():
                cursor.syntax_error("A meta-name cannot be used in a section")
            if name.is_text() and name_count == 1 and last_token_type != TokenType.NAME_PATH_SEPARATOR:
                cursor.syntax_error("Text names are not allowed at the document root")
            last_token_type = token.type
            yield token
            continue
        cursor.syntax_error(
            "Unexpected characters in section. Expected a name, path separator, or end of section marker"
        )
    if name_count == 0:
        cursor.syntax_error("A section must contain at least one name")
    if last_token_type == TokenType.NAME_PATH_SEPARATOR:
        cursor.syntax_error("A section must not end with a name path separator")
    yield from tokens
    tokens = scan_for_end_of_line(cursor)
    if tokens is None:
        cursor.syntax_error("Unexpected content after the section, expected end of line")
    yield from tokens
    cursor.next_line()
    return


def scan_for_section_end(cursor: Cursor, is_list_section: bool) -> list[Token] | None:
    """
    Return tokens for a section end marker if present.

    :param cursor: Cursor positioned at the start of the section end marker.
    :param is_list_section: True if the current section is a list section.
    """

    match = cursor.match(RE_SECTION_END)
    if match is None:
        return None
    result = []
    if spacing := match.group("in_section_spacing"):
        result.append(cursor.token(TokenType.SPACING, spacing))  # pragma: no cover
    end_marker = match.group("section_marker")
    if is_list_section:
        result.append(cursor.token(TokenType.SECTION_LIST_CLOSE, end_marker))
    else:
        if "*" in end_marker:
            cursor.syntax_error("Regular section end marker must not contain a '*' character")
        result.append(cursor.token(TokenType.SECTION_MAP_CLOSE, end_marker))
    return result


def handle_section_error_indentation(cursor: Cursor, match: re.Match) -> None:
    """
    Report an error when a section starts with indentation.

    :param cursor: Cursor positioned at the start of the section.
    :param match: Match object produced by :data:`RE_SECTION_ERROR_INDENTATION`.
    """

    cursor.syntax_error("Sections must start at the beginning of the line")
