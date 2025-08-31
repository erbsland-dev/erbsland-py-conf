#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerBytes(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_bytes",
        [
            ("<>", b""),
            ("< >", b""),
            ("<      >", b""),
            ("<  \t \t \t\t    >", b""),
            ("<00>", bytes.fromhex("00")),
            ("<0000>", bytes.fromhex("0000")),
            ("<00000000>", bytes.fromhex("00000000")),
            ("<000000ee>", bytes.fromhex("000000ee")),
            (
                "<00112233445566778899aabbccddeeffAABBCCDDEEFF>",
                bytes.fromhex("00112233445566778899aabbccddeeffaabbccddeeff"),
            ),
            ("<    ab12cd34>", bytes.fromhex("ab12cd34")),
            ("<ab     12cd34>", bytes.fromhex("ab12cd34")),
            ("<ab 12\tcd 34>", bytes.fromhex("ab12cd34")),
            ("<ab12 cd34    >", bytes.fromhex("ab12cd34")),
            ("<\tab12\tcd34\t>", bytes.fromhex("ab12cd34")),
            ("<hex:>", b""),
            ("<hex: >", b""),
            ("<hex:ffee>", bytes.fromhex("ffee")),
            ("<hex: ffee>", bytes.fromhex("ffee")),
            ("<hex: ff    ee   >", bytes.fromhex("ffee")),
        ],
    )
    def test_valid_single_line_bytes(self, content, expected_bytes):
        self.setup_for_value(content)
        self.expect_value_begin()
        token = next(self.tokenGenerator)
        assert token.type == TokenType.BYTES
        assert token.raw_text == content
        assert token.value == expected_bytes
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_category",
        [
            ("<", ErrorCategory.SYNTAX),
            ("<h", ErrorCategory.SYNTAX),
            ("<he", ErrorCategory.SYNTAX),
            ("<hex", ErrorCategory.SYNTAX),
            ("<hex:", ErrorCategory.SYNTAX),
            ("<0", ErrorCategory.SYNTAX),
            ("<00", ErrorCategory.SYNTAX),
            ("<    0", ErrorCategory.SYNTAX),
            ("<    00", ErrorCategory.SYNTAX),
            ("<0>", ErrorCategory.SYNTAX),
            ("< 0>", ErrorCategory.SYNTAX),
            ("< 12 34 5>", ErrorCategory.SYNTAX),
            ("<123 456>", ErrorCategory.SYNTAX),
            ("<123u56>", ErrorCategory.SYNTAX),
            ("<123O56>", ErrorCategory.SYNTAX),
            ("<hex:h23456>", ErrorCategory.SYNTAX),
        ],
    )
    def test_invalid_single_line_bytes(self, content, expected_category):
        self.setup_for_value(content)
        with pytest.raises(Error) as ei:
            # exhaust tokens to trigger parsing
            for _ in self.tokenGenerator:
                pass
        assert ei.value.category == expected_category

    def test_unknown_format_is_unsupported(self):
        self.setup_for_value("<base64:23456>")
        with pytest.raises(Error) as ei:
            for _ in self.tokenGenerator:
                pass
        assert ei.value.category == ErrorCategory.UNSUPPORTED
