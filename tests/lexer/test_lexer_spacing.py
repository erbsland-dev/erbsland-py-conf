#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import pytest

from erbsland.conf.error import Error, ConfCharacterError
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerSpacing(LexerHelper):

    def test_empty_stream(self):
        self.setup_generator("")
        self.expect_end_of_stream()

    def test_spacing(self):
        self.setup_generator("     \t  \t\n    \r\n    ")
        self.expect_token(TokenType.SPACING, expected_raw="     \t  \t")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\r\n")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_end_of_stream()

    def test_empty_lines_and_comments(self):
        self.setup_generator("# This is a comment\n\n    # Another comment\n")
        self.expect_token(TokenType.COMMENT, expected_raw="# This is a comment")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.SPACING, expected_raw="    ")
        self.expect_token(TokenType.COMMENT, expected_raw="# Another comment")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    @pytest.mark.parametrize(
        "document",
        [
            "    \n    \r \n    ",
            "\r\r\r",
            "\r\n\r\r\n",
            "           \r",
        ],
    )
    def test_error_in_line_break(self, document):
        self.setup_generator("    \n    \r \n    ")
        with pytest.raises(Error):
            token = next(self.tokenGenerator)
            while token.type != TokenType.END_OF_DATA:
                token = next(self.tokenGenerator)

    @pytest.mark.parametrize(
        "pattern",
        [
            "%(char)s",
            "    %(char)s",
            "    %(char)s    \n\n",
            "# valid line\n# valid line\n   %(char)s    \n\n",
            "    # In %(char)s comment\n",
        ],
    )
    @pytest.mark.parametrize(
        "char",
        [
            *[chr(v) for v in range(0x00, 0x09)],
            chr(0x0B),
            chr(0x0C),
            *[chr(v) for v in range(0x0E, 0x20)],
            *[chr(v) for v in range(0x7F, 0xA0)],
        ],
    )
    def test_pattern_with_spacing(self, pattern, char):
        self.setup_generator(pattern % {"char": char})
        with pytest.raises(ConfCharacterError):
            token = next(self.tokenGenerator)
            while token.type != TokenType.END_OF_DATA:
                token = next(self.tokenGenerator)
