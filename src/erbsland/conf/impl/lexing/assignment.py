#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import re

from erbsland.conf.error import Error
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.spacing import scan_for_spacing, scan_for_end_of_line, scan_for_indentation
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.lexing.value import handle_values
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name, META_NAME_SIGNATURE

# Match an assignment that starts with whitespace to provide a clearer error message.
RE_NAME_ASSIGMENT_ERROR_INDENTATION = re.compile(
    r"""(?xi)
    ^ [\x20\t]+ # Error: Name must start at the beginning of the line
    (?: @? [a-z][a-z0-9_\x20]*? | " (?: [^\\"] | \\. )* " ) [\x20\t]* [=:]
    """
)


# Regular expression for matching a name followed by an assignment operator.
RE_NAME_ASSIGNMENT = re.compile(
    r"""(?xi)
    ^ # start of line
    (?P<name>
        @? [a-z][a-z0-9_\x20]*? # Anything that could be a regular name (checked later)
    |
        " (?: [^\\"\n\r] | \\. )* (?: " | \Z )  # Capture a vaguely valid string (checked later)
    )
    (?P<spacing> [\x20\t]* ) # greedy whitespace
    (?P<separator> [=:] | \Z ) # assignment operator ($ to catch unexpected ends)
    """
)


def handle_name_assigment_error_indentation(cursor: Cursor, match) -> None:
    """Report a syntax error when a name assignment is indented."""

    cursor.syntax_error("Name assignments must start at the beginning of the line")


def handle_tokens_from_assignment(cursor: Cursor, match: re.Match) -> TokenGenerator:
    """
    Generate tokens for a matched name assignment.

    The function yields tokens for the name, optional spacing, the assignment
    separator, and the value.  It also handles multi-line values where the value
    is placed on the following line and indented.

    :param cursor: Cursor positioned at the start of the assignment.
    :param match: The match from `RE_NAME_ASSIGNMENT`.
    """

    cursor.indentation_pattern = ""  # Reset the indentation pattern for each assignment.
    try:
        raw_text = match.group("name")
        if raw_text.startswith('"') and (len(raw_text) == 1 or not raw_text.endswith('"')):
            yield cursor.error_token(raw_text, "Text name with missing closing quote")
            return  # pragma: no cover
        name = Name.from_document(raw_text)
        if name.is_meta() and name == META_NAME_SIGNATURE:
            if cursor.position.line != 1:
                cursor.syntax_error("Signature must be defined in the first line of the document.")
            if not cursor.syntax_mode:  # Ignore in syntax mode
                if not cursor.digest_enabled:
                    cursor.unsupported("Signature validation is not configured.")
                cursor.start_digest_calculation()
        yield cursor.token(TokenType.NAME, raw_text, name)
    except Error as error:
        raise error.with_source(cursor.create_location()) from error
    if raw_text := match.group("spacing"):
        yield cursor.token(TokenType.SPACING, raw_text)
    raw_text = match.group("separator")
    if not raw_text:
        cursor.unexpected_end("Unexpected end after value name.")
    yield cursor.token(TokenType.NAME_VALUE_SEPARATOR, raw_text)
    is_value_on_next_line = False
    if tokens := scan_for_end_of_line(cursor):
        yield from tokens
        is_value_on_next_line = True
        # if we get the end of the line, the value must be on the next line.
        cursor.next_line()
        if not cursor.has_more_content():
            cursor.unexpected_end("Expected a value after the name and separator")
        if token := scan_for_indentation(cursor):
            yield token
        else:
            cursor.syntax_error("Expected indentation with the value after the name and separator in the previous line")
    else:
        if token := scan_for_spacing(cursor):
            yield token
    yield from handle_values(cursor, is_value_on_next_line)
