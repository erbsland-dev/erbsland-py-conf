#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import erbsland.conf.impl.lexing.bool_value as bool_value
import erbsland.conf.impl.lexing.byte_value as byte_value
import erbsland.conf.impl.lexing.common_value as common_value
from erbsland.conf.impl.lexing.cursor import Cursor
import erbsland.conf.impl.lexing.datetime_value as datetime_value
import erbsland.conf.impl.lexing.float_value as float_value
import erbsland.conf.impl.lexing.integer_value as integer_value
from erbsland.conf.impl.lexing.rule import ScanRule, GeneratorRule
import erbsland.conf.impl.lexing.spacing as spacing
import erbsland.conf.impl.lexing.text as text
from erbsland.conf.impl.lexing.types import TokenGenerator
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Scanning rules for values that fit on a single line.
SINGLE_LINE_VALUE_RULES: list[ScanRule] = [
    ScanRule(float_value.RE_FLOAT_LITERAL, float_value.scan_for_float_literal),
    ScanRule(bool_value.RE_BOOL_LITERAL, bool_value.scan_for_bool),
    ScanRule(datetime_value.RE_INCOMPLETE_DATETIME, datetime_value.report_incomplete_datetime),
    ScanRule(datetime_value.RE_DATETIME, datetime_value.scan_for_datetime),
    ScanRule(float_value.RE_INCOMPLETE_FLOAT, float_value.report_incomplete_float),
    ScanRule(float_value.RE_FLOAT, float_value.scan_for_float),
    ScanRule(integer_value.RE_INCOMPLETE_INTEGER, integer_value.report_incomplete_integer),
    ScanRule(integer_value.RE_INTEGER, integer_value.scan_for_integer_or_time_delta),
    ScanRule(text.RE_SINGLE_LINE_TEXT, text.scan_for_text),
    ScanRule(text.RE_SINGLE_LINE_CODE, text.scan_for_code),
    ScanRule(text.RE_SINGLE_LINE_REGEX, text.scan_for_regex),
    ScanRule(byte_value.RE_SINGLE_LINE_BYTES, byte_value.scan_for_single_line_bytes),
]

# Scanning rules for multi-line values (the opening quotes of multi-line values).
MULTI_LINE_VALUE_RULES: list[GeneratorRule] = [
    GeneratorRule(text.RE_MULTI_LINE_TEXT_OPEN, text.handle_multi_line_text),
    GeneratorRule(text.RE_MULTI_LINE_CODE_OPEN, text.handle_multi_line_code),
    GeneratorRule(text.RE_MULTI_LINE_REGEX_OPEN, text.handle_multi_line_regex),
    GeneratorRule(byte_value.RE_MULTI_LINE_BYTES_OPEN, byte_value.handle_multi_line_bytes),
]


def expect_single_line_value(cursor: Cursor) -> Token:
    """Return a single-line value token or raise a syntax error."""

    token = scan_for_single_line_value(cursor)
    if token is None:
        cursor.syntax_error("Expected a value after the separator")
    return token


def expect_value_list_separator(cursor: Cursor) -> TokenGenerator:
    """Yield tokens for spacing and a value separator, raising on failure."""

    if token := spacing.scan_for_spacing(cursor):
        yield token
    token = common_value.scan_for_value_list_separator(cursor)
    if token is None:
        cursor.syntax_error("Expected a value separator or the end of this line")
    yield token
    if token := spacing.scan_for_spacing(cursor):
        yield token


def scan_for_multi_line_value_list_separator(cursor: Cursor) -> Token | None:
    """Scan for the multi-line value list separator ``*``."""

    if match := cursor.match(common_value.RE_MULTI_LINE_LIST_SEPARATOR):
        return cursor.token(TokenType.MULTI_LINE_VALUE_LIST_SEPARATOR, match.group())
    return None


def handle_multi_line_list(cursor: Cursor) -> TokenGenerator:
    """Yield tokens for a multi-line list of values."""

    while True:
        if token := scan_for_multi_line_value_list_separator(cursor):
            yield token
        else:
            cursor.syntax_error("Expected a value separator '*' after the indentation to continue the list")
        if token := spacing.scan_for_spacing(cursor):
            yield token
        if token := scan_for_single_line_value(cursor):
            yield token
            # There may be more values.
            while True:
                # Stop at the end of the line.
                if (tokens := spacing.scan_for_end_of_line(cursor)) is not None:
                    yield from tokens
                    break
                yield from expect_value_list_separator(cursor)
                yield expect_single_line_value(cursor)
        else:
            cursor.syntax_error("Expected a value after the multi-line list separator")
        cursor.next_line()
        if not cursor.has_more_content():
            break  # If there is no more content, we are done.
        if tokens := spacing.scan_for_end_of_line(cursor):  # If we encounter an empty line, we are done.
            yield from tokens
            cursor.next_line()
            break
        if token := spacing.scan_for_indentation(cursor, must_match_exactly=True):
            yield token
        else:
            break  # If the line does not start with indentation, we are done.
    return


def handle_values(cursor: Cursor, is_value_on_next_line: bool) -> TokenGenerator:
    """Yield tokens for single- or multi-line value constructs."""

    token: Token  # For type checks
    tokens: list[Token]  # For type checks
    if is_value_on_next_line and cursor.match(common_value.RE_MULTI_LINE_LIST_SEPARATOR):
        yield from handle_multi_line_list(cursor)
        return
    if token := scan_for_single_line_value(cursor):
        yield token
        # If we got a single-line value, we could get a list of values.
        while True:
            # Stop at the end of the line.
            if (tokens := spacing.scan_for_end_of_line(cursor)) is not None:
                break
            yield from expect_value_list_separator(cursor)
            yield expect_single_line_value(cursor)
        yield from tokens  # End of the line.
        cursor.next_line()
        return
    # No single-line value matched; try multi-line constructs.
    for rule in MULTI_LINE_VALUE_RULES:
        if match := cursor.match(rule.pattern):
            yield from rule.handler(cursor, match)
            cursor.next_line()
            return
    # Neither single-line nor multi-line value matched.
    cursor.syntax_error("Expected a valid value but got something else")


def scan_for_single_line_value(cursor: Cursor) -> Token | None:
    """Scan for a value that fits on a single line."""

    for rule in SINGLE_LINE_VALUE_RULES:
        if match := cursor.match(rule.pattern):
            if token := rule.scanner(cursor, match):
                return token
    return None
