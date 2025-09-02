#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import enum
from pathlib import Path
from typing import Optional

from erbsland.conf.location import Location, Position
from erbsland.conf.source import Source, SourceIdentifier


class ErrorCategory(enum.Enum):
    """
    The error category is used to classify errors that occur during parsing or evaluation.
    """

    IO = ("IO", 1)
    """A problem occurred while reading data from an I/O stream."""
    ENCODING = ("Encoding", 2)
    """The document contains a problem with UTF-8 encoding."""
    UNEXPECTED_END = ("UnexpectedEnd", 3)
    """The document ended unexpectedly."""
    CHARACTER = ("Character", 4)
    """The document contains a control character that is not allowed."""
    SYNTAX = ("Syntax", 5)
    """The document has a syntax error."""
    LIMIT_EXCEEDED = ("LimitExceeded", 6)
    """The size of a name, text, or buffer exceeds the permitted limit."""
    NAME_CONFLICT = ("NameConflict", 7)
    """The same name has already been defined earlier in the document."""
    INDENTATION = ("Indentation", 8)
    """The indentation of a continued line does not match the previous line."""
    UNSUPPORTED = ("Unsupported", 9)
    """The requested feature/version is not supported by this parser."""
    SIGNATURE = ("Signature", 10)
    """The document’s signature was rejected."""
    ACCESS = ("Access", 11)
    """The document was rejected due to an access check."""
    VALIDATION = ("Validation", 12)
    """The document did not meet one of the validation rules."""
    INTERNAL = ("Internal", 99)
    """The parser encountered an unexpected internal error."""
    VALUE_NOT_FOUND = ("ValueNotFound", 101)
    """A value does not exist."""
    TYPE_MISMATCH = ("TypeMismatch", 102)
    """A value exists but has the wrong type for a conversion."""

    def __str__(self) -> str:
        """Return the name of the error category."""
        return self.value[0]

    def code(self) -> int:
        """Return the numeric code of the error category."""
        return self.value[1]


class ErrorOutput(enum.IntFlag):
    """Flags to control the output of errors."""

    FILENAME_ONLY = enum.auto()
    """Only display the filename, not the full path."""

    USE_LINES = enum.auto()
    """Break the error message into multiple lines."""

    DEFAULT = 0
    """Default format."""


