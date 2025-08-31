#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.impl.text_escape import (
    UnescapeError,
    escape_name_path_text,
    escape_text,
    escape_text_for_test,
    unescape_regex,
    unescape_text,
)


class TestTextEscape:
    def test_escape_text(self):
        text = "\\" + '"' + "$" + "\n" + "\r" + "\t" + "\x00" + "\x1b" + "\x80" + "A" + "é"
        expected = (
            "\\\\"  # backslash -> \\
            + '\\"'  # double quote -> \"
            + "\\$"  # dollar sign -> \$
            + "\\n"  # newline -> \n
            + "\\r"  # carriage return -> \r
            + "\\t"  # tab -> \t
            + "\\u{0}"  # null character -> \u{0}
            + "\\u{1b}"  # ESC -> \u{1b}
            + "\\u{80}"  # control range 0x80 -> \u{80}
            + "A"  # regular ASCII
            + "é"  # non-ASCII character
        )
        assert escape_text(text) == expected

    def test_escape_text_for_test(self):
        text = "\\" + '"' + ".:=" + "\x1f" + "\x7f" + "\u0100" + "A"
        expected = "\\u{5c}\\u{22}\\u{2e}\\u{3a}\\u{3d}" "\\u{1f}\\u{7f}\\u{100}A"
        assert escape_text_for_test(text) == expected

    def test_escape_name_path_text(self):
        text = "\\" + '"' + ".:=" + "\x1f" + "\x7f" + "\u0100" + "A"
        expected = "\\u{5c}\\u{22}\\u{2e}\\u{3a}\\u{3d}" "\\u{1f}\\u{7f}\\u{100}A"
        assert escape_name_path_text(text) == expected

    def test_unescape_text_success(self):
        content = (
            "\\\\"  # \\
            + '\\"'  # \"
            + "\\$"  # \$
            + "\\n"  # \n
            + "\\r"  # \r
            + "\\t"  # \t
            + "\\N"  # \N
            + "\\R"  # \R
            + "\\T"  # \T
            + "\\u0041"  # \uXXXX
            + "\\u{42}"  # \u{XX}
        )
        assert unescape_text(content) == "\\" + '"$\n\r\t\n\r\tAB'

    @pytest.mark.parametrize(
        "content,message",
        [
            pytest.param("\\", "Unexpected end after backslash", id="trailing-backslash"),
            pytest.param("\\u123", "Expected 4 hex digits", id="short-uni"),
            pytest.param("\\u{123456789}", "1-8 hex digits are allowed", id="uni2-too-long"),
            pytest.param("\\u0000", "Invalid Unicode code point", id="cp-zero"),
            pytest.param("\\u{110000}", "Invalid Unicode code point", id="cp-too-large"),
            pytest.param("\\uD800", "Invalid Unicode code point", id="surrogate"),
            pytest.param("\\q", "Unknown escape sequence", id="unknown"),
        ],
    )
    def test_unescape_text_error(self, content: str, message: str):
        with pytest.raises(UnescapeError) as exc:
            unescape_text(content)
        assert str(exc.value) == message

    def test_unescape_regex(self):
        assert unescape_regex("\\/") == "/"
        assert unescape_regex("\\\\") == "\\\\"
        assert unescape_regex("\\x") == "\\x"
        with pytest.raises(UnescapeError) as exc:
            unescape_regex("\\")
        assert exc.value.offset == 0
