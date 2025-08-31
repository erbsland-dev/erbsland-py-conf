#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import re
from typing import NoReturn

from erbsland.conf.error import (
    ConfInternalError,
    Error,
    ConfCharacterError,
    ConfSyntaxError,
    ConfLimitExceeded,
    ConfUnexpectedEnd,
    ConfIndentationError,
    ConfUnsupportedError,
)
from erbsland.conf.impl.position_counter import PositionCounter
from erbsland.conf.impl.text_escape import escape_text
from erbsland.conf.impl.token import TokenStorageType, Token
from erbsland.conf.impl.token_type import TokenType
from erbsland.conf.location import Location, Position
from erbsland.conf.source import Source


# Match all illegal control characters.
RE_ILLEGAL_CTRL = re.compile(r"[\x00-\x08\x0A-\x1F\x7F-\xA0]")


class Cursor:
    """Cursor for the lexer that keeps track of the current position."""

    def __init__(self, source: Source, *, digest_enabled: bool = False):
        """Initialize the cursor with the given source."""

        self._source = source
        self._line: str | None = None
        self._position_counter = PositionCounter()
        self._indentation_pattern = ""
        if not self._source.is_open():
            raise ConfInternalError("Source must be open", source=self._source)
        self._digest_enabled = digest_enabled

    def __repr__(self):
        """Return a debug representation of the cursor."""

        max_chars = 16
        truncated_line = self._line[:max_chars]
        if len(self._line) > max_chars:
            truncated_line += "..."
        truncated_line = escape_text(truncated_line)
        index = self._position_counter.column - 1
        up_next = self._line[index : index + max_chars]
        if index + max_chars < len(self._line):
            up_next += "..."
        up_next = escape_text(up_next)
        return f'{self._position_counter}, up_next="{up_next}", line="{truncated_line}"'

    @property
    def position(self) -> Position:
        """Return the current position."""
        return self._position_counter.position()

    @property
    def indentation_pattern(self) -> str:
        """Pattern that defines the indentation of the current block."""

        return self._indentation_pattern

    @indentation_pattern.setter
    def indentation_pattern(self, value: str):
        """Set the indentation pattern for the current block."""

        self._indentation_pattern = value

    def initialize(self):
        """Prepare the cursor by reading the first line and skipping an optional BOM."""

        self._read_and_verify_line()  # Read the initial line.
        # Skip an optional UTF-8 BOM at the start of the document
        if self._line.startswith("\ufeff"):
            self._line = self._line[1:]

    def has_more_content(self) -> bool:
        """Return ``True`` if the source contains more content."""

        return self._line != ""

    def next_line(self):
        """Advance to the next line in the source."""

        self._read_and_verify_line()

    def expect_next_line(self, or_unexpected_end: str):
        """Advance to the next line or raise an unexpected end error."""

        self.next_line()
        if not self.has_more_content():
            self.unexpected_end(or_unexpected_end)

    def match(self, regex: re.Pattern) -> re.Match | None:
        """Return a match for ``regex`` starting at the current position."""

        return regex.match(self._line, self._position_counter.column - 1)

    def raw_text_to_eol(self) -> str:
        """
        Return the raw text from the current position to the end of the line.

        Primarily used for fast processing of multi-line text.
        """

        return self._line[self._position_counter.column - 1 :]

    def token(self, token_type: TokenType, raw_text: str, value: TokenStorageType = None) -> Token:
        """Create a token and advance the cursor by the length of ``raw_text``."""

        begin = self._position_counter.position()
        self._position_counter.advance(len(raw_text))
        end = self._position_counter.position()
        return Token(token_type=token_type, begin=begin, end=end, raw_text=raw_text, value=value)

    def error_token(self, raw_text: str, message: str) -> Token:
        """Convenience wrapper that creates an error token."""

        return self.token(TokenType.ERROR, raw_text, message)

    def character_error(self, message: str, **kwargs) -> NoReturn:
        """Raise a character-level error at the current location."""

        raise ConfCharacterError(message, source=self.create_location(), **kwargs)

    def syntax_error(self, message: str, **kwargs) -> NoReturn:
        """Raise a syntax error or unexpected end if at the line's end."""

        # If the cursor is at the end of the line, then the error is actually an unexpected end of the document.
        if self._position_counter.column == len(self._line) + 1:
            self.unexpected_end(message, **kwargs)
        raise ConfSyntaxError(message, source=self.create_location(), **kwargs)

    def limit_exceeded(self, message: str, **kwargs) -> NoReturn:
        """Raise a limit exceeded error."""

        raise ConfLimitExceeded(message, source=self.create_location(), **kwargs)

    def unexpected_end(self, message: str, **kwargs) -> NoReturn:
        """Raise an unexpected end error."""

        raise ConfUnexpectedEnd(message, source=self.create_location(), **kwargs)

    def indentation_error(self, message: str, **kwargs):
        """Raise an indentation error."""

        raise ConfIndentationError(message, source=self.create_location(), **kwargs)

    def unsupported(self, message: str, **kwargs):
        """Raise an unsupported feature error."""

        raise ConfUnsupportedError(message, source=self.create_location(), **kwargs)

    def create_location(self) -> Location:
        """Return a :class:`Location` for the current token start position."""

        return Location(self._source.identifier, self._position_counter.position())

    @property
    def digest_enabled(self) -> bool:
        """Return ``True`` if digest calculation is enabled."""
        return self._digest_enabled

    def start_digest_calculation(self) -> None:
        """Start the calculation of the digest at the next line."""
        try:
            self._source.start_digest_calculation()
        except NotImplementedError:
            self.unsupported("Digest calculation is not supported by this source.")

    def _read_and_verify_line(self):
        """Read the next line and check for illegal control characters."""

        self._line = self._source.readline()  # source checks maximum length and UTF-8 encoding
        if len(self._line) == 0:  # EOF
            return
        # Advance the position counter
        self._position_counter.advance_line()
        # Scan the content for illegal control characters.
        content = self._strip_line_break(self._line)
        if m := RE_ILLEGAL_CTRL.search(content):
            self._position_counter.advance(m.start())
            if m.group(0) == "\r":
                self.character_error("Misplaced carriage return")
            self.character_error("Illegal control character")

    def _strip_line_break(self, line: str) -> str:
        """Remove the trailing newline characters from ``line`` and validate it."""

        if line.endswith("\r\n"):
            return line[:-2]
        if line.endswith("\n"):
            return line[:-1]
        if line.endswith("\r"):  # It seems the new-line got cut off
            self.unexpected_end("Expected end of line. Missing new-line character after carriage return")
        return line
