#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0
import pytest

from erbsland.conf.error import Error
from erbsland.conf.impl.lexing.lexer import Lexer
from erbsland.conf.impl.text_source import TextSource
from lexer.lexer_helper import LexerHelper


class TestLexerIo(LexerHelper):

    def test_not_open(self):
        with pytest.raises(Error):
            self.source = TextSource("abc")
            self.lexer = Lexer(self.source)
            self.tokenGenerator = self.lexer.tokens()
            self.token = next(self.tokenGenerator)
