#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.impl.lexing.common_value import REP_VALID_END_OF_VALUE, validate_and_cleanup_digit_separators
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Match an explicit ``inf`` or ``nan`` literal.
RE_FLOAT_LITERAL = re.compile(
    rf"""(?xi)
    [+-]?
    (?: inf | nan )
    {REP_VALID_END_OF_VALUE}
    """
)

# Match anything that looks like a floating-point number.
RE_FLOAT = re.compile(
    rf"""(?xi)
    (?P<sign>           [-+]                       )?
    (?:
        (?P<whole>      [0-9']+                    )?
        (?P<decimal>    \.                         )
        (?P<fraction>   (?(whole)[0-9']*|[0-9']+)  )
        (?P<exponent>   e[-+]?[0-9]+               )?
    |
        (?P<whole2>     [0-9']+                    )
        (?P<exponent2>  e[-+]?[0-9]+               )
    )
    {REP_VALID_END_OF_VALUE}
    """
)

# Detect cases where a floating-point number appears to be unintentionally truncated.
RE_INCOMPLETE_FLOAT = re.compile(
    r"""(?xi)
    [+-]?
    (?:
        [0-9']+e[-+]?
        |
        [0-9']+\.
        |
        [0-9']+\.[0-9']*e[-+]?
        |
        [0-9']*\.[0-9']+e[-+]?
    )
    \Z
    """
)


def report_incomplete_float(cursor: Cursor, match: re.Match) -> Token | None:
    """
    Return an error token for an incomplete floating-point number.

    :param cursor: Cursor positioned at the start of the incomplete float value.
    :param match: Match object produced by :data:`RE_INCOMPLETE_FLOAT`.
    """

    return cursor.error_token(match.group(), "A floating-point number seems to be incomplete")


def scan_for_float_literal(cursor: Cursor, match: re.Match) -> Token | None:
    """
    Create a token from an explicit ``inf`` or ``nan`` literal.

    :param cursor: Cursor positioned at the start of the literal.
    :param match: Match object produced by :data:`RE_FLOAT_LITERAL`.
    """

    return cursor.token(TokenType.FLOAT, match.group(), float(match.group()))


def scan_for_float(cursor: Cursor, match: re.Match) -> Token | None:
    """
    Validate and convert a floating-point number to a token.

    :param cursor: Cursor positioned at the start of the float value.
    :param match: Match object produced by :data:`RE_FLOAT`.
    """

    sign = match.group("sign") or ""
    whole_group = match.group("whole") or match.group("whole2") or ""
    whole = validate_and_cleanup_digit_separators(cursor, whole_group, match.group())
    if isinstance(whole, Token):
        return whole
    if len(whole) > 1 and whole.startswith("0"):
        cursor.syntax_error("A floating-point number must not be zero-padded")
    decimal = match.group("decimal") or ""
    fraction_group = match.group("fraction") or ""
    fraction = validate_and_cleanup_digit_separators(cursor, fraction_group, match.group())
    if isinstance(fraction, Token):
        return fraction
    if len(whole) + len(fraction) > 20:
        cursor.limit_exceeded("A floating-point number must not have more than 20 digits")
    exponent = match.group("exponent") or match.group("exponent2") or ""
    if exponent:
        exponent_digits = exponent[2:] if exponent[1] in "+-" else exponent[1:]
        if len(exponent_digits) > 6:
            cursor.limit_exceeded("A floating-point exponent must not have more than 6 digits")
    cleaned_up_text = f"{sign}{whole}{decimal}{fraction}{exponent}"
    try:
        value = float(cleaned_up_text)
        # If the value overflowed to infinity due to exponent, treat as limit exceeded (but not for explicit INF literal)
        if exponent and (value == float("inf") or value == -float("inf")):
            cursor.limit_exceeded("The floating-point value exceeds the maximum size")
        return cursor.token(TokenType.FLOAT, match.group(), value)
    except ValueError as error:
        raise cursor.syntax_error(f"The floating-point value is not valid", system_message=str(error))
