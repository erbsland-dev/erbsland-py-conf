#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from erbsland.conf.error import ConfCharacterError, ConfLimitExceeded, ConfSyntaxError
from erbsland.conf.impl.limits import MAX_LINE_LENGTH, MAX_NAME_LENGTH
from erbsland.conf.impl.text_escape import UnescapeError, escape_name_path_text, unescape_text


class NameType(Enum):
    """Enumeration of the different name types."""

    REGULAR = auto()
    TEXT = auto()
    INDEX = auto()
    TEXT_INDEX = auto()


NameStorage = str | int


RE_INVALID_REGULAR_NAME_CHARACTERS = re.compile(r"(?i)[^a-z0-9_ ]")
RE_INVALID_DOUBLE_NAME_SEPARATOR = re.compile(r"[_ ]{2,}")

RE_VALID_NORMALIZED_REGULAR_NAME = re.compile(r"^@?[a-z][a-z0-9]*(_[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class Name:
    """Represent a single name.

    - A regular name is always converted into its normalized lower-case form.
    - A text name is kept as is.
    - An index name is neither normalized nor range checked.
    """

    _type: NameType
    _value: str | int

    def __post_init__(self):
        t, v = self._type, self._value
        if t in (NameType.REGULAR, NameType.TEXT):
            if not isinstance(v, str):
                raise ValueError(f"Invalid name type '{t}' for value '{v}': must be a string")
            if t is NameType.REGULAR:
                nv = self.normalize(v)
            else:
                self.validate_text(v)
                nv = v
        elif t in (NameType.INDEX, NameType.TEXT_INDEX):
            if not isinstance(v, int):
                raise ValueError(f"Invalid name type '{t}' for value '{v}': must be an integer")
            if v < 0:
                raise ValueError(f"Invalid name type '{t}' for value '{v}': must be a positive index")
            nv = v
        object.__setattr__(self, "_value", nv)

    @classmethod
    def create_regular(cls, name: str) -> Name:
        """
        Create a regular name from ``name``.

        :param name: The raw name text.
        :return: A ``Name`` instance of type ``REGULAR``.
        :raises ConfSyntaxError: If ``name`` violates the regular name rules.
        """

        cls.validate_regular_name(name)
        normalized = cls.normalize(name)
        return cls(NameType.REGULAR, normalized)

    @classmethod
    def create_text(cls, text: str) -> Name:
        """
        Create a text name from ``text``.

        :param text: The text of the name.
        :return: A ``Name`` instance of type ``TEXT``.
        """

        cls.validate_text(text)
        return cls(NameType.TEXT, text)

    @classmethod
    def create_index(cls, index: int) -> Name:
        """Create an index name from ``index``."""

        return cls(NameType.INDEX, index)

    @classmethod
    def create_text_index(cls, index: int) -> Name:
        """Create a text index name from ``index``."""

        return cls(NameType.TEXT_INDEX, index)

    @property
    def type(self) -> NameType:
        """Return the :class:`NameType` of this name."""

        return self._type

    def is_regular(self) -> bool:
        """Return ``True`` if this name is a regular name."""

        return self._type == NameType.REGULAR

    def is_text(self) -> bool:
        """Return ``True`` if this name is a text name."""

        return self._type == NameType.TEXT

    def is_index(self) -> bool:
        """Return ``True`` if this name is an index name."""

        return self._type == NameType.INDEX

    def is_text_index(self) -> bool:
        """Return ``True`` if this name is a text index."""

        return self._type == NameType.TEXT_INDEX

    def is_meta(self) -> bool:
        """Return ``True`` if this regular name starts with ``@``."""

        return self.is_regular() and isinstance(self._value, str) and self._value.startswith("@")

    def as_text(self) -> str:
        """
        Return the underlying string value.

        :return: The name text.
        :raises TypeError: If the name does not store text.
        """

        if self._type in (NameType.REGULAR, NameType.TEXT):
            return str(self._value)
        raise TypeError("Name is not a text-type")

    def as_index(self) -> int:
        """
        Return the underlying integer value.

        :return: The index value.
        :raises TypeError: If the name does not store an index.
        """

        if self._type in (NameType.INDEX, NameType.TEXT_INDEX):
            return int(self._value)
        raise TypeError("Name is not an index-type")

    def to_path_text(self) -> str:
        """Return the name formatted for use in a name path."""

        if self.is_regular():
            return self.as_text()
        if self.is_text():
            return f'"{escape_name_path_text(self.as_text())}"'
        if self.is_index():
            return f"[{self.as_index()}]"
        if self.is_text_index():
            return f'""[{self.as_index()}]'
        return ""

    @classmethod
    def normalize(cls, text: str) -> str:
        """Normalize ``text`` for use as a regular name."""

        text = text.replace(" ", "_").lower()
        if RE_VALID_NORMALIZED_REGULAR_NAME.match(text) is None:
            raise ValueError(f"Invalid regular name syntax: '{text}'")
        return text

    @classmethod
    def validate_text(cls, text: str) -> None:
        """Validate the syntax of a text name."""

        # API checks.
        if not text:
            raise ValueError("'text' must not be empty")
        if not isinstance(text, str):
            raise ValueError("Invalid text name: not a string")
        # Syntax checks.
        if len(text) > MAX_LINE_LENGTH:
            raise ConfLimitExceeded("The text name exceeds the maximum length")
        if "\x00" in text:
            raise ConfCharacterError("The text name contains a U+0000 character, which is not allowed")

    @classmethod
    def validate_regular_name(cls, name: str):
        """Validate the syntax of a regular name."""

        # API checks.
        if not name:
            raise ValueError("'name' must not be empty")
        if not isinstance(name, str):
            raise ValueError("'name' must be a string")
        # Syntax checks.
        if len(name) > MAX_NAME_LENGTH:
            raise ConfLimitExceeded("The name exceeds the maximum length")
        if name.startswith(" "):
            raise ConfSyntaxError("A name must not start with a space")
        if name.endswith(" ") or name.endswith("_"):
            raise ConfSyntaxError("A name must not end with a space or underscore")
        if match := RE_INVALID_REGULAR_NAME_CHARACTERS.search(name, (1 if name.startswith("@") else 0)):
            raise ConfSyntaxError(f"The name contains an unexpected character at position {match.start() + 1}")
        if name == "@":
            raise ConfSyntaxError("A meta-name must not be empty")
        assert len(name) >= 1
        if not name[1 if name.startswith("@") else 0].isalpha():
            raise ConfSyntaxError("A name must start with a letter")
        if match := RE_INVALID_DOUBLE_NAME_SEPARATOR.search(name):
            raise ConfSyntaxError(
                f"The name contains two consecutive underscores/spaces at position {match.start() + 1}"
            )

    @classmethod
    def from_document(cls, raw_text: str) -> Name:
        """
        Parse a name captured from a document.

        :param raw_text: The raw text captured from the document.
        :return: The parsed name.
        :raises ConfSyntaxError: If ``raw_text`` contains invalid syntax.
        """
        if not raw_text:
            raise ValueError("'raw_text' must not be empty")
        if not isinstance(raw_text, str):
            raise ValueError("'raw_text' must be a string")
        if raw_text.startswith('"'):
            if not raw_text.endswith('"'):
                raise ValueError("'raw_text' must end with '\"'")
            text = raw_text[1:-1]
            if not text:
                raise ConfSyntaxError("A text name must not be empty")
            try:
                text = unescape_text(text)
            except UnescapeError as error:
                raise ConfSyntaxError(f"Invalid escape sequence. {error}", offset=error.offset) from error
            return cls.create_text(text)
        return cls.create_regular(raw_text)

    def __str__(self):
        """Return the path representation of this name."""

        return self.to_path_text()

    def _sort_key(self) -> tuple[int, NameStorage]:
        return self._type.value, self._value

    def __lt__(self, other: Name) -> bool:
        """
        Compare two names for sorting.

        Sorting mixed element types is stable but undefined.
        """
        if not isinstance(other, Name):
            return NotImplemented
        return self._sort_key() < other._sort_key()


def RegularName(name: str) -> Name:
    """Construct a regular name."""
    return Name.create_regular(name)


def TextName(text: str) -> Name:
    """Construct a text name."""
    return Name.create_text(text)


META_NAME_VERSION = Name(NameType.REGULAR, "@version")
META_NAME_SIGNATURE = Name(NameType.REGULAR, "@signature")
META_NAME_INCLUDE = Name(NameType.REGULAR, "@include")
META_NAME_FEATURES = Name(NameType.REGULAR, "@features")
META_NAMES = [META_NAME_VERSION, META_NAME_SIGNATURE, META_NAME_INCLUDE, META_NAME_FEATURES]
