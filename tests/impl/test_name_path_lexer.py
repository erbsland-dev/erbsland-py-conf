#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import re

import pytest

from erbsland.conf.error import ConfCharacterError, ConfLimitExceeded, ConfSyntaxError
from erbsland.conf.impl.limits import MAX_LINE_LENGTH, MAX_NAME_PATH_LENGTH
from erbsland.conf.impl.name_path_lexer import NamePathLexer


@pytest.mark.parametrize(
    "text, exc, match",
    [
        pytest.param("a\x01b", ConfCharacterError, "unescaped control character", id="control-character"),
        pytest.param(
            ".".join(f"n{i}" for i in range(MAX_NAME_PATH_LENGTH + 1)),
            ConfLimitExceeded,
            "must not exceed",
            id="too-many-names",
        ),
        pytest.param('[0]"b"', ConfSyntaxError, "separator", id="missing-separator"),
        pytest.param('"\\', ConfSyntaxError, "Unterminated quoted string", id="unterminated-escape"),
    ],
)
def test_name_path_lexer_parse_errors(text, exc, match):
    with pytest.raises(exc, match=match):
        NamePathLexer.parse(text)


def test_parse_quoted_name_too_long():
    long_text = "a" * (MAX_LINE_LENGTH + 1)
    lexer = NamePathLexer(f'"{long_text}"')
    with pytest.raises(ConfLimitExceeded, match="exceeds the maximum length"):
        lexer._parse_quoted()


def test_read_index_empty(monkeypatch):
    monkeypatch.setattr(NamePathLexer, "RE_INDEX", re.compile(r"\[\s*([0-9'\s]*)\s*\]"))
    lexer = NamePathLexer("[]")
    with pytest.raises(ConfSyntaxError, match="Index must not be empty"):
        lexer._read_index()
