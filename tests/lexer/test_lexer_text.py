#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerText(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            ('""', ""),
            ('"Hello, World!"', "Hello, World!"),
            # Simple escapes
            ('"\\\\"', "\\"),  # \\ -> \
            ('"\\""', '"'),  # \\" -> "
            ('"\\$"', "$"),  # \$ -> $
            # Control character escapes (case-insensitive)
            ('"Line\\nBreak"', "Line\nBreak"),
            ('"Carriage\\rReturn"', "Carriage\rReturn"),
            ('"Tab\\tHere"', "Tab\tHere"),
            ('"Mix\\N\\R\\T"', "Mix\n\r\t"),
            # Unicode escapes: fixed 4 hex digits
            ('"Letter\\u0041"', "LetterA"),
            ('"Lower\\u0041Upper"', "LowerAUpper"),
            # Unicode escapes: variable length in braces (1-8 hex digits)
            ('"Smiley: \\u{1f604}"', "Smiley: 😄"),
            ('"A: \\u{41}"', "A: A"),
            ('"Zero padded: \\u{00000041}"', "Zero padded: A"),
            # Mixed content
            ('"\\\\ \\" \\$ \\n \\r \\t \\u0041 \\u{41}"', '\\ " $ \n \r \t A A'),
        ],
    )
    def test_valid_text(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.TEXT, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            '"',  # Missing closing quote
            '"unterminated',  # Missing closing quote
            '"Unknown \\x escape"',  # Unknown escape
            '"Bad hex \\u12"',  # Too short fixed unicode
            '"Empty braces \\u{}"',  # Empty braces
            '"Bad braces \\u{xyz}"',  # Non-hex digits
            '"Too big \\u{110000}"',  # > U+10FFFF
            '"Surrogate \\u{d800}"',  # Surrogate area
            '"Null forbidden \\u0000"',  # Null forbidden
            '"Null forbidden 2 \\u{0}"',  # Null forbidden
            '"Ends with backslash \\"',  # Incomplete escape at end
        ],
    )
    def test_invalid_text(self, content):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            # According to the reference, these are all syntax errors for text values
            assert e.category == ErrorCategory.SYNTAX
