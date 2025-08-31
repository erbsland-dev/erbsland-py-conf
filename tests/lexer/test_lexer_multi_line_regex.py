#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerMultiLineRegex(LexerHelper):
    def test_valid_multi_line_regex(self):
        content = "///\n    ^a\\/b$\n    c\\d+\n    ///"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_REGEX_OPEN, expected_raw="///")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_REGEX, expected_raw="^a\\/b$", expected_value="^a/b$")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_REGEX, expected_raw="c\\d+", expected_value="c\\d+")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_REGEX_CLOSE, expected_raw="///")
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            (
                "///\n    first\n  second\n    ///",
                ErrorCategory.INDENTATION,
            ),
            (
                "///\n    text\\\n    ///",
                ErrorCategory.SYNTAX,
            ),
            (
                "///\n    missing end",
                ErrorCategory.UNEXPECTED_END,
            ),
        ],
    )
    def test_invalid_multi_line_regex(self, content, expected_category):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            assert e.category == expected_category