class Error(Exception):
    """Represents a problem encountered while parsing a document or accessing a value."""

    __slots__ = ("_category", "_message", "_source", "_path", "_system_message", "_name_path", "_offset")

    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        *,
        source: Source | SourceIdentifier | Location | None = None,
        position: Position | None = None,
        path: Path | None = None,
        system_message: str | None = None,
        name_path: Optional["NamePath"] = None,
        offset: int | None = None,
    ):
        """
        Create a new error.

        :param category: The error category.
        :param message: Human-readable message describing the problem.
        :param source: Source, source identifier, or location of the error.
        :param position: Position within the source when ``source`` is provided.
        :param path: Path that caused the error.
        :param system_message: System-specific message describing the error.
        :param name_path: Name path of the value that caused the error.
        :param offset: Offset of the error from the start of the given source location.
        """
        super().__init__(message)
        self._category: ErrorCategory = category
        if not isinstance(self._category, ErrorCategory):
            raise ValueError("'category' must be an ErrorCategory object")
        self._message: str = message
        if not isinstance(self._message, str):
            raise ValueError("'message' must be a string")
        self._source: Location | None = None
        if source is not None:
            if position is not None and not isinstance(position, Position):
                raise ValueError("'position' must be a Position object")
            if isinstance(source, Location):
                self._source = source
            elif isinstance(source, SourceIdentifier):
                self._source = Location(source_identifier=source, position=position)
            elif isinstance(source, Source):
                self._source = Location(source_identifier=source.identifier, position=position)
            else:
                raise ValueError("'source' must be a Source, SourceIdentifier or Location object")
        if offset is not None:
            if not isinstance(offset, int):
                raise ValueError("'offset' must be an integer")
            if self._source is not None:
                self._source = self._source.with_offset(offset)
        self._offset = offset
        self._path: Path | None = path
        if self._path is not None and not isinstance(self._path, Path):
            raise ValueError("'path' must be a Path object.")
        self._system_message: str | None = system_message
        if self._system_message is not None and not isinstance(self._system_message, str):
            raise ValueError("'system_message' must be a string")
        self._name_path: Optional["NamePath"] = name_path

    @property
    def category(self) -> ErrorCategory:
        """Category of the error."""

        return self._category

    @property
    def code(self) -> int:
        """Numeric code of the error category."""

        return self._category.code()

    @property
    def message(self) -> str:
        """Human-readable error message."""

        return self._message

    @property
    def location(self) -> Location | None:
        """Location where the error occurred, if available."""

        return self._source

    @property
    def path(self) -> Path | None:
        """Path associated with the error, if any."""

        return self._path

    @property
    def system_message(self) -> str | None:
        """System-specific message describing the error, if any."""

        return self._system_message

    @property
    def name_path(self) -> Optional["NamePath"]:
        """Name path of the value that caused the error, if available."""

        return self._name_path

    @property
    def offset(self) -> int | None:
        """Offset of the error from the start of the given source location, if available."""

        return self._offset

    def to_text(self, output: ErrorOutput = ErrorOutput.DEFAULT) -> str:
        """Return a readable string representation of the error."""

        parts = [self._message]
        if self._source is not None:
            compact = bool(output & ErrorOutput.FILENAME_ONLY)
            source_text = self._source.to_text(compact=compact)
            parts.append(f"source={source_text}")
        if self._path is not None:
            if output & ErrorOutput.FILENAME_ONLY:
                path_text = self._path.name
            else:
                path_text = self._path.as_posix()
            parts.append(f"path={path_text}")
        if self._system_message:
            parts.append(f"system error={self._system_message}")
        if self._name_path is not None:
            parts.append(f"name-path={self._name_path}")
        if output & ErrorOutput.USE_LINES:
            return "\n    ".join(part.replace("=", ": ") for part in parts)
        return ", ".join(parts)

    def __str__(self) -> str:
        """Return a readable string representation of the error."""

        return self.to_text()

    def _all_args(self) -> dict[str, object]:
        """Return the initialization arguments used to create this error."""

        return {
            "category": self._category,
            "message": self._message,
            "source": self._source,
            "path": self._path,
            "system_message": self._system_message,
            "offset": self._offset,
            "name_path": self._name_path,
        }

    def with_source(self, source: Source | SourceIdentifier | Location) -> Error:
        """Return a copy of the error with ``source`` replaced."""

        args = self._all_args()
        args["source"] = source
        new_error = self.__class__(**args)
        assert new_error is not None
        assert isinstance(new_error, Error)
        return new_error

    def with_name_path(self, name_path: "NamePath") -> Error:
        """Return a copy of the error with ``name_path`` replaced."""

        args = self._all_args()
        args["name_path"] = name_path
        new_error = self.__class__(**args)
        assert new_error is not None
        assert isinstance(new_error, Error)
        return new_error


class ConfIoError(Error):
    """Error raised when an I/O operation fails."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.IO
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfEncodingError(Error):
    """Error raised when UTF-8 encoding is invalid."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.ENCODING
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfUnexpectedEnd(Error):
    """Error raised when a document ends unexpectedly."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.UNEXPECTED_END
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfCharacterError(Error):
    """Error raised for invalid control characters."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.CHARACTER
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfSyntaxError(Error):
    """Error raised for syntax errors in the document."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.SYNTAX
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfLimitExceeded(Error):
    """Error raised when a size limit is exceeded."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.LIMIT_EXCEEDED
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfNameConflict(Error):
    """Error raised on name conflicts."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.NAME_CONFLICT
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfIndentationError(Error):
    """Error raised for inconsistent indentation in continued lines."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.INDENTATION
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfUnsupportedError(Error):
    """Error raised for features not supported by the parser."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.UNSUPPORTED
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfSignatureError(Error):
    """Error raised when a document's signature is rejected."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.SIGNATURE
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfAccessError(Error):
    """Error raised when a document fails an access check."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.ACCESS
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfValidationError(Error):
    """Error raised when the document violates validation rules."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.VALIDATION
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfInternalError(Error):
    """Error raised when the parser encounters an unexpected internal issue."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.INTERNAL
        kwargs["message"] = message
        super().__init__(**kwargs)


class ConfValueNotFound(Error, KeyError):
    """Error raised when a requested value is missing."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.VALUE_NOT_FOUND
        kwargs["message"] = message
        super().__init__(**kwargs)
        if "name_path" in kwargs:
            name_path_str = kwargs["name_path"].to_text()
        else:
            name_path_str = "Unknown name path"
        self.args = (name_path_str,)


class ConfTypeMismatch(Error):
    """Error raised when a value has the wrong type for conversion."""

    def __init__(self, message: str, **kwargs):
        kwargs["category"] = ErrorCategory.TYPE_MISMATCH
        kwargs["message"] = message
        super().__init__(**kwargs)
