#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import datetime
import re

from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.impl.lexing.common_value import REP_VALID_END_OF_VALUE
from erbsland.conf.impl.lexing.cursor import Cursor
from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType


# Match a date, time or datetime value.
RE_DATETIME = re.compile(
    r"""(?xi)
    (?=\d{4}-|t?\d{2}:)               # Make sure we are matching a date or time
    (?P<date>                         # Match an optional date, e.g. "2025-01-01"
        \d{4} - \d{2} - \d{2}
    )?
    (?:                               # Make the time part optional.
        (?(date)[t\x20]|t?)           # If a date is matched, require a separator ("t" or space)
        (?P<time>
            \d{2} : \d{2}             # Match a time, e.g. "12:34:56" or "07:59"
            (?: : \d{2} )?            # Seconds are optional.
        )
        (?P<second_fraction>
            \.                        # A decimal point introduces a fractional part.
            \d+                       # Do not limit the fractional digits (check later).
        )?
        (?P<timezone>                 # Match an optional timezone, e.g. "-02", "+01:00" or "z" for UTC
            z
            |
            [+-]
            (?P<tz_hour>   \d{2} )
            (?P<tz_minute> : \d{2} )?
        )?
    )?
    """
    + REP_VALID_END_OF_VALUE
)


# Matching all incomplete date, time or datetime values that look like real cut-off values.
RE_INCOMPLETE_DATETIME = re.compile(
    r"""(?xi)
    \d{4}- (?:\d\d? (?:-\d? (?:\d[\x20t]\d? (?:\d:\d? (?:\d:\d? (?:\d[+-] (?:\d (?:\d:\d?)?)?)?)?)?)?)?)?\Z
    |
    \d{2}: (?:\d (?:\d:\d? (?:\d[+-] (?:\d (?:\d:\d?)?)?)?)?)?\Z
    """
)


def report_incomplete_datetime(cursor: Cursor, match: re.Match) -> Token | None:
    """
    Return an error token indicating that the datetime is incomplete.

    :param cursor: Cursor positioned at the start of the incomplete datetime value.
    :param match: Match object produced by :data:`RE_INCOMPLETE_DATETIME`.
    """

    return cursor.error_token(match.group(), "The date, time or datetime seems to be incomplete")


def scan_for_datetime(cursor: Cursor, match: re.Match[str]) -> Token | None:
    """
    Return a token for the matched date, time, or datetime value.

    :param cursor: Cursor positioned at the start of the value.
    :param match: Match object produced by :data:`RE_DATETIME`.
    """

    date_text = match.group("date") or ""
    second_fraction = match.group("second_fraction") or ""
    time_text = match.group("time") or ""
    if len(time_text) == 5:  # Only hour:minute
        time_text += ":00"
        if second_fraction:
            cursor.syntax_error("The seconds fraction can only be specified if seconds are given.")
    timezone_text = (match.group("timezone") or "").upper()
    if len(timezone_text) == 3:  # Append minute offset if missing
        timezone_text += ":00"
    if second_fraction and len(second_fraction) > 10:  # '.' + 9 digits = 10
        cursor.syntax_error("The second fraction must not contain more than 9 digits")

    # Validate timezone offset ranges if present (except 'Z')
    if timezone_text and timezone_text != "Z":
        if match.group("tz_hour") is not None:
            hh = int(match.group("tz_hour"))
            if not (0 <= hh <= 23):
                cursor.syntax_error("The timezone hour offset must be between 00 and 23")
        if match.group("tz_minute") is not None:
            mm = int(match.group("tz_minute")[1:])
            if not (0 <= mm <= 59):
                cursor.syntax_error("The timezone minute offset must be between 00 and 59")

    # Date-only
    if date_text and not time_text:
        try:
            return cursor.token(TokenType.DATE, match.group(), datetime.date.fromisoformat(date_text))
        except ValueError as error:
            cursor.syntax_error("The date is not valid", system_message=str(error))

    # Time-only
    if not date_text:
        try:
            value = Time.fromisoformat(f"{time_text}{second_fraction}{timezone_text}")
            return cursor.token(TokenType.TIME, match.group(), value)
        except ValueError as error:
            cursor.syntax_error("The time is not valid", system_message=str(error))

    # Date and time combined
    try:
        value = DateTime.fromisoformat(f"{date_text}T{time_text}{second_fraction}{timezone_text}")
        return cursor.token(TokenType.DATE_TIME, match.group(), value)
    except ValueError as error:
        cursor.syntax_error("The datetime is not valid", system_message=str(error))
