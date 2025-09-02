#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Any

from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.location import Position


@dataclass(frozen=True, slots=True)
class SyntaxToken:
    """A token for syntax highlighting."""

    token_type: str
    begin: Position
    end: Position
    raw_text: str
    value: Any | None = None

    @property
    def index(self) -> int:
        return self.begin.character_index

    @property
    def line(self) -> int:
        return self.begin.line

    @property
    def column(self) -> int:
        return self.begin.column


SyntaxTokenGenerator = Generator[SyntaxToken, None, None]


class SyntaxLexer:
    """Public lexer interface for syntax highlighting."""

    def __init__(self, text: str):
        """Initialize the lexer with the given text."""
        self._text = text

    def tokens(self) -> SyntaxTokenGenerator:
        """Yield tokens for syntax highlighting."""
        source = TextSource(self._text)
        source.open()
        lexer = Lexer(source, syntax_mode=True)
        for token in lexer.tokens():
            if token.type != TokenType.END_OF_DATA:
                yield SyntaxToken(str(token.type), token.begin, token.end, token.raw_text, token.value)
        return None
