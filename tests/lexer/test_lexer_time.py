#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import pytest

from erbsland.conf.datetime import Time, DateTime
from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerTime(LexerHelper):

    @pytest.mark.parametrize(
        "content, expected_iso",
        [
            ("12:34", "12:34:00"),
            ("12:34:56", "12:34:56"),
            ("t12:34:56", "12:34:56"),
            ("T12:34:56", "12:34:56"),
            ("00:00:00", "00:00:00"),
            ("23:59:59", "23:59:59"),
            ("12:34:56.1", "12:34:56.100000"),
            ("12:34:56.123", "12:34:56.123000"),
            ("12:34:56.123456", "12:34:56.123456"),
            # with timezone offsets
            ("12:34:56+01:00", "12:34:56+01:00"),
            ("12:34:56-02:30", "12:34:56-02:30"),
            ("12:34:56Z", "12:34:56+00:00"),
            ("12:34z", "12:34:00+00:00"),
            ("t12:34:56+01", "12:34:56+01:00"),
            ("12:34-03", "12:34:00-03:00"),
            ("12:00+23:59", "12:00:00+23:59"),
            ("12:00-23:59", "12:00:00-23:59"),
            ("06:21:07.123+05:45", "06:21:07.123000+05:45"),
        ],
    )
    def test_valid_time(self, content: str, expected_iso: str):
        self.setup_for_value(content)
        self.expect_value_begin()
        expected_value = Time.fromisoformat(expected_iso)
        token = next(self.tokenGenerator)
        assert token.type == TokenType.TIME
        assert token.raw_text == content
        assert token.value == expected_value
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            "24:00:00",  # invalid hour
            "12:60:00",  # invalid minute
            "12:00:60",  # invalid second
            "12:34.1",  # fraction given without seconds
            "12:34:56.1234567890",  # too many fraction digits (>9)
            "12:00+24:00",  # offset hour out of range
            "12:00+00:60",  # offset minute out of range
        ],
    )
    def test_invalid_time(self, content: str):
        self.setup_for_value(content)
        with pytest.raises(Error) as e:
            for _ in self.tokenGenerator:
                pass
        assert e.value.category == ErrorCategory.SYNTAX

    def test_time_in_list_context(self):
        content = "12:00:00, 23:59:59.123456"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.TIME, expected_raw="12:00:00", expected_value=Time.fromisoformat("12:00:00"))
        self.expect_token(TokenType.VALUE_LIST_SEPARATOR, expected_raw=",")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(
            TokenType.TIME,
            expected_raw="23:59:59.123456",
            expected_value=Time.fromisoformat("23:59:59.123456"),
        )
        self.expect_value_end()
