#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True, eq=True, order=True)
class SourceIdentifier:
    """
    Identify the origin of configuration data.

    :var name: Human-readable type of the source, e.g. ``"file"``.
    :var path: Location of the source, such as a file path.
    """

    name: str
    path: str

    FILE: ClassVar[str] = "file"  # The name for file sources.
    TEXT: ClassVar[str] = "text"  # The name for text sources.

    def __str__(self) -> str:
        return self.to_text()

    def __repr__(self) -> str:
        return f"SourceIdentifier({self.name}:{self.path})"

    def to_text(self, *, compact=False) -> str:
        """
        Return a user-friendly representation of the source identifier.

        :param compact: If ``True``, return a compact representation.
        """
        path = self.path
        if self.name == self.FILE and compact:
            path = path.replace("\\", "/").split("/")[-1]
        return f"{self.name}:{path}"


class Source(ABC):
    """Abstract base class for configuration sources."""

    @abstractmethod
    def open(self) -> None:
        """
        Open the source.

        :raises ConfIoError: If the source cannot be opened.
        """

    @abstractmethod
    def is_open(self) -> bool:
        """Return ``True`` if the source is open, ``False`` otherwise."""

    @abstractmethod
    def readline(self) -> str:
        """
        Read a single line from the source.

        :returns: The line read, or an empty string if the end of the source has been reached.
        :raises ConfIoError: If there was an IO problem reading the source.
        :raises ConfLimitExceeded: If the line exceeds :data:`MAX_LINE_LENGTH` bytes.
        :raises ConfEncodingError: If the data cannot be decoded as UTF-8.
        """

    @abstractmethod
    def start_digest_calculation(self):
        """
        Start or restart the digest calculation.

        The digest calculation shall start at the next ``readline()`` call.
        If the digest calculation is already running, it shall be restarted.

        :raises NotImplementedError: If the source does not support digest calculation.
        """

    @abstractmethod
    def get_digest(self) -> str:
        """
        Get the digest of the source.

        The document digest shall always be reported as a string in the format ``<algorithm> <digest>``.
        Algorithm is the lowercase name of the algorithm used, e.g. ``sha3-256``.
        Digest is the hexadecimal representation of the digest.

        :returns: The digest of the source or an empty string if digests are not supported.
        """

    @abstractmethod
    def close(self):
        """Close the source."""

    @property
    @abstractmethod
    def identifier(self) -> SourceIdentifier:
        """Return the :class:`SourceIdentifier` for this source."""

    def __repr__(self) -> str:
        return f"Source({self.identifier})"
