#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from typing import Union

from erbsland.conf.impl.name_path_lexer import NamePathLexer
from erbsland.conf.name import Name


class NamePath:
    """Represent a name path pointing to a value."""

    def __init__(self, path: Union[Name, list[Name], None] = None):
        """
        Create a new :class:`NamePath`.

        :param path: Either a single :class:`Name` or a list of names.
        """

        self._path: list[Name] = []
        if path is not None:
            if isinstance(path, Name):
                self._path.append(path)
            elif isinstance(path, list):
                for name in path:
                    if not isinstance(name, Name):
                        raise ValueError(f"Invalid name in path: {name}")
                self._path = path

    def __iter__(self):
        """Iterate over all names in the path."""

        return iter(self._path)

    def __len__(self) -> int:
        """Return the number of segments in the path."""

        return len(self._path)

    def __getitem__(self, index_or_slice: int | slice) -> Name | NamePath:
        """
        Return a name or sub-path at ``index_or_slice``.

        :param index_or_slice: The index or slice to access.
        :return: The :class:`Name` or :class:`NamePath` at the given position.
        :raises TypeError: If ``index_or_slice`` is not an ``int`` or ``slice``.
        """

        if not isinstance(index_or_slice, (int, slice)):
            raise TypeError(f"Index must be an integer or slice, not {type(index_or_slice)}")
        if isinstance(index_or_slice, int):
            return self._path[index_or_slice]
        return NamePath(self._path[index_or_slice])

    def __eq__(self, other: NamePath) -> bool:
        """Return ``True`` if this path equals ``other``."""

        if not isinstance(other, NamePath):
            return NotImplemented
        return self._path == other._path

    def __lt__(self, other: NamePath) -> bool:
        """Return ``True`` if this path sorts before ``other``."""

        if not isinstance(other, NamePath):
            return NotImplemented
        return self._path < other._path

    def __hash__(self) -> int:
        """Return a hash based on the contained names."""

        return hash(tuple(self._path))

    def __truediv__(self, other: Name | NamePath | str) -> NamePath:
        """
        Return a new path with ``other`` appended.

        :param other: A :class:`Name`, another :class:`NamePath` or a string to append.
        :return: The combined :class:`NamePath`.
        :raises TypeError: If ``other`` has an unsupported type.
        """

        if isinstance(other, str):
            return NamePath(self._path + [NamePath.from_text(other)])
        if isinstance(other, NamePath):
            return NamePath(self._path + other._path)
        if isinstance(other, Name):
            return NamePath(self._path + [other])
        raise TypeError(f"Unsupported type for path segment: {type(other)}")

    def copy(self) -> NamePath:
        """Return a shallow copy of this path."""

        return NamePath(self._path.copy())

    def __copy__(self):
        """Return a shallow copy of this path."""

        return self.copy()

    def append(self, other: Name | NamePath | str) -> None:
        """Append ``other`` to this path.

        :param other: A :class:`Name`, another :class:`NamePath` or a string to append.
        :raises TypeError: If ``other`` has an unsupported type.
        """

        if isinstance(other, str):
            path = NamePath.from_text(other)
        elif isinstance(other, Name):
            path = NamePath([other])
        elif isinstance(other, NamePath):
            path = other
        else:
            raise TypeError(f"Unsupported type for path segment: {type(other)}")
        self._path.extend(path._path)

    def to_text(self) -> str:
        """Return the path formatted as text."""

        parts: list[str] = []
        first = True
        for name in self._path:
            if not first and not name.is_index():
                parts.append(".")
            parts.append(name.to_path_text())
            first = False
        return "".join(parts)

    @classmethod
    def from_text(cls, text: str) -> NamePath:
        r"""
        Parse a name path from ``text``.

        A path is a sequence of segments separated by dots. Segments may be regular names (``foo``),
        numeric indices (``[0]``), quoted text names (``"foo"``) or text indices (``""[0]``).
        Spacing around segments is ignored.
        Quoted names use standard backslash escapes such as ``"``, ``\n`` or ``\u``.

        :param text: The text to parse.
        :return: The parsed path.
        :raises ConfSyntaxError: If ``text`` contains invalid syntax.
        """

        names = NamePathLexer.parse(text)
        return cls(names)

    def __str__(self) -> str:
        """Return the text representation of this path."""

        return self.to_text()

    def __repr__(self) -> str:
        """Return a debug representation of this path."""

        return f"NamePath({self.to_text()})"
