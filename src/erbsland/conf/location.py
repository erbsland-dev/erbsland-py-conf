#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0


from __future__ import annotations

from dataclasses import dataclass, field

from erbsland.conf.source import SourceIdentifier


@dataclass(frozen=True, slots=True, eq=True, order=True)
class Position:
    """Represent a position in a document."""

    line: int = -1
    """The line number or ``-1`` if undefined."""

    column: int = -1
    """The column number or ``-1`` if undefined."""

    character_index: int = -1
    """The character index or ``-1`` if undefined."""

    def is_undefined(self) -> bool:
        """Return ``True`` if the position is not defined."""

        return self.line < 0 or self.column < 0

    def __str__(self) -> str:
        """Return a user-friendly representation of the position."""

        if self.is_undefined():
            return "undefined"
        return f"{self.line}:{self.column}"

    def with_offset(self, offset: int) -> Position:
        """Return a new :class:`Position` shifted by ``offset`` columns."""

        if self.is_undefined():
            return Position()
        new_column = self.column
        if self.column >= 0:
            new_column += offset
        new_character_index = self.character_index
        if self.character_index >= 0:
            new_character_index += offset
        return Position(self.line, new_column, new_character_index)


@dataclass(frozen=True, slots=True, eq=True, order=True)
class Location:
    """Represent the location of an element in a document."""

    source_identifier: SourceIdentifier
    position: Position = field(default_factory=Position)

    def __str__(self) -> str:
        """Return a user-friendly representation of the location."""

        return self.to_text()

    def to_text(self, *, compact=False) -> str:
        """
        Return a user-friendly representation of the location.

        :param compact: If ``True``, return a compact representation.
        """
        source_id = self.source_identifier.to_text(compact=compact)
        return f"{source_id}:[{self.position}]"

    def with_offset(self, offset: int) -> Location:
        """Return a new :class:`Location` shifted by ``offset`` columns."""

        return Location(self.source_identifier, self.position.with_offset(offset))
