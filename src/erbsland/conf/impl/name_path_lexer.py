#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re

from erbsland.conf.error import ConfSyntaxError, ConfLimitExceeded, ConfCharacterError
from erbsland.conf.impl.lexing.cursor import RE_ILLEGAL_CTRL
from erbsland.conf.impl.limits import (
    MAX_LINE_LENGTH,
    MAX_NAME_LENGTH,
    MAX_NAME_PATH_LENGTH,
)
from erbsland.conf.impl.text_escape import unescape_text, UnescapeError
from erbsland.conf.name import Name


class NamePathLexer:
    """
    Lexer for name path strings.

    Converts a textual representation of a name path into a list of :class:`Name` objects.
    The logic lives here to keep :class:`erbsland.conf.name_path.NamePath` clean and easy to read.
    """

    RE_INDEX = re.compile(r"\[\s*([0-9][0-9'\s]*)\s*\]")

    def __init__(self, text: str) -> None:
        self.text = text
        self.length = len(text)
        self.pos = 0
        self.prev: str | None = None  # "name", "index", "text_index", "dot"
        self.names: list[Name] = []

    @classmethod
    def parse(cls, text: str) -> list[Name]:
        if not text:
            return []
        lexer = cls(text)
        lexer._validate_source()
        lexer._lex()
        return lexer.names

    # --- Top level parsing logic ---

    def _validate_source(self) -> None:
        if self.length > MAX_LINE_LENGTH:
            raise ConfLimitExceeded(f"The name path exceeds the maximum length of {MAX_LINE_LENGTH} characters")
        if match := RE_ILLEGAL_CTRL.search(self.text):
            if match.group() in ["\r", "\n"]:
                raise ConfSyntaxError(
                    f"The name path contains an unescaped line-break character at position {match.start()}"
                )
            raise ConfCharacterError(
                f"The name path contains an unescaped control character at position {match.start()}"
            )

    def _lex(self) -> None:
        while True:
            self._consume_whitespace()
            if self.pos >= self.length:
                break
            ch = self.text[self.pos]
            if ch == ".":
                self._parse_dot()
            elif ch == "[":
                self._parse_index()
            elif ch == '"':
                self._parse_quoted()
            else:
                self._parse_regular()
            if len(self.names) > MAX_NAME_PATH_LENGTH:
                raise ConfLimitExceeded(f"A name path must not exceed {MAX_NAME_PATH_LENGTH} names")
        self._consume_whitespace()
        if self.pos != self.length or self.prev == "dot":
            raise ConfSyntaxError("Invalid name path")

    def _consume_whitespace(self) -> None:
        while self.pos < self.length and self.text[self.pos] in " \t":
            self.pos += 1

    # --- Token parsers ---

    def _parse_dot(self) -> None:
        if self.prev in (None, "dot"):
            raise ConfSyntaxError("Two consecutive name path separators are not allowed")
        self.prev = "dot"
        self.pos += 1

    def _parse_index(self) -> None:
        if self.prev in ("dot", "text_index"):
            raise ConfSyntaxError("An index must not follow a path separator")
        index = self._read_index()
        self.names.append(Name.create_index(index))
        self.prev = "index"

    def _parse_quoted(self) -> None:
        if self.prev not in (None, "dot"):
            raise ConfSyntaxError("Expected a name path separator before another name element")
        content = self._read_quoted_content()
        if content == "":
            if self.pos < self.length and self.text[self.pos] == "[":
                index = self._read_index()
                self.names.append(Name.create_text_index(index))
                self.prev = "text_index"
            else:
                raise ConfSyntaxError("Expected a name or index")
        else:
            if len(content) > MAX_LINE_LENGTH:
                raise ConfLimitExceeded(f"The text name exceeds the maximum length of {MAX_LINE_LENGTH} characters")
            self.names.append(Name.create_text(content))
            self.prev = "name"

    def _parse_regular(self) -> None:
        if self.prev not in (None, "dot"):
            raise ConfSyntaxError("Expected a name path separator before another name element")
        end = self.pos
        while end < self.length and self.text[end] not in ".[":
            end += 1
        segment = self.text[self.pos : end].rstrip(" \t")
        if not segment or len(segment.strip()) > MAX_NAME_LENGTH:
            raise ConfLimitExceeded("The name exceeds the maximum length")
        self.names.append(Name.create_regular(segment))
        self.pos = end
        self.prev = "name"

    # --- Helpers ---

    def _read_index(self) -> int:
        match = self.RE_INDEX.match(self.text, self.pos)
        if not match:
            raise ConfSyntaxError("The index has an invalid format")
        number = match.group(1).replace("'", "").replace(" ", "")
        if not number:
            raise ConfSyntaxError("Index must not be empty")
        self.pos = match.end()
        return int(number)

    def _read_quoted_content(self) -> str:
        # Skip opening quote
        self.pos += 1
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '"':
                raw = self.text[start : self.pos]
                self.pos += 1
                try:
                    return unescape_text(raw)
                except UnescapeError as error:
                    raise ConfSyntaxError(f"Invalid escape sequence. {error}", offset=error.offset) from error
            if ch == "\\":
                self.pos += 1
                if self.pos >= self.length:
                    break
            self.pos += 1
        raise ConfSyntaxError("Unterminated quoted string")
