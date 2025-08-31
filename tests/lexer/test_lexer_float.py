#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import math
import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.impl.token_type import TokenType
from lexer.lexer_helper import LexerHelper


class TestLexerFloat(LexerHelper):

    @pytest.mark.parametrize(
        "content,expected_value,is_nan,is_inf",
        [
            ("0.0", 0.0, False, False),
            (".0", 0.0, False, False),
            ("0.", 0.0, False, False),
            ("+0.", 0.0, False, False),
            ("-0.0", -0.0, False, False),
            ("1.0", 1.0, False, False),
            ("-1.0", -1.0, False, False),
            ("12345.6789", 12345.6789, False, False),
            ("0.0000000000000001", 1e-16, False, False),
            ("1e0", 1e0, False, False),
            ("1E+10", 1e10, False, False),
            ("1E-5", 1e-5, False, False),
            ("12.34e56", 12.34e56, False, False),
            ("10000000000e-000005", 10000000000.0e-5, False, False),
            ("8'283.9e-5", 8283.9e-5, False, False),
            ("100'000.000'001", 100000.000001, False, False),
            ("nan", math.nan, True, False),
            ("+NaN", math.nan, True, False),
            ("-NaN", -math.nan, True, False),
            ("inf", math.inf, False, True),
            ("+INF", math.inf, False, True),
            ("-inf", -math.inf, False, True),
        ],
    )
    def test_valid_float(self, content, expected_value, is_nan, is_inf):
        self.setup_for_value(content)
        self.expect_value_begin()
        token = next(self.tokenGenerator)
        assert token.type == TokenType.FLOAT
        assert token.raw_text == content
        if is_nan:
            assert math.isnan(token.value)
        elif is_inf:
            assert math.isinf(token.value)
            # sign check for -inf
            if content.strip().startswith("-"):
                assert token.value < 0
            else:
                assert token.value > 0
        else:
            assert token.value == expected_value
        self.expect_value_end()

    @pytest.mark.parametrize(
        "content,expected_errors",
        [
            ("005.293", [ErrorCategory.SYNTAX]),
            ("10000000000.00000000001", [ErrorCategory.LIMIT_EXCEEDED]),
            ("1.000000000000000000000", [ErrorCategory.LIMIT_EXCEEDED]),
            ("12.3.4", [ErrorCategory.SYNTAX]),
            ("1.23e1234567", [ErrorCategory.LIMIT_EXCEEDED]),
            ("0x1.23p+1", [ErrorCategory.SYNTAX]),
            ("'100'000.0", [ErrorCategory.SYNTAX]),
            ("100'000'.0", [ErrorCategory.SYNTAX]),
            ("100''000.0", [ErrorCategory.SYNTAX]),
            ("0.'100'000", [ErrorCategory.SYNTAX]),
            ("0.100'000'", [ErrorCategory.SYNTAX, ErrorCategory.UNEXPECTED_END]),
            ("0.100''000", [ErrorCategory.SYNTAX]),
        ],
    )
    def test_errors_in_float(self, content, expected_errors):
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
