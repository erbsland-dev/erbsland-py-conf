#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from erbsland.conf.impl.file_source import FileSource
from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.impl.token import TokenStorageType
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.name import Name


class LexerHelper:

    def setup_generator(self, content_or_file: str | Path):
        if isinstance(content_or_file, Path):
            self.source = FileSource(content_or_file)
        else:
            self.source = TextSource(content_or_file)
        self.source.open()
        self.lexer = Lexer(self.source)
        self.tokenGenerator = self.lexer.tokens()

    def setup_for_value(self, value_content: str):
        self.setup_generator(f"[main]\nvalue: {value_content}\n")

    def expect_value_begin(self):
        """Test for the beginning of a value."""
        self.expect_token(TokenType.SECTION_MAP_OPEN, expected_raw="[")
        self.expect_token(TokenType.NAME, expected_raw="main", expected_value=Name.create_regular("main"))
        self.expect_token(TokenType.SECTION_MAP_CLOSE, expected_raw="]")
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_token(TokenType.NAME, expected_raw="value")
        self.expect_token(TokenType.NAME_VALUE_SEPARATOR, expected_raw=":")
        self.expect_token(TokenType.SPACING, expected_raw=" ")

    def expect_value_end(self):
        """Test for the end of a value."""
        self.expect_token(TokenType.LINE_BREAK, expected_raw="\n")
        self.expect_end_of_stream()

    def expect_token(self, token_type: TokenType, *, expected_raw: str = None, expected_value: TokenStorageType = None):
        """Test for a specific token."""
        token = next(self.tokenGenerator)
        assert token.type == token_type, f"Expected token type {token_type}, got {token.type}"
        if expected_raw is not None:
            assert token.raw_text == expected_raw, f"Expected raw text '{expected_raw}', got '{token.raw_text}'"
        if expected_value is not None:
            assert token.value == expected_value, f"Expected value '{expected_value}', got '{token.value}'"

    def expect_end_of_stream(self):
        """Test for the end of the stream."""
        # The stream must end with an end of data token.
        token = next(self.tokenGenerator)
        assert token.type == TokenType.END_OF_DATA
        # After the end of data token, the stream must end.
        with pytest.raises(StopIteration):
            next(self.tokenGenerator)
