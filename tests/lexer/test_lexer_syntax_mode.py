#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from pathlib import Path

from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.syntax.lexer import SyntaxLexer
from .lexer_helper import LexerHelper


DATA_DIR = Path(__file__).parent / "data"


class TestLexerSyntaxMode(LexerHelper):

    def test_basic_document(self):
        self.setup_generator(DATA_DIR / "syntax_mode_1.elcl", syntax_mode=True)
        self.expect_token(TokenType.COMMENT, expected_raw="# Comment")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main")
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(TokenType.INTEGER, expected_raw="123")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    def test_error_recovery(self):
        self.setup_generator(DATA_DIR / "syntax_mode_2.elcl", syntax_mode=True)
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main")
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value_a")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(TokenType.ERROR, expected_raw="~~~error~~~")
        self.expect_token(TokenType.SKIPPED, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value_b")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")
        self.expect_token(TokenType.INTEGER, expected_raw="123")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    def test_error_with_offset(self):
        self.setup_generator(DATA_DIR / "syntax_mode_3.elcl", syntax_mode=True)
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main")
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.SKIPPED, expected_raw="value: \"text")
        self.expect_token(TokenType.ERROR, expected_raw=" text\"")
        self.expect_token(TokenType.SKIPPED, expected_raw="\n")
        self.expect_end_of_stream()

    def test_public_interface(self):
        content = (DATA_DIR / "syntax_mode_1.elcl").read_bytes().decode("utf-8") # Preserve NL!
        syntax_lexer = SyntaxLexer(content)
        expected_tokens = [
            (TokenType.COMMENT, "# Comment"),
            (TokenType.LINE_BREAK, "\n"),
            (TokenType.SECTION_MAP_OPEN, "["),
            (TokenType.NAME, "main"),
            (TokenType.SECTION_MAP_CLOSE, "]"),
            (TokenType.LINE_BREAK, "\n"),
            (TokenType.NAME, "value"),
            (TokenType.NAME_VALUE_SEPARATOR, ":"),
            (TokenType.SPACING, " "),
            (TokenType.INTEGER, "123"),
            (TokenType.LINE_BREAK, "\n"),
        ]
        for index, token in enumerate(syntax_lexer.tokens()):
            expected_token_type, expected_raw = expected_tokens[index]
            assert expected_token_type.value == token.token_type
            assert expected_raw == token.raw_text


