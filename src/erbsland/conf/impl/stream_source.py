#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from abc import ABC, abstractmethod

from erbsland.conf.source import Source, SourceIdentifier


class StreamSource(Source, ABC):
    """Base class for sources backed by a file-like stream."""

    def __init__(self) -> None:
        """Initialize without an open stream."""

        self._stream = None
        self._identifier: SourceIdentifier | None = None

    def is_open(self) -> bool:
        """Return ``True`` if a stream is currently attached what means that this source is open."""

        return self._stream is not None

    @abstractmethod
    def readline(self) -> str:
        """Read a single line from the underlying stream."""

    def close(self) -> None:
        """Close the underlying stream if it is open."""

        if self._stream is not None:
            self._stream.close()
            self._stream = None

    @property
    def identifier(self) -> SourceIdentifier:
        """Identifier of the source, used in diagnostics."""

        return self._identifier
