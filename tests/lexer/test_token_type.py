#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.impl.token_type import TokenType


class TestTokenType:
    @pytest.mark.parametrize(
        "token_type",
        [
            TokenType.MULTI_LINE_TEXT_OPEN,
            TokenType.MULTI_LINE_CODE_OPEN,
            TokenType.MULTI_LINE_REGEX_OPEN,
            TokenType.MULTI_LINE_BYTES_OPEN,
        ],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_open_true(self, token_type: TokenType) -> None:
        assert token_type.is_multi_line_open()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.MULTI_LINE_TEXT_CLOSE, TokenType.TEXT, TokenType.LINE_BREAK],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_open_false(self, token_type: TokenType) -> None:
        assert not token_type.is_multi_line_open()

    @pytest.mark.parametrize(
        "token_type",
        [
            TokenType.MULTI_LINE_TEXT_CLOSE,
            TokenType.MULTI_LINE_CODE_CLOSE,
            TokenType.MULTI_LINE_REGEX_CLOSE,
            TokenType.MULTI_LINE_BYTES_CLOSE,
        ],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_close_true(self, token_type: TokenType) -> None:
        assert token_type.is_multi_line_close()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.MULTI_LINE_TEXT_OPEN, TokenType.CODE, TokenType.TEXT],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_close_false(self, token_type: TokenType) -> None:
        assert not token_type.is_multi_line_close()

    @pytest.mark.parametrize(
        "token_type",
        [
            TokenType.MULTI_LINE_TEXT,
            TokenType.MULTI_LINE_CODE,
            TokenType.MULTI_LINE_REGEX,
        ],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_text_true(self, token_type: TokenType) -> None:
        assert token_type.is_multi_line_text()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.MULTI_LINE_BYTES, TokenType.TEXT, TokenType.CODE],
        ids=lambda t: t.name,
    )
    def test_is_multi_line_text_false(self, token_type: TokenType) -> None:
        assert not token_type.is_multi_line_text()

    @pytest.mark.parametrize(
        "token_type",
        [
            TokenType.INTEGER,
            TokenType.BOOLEAN,
            TokenType.FLOAT,
            TokenType.TEXT,
            TokenType.CODE,
            TokenType.REG_EX,
            TokenType.BYTES,
            TokenType.DATE,
            TokenType.TIME,
            TokenType.DATE_TIME,
            TokenType.TIME_DELTA,
        ],
        ids=lambda t: t.name,
    )
    def test_is_single_line_value_true(self, token_type: TokenType) -> None:
        assert token_type.is_single_line_value()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.MULTI_LINE_TEXT_OPEN, TokenType.NAME, TokenType.MULTI_LINE_TEXT],
        ids=lambda t: t.name,
    )
    def test_is_single_line_value_false(self, token_type: TokenType) -> None:
        assert not token_type.is_single_line_value()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.SPACING, TokenType.COMMENT, TokenType.ERROR],
        ids=lambda t: t.name,
    )
    def test_is_spacing_true(self, token_type: TokenType) -> None:
        assert token_type.is_spacing()

    @pytest.mark.parametrize(
        "token_type",
        [TokenType.LINE_BREAK, TokenType.INDENTATION, TokenType.NAME],
        ids=lambda t: t.name,
    )
    def test_is_spacing_false(self, token_type: TokenType) -> None:
        assert not token_type.is_spacing()
