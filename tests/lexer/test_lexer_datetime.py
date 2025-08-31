#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerDateTime(LexerHelper):

    @pytest.mark.parametrize(
        "content, expected_source",
        [
            ("2025-01-01T12:34", "2025-01-01T12:34:00"),
            ("2025-01-01t12:34:56", "2025-01-01T12:34:56"),
            ("2025-01-01 12:34:56", "2025-01-01T12:34:56"),
            ("2025-01-01T12:34:56.123", "2025-01-01T12:34:56.123000"),
            ("2025-01-01T12:34:56.123456", "2025-01-01T12:34:56.123456"),
            ("2025-01-01T12:34:56+01", "2025-01-01T12:34:56+01:00"),
            ("2025-01-01T12:34:56+01:30", "2025-01-01T12:34:56+01:30"),
            ("2025-01-01T12:34:56Z", "2025-01-01T12:34:56Z"),
            ("2025-01-01t12:34:56z", "2025-01-01T12:34:56Z"),
            ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00Z"),
            ("9999-12-31 23:59:59.999999", "9999-12-31T23:59:59.999999"),
            ("2025-01-01T12:00:00+23:59", "2025-01-01T12:00:00+23:59"),
            ("2025-01-01T12:00:00-23:59", "2025-01-01T12:00:00-23:59"),
        ],
    )
    def test_valid_datetime(self, content: str, expected_source: str):
        self.setup_for_value(content)
        self.expect_value_begin()
        expected_value = datetime.datetime.fromisoformat(expected_source)
        token = next(self.tokenGenerator)
        assert token.type == TokenType.DATE_TIME
        assert token.raw_text == content
        assert token.value == expected_value
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            "2025-01-01T24:00:00",  # invalid hour
            "2025-01-01T12:60:00",  # invalid minute
            "2025-01-01T12:00:60",  # invalid second
            "2025-01-01T12:34.1",  # fraction given without seconds
            "2025-01-01T12:34:56.1234567890",  # fraction too long (>9)
            "2025-13-01T12:34:56",  # invalid month
            "2025-00-01T12:34:56",  # invalid month
            "2025-02-30T12:34:56",  # invalid day
            "2025-01-01T12:00:00+24:00",  # offset hour out of range
            "2025-01-01T12:00:00+00:60",  # offset minute out of range
        ],
    )
    def test_invalid_datetime(self, content: str):
        self.setup_for_value(content)
        with pytest.raises(Error) as e:
            for _ in self.tokenGenerator:
                pass
        # Syntax or unexpected end depending on where it fails, but at least a syntax error should be raised
        assert e.value.category == ErrorCategory.SYNTAX

    def test_mixed_list_values(self):
        content = "2025-01-01, 12:00:00, 2025-01-01T12:00:00"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(
            TokenType.DATE, expected_raw="2025-01-01", expected_value=datetime.date.fromisoformat("2025-01-01")
        )
        self.expect_token(TokenType.VALUE_LIST_SEPARATOR, expected_raw=",")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        # Time
        token = next(self.tokenGenerator)
        assert token.type == TokenType.TIME
        assert token.raw_text == "12:00:00"
        assert token.value == datetime.time.fromisoformat("12:00:00")
        # Separator
        self.expect_token(TokenType.VALUE_LIST_SEPARATOR, expected_raw=",")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        # DateTime
        expected_dt = datetime.datetime.fromisoformat("2025-01-01T12:00:00")
        token = next(self.tokenGenerator)
        assert token.type == TokenType.DATE_TIME
        assert token.raw_text == "2025-01-01T12:00:00"
        assert token.value == expected_dt
        self.expect_value_end()
