#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerMultiLineBytes(LexerHelper):
    def test_valid_multi_line_bytes_basic(self):
        content = "<<<\n    01ff a0 7b\n    >>>"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(
            TokenType.MULTI_LINE_BYTES,
            expected_raw="01ff a0 7b",
            expected_value=bytes.fromhex("01ff a0 7b"),
        )
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_value_end()

    def test_valid_multi_line_bytes_with_format_and_comment(self):
        content = "<<<hex  # data\n    f0ba1412 0177ec42\n    >>>"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.MULTI_LINE_BYTES_FORMAT, expected_raw="hex")
        self.expect_token(TokenType.SPACING, expected_raw="  ")
        self.expect_token(TokenType.COMMENT, expected_raw="# data")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(
            TokenType.MULTI_LINE_BYTES,
            expected_raw="f0ba1412 0177ec42",
            expected_value=bytes.fromhex("f0ba1412 0177ec42"),
        )
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_value_end()

    def test_empty_lines_and_comments_inside(self):
        content = "<<<\n\n    0100\n        # align\n\n    ec24\n    >>>"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # empty line
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # empty line
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES, expected_raw="0100", expected_value=bytes.fromhex("0100"))
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        # line with indentation plus spacing and comment only
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_token(TokenType.COMMENT, expected_raw="# align")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")  # another empty line
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES, expected_raw="ec24", expected_value=bytes.fromhex("ec24"))
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_value_end()

    def test_comment_after_close(self):
        content = "<<<\n    01\n    >>>   # end"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES, expected_raw="01", expected_value=bytes.fromhex("01"))
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_token(TokenType.SPACING, expected_raw="   ")
        self.expect_token(TokenType.COMMENT, expected_raw="# end")
        self.expect_value_end()

    def test_next_line_multiline_bytes(self):
        content = "\n    <<<\n    0102 03\n    >>>"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES, expected_raw="0102 03", expected_value=bytes.fromhex("0102 03"))
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_value_end()

    def test_crlf_line_breaks(self):
        content = "<<<\r\n    aa\r\n    >>>"
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.MULTI_LINE_BYTES_OPEN, expected_raw="<<<")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\r\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES, expected_raw="aa", expected_value=bytes.fromhex("aa"))
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\r\n")
        self.expect_token(TokenType.INDENTATION, expected_raw="    ")
        self.expect_token(TokenType.MULTI_LINE_BYTES_CLOSE, expected_raw=">>>")
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            # Indentation mismatch
            ("<<<\n    aabb\n  cc\n    >>>", ErrorCategory.INDENTATION),
            # Invalid hex sequence (non-hex characters)
            ("<<<\n    zz\n    >>>", ErrorCategory.SYNTAX),
            # Invalid hex due to spacing within a byte (odd count)
            ("<<<\n    0 1\n    >>>", ErrorCategory.SYNTAX),
            # Unterminated (missing close)
            ("<<<\n    01", ErrorCategory.UNEXPECTED_END),
            # Unsupported but valid format identifier
            ("<<<base64\n    00\n    >>>", ErrorCategory.UNSUPPORTED),
            # Invalid format syntax: colon in multi-line
            ("<<<hex:\n    00\n    >>>", ErrorCategory.SYNTAX),
            # Invalid format syntax: spacing before identifier
            ("<<< hex\n    00\n    >>>", ErrorCategory.SYNTAX),
            # Invalid identifier start
            ("<<<_fmt\n    00\n    >>>", ErrorCategory.SYNTAX),
            # Identifier too long (>16)
            ("<<<format01234567890\n    00\n    >>>", ErrorCategory.LIMIT_EXCEEDED),
        ],
    )
    def test_invalid_multi_line_bytes(self, content, expected_category):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            assert e.category == expected_category
