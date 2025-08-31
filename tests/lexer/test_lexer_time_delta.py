#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.time_delta import TimeDelta, TimeUnit
from lexer.lexer_helper import LexerHelper


class TestLexerTimeDelta(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Seconds with and without sign
            ("0s", TimeDelta(0, TimeUnit.SECOND)),
            ("1s", TimeDelta(1, TimeUnit.SECOND)),
            ("+1s", TimeDelta(1, TimeUnit.SECOND)),
            ("-1s", TimeDelta(-1, TimeUnit.SECOND)),
            ("23'932s", TimeDelta(23932, TimeUnit.SECOND)),
            ("+23'932s", TimeDelta(23932, TimeUnit.SECOND)),
            ("-529'000s", TimeDelta(-529000, TimeUnit.SECOND)),
            # Optional single space before unit
            ("0 s", TimeDelta(0, TimeUnit.SECOND)),
            ("1 s", TimeDelta(1, TimeUnit.SECOND)),
            ("+1 s", TimeDelta(1, TimeUnit.SECOND)),
            ("-1 s", TimeDelta(-1, TimeUnit.SECOND)),
            ("23'932 s", TimeDelta(23932, TimeUnit.SECOND)),
            ("+23'932 s", TimeDelta(23932, TimeUnit.SECOND)),
            ("-529'000 s", TimeDelta(-529000, TimeUnit.SECOND)),
        ],
    )
    def test_valid_time_delta_seconds_range(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.TIME_DELTA, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Microseconds (long/unit and short forms, including µs)
            ("123 microsecond", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 microseconds", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123us", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 us", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 µs", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("+123us", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("-123us", TimeDelta(-123, TimeUnit.MICROSECOND)),
            # Milliseconds
            ("123 millisecond", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123 milliseconds", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123ms", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123 ms", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("+123ms", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("-123ms", TimeDelta(-123, TimeUnit.MILLISECOND)),
            # Seconds
            ("123 second", TimeDelta(123, TimeUnit.SECOND)),
            ("123 seconds", TimeDelta(123, TimeUnit.SECOND)),
            ("123s", TimeDelta(123, TimeUnit.SECOND)),
            ("123 s", TimeDelta(123, TimeUnit.SECOND)),
            ("+123s", TimeDelta(123, TimeUnit.SECOND)),
            ("-123s", TimeDelta(-123, TimeUnit.SECOND)),
            # Minutes
            ("123 minute", TimeDelta(123, TimeUnit.MINUTE)),
            ("123 minutes", TimeDelta(123, TimeUnit.MINUTE)),
            ("123m", TimeDelta(123, TimeUnit.MINUTE)),
            ("123 m", TimeDelta(123, TimeUnit.MINUTE)),
            ("+123m", TimeDelta(123, TimeUnit.MINUTE)),
            ("-123m", TimeDelta(-123, TimeUnit.MINUTE)),
            # Hours
            ("123 hour", TimeDelta(123, TimeUnit.HOUR)),
            ("123 hours", TimeDelta(123, TimeUnit.HOUR)),
            ("123h", TimeDelta(123, TimeUnit.HOUR)),
            ("123 h", TimeDelta(123, TimeUnit.HOUR)),
            ("+123h", TimeDelta(123, TimeUnit.HOUR)),
            ("-123h", TimeDelta(-123, TimeUnit.HOUR)),
            # Days
            ("123 day", TimeDelta(123, TimeUnit.DAY)),
            ("123 days", TimeDelta(123, TimeUnit.DAY)),
            ("123d", TimeDelta(123, TimeUnit.DAY)),
            ("123 d", TimeDelta(123, TimeUnit.DAY)),
            ("+123d", TimeDelta(123, TimeUnit.DAY)),
            ("-123d", TimeDelta(-123, TimeUnit.DAY)),
            # Weeks
            ("123 week", TimeDelta(123, TimeUnit.WEEK)),
            ("123 weeks", TimeDelta(123, TimeUnit.WEEK)),
            ("123w", TimeDelta(123, TimeUnit.WEEK)),
            ("123 w", TimeDelta(123, TimeUnit.WEEK)),
            ("+123w", TimeDelta(123, TimeUnit.WEEK)),
            ("-123w", TimeDelta(-123, TimeUnit.WEEK)),
        ],
    )
    def test_valid_time_delta_units(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.TIME_DELTA, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Case-insensitive variants for supported units
            ("123 MiCrOsEcOnD", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 MiCrOsEcOnDs", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 Us", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 µS", TimeDelta(123, TimeUnit.MICROSECOND)),
            ("123 MILLISECOND", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123 MILLISECONDS", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123 MS", TimeDelta(123, TimeUnit.MILLISECOND)),
            ("123 SECOND", TimeDelta(123, TimeUnit.SECOND)),
            ("123 SECONDS", TimeDelta(123, TimeUnit.SECOND)),
            ("123 S", TimeDelta(123, TimeUnit.SECOND)),
            ("123 MINUTE", TimeDelta(123, TimeUnit.MINUTE)),
            ("123 MINUTES", TimeDelta(123, TimeUnit.MINUTE)),
            ("123 M", TimeDelta(123, TimeUnit.MINUTE)),
            ("123 HOUR", TimeDelta(123, TimeUnit.HOUR)),
            ("123 HOURS", TimeDelta(123, TimeUnit.HOUR)),
            ("123 H", TimeDelta(123, TimeUnit.HOUR)),
            ("123 DAY", TimeDelta(123, TimeUnit.DAY)),
            ("123 DAYS", TimeDelta(123, TimeUnit.DAY)),
            ("123 D", TimeDelta(123, TimeUnit.DAY)),
            ("123 WEEK", TimeDelta(123, TimeUnit.WEEK)),
            ("123 WEEKS", TimeDelta(123, TimeUnit.WEEK)),
            ("123 W", TimeDelta(123, TimeUnit.WEEK)),
        ],
    )
    def test_case_insensitive_time_delta_units(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.TIME_DELTA, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_errors",
        [
            # Decimal limits exceeded with units
            ("-9223372036854775809s", [ErrorCategory.LIMIT_EXCEEDED]),
            ("9223372036854775808s", [ErrorCategory.LIMIT_EXCEEDED]),
            # Decimal wrong syntax (prevent octal-like forms)
            ("00s", [ErrorCategory.SYNTAX]),
            ("01s", [ErrorCategory.SYNTAX]),
            ("-00s", [ErrorCategory.SYNTAX]),
            ("-01s", [ErrorCategory.SYNTAX]),
            ("02938s", [ErrorCategory.SYNTAX]),
            # Digit separator problems
            ("'123s", [ErrorCategory.SYNTAX]),
            ("123's", [ErrorCategory.SYNTAX, ErrorCategory.UNEXPECTED_END]),
            ("1''23s", [ErrorCategory.SYNTAX]),
            # Binary/hex not allowed for time-deltas
            ("0x10s", [ErrorCategory.SYNTAX]),
            ("0b1010s", [ErrorCategory.SYNTAX]),
        ],
    )
    def test_errors_in_time_delta(self, content, expected_errors):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            if isinstance(expected_errors, list):
                assert e.category in expected_errors, f"Expected one of {expected_errors}, got {e.category}"
            else:
                assert e.category == expected_errors, f"Expected error category {expected_errors}, got {e.category}"
