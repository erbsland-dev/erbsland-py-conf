#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerBoolean(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # lower case
            ("true", True),
            ("yes", True),
            ("enabled", True),
            ("on", True),
            ("false", False),
            ("no", False),
            ("disabled", False),
            ("off", False),
            # upper case
            ("TRUE", True),
            ("YES", True),
            ("ENABLED", True),
            ("ON", True),
            ("FALSE", False),
            ("NO", False),
            ("DISABLED", False),
            ("OFF", False),
            # mixed case
            ("TrUe", True),
            ("YeS", True),
            ("EnAbLed", True),
            ("On", True),
            ("FaLsE", False),
            ("No", False),
            ("DiSaBlEd", False),
            ("OfF", False),
        ],
    )
    def test_valid_boolean(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.BOOLEAN, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content",
        [
            "truee",
            "true0",
            "false'",
            "tru",
            "fals",
            "tr",
            "fa",
            "t",
            "f",
            "tru",
        ],
    )
    def test_invalid_boolean(self, content):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            assert e.category == ErrorCategory.SYNTAX
