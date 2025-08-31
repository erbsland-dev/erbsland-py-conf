#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from io import StringIO

from erbsland.conf.error import ConfLimitExceeded, ConfIoError
from erbsland.conf.impl.limits import MAX_LINE_LENGTH
from erbsland.conf.impl.stream_source import StreamSource
from erbsland.conf.source import SourceIdentifier


class TextSource(StreamSource):
    """
    Stream source backed by a string.

    This class allows the parser to read data from a plain Python string instead of an external file-like object.
    """

    def __init__(self, text: str):
        """
        Create a new :class:`TextSource` from *text*.

        :param text: The textual content to expose through the streaming interface.
        """

        if not isinstance(text, str):
            raise TypeError(f"'text' must be a string, not {type(text)}")
        super().__init__()
        self._text = text
        self._identifier = SourceIdentifier(SourceIdentifier.TEXT, "")

    def open(self):
        """Open the source and return a readable stream."""

        self._stream = StringIO(self._text)
        return self._stream

    def readline(self) -> str:
        """
        Read a single line from the source.

        :raises ConfIoError: If the stream has not been opened.
        :raises ConfLimitExceeded: If a line exceeds :data:`MAX_LINE_LENGTH` bytes.
        """

        if not self.is_open():
            raise ConfIoError("Trying to read from a closed stream")

        assert self._stream is not None  # for type checkers
        max_bytes = MAX_LINE_LENGTH + 16
        text = self._stream.readline(max_bytes)
        char_count = len(text)
        if char_count == max_bytes and not text.endswith(("\n", "\r")):
            raise ConfLimitExceeded(f"Line exceeds maximum length of {MAX_LINE_LENGTH} bytes")
        max_utf8_length = char_count * 4
        if max_utf8_length <= MAX_LINE_LENGTH:
            return text
        if char_count > MAX_LINE_LENGTH:
            raise ConfLimitExceeded(f"Line exceeds maximum length of {MAX_LINE_LENGTH} bytes")
        encoded = text.encode("utf-8")  # Check the UTF-8 encoding
        if len(encoded) > MAX_LINE_LENGTH:
            raise ConfLimitExceeded(f"Line exceeds maximum length of {MAX_LINE_LENGTH} bytes")
        return text

    def start_digest_calculation(self):
        raise NotImplementedError("Text sources do not support digest calculation")

    def get_digest(self) -> str:
        return ""
