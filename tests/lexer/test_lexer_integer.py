#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerInteger(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Decimal valid values
            ("0", 0),
            ("-0", 0),
            ("1", 1),
            ("-1", -1),
            ("1234567890", 1234567890),
            ("-5'239", -5239),
            ("-9223372036854775808", -9223372036854775808),
            ("9223372036854775807", 9223372036854775807),
            ("-9'223'372'036'854'775'808", -9223372036854775808),
            ("9'223'372'036'854'775'807", 9223372036854775807),
        ],
    )
    def test_valid_integer_decimal(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.INTEGER, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Hexadecimal valid values
            ("0x0", 0),
            ("0x00", 0),
            ("0x0000000000000000", 0),
            ("-0x0", 0),
            ("0x1", 1),
            ("0xa", 0xA),
            ("0x0123456789abcdef", 0x0123456789ABCDEF),
            ("0x0123456789ABCDEF", 0x0123456789ABCDEF),
            ("-0x0123456789abcdef", -0x0123456789ABCDEF),
            ("-0x0123456789ABCDEF", -0x0123456789ABCDEF),
            ("0x0123'4567'89ab'cdef", 0x0123456789ABCDEF),
            ("-0x8000000000000000", -9223372036854775808),
            ("0x7fffffffffffffff", 9223372036854775807),
        ],
    )
    def test_valid_integer_hexadecimal(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.INTEGER, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_value",
        [
            # Binary valid values
            ("0b0", 0),
            ("0b00", 0),
            ("0b0000000000000000", 0),
            ("-0b0", 0),
            ("0b1", 1),
            ("0b10", 2),
            ("-0b1000000000000000000000000000000000000000000000000000000000000000", -9223372036854775808),
            ("0b0111111111111111111111111111111111111111111111111111111111111111", 9223372036854775807),
            ("-0b1010'1000'1111'0010", -0b1010100011110010),
        ],
    )
    def test_valid_integer_binary(self, content, expected_value):
        self.setup_for_value(content)
        self.expect_value_begin()
        self.expect_token(TokenType.INTEGER, expected_raw=content, expected_value=expected_value)
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_errors",
        [
            # Decimal limits exceeded
            ("-9223372036854775809", [ErrorCategory.LIMIT_EXCEEDED]),
            ("9223372036854775808", [ErrorCategory.LIMIT_EXCEEDED]),
            ("-1000000000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            ("1000000000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            # Decimal wrong syntax (prevent octal-like forms)
            ("00", [ErrorCategory.SYNTAX]),
            ("01", [ErrorCategory.SYNTAX]),
            ("-00", [ErrorCategory.SYNTAX]),
            ("-01", [ErrorCategory.SYNTAX]),
            ("02938", [ErrorCategory.SYNTAX]),
            # Decimal digit separator problems
            ("'123", [ErrorCategory.SYNTAX]),
            ("123'", [ErrorCategory.SYNTAX, ErrorCategory.UNEXPECTED_END]),
            ("1''23", [ErrorCategory.SYNTAX]),
            # Hex limits exceeded
            ("0x00000000000000000000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            ("-0x8000000000000001", [ErrorCategory.LIMIT_EXCEEDED]),
            ("0x8000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            # Hex syntax problems
            ("0xabcdefg", [ErrorCategory.SYNTAX]),
            ("0x'0000", [ErrorCategory.SYNTAX]),
            ("0x0000'", [ErrorCategory.SYNTAX, ErrorCategory.UNEXPECTED_END]),
            ("0x00''00", [ErrorCategory.SYNTAX]),
            # Binary limits exceeded
            ("0b1000000000000000000000000000000000000000000000000000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            ("-0b1000000000000000000000000000000000000000000000000000000000000001", [ErrorCategory.LIMIT_EXCEEDED]),
            # Binary syntax problems
            ("0b102", [ErrorCategory.SYNTAX]),
            ("0b'0000", [ErrorCategory.SYNTAX]),
            ("0b0000'", [ErrorCategory.SYNTAX, ErrorCategory.UNEXPECTED_END]),
            ("0b00''00", [ErrorCategory.SYNTAX]),
            # Byte unit limits exceeded
            ("1zb", [ErrorCategory.LIMIT_EXCEEDED]),
        ],
    )
    def test_errors_in_integer(self, content, expected_errors):
        self.setup_for_value(content)
        try:
            for _ in self.tokenGenerator:
                pass
            assert False, "Expected an error"
        except Error as e:
            if isinstance(expected_errors, list):
                assert e.category in expected_errors, f"Expected one of {expected_errors}, got {e.category}"
            else:
                assert e.category == expected_errors, f"Expected error category {expected_errors}, got {e.category}"
