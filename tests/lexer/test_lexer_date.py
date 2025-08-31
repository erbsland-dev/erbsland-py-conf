#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import datetime
import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerDate(LexerHelper):

    @pytest.mark.parametrize(
        "content",
        [
            "2025-01-01",
            "1999-12-31",
            "0001-01-01",
            "9999-12-31",
            "2000-02-29",  # leap year valid
        ],
    )
    def test_valid_date(self, content: str):
        self.setup_for_value(content)
        self.expect_value_begin()
        # For dates, the lexer stores a datetime at midnight
        expected_value = datetime.date.fromisoformat(content)
        self.expect_token(TokenType.DATE, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            "2025-13-01",  # invalid month
            "2025-00-01",  # invalid month
            "2025-02-30",  # invalid day
            "2025-01-32",  # invalid day
            "2025-1-01",  # wrong format
            "25-01-01",  # wrong format
            "2025-01-01Z",  # trailing garbage
            "1900-02-29",  # not a leap year
        ],
    )
    def test_invalid_date(self, content: str):
        self.setup_for_value(content)
        with pytest.raises(Error) as e:
            for _ in self.tokenGenerator:
                pass
        assert e.value.category == ErrorCategory.SYNTAX

    def test_date_in_list_context(self):
        content = "2025-08-15, 2020-02-29"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(
            TokenType.DATE, expected_raw="2025-08-15", expected_value=datetime.date.fromisoformat("2025-08-15")
        )
        self.expect_token(TokenType.VALUE_LIST_SEPARATOR, expected_raw=",")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(
            TokenType.DATE, expected_raw="2020-02-29", expected_value=datetime.date.fromisoformat("2020-02-29")
        )
        self.expect_value_end()
