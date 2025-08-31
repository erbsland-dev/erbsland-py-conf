#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.common_value import validate_and_cleanup_digit_separators, REP_VALID_END_OF_VALUE
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.time_delta import TIME_DELTA_UNIT_MAP, TimeDelta


# Roughly matches any integer or time-delta value.
RE_INTEGER = re.compile(
    rf"""(?xi)
    (?P<sign>     [-+]                             )?
    (?P<base>     0[xb]                            )?
    (?P<digits>   (?(base)[0-9a-fA-F']+|[0-9']+)   )
    (?:
        \x20?
        (?P<byte_unit>
            kb | mb | gb | tb | pb | eb | zb | yb |
            kib | mib | gib | tib | pib | eib | zib | yib
        )
    |
        \x20?
        (?P<time_unit>
            nanoseconds | nanosecond | ns |
            microseconds | microsecond | µs | us |
            milliseconds | millisecond | ms |
            seconds | second | s |
            minutes | minute | m |
            hours | hour | h |
            days | day | d |
            weeks | week | w |
            months | month |
            years | year
        )
    )?
    {REP_VALID_END_OF_VALUE}
    """
)

# An integer base at the end of a line is unexpected.
RE_INCOMPLETE_INTEGER = re.compile(r"(?xi)[-+]?0[xb]\Z")


# All supported suffixes and their factors. -1 = limit exceeded
BYTE_FACTORS = {
    "kb": 1000,
    "mb": 1000000,
    "gb": 1000000000,
    "tb": 1000000000000,
    "pb": 1000000000000000,
    "eb": 1000000000000000000,
    "zb": -1,
    "yb": -1,
    "kib": 1024,
    "mib": 1048576,
    "gib": 1073741824,
    "tib": 1099511627776,
    "pib": 1125899906842624,
    "eib": 1152921504606846976,
    "zib": -1,
    "yib": -1,
}

# The minimum and maximum integer values for 64-bit checks.
MIN_INT64 = -(1 << 63)
MAX_INT64 = (1 << 63) - 1


def report_incomplete_integer(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """
    Return an error token for an integer base with no digits.

    :param cursor: Cursor positioned at the start of the incomplete integer value.
    :param match: Match object produced by :data:`RE_INCOMPLETE_INTEGER`.
    """

    return cursor.error_token(match.group(), "Unexpected integer base with no digits")


def scan_for_integer_or_time_delta(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """
    Convert a matched integer or time-delta value to a token.

    Supports decimal, binary, and hexadecimal numbers with optional byte or time units.

    :param cursor: Cursor positioned at the start of the value.
    :param match: Match object produced by :data:`RE_INTEGER`.
    """

    base = 10
    max_digits = 19
    if match.group("base") in ["0x", "0X"]:
        base = 16
        max_digits = 16
    elif match.group("base") in ["0b", "0B"]:
        base = 2
        max_digits = 64
    digits_text = validate_and_cleanup_digit_separators(cursor, match.group("digits"), match.group())
    if isinstance(digits_text, Token):
        return digits_text
    if len(digits_text) > max_digits:
        cursor.limit_exceeded(f"The integer exceeds the maximum number of digits ({max_digits})")
    if base == 10 and len(digits_text) > 1 and digits_text.startswith("0"):
        cursor.syntax_error("A decimal number cannot start with a zero")
    try:
        value = int(digits_text, base)
    except ValueError as error:
        cursor.syntax_error(f"The integer is not valid", system_message=str(error))
    if match.group("sign") == "-":
        value = -value
    if byte_unit := match.group("byte_unit"):
        factor = BYTE_FACTORS[byte_unit.lower()]
        if factor == -1:
            cursor.limit_exceeded("The integer exceeds the maximum size")
        value *= factor
    if not (MIN_INT64 <= value <= MAX_INT64):
        cursor.limit_exceeded("The integer exceeds the maximum size")
    if time_unit := match.group("time_unit"):
        if base != 10:
            cursor.syntax_error("Time-deltas must use decimal numbers.")
        unit = TIME_DELTA_UNIT_MAP[time_unit.lower()]
        time_delta = TimeDelta(value, unit)
        return cursor.token(TokenType.TIME_DELTA, match.group(), time_delta)
    return cursor.token(TokenType.INTEGER, match.group(), value)
