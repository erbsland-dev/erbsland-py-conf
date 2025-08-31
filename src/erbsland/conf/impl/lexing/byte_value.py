#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.common_value import REP_VALID_END_OF_VALUE
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.lexing.spacing import (
    expect_end_of_line,
    scan_for_indentation,
    scan_for_end_of_line,
    RE_END_OF_LINE,
)
from erbsland.conf.impl.lexing.text import scan_for_empty_text_line
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Single-line bytes value
# Format: < [format:] [spacing] (hex_byte [spacing])* >
# - format (optional): [a-z][a-z0-9_-]{0,15}
# - hex_byte: two hex digits (case-insensitive)
# - spacing: spaces or tabs between bytes (not within)
RE_SINGLE_LINE_BYTES = re.compile(
    rf"""(?xi)
    <
    (?! << )    # Do not match multi-line bytes
    (?:         # optional format followed by colon
        (?P<format>        [a-z][a-z0-9_-]*    )
        (?: : | \Z )
    )?
    (?P<body>              [^>\r\n]*           )  # body: hex digits with optional spacing (validated later)
    (?P<close_quote>       > | \Z              )
    {REP_VALID_END_OF_VALUE}
    """
)


RE_BYTES_INVALID_BODY = re.compile(r"(?i)[^a-f0-9\t\x20]")


RE_MULTI_LINE_BYTES_OPEN = re.compile(
    r"""(?xi)
    (?P<open_quote>    <<<                     )
    (?P<format>        [a-z][a-z0-9_-]*        )?    
    """
)

RE_MULTI_LINE_CLOSE = re.compile(
    r"""(?x)
    (?P<close_quote>    >>>                     )
    """
)


def scan_for_single_line_bytes(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """
    Return a token for a single-line bytes value if it is valid.

    :param cursor: Cursor positioned at the start of the bytes value.
    :param match: The match from the `RE_SINGLE_LINE_BYTES` regex.
    """

    if not match.group("close_quote"):
        return cursor.error_token(match.group(), "Bytes sequence with missing closing quote")
    format_id = match.group("format")
    if format_id is not None:
        if len(format_id) > 16:
            cursor.limit_exceeded("The format identifier must not exceed 16 characters")
        if format_id.lower() != "hex":  # Valid identifier but unsupported
            cursor.unsupported(f"The byte-data format '{format_id}' is not supported by this parser.")
    body = match.group("body") or ""
    if invalid_match := RE_BYTES_INVALID_BODY.search(body):
        cursor.syntax_error("Unexpected character in bytes value", offset=invalid_match.start() - match.start())
    try:
        data = bytes.fromhex(body)
    except ValueError as error:
        cursor.syntax_error("Invalid hexadecimal byte sequence", system_message=str(error))
    return cursor.token(TokenType.BYTES, match.group(), data)


def scan_for_multi_line_bytes_close(cursor: Cursor) -> Token | None:
    """Scan for the closing quote of a multi-line bytes value."""

    if match := cursor.match(RE_MULTI_LINE_CLOSE):
        return cursor.token(TokenType.MULTI_LINE_BYTES_CLOSE, match.group())
    return None


def handle_multi_line_bytes(cursor: Cursor, match: re.Match[str]) -> TokenGenerator:
    """
    Generate tokens for a multi-line bytes sequence.

    :param cursor: Cursor positioned at the start of the multi-line bytes value.
    :param match: Regex match for `RE_MULTI_LINE_BYTES_OPEN`.
    """

    yield cursor.token(TokenType.MULTI_LINE_BYTES_OPEN, match.group("open_quote"))
    if format_id := match.group("format"):
        # First, check whether the format is the last token on this line.
        format_token = cursor.token(TokenType.MULTI_LINE_BYTES_FORMAT, format_id)
        end_of_line_tokens = scan_for_end_of_line(cursor)
        if end_of_line_tokens is None:
            yield cursor.error_token(
                match.group(), "The format identifier after the opening bytes quote contains unexpected characters."
            )
            return  # pragma: no cover
        if len(format_id) > 16:
            cursor.limit_exceeded("The format identifier must not exceed 16 characters")
        if format_id.lower() != "hex":
            cursor.unsupported(f"The byte-data format '{format_id}' is not supported by this parser.")
        yield format_token
        yield from end_of_line_tokens
    else:
        yield from expect_end_of_line(cursor, "Expected end of line after the opening multi-line bytes quote")
    cursor.expect_next_line("Expected additional lines with multi-line content after the opening quote")
    while True:
        if tokens := scan_for_empty_text_line(cursor):
            yield from tokens
            cursor.expect_next_line("Expected additional lines with multi-line content")
            continue
        if token := scan_for_indentation(cursor):
            yield token
        else:
            cursor.syntax_error("Expected indentation or empty line to continue the multi-line content")
        if token := scan_for_multi_line_bytes_close(cursor):
            yield token
            yield from expect_end_of_line(cursor, "Expected end of line after the closing quote")
            break
        bytes_text = cursor.raw_text_to_eol()
        if m := RE_END_OF_LINE.search(bytes_text):
            content_end = m.start()
            bytes_text = bytes_text[:content_end]
        if bytes_text:
            try:
                data = bytes.fromhex(bytes_text)
            except ValueError as error:
                cursor.syntax_error("Invalid hexadecimal byte sequence", system_message=str(error))
            yield cursor.token(TokenType.MULTI_LINE_BYTES, bytes_text, data)
        yield from scan_for_end_of_line(cursor)
        cursor.expect_next_line("Expected additional lines with multi-line content")
    return
