#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


import hashlib
from pathlib import Path
from typing import Protocol

from erbsland.conf.error import ConfEncodingError, ConfIoError, ConfLimitExceeded
from erbsland.conf.impl.limits import MAX_LINE_LENGTH
from erbsland.conf.impl.stream_source import StreamSource
from erbsland.conf.source import SourceIdentifier


class SupportsHash(Protocol):
    def update(self, data: bytes) -> None: ...
    def digest(self) -> bytes: ...
    def hexdigest(self) -> str: ...
    @property
    def name(self) -> str: ...


class FileSource(StreamSource):
    """Read configuration text from a file path."""

    def __init__(self, path: str | Path):
        """
        Create a file source.

        :param path: File system path to the document.
        """

        super().__init__()
        if not isinstance(path, (str, Path)):
            raise TypeError("'path' must be a str or Path")
        self._path = Path(path).resolve(strict=False)
        self._identifier = SourceIdentifier(SourceIdentifier.FILE, self._path.as_posix())
        self._buffer = b""
        self._hash: SupportsHash | None = None

    def open(self) -> None:
        """
        Open the file for reading.

        :raises `ConfIoError: If the file cannot be opened.
        """

        try:
            self._stream = self._path.open("rb")
        except Exception as e:  # pragma: no cover - pass through message
            raise ConfIoError("Failed to open file", path=self._path, system_message=str(e)) from e

    def readline(self) -> str:
        """
        Read a single UTF-8 line from the file.

        :raises ConfIoError: If the stream is not open.
        :raises ConfLimitExceeded: If the line exceeds `MAX_LINE_LENGTH` bytes.
        :raises ConfEncodingError: If the data cannot be decoded as UTF-8.
        """

        if not self.is_open():
            raise ConfIoError("Trying to read from a closed stream")
        assert self._stream is not None
        # Read up to one more than the limit to detect overlong lines (in bytes)
        line_bytes = self._stream.readline(MAX_LINE_LENGTH + 1)
        if line_bytes == b"":  # EOF
            return ""
        if len(line_bytes) > MAX_LINE_LENGTH:  # Check byte-length limit
            raise ConfLimitExceeded(f"Line exceeds maximum length of {MAX_LINE_LENGTH} bytes")
        if self._hash is not None:
            self._hash.update(line_bytes)

        try:
            return line_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as e:  # pragma: no cover - rewrap as custom error
            raise ConfEncodingError(str(e))

    def start_digest_calculation(self):
        self._hash = hashlib.new("sha3-256")

    def get_digest(self) -> str:
        return f"{self._hash.name.lower()} {self._hash.hexdigest()}"
