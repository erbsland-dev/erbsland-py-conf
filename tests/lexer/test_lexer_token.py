#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.impl.token import Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.location import Position
from erbsland.conf.name import Name


class TestToken:
    def test_default_initialization(self):
        token = Token(TokenType.END_OF_DATA)
        assert token.type is TokenType.END_OF_DATA
        assert token.begin is None
        assert token.end is None
        assert token.raw_text is None
        assert token.value is None

    def test_initialization_with_name_value(self):
        begin = Position(1, 1)
        end = Position(1, 5)
        name = Name.create_regular("test")
        token = Token(TokenType.NAME, begin=begin, end=end, raw_text="test", value=name)
        assert token.type is TokenType.NAME
        assert token.begin == begin
        assert token.end == end
        assert token.raw_text == "test"
        assert token.value == name

    def test_initialization_with_storage_value_and_repr(self):
        begin = Position(1, 1)
        end = Position(1, 3)
        token = Token(TokenType.INTEGER, begin=begin, end=end, raw_text="42", value=42)
        assert token.value == 42
        assert repr(token) == "Token(INTEGER, 1:1-1:3, 42)"

    @pytest.mark.parametrize(
        "token_type, begin, end, raw_text, value, message",
        [
            pytest.param("foo", None, None, None, None, "'token_type' must be a TokenType", id="token_type"),
            pytest.param(TokenType.NAME, 1, None, None, None, "'begin' must be a Position", id="begin"),
            pytest.param(TokenType.NAME, None, 1, None, None, "'end' must be a Position", id="end"),
            pytest.param(TokenType.NAME, None, None, 123, None, "'raw_text' must be a string", id="raw_text"),
            pytest.param(
                TokenType.NAME,
                None,
                None,
                None,
                [1],
                "Invalid type for token value",
                id="value",
            ),
        ],
    )
    def test_invalid_initialization(self, token_type, begin, end, raw_text, value, message):
        with pytest.raises(ValueError, match=message):
            Token(token_type, begin=begin, end=end, raw_text=raw_text, value=value)
