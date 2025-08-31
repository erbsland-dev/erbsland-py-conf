#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

import pytest

from erbsland.conf.error import ConfIoError, ConfLimitExceeded
from erbsland.conf.impl.limits import MAX_LINE_LENGTH
from erbsland.conf.impl.text_source import TextSource


class TestTextSourceReadline:
    def _open_source(self, text: str) -> TextSource:
        source = TextSource(text)
        source.open()
        return source

    def test_readline_without_open(self):
        source = TextSource("data")
        with pytest.raises(ConfIoError):
            source.readline()

    def test_short_ascii_line(self):
        source = self._open_source("hello\n")
        try:
            assert source.readline() == "hello\n"
        finally:
            source.close()

    def test_line_without_newline_exceeds_limit(self):
        text = "x" * (MAX_LINE_LENGTH + 20)
        source = self._open_source(text)
        try:
            with pytest.raises(ConfLimitExceeded):
                source.readline()
        finally:
            source.close()

    def test_char_count_exceeds_limit(self):
        text = "y" * (MAX_LINE_LENGTH + 1) + "\n"
        source = self._open_source(text)
        try:
            with pytest.raises(ConfLimitExceeded):
                source.readline()
        finally:
            source.close()

    def test_encoding_within_limit(self):
        text = ("é" * 1999) + "\n"
        source = self._open_source(text)
        try:
            assert source.readline() == text
        finally:
            source.close()

    def test_encoding_exceeds_limit(self):
        text = ("😀" * 1000) + "\n"
        source = self._open_source(text)
        try:
            with pytest.raises(ConfLimitExceeded):
                source.readline()
        finally:
            source.close()
