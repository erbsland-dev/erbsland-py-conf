#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerCode(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            ("``", ""),
            ("`simple`", "simple"),
            ("`with spaces`", "with spaces"),
            # Backslashes and characters must be preserved literally (no escaping in code text)
            (r"`\\\\\\`", r"\\\\\\"),
            (r"`\n\t\r`", r"\n\t\r"),
            (r"`\u0041`", r"\u0041"),
            (r"`$\"'`", r"$\"'"),
            ("`äöüß€`", "äöüß€"),
        ],
    )
    def test_valid_code(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        # Raw must include the backticks, value must be inner content
        self.expect_token(TokenType.CODE, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            ("`unterminated", ErrorCategory.SYNTAX),  # Missing closing backtick
        ],
    )
    def test_invalid_code(self, content, expected_category):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            assert e.category == expected_category
