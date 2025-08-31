#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import re
import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerRegex(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_pattern",
        [
            ("//", ""),
            ("/abc/", "abc"),
            ("/[a-z]+/", "[a-z]+"),
            # Escaping a slash should yield a literal slash in the pattern
            (r"/a\/b/", r"a/b"),
            # Escaping a backslash should keep two backslashes in the pattern
            (r"/a\\b/", r"a\\b"),
            # Other escapes must be passed through unchanged
            (r"/\n\t\r\d\w/", r"\n\t\r\d\w"),
            (r"/\u0041\x41/", r"\u0041\x41"),
            ("/äöüß€/", "äöüß€"),
        ],
    )
    def test_valid_regex(self, content, expected_pattern):
        self.setup_for_value(content)
        self.expect_value_begin()
        # The regex token
        token = next(self.tokenGenerator)
        assert token.type == TokenType.REG_EX
        assert token.raw_text == content  # Raw must include the slashes
        assert isinstance(token.value, re.Pattern)
        assert token.value.pattern == expected_pattern
        # The rest of the line must be end
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            "/unterminated",  # Missing closing slash
            r"/endswithbackslash\\",  # Trailing backslash without char to escape
        ],
    )
    def test_invalid_regex(self, content):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            # Missing closing slash or incomplete escape are syntax errors
            assert e.category == ErrorCategory.SYNTAX

    @pytest.mark.parametrize(
        "content,patch_unescape,message",
        [
            pytest.param("/abc/", True, "Invalid escape sequence", id="invalid-escape"),
            pytest.param("/(/", False, "Invalid regular expression", id="invalid-pattern"),
        ],
    )
    def test_regex_errors(self, content, patch_unescape, message, monkeypatch):
        if patch_unescape:
            from erbsland.conf.impl.text_escape import UnescapeError

            def _raise(_):
                raise UnescapeError("boom", 0)

            monkeypatch.setattr("erbsland.conf.impl.lexing.text.unescape_regex", _raise)
        self.setup_for_value(content)
        with pytest.raises(Error) as excinfo:
            for _ in self.tokenGenerator:
                pass
        assert excinfo.value.category == ErrorCategory.SYNTAX
        assert message in excinfo.value.message
