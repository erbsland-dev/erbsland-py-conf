#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from erbsland.conf.impl.text_source import TextSource
from erbsland.conf.impl.lexing.cursor import Cursor


class TestCursorRepr:
    def test_smoke_repr(self):
        source = TextSource("Hello World\n")
        source.open()
        cursor = Cursor(source)
        cursor.initialize()
        assert repr(cursor) == '1:1, up_next="Hello World\\n", line="Hello World\\n"'
